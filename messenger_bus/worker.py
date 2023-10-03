import asyncio
import json
import logging

import pika
from .service_container import message_bus

FORMAT = '%(asctime)s %(levelname)s:%(name)s:%(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('messenger')
logger.setLevel(logging.DEBUG)

class WorkerInterface:

    def __init__(self):
        pass

    def _connect(self):
        """ etablit la connection avec le serveur AMQP"""
        raise NotImplementedError

    def consume(self):
        """ ecoute les nouveaux messages et les dispatch dans le bus"""
        raise NotImplementedError

    def _on_message(self, ch, method, properties, body):
        """ traite la reception de nouveaux message """
        raise NotImplementedError

class DefaultWorker(WorkerInterface):

    def __init__(self):
        super(DefaultWorker, self).__init__()
        self.connection = None
        self.channel = None
        self.queue_name = None
        self.exchange_name = None

    def _connect(self):
        self.connection, self.channel, self.queue_name, self.exchange_name = createConnection()
        return self

    async def consume(self):
        # result = channel.queue_declare('', exclusive=True, durable=True)
        # queue_name = result.method.queue
        max_attempts = 100

        while True:
            try:
                self._connect()
                self.channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_message, auto_ack=False)

                try:
                    self.channel.start_consuming()
                except KeyboardInterrupt:
                    self.channel.stop_consuming()
                    if self.connection:
                        self.connection.close()
                    break

            except pika.exceptions.ConnectionClosedByBroker:
                # Uncomment this to make the example not attempt recovery
                # from server-initiated connection closure, including
                # when the node is stopped cleanly
                # except pika.exceptions.ConnectionClosedByBroker:
                #     pass
                logger.debug("Impossible de se connecter au serveur")

            except pika.exceptions.AMQPConnectionError as e:
                logger.debug("Impossible de se connecter au serveur")
                # Do not recover on channel errors

            except pika.exceptions.AMQPChannelError as err:
                logger.debug("Caught a channel error: {}, stopping...".format(err))
                print("Caught a channel error: {}, stopping...".format(err))

            except Exception as e:
                logger.debug(e)
                continue
            finally:
                logger.debug("Reconnection du service...")

            await asyncio.sleep(1)

            #max_attempts -= 1

    def _on_message(self,ch, method, properties, body):
        try:
            print(" [x] %r:%r" % (method.routing_key, body))
            # task = asyncio.create_task(message_bus.receive(body.decode(),properties.__dict__))
            try:
                message_bus.receive(body.decode(),properties.__dict__)
            except Exception as e:
                logger.debug(e)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.debug(e)
            ch.basic_ack(delivery_tag=method.delivery_tag)

            try:
                message = json.loads(body.decode())
                headers = {"x-retry":True, "x-retry-count":0}

                if "x-retry-count" in properties.headers:
                    headers["x-retry-count"] = properties.headers["x-retry-count"] + 1

                message_bus.dispatch(message, method.routing_key,{"headers":headers})
            except:
                pass