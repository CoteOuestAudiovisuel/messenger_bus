from ..service_container import class_loader

from .event_store_interface import EventStoreInterface

class RepositoryInterface:

    def __init__(self, event_store:EventStoreInterface):
        self._event_store = event_store

    def _hydrate(self, dto:dict):
        from saga.saga_orchestrator import SagaOrchestratorInterface
        saga = SagaOrchestratorInterface.create_from(dto)

        saga._repository = self
        return saga

    def find(self,uuid:str):
        data = self._event_store.find(uuid)
        if data:
            return self._hydrate(data)

    def save(self, saga):
        self._event_store.save(saga)

    def save_step(self, saga, step):
        self._event_store.update_step(saga,step)

