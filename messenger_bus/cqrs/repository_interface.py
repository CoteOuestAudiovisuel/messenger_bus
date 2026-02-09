from .event_capacity import EventCapacity
from .event_store_interface import EventStoreInterface
from .mapping import Mapping


@Mapping(entity_class=EventCapacity)
class RepositoryInterface:

    def __init__(self, event_store:EventStoreInterface):
        self._event_store = event_store

    def to_domain_events(self, events_data) -> tuple:
        raise NotImplementedError

    def find(self,uuid:str):
        version = 0
        snapshot = self._event_store.get_latest_snapshot(uuid)
        if snapshot:
            aggregate = self._entity_class.from_snapshot(snapshot.get("payload"))
            version = snapshot["version"]
        else:
            aggregate = self._entity_class()

        # Rejouer les événements après le snapshot
        _entity_id,_version,events = self.to_domain_events(self._event_store.get_events(uuid, version))
        aggregate.uuid = _entity_id
        aggregate.version = _version

        aggregate = self._entity_class.from_events(events, with_entity=aggregate)
        return aggregate

    def save(self, aggregat,events:list):
        for event in events:
            self._event_store.add(aggregat,event)


