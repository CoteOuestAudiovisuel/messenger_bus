class MessengerBusNotSentException(Exception):

    def __init__(self,body,properties):
        self.body = body
        self.properties = properties