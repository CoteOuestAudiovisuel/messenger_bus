import json
from copy import deepcopy

from ..message_handler import CommandInterface

class EventCapacity:

    def __init__(self):
        self._events:list = []
        self.version = 0
        self.uuid = None
        self._instance_id = None

    def apply(self, event:CommandInterface):
        raise NotImplementedError

    def from_events(events:list, with_entity=None):
        raise NotImplementedError

    def _raise(self, event:CommandInterface):
        self._events.append(event)

    def raised_events(self):
        from copy import deepcopy
        return deepcopy(self._events)

    def __repr__(self):
        _d = deepcopy(self.__dict__)
        _d1 = {k:v for k,v in _d.items() if not k.startswith("_")}
        return _d1

    def __str__(self):
        return json.dumps(self.__repr__())

    def get_value(self) -> dict:
        return self.__repr__()

    @classmethod
    def from_snapshot(cls, snapshot):
        """Reconstruit un agrégat à partir d’un snapshot."""
        aggregate = cls()
        aggregate.__dict__.update(snapshot)
        return aggregate