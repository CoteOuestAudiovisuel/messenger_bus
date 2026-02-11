import asyncio
from dataclasses import dataclass
import json
import logging
import os
import traceback

import aio_pika
import pika
from aio_pika.abc import AbstractIncomingMessage

from .transport import TransportInterface, ClientServerTransport
from typing import Any

FORMAT = '%(asctime)s %(levelname)s:%(name)s:%(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('messenger')
logger.setLevel(logging.DEBUG)

@dataclass
class WorkerInitParams:
    pass

@dataclass
class WorkerRabbitMQInitParams(WorkerInitParams):
    connection_uri: str
    queue_name: str
    exchange_name: str
    exchange_type: str
    binding_keys: list[str]
    auto_ack: bool = False


class WorkerInterface:

    def __init__(self, params:WorkerInitParams,transport_name:str):
        from .service_container import transport_manager

        self._params: WorkerInitParams = params
        self._transport: ClientServerTransport = transport_manager.get(transport_name)

    async def _connect(self):
        """ etablit la connection avec le serveur AMQP"""
        raise NotImplementedError

    async def consume(self):
        """ ecoute les nouveaux messages et les dispatch dans le bus"""
        raise NotImplementedError

    async def _on_message(self, message:Any):
        """ traite la reception de nouveaux message """
        raise NotImplementedError


class RabbitMQWorker(WorkerInterface):

    def __init__(self, params:WorkerRabbitMQInitParams, transport_name:str):
        super().__init__(params, transport_name=transport_name)
        self.connection = None
        self.channel = None

    async def _connect(self):

        connection = await aio_pika.connect_robust(self._params.connection_uri)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        await channel.declare_exchange(name=self._params.exchange_name, type=self._params.exchange_type, durable=True)
        my_queue = await channel.declare_queue(self._params.queue_name, durable=True, arguments={"x-max-priority": 10})

        for binding_key in self._params.binding_keys:
            await my_queue.bind(exchange=self._params.exchange_name, routing_key=binding_key)

        return (connection, channel, my_queue)


    async def _on_message(self,message: AbstractIncomingMessage) -> None:
        from .service_container import message_bus

        try:
            print("[x] %r:%r" % (message.routing_key, message.body))
            try:
                self._transport.receive(message.body.decode(), {**message.info(), "timestamp":""})
            except Exception as e:
                logger.warning(traceback.format_exc())

            if not self._params.auto_ack:
                await message.ack()
        except Exception as e:
            logger.debug(e)

            if not self._params.auto_ack:
                await message.ack()

            try:
                m = json.loads(message.body.decode())
                headers = {"x-retry": True, "x-retry-count": 0}

                if "x-retry-count" in m.headers:
                    headers["x-retry-count"] = m.headers["x-retry-count"] + 1

                self._transport.dispatch(m, message.routing_key, {"headers": headers})
            except:
                pass

    async def consume(self):
        connection, channel, queue = await self._connect()
        await queue.consume(self._on_message, no_ack=self._params.auto_ack)
        await asyncio.Future()