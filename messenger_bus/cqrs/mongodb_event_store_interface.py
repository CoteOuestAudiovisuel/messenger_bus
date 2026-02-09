import datetime

from .event import DomainEvent
from .event_capacity import EventCapacity
from .event_store_interface import EventStoreInterface

class MongoDBEventStoreInterface(EventStoreInterface):

    def __init__(self, db):
        super().__init__(db)

    def add(self, aggregat:EventCapacity, event:DomainEvent):
        """
        on va stocker l'evenement dans la base de donnée
        puis on va envoyer un message dans le l'event bus
        :param event:
        :return:
        """

        # save in eventstore database
        new_version = aggregat.version + 1
        payload = {
            "entity_type": aggregat.__class__.__name__,
            "entity_id": aggregat.uuid,
            "version": new_version,
            "event_type":event.__class__.__name__,
            "payload":event.get_value()
        }
        _id = self._db.event_store.insert_one(payload).inserted_id
        aggregat.version = new_version


    def get_latest_snapshot(self,uuid:str) -> dict:
        return self._db.event_store_snapshot.find_one({"entity_id": uuid}, sort=[("created_at",-1)])

    def add_snapshot(self, uuid: str, snapshot_data: dict, version: int):
        """Sauvegarde un snapshot."""
        payload = {
            "version": version,
            "entity_id": uuid,
            "payload": snapshot_data,
            "created_at": datetime.datetime.utcnow()
        }
        _id = self._db.event_store_snapshot.insert_one(payload).inserted_id
        return  _id


    def get_events(self, uuid: str, after_version=None):
        """Récupère les événements pour une entité après une version spécifique."""
        version_check = {}
        if after_version:
            version_check["version"] = {"$gt":after_version}

        return [i for i in self._db.event_store.aggregate([
            {"$match":{
                "entity_id": uuid,
                **version_check
            }},
            {"$sort":{
                "created_at":1
            }}
        ])]