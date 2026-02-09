from .event import DomainEvent
from .repository_interface import RepositoryInterface

class ProjectorInterface:

    def __init__(self, repository:RepositoryInterface):
        self._repository = repository

    def notify(self, event:DomainEvent):
        raise NotImplementedError
