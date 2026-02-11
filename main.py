from messenger_bus.message_handler import CommandInterface
from messenger_bus.worker import WorkerRabbitMQInitParams
a = WorkerRabbitMQInitParams(
    connection_uri="iii",
    auto_ack=True,
    queue_name="hhh",
    exchange_name="ttt",
    exchange_type="kkk", binding_keys=['jjj'])
print(a.auto_ack)
# class DomainEvent(CommandInterface):
#     year = 2015
#
#     def __init__(self, **kwargs):
#         super().__init__(kwargs)
#
# print(DomainEvent(year=2025))