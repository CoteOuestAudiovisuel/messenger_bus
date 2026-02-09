import datetime
from .event_store_interface import EventStoreInterface

class MongoDBEventStoreInterface(EventStoreInterface):

    def __init__(self, db):
        super().__init__(db)

    def save(self, saga):
        if not self.find(saga.uuid):
            _id = self._db.saga_store.insert_one(saga.get_value()).inserted_id
        else:
            self._db.saga_store.update_one({"uuid": saga.uuid}, {
                "$set": saga.get_value()
            })

    def update_step(self, saga,step):

        self._db.saga_store.update_one({"uuid":saga.uuid, "steps.uuid":step.uuid},{
            "$set":{
                "steps.$":step.get_value()
            }
        })

    def find(self, uuid: str):
        return self._db.saga_store.find_one({"uuid": uuid})