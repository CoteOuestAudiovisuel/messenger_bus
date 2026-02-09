from ..bus import MessageBusInterface
from ..stamp import DispatchAfterCurrentBusStamp, EntityStamp
from .event_capacity import EventCapacity


class PublisherInterface:

    def __init__(self, bus:MessageBusInterface):
        self._bus = bus

    def publish(self, aggregate:EventCapacity,events, routing_key=None):
        raise NotImplementedError



class DomainEventPublisherInterface(PublisherInterface):

    def __init__(self, bus: MessageBusInterface):
        super().__init__(bus)

    def publish(self, aggregate:EventCapacity,events, routing_key=None):

        for event in events:
            obj = {
                "stamps": [
                    EntityStamp(entity_id=aggregate.uuid, entity_version=aggregate.version),
                    DispatchAfterCurrentBusStamp()
                ],
                "bus": "event.bus",
            }

            if routing_key:
                obj["routing_key"] = routing_key

            r = self._bus.dispatch(event, obj)


class SagaPublisherInterface(PublisherInterface):

    def __init__(self, bus: MessageBusInterface):
        super().__init__(bus)

    def publish(self, aggregate:EventCapacity,events, routing_key=None):

        for event in events:
            obj = {
                "stamps": [
                    EntityStamp(entity_id=aggregate.uuid, entity_version=aggregate.version),
                    DispatchAfterCurrentBusStamp()
                ],
                "bus": "event.bus",
            }

            if routing_key:
                obj["routing_key"] = routing_key

            r = self._bus.dispatch(event, obj)