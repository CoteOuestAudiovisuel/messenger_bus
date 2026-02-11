from messenger_bus.message_handler import CommandInterface
from messenger_bus.worker import WorkerRabbitMQInitParams

class DomainEvent(CommandInterface):
    year = 2015

    def __init__(self, **kwargs):
        super().__init__(kwargs)

print(DomainEvent(year=2025))