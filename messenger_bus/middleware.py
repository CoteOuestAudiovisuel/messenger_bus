import logging

from .message_handler import process_handlers
from .stamp import (SignatureStamp, TransportStamp)
from .envelope import (Envelope)
import hmac

FORMAT = '%(asctime)s %(levelname)s:%(name)s:%(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('messenger')
logger.setLevel(logging.DEBUG)




class MiddlewareInterface:
    """
    middleware permettant d'intercepter les envelopes en envoi comme en reception
    """
    def __init__(self, priority:int = 100):
       self.priority = priority

    def handle(self,envelope:Envelope, stack) -> Envelope:
        raise NotImplementedError

class EndMiddleware(MiddlewareInterface):
    """
    marque la fin des middlewares
    """
    def __init__(self):
       super().__init__()

    def handle(self,envelope:Envelope, stack) -> Envelope:
        return envelope

class SignatureMiddleware(MiddlewareInterface):
    """
    ajoute une signature electronique aux données envoyées
    """
    def __init__(self):
       super().__init__()

    def handle(self,envelope:Envelope, stack) -> Envelope:
        stamp:SignatureStamp = envelope.last("SignatureStamp")
        if not stamp:
            body = str(envelope.message)
            token = hmac.digest(b"zakes25649", body.encode(), digest="sha256").hex()

            envelope = envelope.update(SignatureStamp("myProducerId",token))

        return stack.next().handle(envelope, stack)

class SendMiddleware(MiddlewareInterface):
    """
    middleware en charge de l'envoi des messages
    """
    def __init__(self):
        super().__init__(0)

    def handle(self,envelope:Envelope, stack) -> Envelope:

        if envelope.last("SendingStamp"):
            stamp_transport: TransportStamp = envelope.last("TransportStamp")
            transport = stamp_transport.transport
            envelope = transport.produce(envelope)

        return stack.next().handle(envelope,stack)

class MessageHandlerMiddleware(MiddlewareInterface):
    """
    middleware en charge de l'execution du code apres reception d'un message
    """
    def __init__(self):
        super().__init__(0)
        pass

    def handle(self,envelope:Envelope, stack) -> Envelope:

        if envelope.last("ReceivedStamp"):
            envelope = process_handlers(envelope)

        return stack.next().handle(envelope,stack)

class MiddlewareManager:
    """
    le middleware manager, il sert a orchestrer tout les middlewares
    """
    def __init__(self, middlewares: list):
        self._middlewares = []
        self.currentEnvelope = None
        self.iterable = None

        middlewares += [
            SendMiddleware(),
            MessageHandlerMiddleware(),
        ]

        for middleware in middlewares:
            if middleware.priority <= 10 and type(middleware) not in [SendMiddleware, MessageHandlerMiddleware]:
                middleware.priority = 11
            self.add(middleware)

        self._middlewares = sorted(self._middlewares, key=lambda el: el.priority, reverse=True)

    def add(self, middleware: MiddlewareInterface):
        """ ajoute un middleware au manager"""
        try:
            self._middlewares.index(middleware)
        except ValueError as e:
            self._middlewares.append(middleware)
        return self

    def remove(self, middleware: MiddlewareInterface):
        """ supprime un middleware au manager"""
        try:
            self._middlewares.remove(middleware)
        except ValueError as e:
            pass
        return self

    def next(self) -> MiddlewareInterface:
        """
        retourne le prochain
        :return:
        """
        middleware = None
        try:
            middleware = next(self.iterable)
        except StopIteration as e:
            middleware = EndMiddleware()

        return middleware

    def run(self, envelope: Envelope) -> Envelope:
        self.currentEnvelope = envelope
        self.iterable = iter(self._middlewares)
        self.next().handle(envelope, self)
        return envelope
