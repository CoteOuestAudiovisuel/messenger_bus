from .event import DomainEvent
from .event_capacity import EventCapacity


class EventStoreInterface:

    def __init__(self, db):
        self._db = db

    def add(self, aggregat:EventCapacity, event:DomainEvent):
        raise NotImplementedError


    def get_latest_snapshot(self,uuid:str) -> dict:
        raise NotImplementedError

    def add_snapshot(self, uuid: str, snapshot_data: dict, version: int):
        """Sauvegarde un snapshot."""
        raise NotImplementedError


    def get_events(self, uuid: str, after_version=None):
        """Récupère les événements pour une entité après une version spécifique."""
        raise NotImplementedError