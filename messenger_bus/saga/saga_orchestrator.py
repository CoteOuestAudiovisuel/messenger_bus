import asyncio
import datetime
import json
import os
import secrets
import time
import uuid
from copy import deepcopy
from typing import List

from ..message_handler import CommandInterface
from ..service_container import class_loader

from .event_store_interface import EventStoreInterface
from .mongodb_event_store_interface import MongoDBEventStoreInterface
from .publisher_interface import SagaCommandPublisherInterface
from .repository_interface import RepositoryInterface
from .transport import SagaTransportInterface, SagaRabbitMQTransport


class SagaCommand(CommandInterface):
    pass

class SagaStep:

    def __init__(self, uuid:str, command:dict, compensation:dict, status:str = "pending"):
        self.uuid = uuid
        self.command:dict = command
        self.compensation:dict = compensation
        self.status:str = status
        self.reply_queue: str = secrets.token_urlsafe(12)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return json.dumps(self.get_value())

    def get_value(self):
        e = deepcopy({k:v for k,v in self.__dict__.items() if not k.startswith("_")})
        return e

    @classmethod
    def create_from(self, dto: dict):
        compensation = dto.get("compensation", {})
        command = dto.get("command", {})
        step: SagaStep = SagaStep(uuid=dto.get("uuid"), command=command, compensation=compensation)
        step.status = dto.get("status","pending")
        step.reply_queue = dto.get("reply_queue")
        return step

class SagaOrchestratorInterface:

    def __init__(self, repository:RepositoryInterface=None, transport:SagaTransportInterface = None):
        self.uuid:str = None
        self.steps:List[SagaStep] = []
        self.created_at = None
        self.status:str = "pending"
        self.reply_queue:str = secrets.token_urlsafe(12)
        self._repository:RepositoryInterface = repository
        self._transport: SagaTransportInterface = transport
        self._iter = None

    async def connect(self):
        raise NotImplementedError

    async def send_message(self, routing_key:str, reply_to:str, message):
        raise NotImplementedError

    async def listen_for_response(self,listen_on:str, timeout:int = 30):
        raise NotImplementedError

    def build(self):
        raise NotImplementedError

    async def send_message_with_timeout(self, routing_key:str, reply_to:str, message, timeout=10):
        """
        envoi un message avec un timeout, c'est a dire un delais de reception d'une reponse
        passé ce delais l'etape est marquée comme echouée.

        :param routing_key:
        :param reply_to:
        :param message:
        :param timeout:
        :return:
        """

        await self.send_message(routing_key, reply_to,message)

        try:
            # Attendre la réponse pendant `timeout` secondes
            response = await self.listen_for_response(reply_to,timeout)
            return response
        except Exception as e:
            return {"status": "timeout"}

    def add_step(self, step:SagaStep):
        """
        ajoute une étape à l'orchestrateur
        :param step:
        :return:
        """

        assert isinstance(step, SagaStep)
        self.steps.append(step)

    async def execute_step(self,step:SagaStep):
        """
        execute une etape de l'orchestration

        :param step:
        :return:
        """
        try:
            if step.status == "completed": return True

            step.status = "in_progress"
            self.save_step(step)

            response = await self.send_message_with_timeout(
                step.command.get("name"),
                step.reply_queue,
                step.command.get("payload"),
                timeout=600
            )

            step.status = response["status"]
            self.save_step(step)

            if response["status"] in ["failed","timeout"]:
                return False

        except Exception as e:
            print(f"Step failed: {e}. Rolling back...")
            step.status = "failed"
            self.save_step(step)
            return False

        return True


    async def execute(self):
        """
        permert le demarage de l'orchestration
        :return:
        """
        await self.connect()

        # si toutes les etapes ont déja été bien executées, on ne fait rien
        # dans le cas contraire, on execute les etapes restantes.
        if len([step for step in self.steps if step.status == "success"]) == len(self.steps):
            return

        for pos,step in enumerate(self.steps):
            if step.status != "pending": continue

            r = await self.execute_step(step)

            if not r:
                await self.execute_compensations(pos)
                break

        if len([step for step in self.steps if step.status == "success"]) == len(self.steps):
            self.status = "completed"
        else:
            self.status = "failed"

        self.save()

        await self._transport.disconnect()


    async def execute_step_compensation(self,step:SagaStep):
        """
        demarrage de la politique de compensation.
        lorsqu'une étape echoue, il faut recuperer toutes les étapes antérieurs et les annuler.

        :param step:
        :return:
        """
        try:
            #if step.status in ["compensation_success"]: return True

            step.status = "compensation_in_progress"
            self.save_step(step)

            response = await self.send_message_with_timeout(
                step.compensation.get("name"),
                "compensation_" + step.reply_queue,
                step.compensation.get("payload"),
                timeout=600
            )

            step.status = "compensation_" + response["status"]
            self.save_step(step)

            if response["status"] in ["failed","timeout"]:
                return False

        except Exception as e:
            print(f"Compensation step failed: {e}")
            step.status = "compensation_failed"
            self.save_step(step)

            return False

        return True

    async def execute_compensations(self, failed_step_index:int):
        """
        execute une étape de compensation

        :param failed_step_index:
        :return:
        """

        concerned_steps = reversed([step for pos,step in enumerate(self.steps) if pos <= failed_step_index])
        for step in concerned_steps:
            await self.execute_step_compensation(step)

        self.status = "failed"
        self.save()

    def save_step(self, step:SagaStep):
        self._repository.save_step(self,step)

    def save(self):
        self._repository.save(self)

    def get_value(self):
        return {
            "uuid": self.uuid,
            "status": self.status,
            "reply_queue": self.reply_queue,
            "created_at": self.created_at,
            "steps": [step.get_value() for step in self.steps],
            "metadata":{
                "classname": self.__class__.__name__,
                "module": self.__class__.__module__
            }
        }

    def __str__(self):
        return json.dumps(self.get_value())

    def __repr__(self):
        return self.__str__()

    @classmethod
    def create_from(cls, dto):
        """
        methode statique pour creer un orchestrateur à partir d'un DTO.
        etat enregistré dans la base de données
        :param dto:
        :return:
        """
        saga: SagaOrchestratorInterface = class_loader(dto["metadata"]["module"], dto["metadata"]["classname"])
        saga.uuid = dto.get("uuid")
        saga.status = dto.get("status","pending")
        saga.reply_queue = dto.get("reply_queue")
        saga.created_at = dto.get("created_at")

        for i, v in enumerate(dto.get("steps", [])):
            el = SagaStep.create_from(v)
            saga.add_step(el)
        return saga


class OrderCreateSaga(SagaOrchestratorInterface):

    def __init__(self,repository:RepositoryInterface=None, transport:SagaRabbitMQTransport = None):
        super().__init__(repository, transport)

    def build(self):

        self.uuid = str(uuid.uuid4())
        self.created_at = datetime.datetime.utcnow().timestamp()

        order_id = str(uuid.uuid4())
        self.add_step(SagaStep(
            uuid=str(uuid.uuid4()),
            command={"name":"VerifyConsumer", "payload": {"uuid":order_id}},
            compensation={"name": "RejectOrder", "payload": {"uuid": order_id}}
        ))

        self.add_step(SagaStep(
            uuid=str(uuid.uuid4()),
            command={"name":"VerifyConsumer2", "payload": {"uuid":order_id}},
            compensation={"name": "RejectOrder2", "payload": {"uuid": order_id}}
        ))

        self.save()

    async def connect(self):
        r = await self._transport.connect("VerifyConsumer RejectOrder VerifyConsumer2 RejectOrder2")
        return r

    async def listen_for_response(self,listen_on:str, timeout:int = 30):
        return await self._transport.listen(listen_on, timeout)

    async def send_message(self, routing_key:str, reply_to:str,command):

        await self._transport.dispatch(command,{
            "routing_key":routing_key,
            "properties":{
                "reply_to": reply_to
            }
        })

class OrderCreateSagaRepository(RepositoryInterface):

    def __init__(self, event_store: EventStoreInterface):
        super().__init__(event_store)

    def find(self,uuid:str):
        transport: SagaRabbitMQTransport = SagaRabbitMQTransport(dsn=os.environ.get("RABBITMQ_DSN"))

        saga = super().find(uuid)
        if saga:
            saga._transport = transport

        return saga
