import json
import logging
import sys

from .message_handler import process_handlers
from .stamp import (SignatureStamp, TransportStamp, BusStamp, StopPropagationStamp)
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
       super().__init__(1)

    def handle(self,envelope:Envelope, stack) -> Envelope:

        if envelope.last("SendingStamp"):
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
        super().__init__(-1)

    def handle(self,envelope:Envelope, stack) -> Envelope:

        if envelope.last("SendingStamp") and not envelope.last("DispatchAfterCurrentBusStamp"):
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

    def handle(self,envelope:Envelope, stack) -> Envelope:

        if envelope.last("ReceivedStamp") and not envelope.last("SkipReceivedStamp"):
            envelope = process_handlers(envelope)

        return stack.next().handle(envelope,stack)


class DispatchAfterCurrentBusMiddleware(MiddlewareInterface):
    """
    middleware en charge de l'execution d'un bus apres la fin de traitement du bus en cours
    il faut arreter immediatement le traitement des autres middlewares
    enregistrer l'envelope et le redispatcher a la fin du bus
    """
    def __init__(self):
        super().__init__(2)

    def handle(self,envelope:Envelope, stack) -> Envelope:

        if envelope.last("DispatchAfterCurrentBusStamp") and envelope.last("SendingStamp"):
            stamp:BusStamp = envelope.last("BusStamp")
            stamp.bus.add_event(envelope)
            return envelope

        return stack.next().handle(envelope, stack)



class MiddlewareManager:
    """
    le middleware manager, il sert a orchestrer tout les middlewares
    """
    def __init__(self, middlewares: list=[]):
        self._middlewares = []
        self.currentEnvelope = None
        self.iterable = None

        ms:list = [
            DispatchAfterCurrentBusMiddleware(),
            SendMiddleware(),
            MessageHandlerMiddleware(),
        ] + middlewares

        for middleware in ms:
            if middleware.priority <= 10 and type(middleware) not in [SendMiddleware, MessageHandlerMiddleware, DispatchAfterCurrentBusMiddleware]:
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
            # if not self.iterable:
            #     raise StopIteration
            middleware = next(self.iterable)
        except StopIteration as e:
            middleware = EndMiddleware()

        return middleware

    def run(self, envelope: Envelope) -> Envelope:
        self.currentEnvelope = envelope
        self.iterable = iter(self._middlewares)
        envelope = self.next().handle(envelope, self)

        try:
            next(self.iterable)
            envelope = envelope.update(StopPropagationStamp())
        except:
            pass
        # finally:
        #     self.iterable = None

        return envelope
