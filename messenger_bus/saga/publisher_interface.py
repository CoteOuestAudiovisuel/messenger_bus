from ..bus import MessageBusInterface
from ..stamp import DispatchAfterCurrentBusStamp, EntityStamp

from .stamp import SagaStamp


class PublisherInterface:

    def __init__(self, bus:MessageBusInterface):
        self._bus = bus

    def publish(self, saga,command, routing_key=None, properties=None):
        raise NotImplementedError


class SagaCommandPublisherInterface(PublisherInterface):

    def __init__(self, bus: MessageBusInterface):
        super().__init__(bus)

    def publish(self, saga, command, routing_key=None, properties={}):

        obj = {
            "stamps": [
                SagaStamp(saga_id=saga.uuid),
                DispatchAfterCurrentBusStamp()
            ],
            "bus": "event.bus",
            "properties":properties
        }

        if routing_key:
            obj["routing_key"] = routing_key

        r = self._bus.dispatch(command, obj)