
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

class StampInterface:
    pass

class NonSendableStampInterface(StampInterface):
    pass

class AmqpStamp(NonSendableStampInterface):
    def __init__(self,  routing_key:str = "",  flags:int = 2, attributes:AMQPBasicProperties = AMQPBasicProperties()):
        super().__init__()
        self.routing_key = routing_key
        self.flags = flags
        self.attributes = attributes
        self.is_retryAttempt = False

class SendingStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope est en cours d'envoi
    """
    def __init__(self):
        super().__init__()

class SentStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope a bien été envoyé
    """
    def __init__(self):
        super().__init__()

class NotSentStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope n'a pas pu être envoyé
    """
    def __init__(self):
        super().__init__()

class ReceivedStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope a bien été recu
    """
    def __init__(self):
        super().__init__()

class SkipReceivedStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope doit être bypassé le middleware MessageHandlerMiddleware
    """
    def __init__(self):
        super().__init__()



class DispatchAfterCurrentBusStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope doit etre correctement  traité par un handler
    avant de le passer au prochain handler
    """
    def __init__(self):
        super().__init__()

class StopPropagationStamp(NonSendableStampInterface):
    """
    Stamp indiquant que l'envelope une fin prématuré dans un middleware
    """
    def __init__(self):
        super().__init__()

class BusStamp(NonSendableStampInterface):
    """
    Stamp indiquant le bus par lequel transit le message
    """
    def __init__(self,bus):
        super(BusStamp, self).__init__()
        self.bus = bus


class TransportStamp(NonSendableStampInterface):
    """
    Stamp indiquant le transport par lequel le message est envoyé
    """
    def __init__(self,transport, attributes:dict={}):
        super(TransportStamp, self).__init__()
        self.transport = transport
        self.attributes = attributes

class ResultStamp(NonSendableStampInterface):
    """
    Stamp qui stock le resultat d'une action envoyé dans le bus
    """
    def __init__(self,result):
        super(ResultStamp, self).__init__()
        self.result = result

class SignatureStamp(StampInterface):
    """
    Stamp ajoutant la signature numeric des données transportées
    """
    def __init__(self, producerId:str, payloadToken:str):
        super(SignatureStamp, self).__init__()
        self.producerId = producerId
        self.payloadToken = payloadToken