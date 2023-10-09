import json
import logging
import pathlib
import re
from collections import namedtuple
from copy import deepcopy
from typing import NamedTuple
import uuid

import uuid as uuid

from .envelope import Envelope
from .stamp import AmqpStamp, ResultStamp

FORMAT = '%(asctime)s %(levelname)s:%(name)s:%(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('messenger')
logger.setLevel(logging.DEBUG)

_handlers = []


class CommandInterfaceMeta(type):

    def __new__(metacls, cls, bases, attrs):

        _new_dict = {"__CommandInterfaceMeta_fields__":{"_uuid":None}}
        _to_rem = []
        for k,v in attrs.items():
            if not k.startswith("__") and not k.endswith("__") and not callable(v):
                _new_dict["__CommandInterfaceMeta_fields__"][k] = v
                _to_rem.append(k)

        for k in _to_rem:
            del attrs[k]

        attrs.update(_new_dict)
        return type.__new__(metacls, cls, bases, attrs)

    def __init__(self,cls,bases,attrs):
        super().__init__(cls,bases,attrs)




class CommandInterface(metaclass=CommandInterfaceMeta):

    def __init__(self, payload:dict={}):
        self._hydrate(payload)
        self._uuid = uuid.uuid4()

    def _hydrate(self, payload:dict={}):

        for k,v in payload.items():
            if k not in self.__CommandInterfaceMeta_fields__:
                raise AttributeError("'{}'".format(k))

            setattr(self,k,v)

    def __eq__(self, other):
        for k,v in self.__dict__.items():
            if k not in other or v != other[k]:
                return False
        return True

    def __call__(self, payload:dict={}):
        return CommandInterface(payload)

    def __setattr__(self, key, value):
        if key not in self.__CommandInterfaceMeta_fields__:
            raise KeyError("{}".format(key))

        if key in self.__dict__:
            raise Exception("{} is immutable object".format(self.__class__.__name__))

        super().__setattr__(key,value)

    def __getattr__(self, k):
        if k not in self.__CommandInterfaceMeta_fields__:
            raise AttributeError("'{}'".format(k))
        return self.__dict__.get(k) if k in self.__dict__ else self.__CommandInterfaceMeta_fields__.get(k)

    def __setitem__(self, key, value):
        self.__setattr__(key,value)

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __str__(self):
        return json.dumps(self.__repr__())

    def __repr__(self):
        _d1 = deepcopy(self.__CommandInterfaceMeta_fields__)
        _d = deepcopy(self.__dict__)
        _d1.update(_d)
        _d1["_uuid"] = str(_d1["_uuid"])
        return _d1

    def __contains__(self, k):
        return True if k in self.__CommandInterfaceMeta_fields__ else False

class DefaultCommand(CommandInterface):
    action = None
    payload = None
    def __init__(self, payload:dict={}):
        super().__init__(payload)


def handler(transport:str=None, bus:str=None, binding_key:str=None, priority:int=0, command:CommandInterface=None):
    def wrapper(fn):
        def func(*args,**kwargs):
            return fn(*args, **kwargs)

        item = {
            "transport":transport,
            "bus":bus,
            "binding_key":binding_key,
            "priority": priority,
            "command": command,
            "callback":func,
            "controller":fn
        }

        if type(fn) == type: # annotation mise sur une class
            item["type"] = "class"
        elif type(fn).__name__ == "function": # annotation mise sur une function
            item["type"] = "function"

        _handlers.append(item)
        return func
    return wrapper



def process_handlers(envelope:Envelope) -> Envelope:
    from .transport import AMQPTransport

    stamp = envelope.last("TransportStamp")
    transport = stamp.transport
    transport_attributes:dict = stamp.attributes

    stamp = envelope.last("BusStamp")
    bus = stamp.bus
    message = envelope.message

    print(transport_attributes)

    _handlers_selected = []
    for p in _handlers:

        is_ok = True
        criterias = {}
        # un check transport est actif
        if p.get("transport"):
            criterias["transport"] = False
            if p.get("transport") == transport.definition.name:
                criterias["transport"] = True

        # un check bus est actif
        if p.get("bus"):
            criterias["bus"] = False
            if p.get("bus") == bus.definition.name:
                criterias["bus"] = True

        # un check binding_key est actif
        if p.get("binding_key"):
            criterias["binding_key"] = False

            if not isinstance(message,CommandInterface):
                binding_key = message.get("action")
                if re.search(r"^{}$".format(p.get("binding_key")), binding_key):
                    criterias["binding_key"] = True


        # un check command est actif
        if p.get("command"):
            criterias["command"] = False
            if isinstance(message, CommandInterface):
                if isinstance(message,p.get("command")):
                    criterias["command"] = True
                    print(dir(p["controller"]),p["controller"].__annotations__)

        if p["type"] == "class":
            instance_ = p["controller"]()
            for name,inst in instance_.__call__.__annotations__.items():
                if isinstance(message,inst):
                    criterias["command_type_hint"] = True
                    break

        elif p["type"] == "function":
            for name,inst in p["controller"].__annotations__.items():
                if isinstance(message,inst):
                    criterias["command_type_hint"] = True
                    break

        # critères d'invalidité
        if transport_attributes.get("transport") and p.get("transport") != transport_attributes.get("transport"):
            criterias = {k:False for k,v in criterias.items()}

        if transport_attributes.get("bus") and p.get("bus") != transport_attributes.get("bus"):
            criterias = {k:False for k,v in criterias.items()}


        # check de validation globale
        if len(criterias):
            for k,v in criterias.items():
                if v == False:
                    is_ok = False
                    break

            if is_ok:
                _handlers_selected.append(p)

    _handlers_selected.sort(key=lambda i: i["priority"], reverse=True)

    for p in _handlers_selected:
        callback = p["callback"]
        properties = transport_attributes
        ret = None

        if isinstance(transport, AMQPTransport):
            amqpStamp: AmqpStamp = envelope.last("AmqpStamp")
            if amqpStamp:
                properties = amqpStamp.attributes.__dict__

        argv = [envelope.message]
        argc = 1
        if p["type"] == "class":
            callback = callback()
            argc = len(callback.__call__.__annotations__)

        elif p["type"] == "function":
            argc = len(p["controller"].__annotations__)

        if (argc >= 2):
            argv.append(properties)
        ret = callback(*argv)

        if ret:
            envelope = envelope.update(ResultStamp(ret))

    return envelope

class MessageHandlerInterface:

    def __call__(self, message):
        raise NotImplementedError

class HandlerInterface:

    def __init__(self, binding_key:str, priority:int = 0):
        self._binding_key = binding_key
        self.priority = priority

    def check(self,binding_key:str = "") -> bool:
        match = re.search(r"^{}$".format(self._binding_key), binding_key)
        return True if match else False

    def start(self,binding_key:str, payload:dict,properties:dict={}):
        if self.check(binding_key):
            return self.run(binding_key,payload,properties)
        return None

    def run(self,binding_key:str, payload:dict, properties:dict={}):
        raise NotImplementedError

    def getUsableBindingKey(self):
        binding_key = self._binding_key
        b = binding_key.split(".")
        if len(b) > 2:
            b.pop()
            binding_key = ".".join(b)
        return binding_key

class HandlerManager:

    def __init__(self, handlers:list=[]):
        self._handlers = []

        for handler in handlers:
            self._add(handler)

        self._handlers.sort(key=lambda el: el.priority, reverse=True)

    def _add(self, handler: HandlerInterface):
        try:
            self._handlers.index(handler)
        except ValueError as e:
            self._handlers.append(handler)
        return self


    def run(self,match:str, payload:dict, properties:dict={}):

        self._handlers.sort(key=lambda el: el.priority, reverse=True)

        for handler in self._handlers:
            rst = handler.start(match, payload, properties)
            if rst:
                return rst

        return None