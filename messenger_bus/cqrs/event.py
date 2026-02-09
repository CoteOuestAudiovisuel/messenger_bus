from ..message_handler import CommandInterface

class DomainEvent(CommandInterface):

    def __init__(self, kwargs):
        super().__init__(kwargs)

    def transform(self) -> CommandInterface:
        raise NotImplementedError

    def reverse_transform(self) -> CommandInterface:
        raise NotImplementedError