import asyncio
from dataclasses import dataclass
import json
import logging
import os
import traceback

import aio_pika
import pika
from aio_pika import Message
from aio_pika.abc import AbstractIncomingMessage, MessageInfo

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
        self.exchange = None

    async def _connect(self):

        connection = await aio_pika.connect_robust(self._params.connection_uri)
        channel = await connection.channel()

        self.channel = channel
        self.connection = connection

        await channel.set_qos(prefetch_count=1)
        self.exchange = await channel.declare_exchange(
            name=self._params.exchange_name,
            type=self._params.exchange_type,
            durable=True
        )
        # DLX
        await channel.declare_exchange(
            name=f"{self._params.exchange_name}_dlx",
            type=self._params.exchange_type,
            durable=True
        )


        my_queue = await channel.declare_queue(
            self._params.queue_name,
            durable=True,
            arguments={
                "x-max-priority": 5,
                "x-dead-letter-exchange": f"{self._params.exchange_name}_dlx",
            }
        )
        # queue Retry avec TTL
        retry_ttl_queue = await channel.declare_queue(
            f"{self._params.queue_name}_retry",
            durable=True,
            arguments={
                "x-message-ttl": 30000,  # 30 sec
                "x-dead-letter-exchange":self._params.exchange_name,
            }
        )
        # queue DLQ
        dlx_queue = await channel.declare_queue(
            f"{self._params.queue_name}_dlq",
            durable=True
        )


        for binding_key in self._params.binding_keys:
            await my_queue.bind(
                exchange=self._params.exchange_name,
                routing_key=binding_key
            )

            await dlx_queue.bind(
                exchange=f"{self._params.exchange_name}_dlx",
                routing_key=binding_key
            )

        return (connection, channel, my_queue)


    async def _on_message(self,message: AbstractIncomingMessage) -> None:

        retry_count = self.get_retry_count(message.headers)

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

            if retry_count >= 5:
                logger.warning("Max retries atteint → DLQ")

                # → envoi vers DLQ
                await message.reject(requeue=False)

            else:
                logger.warning(f"Envoi en retry ({retry_count + 1})")

                #Publie dans retry queue

                await self.exchange.publish(
                    Message(
                        message.body,
                        headers=message.headers,
                        content_type=message.content_type,
                        content_encoding=message.content_encoding,
                        delivery_mode=message.delivery_mode,
                        priority=message.priority,
                        correlation_id=message.correlation_id,
                        reply_to=message.reply_to,
                        expiration=message.expiration,
                        message_id=message.message_id,
                        type=message.type,
                        user_id=message.user_id,
                        app_id=message.app_id,
                    ),
                    f"{self._params.queue_name}_retry"
                )

                #ACK pour éviter duplication
                await message.ack()



    async def consume(self):
        connection, channel, queue = await self._connect()
        await queue.consume(self._on_message, no_ack=self._params.auto_ack)
        await asyncio.Future()

    def get_retry_count(self, headers:dict):
        x_death = headers.get("x-opt-death", []) or headers.get("x-death", [])
        if x_death:
            return x_death[0].get("count", 0)

        return 0