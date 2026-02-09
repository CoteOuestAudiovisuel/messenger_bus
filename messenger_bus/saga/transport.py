import json
import pika
from pika.adapters.blocking_connection import BlockingChannel


class AMQPBasicProperties:

    def __init__(self):
        self.content_type = None
        self.content_encoding = None
        self.headers = {}
        self.delivery_mode = 2
        self.priority = 0
        self.correlation_id = None
        self.reply_to = None
        self.expiration = None
        self.message_id = None
        self.timestamp = 0
        self.type = None
        self.user_id = None
        self.app_id = None
        self.cluster_id = None


class SagaTransportInterface:

    def __init__(self):
        pass

    async def connect(self,*args,**kwargs):
        """ permet de se connecter au serveur"""
        raise NotImplementedError

    async def disconnect(self,*args,**kwargs):
        """ permet de se deconnecter du serveur"""
        raise NotImplementedError

    async def dispatch(self, message,options):
        """ permet d'envoyer un message dans le bus"""
        raise NotImplementedError

    async def listen(self, queue_name: str, timeout:int = 30):
        raise NotImplementedError

class SagaRabbitMQTransport(SagaTransportInterface):
    def __init__(self, dsn:str):
        super().__init__()

        self._dsn = dsn
        self._connection = None
        self._channel = None
        self._priv_queue:str = ""

    async def connect(self,binding_keys):
        if self._connection and self._channel:
            return self._connection, self._channel

        node1 = pika.URLParameters(self._dsn)
        nodes = [node1]
        connection = pika.BlockingConnection(parameters=node1)

        channel = connection.channel()
        channel.confirm_delivery()

        channel.exchange_declare(
            exchange="saga",
            exchange_type="direct",
            durable=True
        )

        rst = channel.queue_declare(queue="", exclusive=True)
        self._priv_queue = rst.method.queue

        for binding_key in binding_keys.split(" "):
            channel.queue_bind(
                exchange="saga",
                queue=self._priv_queue,
                routing_key=binding_key
            )

        self._connection, self._channel = connection, channel


    async def disconnect(self):
        #self._channel.cancel()
        self._connection.close()

    async def dispatch(self, message, options: dict):
        """ envoi un message """

        routing_key = options.get("routing_key", "")
        properties = options.get("properties", {})


        attr = AMQPBasicProperties()
        attr.content_type = properties["content_type"] if "content_type" in properties else attr.content_type
        attr.content_encoding = properties[
            "content_encoding"] if "content_encoding" in properties else attr.content_encoding
        attr.headers = properties["headers"] if "headers" in properties else attr.headers
        attr.delivery_mode = properties["delivery_mode"] if "delivery_mode" in properties else attr.delivery_mode
        attr.priority = properties["priority"] if "priority" in properties else attr.priority
        attr.correlation_id = properties["correlation_id"] if "correlation_id" in properties else attr.correlation_id
        attr.reply_to = properties["reply_to"] if "reply_to" in properties else attr.reply_to
        attr.expiration = properties["expiration"] if "expiration" in properties else attr.expiration
        attr.message_id = properties["message_id"] if "message_id" in properties else attr.message_id
        attr.timestamp = properties["timestamp"] if "timestamp" in properties else attr.timestamp
        attr.type = properties["type"] if "type" in properties else attr.type
        attr.user_id = properties["user_id"] if "user_id" in properties else attr.user_id
        attr.app_id = properties["app_id"] if "app_id" in properties else attr.app_id
        attr.cluster_id = properties["cluster_id"] if "cluster_id" in properties else attr.cluster_id


        properties = attr.__dict__
        body = json.dumps(message)

        properties = {k: v for k, v in properties.items() if v != None}

        self._channel.basic_publish(
            exchange="saga",
            routing_key=routing_key,
            body=body.encode(),
            properties=pika.BasicProperties(**properties)
        )

    async def listen(self, queue_name:str, timeout:int = 30):

        message = None
        # channel:BlockingChannel = self._connection.channel()
        # channel.confirm_delivery()
        self._channel.queue_declare(queue=queue_name, exclusive=True)

        for method, properties, body in self._channel.consume(queue_name, inactivity_timeout=timeout):
            # Display the message parts and acknowledge the message
            print(method,properties,body)
            self._channel.basic_ack(method.delivery_tag)

            # Escape out of the loop after 10 messages
            if method.delivery_tag == 10:
                break

            message = json.loads(body.decode())
            break

        self._channel.cancel()
        return message