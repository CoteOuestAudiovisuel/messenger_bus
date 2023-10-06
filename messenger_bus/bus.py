import asyncio
import sys

from .envelope import Envelope
from .message_handler import CommandInterface, DefaultCommand
from .middleware import MiddlewareManager, SignatureMiddleware
from .stamp import BusStamp, TransportStamp, ResultStamp, DispatchAfterCurrentBusStamp
from .transport import TransportInterface


class MessageBusInterfaceDefinition:
    def __init__(self, definition:dict):
        self.name = definition.get("name")
        self.middlewares = definition.get("middleware",[])


class MessageBusInterface:
    """
    """
    def __init__(self, definition:MessageBusInterfaceDefinition):
        #self.middleware_manager = MiddlewareManager(definition.middlewares)
        self.definition = definition
        self._events = []

    def dispatch(self, message, options:dict):
        """ permet d'envoyer un message dans le bus"""
        raise NotImplementedError

    def run(self, envelope:Envelope) -> Envelope:
        """ execute tout les middlewares """
        _item = MiddlewareManager(self.definition.middlewares)
        return _item.run(envelope)

    def has_event(self) -> bool:
        return len(self._events) != 0

    def add_event(self, item:Envelope):
        if not isinstance(item,Envelope):
            raise TypeError(item.__class__.__name__)
        self._events.append(item)

    def remove_event(self, item: Envelope):
        self._events.remove(item)


class MessageBus(MessageBusInterface):
    """
    implementation d'un bus de message
    """
    def __init__(self, definition:MessageBusInterfaceDefinition):
        super().__init__(definition)

    def dispatch(self, message, options:dict):
        """
        ceci est la methode public pour envoyer un message dans le bus
        il faut choir un transport par lequel envoyer le message
        donner la possibilité de customiser le transport dans l'argument "options"
        """
        from .service_container import transport_manager
        transport:TransportInterface = transport_manager.get(options.get("transport"))

        if transport is None:
            transport = transport_manager.get("__default__")

        options.update({
            "stamps": [
                BusStamp(self),
                TransportStamp(transport),
            ]
        })
        transport.dispatch(message,options)


class MessageBusManager:
    """
    le bus manager, il sert a orchestrer tout les bus
    """
    default_bus_name = "messenger.default.bus"
    def __init__(self, bus_defs: list):
        self._buses = {}
        self._default_bus_name = "messenger.default.bus"

        self.add({
            "name": self._default_bus_name,
            "middleware":[
                SignatureMiddleware()
            ]
        })

        for k,bus_def in bus_defs.items():
            bus_def['name'] = k
            self.add(bus_def)



    def __getitem__(self, item):
        return self.get(item)

    def get(self, name:str):
        return self._buses.get(name)

    def add(self, definition):
        """ ajoute un bus au manager"""
        bus = MessageBus(MessageBusInterfaceDefinition(definition))
        self._buses[definition.get("name")] = bus
        return self

    def remove(self, bus_name:str):
        """ supprime un bus au manager"""
        del self._buses[bus_name]
        return self

    def dispatch(self, message,options:dict={}) -> Envelope:
        """
        il faut choir un bus par lequel envoyer le message
        donner la possibilité de customiser le bus dans l'argument "options"
        :param message:
        :param options:
        :return:
        """

        if type(message) == dict:
            message = DefaultCommand(message)
        elif not isinstance(message,CommandInterface):
            raise Exception("message type can only be 'CommandInterface' or dict")


        from .service_container import transport_manager, framework_template
        transports:list = []

        bus = [i for k,i in self._buses.items() if i.definition.name == options.get("bus",self._default_bus_name)]
        if not len(bus):
            raise Exception("Bus '{}' not found".format(options.get("bus")))
        bus = bus.pop()


       # if type(message) == dict:
        """
        on doit deviner le transport a utiliser à partir du fichier de configuration messenger.yml
        """
        for cls, v in framework_template["framework"]["messenger"]["routing"].items():
            _message_class = "{module}.{classname}".format(module=message.__module__,classname=message.__class__.__name__)
            if cls == _message_class:
                if type(v) == list:
                    for el in v:
                        if type(el) == str:
                            if not options.get("transport"):
                                transport:TransportInterface = transport_manager.get(el)
                                transports.append((transport,bus,{}))

                            elif options.get("transport") == el:
                                transport: TransportInterface = transport_manager.get(el)
                                transports.append((transport, bus,{}))
                        else:
                            _transport:TransportInterface = None
                            _bus = None
                            _params = {}
                            if not options.get("transport"):
                                if el.get("transport"):
                                    _transport: TransportInterface = transport_manager.get(el.get("transport"))
                                    if not _transport:
                                        raise Exception("transport {} not found".format(el.get("transport")))

                                    _params["transport"] = el.get("transport")

                            else:
                                if el.get("transport"):
                                    if options.get("transport") == el.get("transport"):
                                        _transport: TransportInterface = transport_manager.get(el.get("transport"))
                                        if not _transport:
                                            raise Exception("transport {} not found".format(el.get("transport")))
                                        _params["transport"] = el.get("transport")

                                else:
                                    _transport: TransportInterface = transport_manager.get(options.get("transport"))
                                    if not _transport:
                                        raise Exception("transport {} not found".format(el.get("transport")))
                                    _params["transport"] = options.get("transport")



                            if not options.get("bus"):
                                if el.get("bus"):
                                    _bus = [i for k, i in self._buses.items() if i.definition.name == el.get("bus")]
                                    if not _bus:
                                        raise Exception("Bus '{}' not found".format(el.get("bus")))
                                    _params["bus"] = el.get("bus")
                                    _bus = _bus.pop()

                            else:
                                if el.get("bus"):
                                    if options.get("bus") == el.get("bus"):
                                        _bus = [i for k, i in self._buses.items() if i.definition.name == el.get("bus")]
                                        if not _bus:
                                            raise Exception("Bus '{}' not found".format(el.get("bus")))
                                        _params["bus"] = el.get("bus")
                                        _bus = _bus.pop()

                                else:
                                    _bus = [i for k, i in self._buses.items() if i.definition.name == options.get("bus")]
                                    if not _bus:
                                        raise Exception("Bus '{}' not found".format(options.get("bus")))

                                    _params["bus"] = options.get("bus")
                                    _bus = _bus.pop()


                            if _transport or _bus:
                                transports.append((_transport, _bus, _params))


                elif type(v) == dict:
                    _transport: TransportInterface = None
                    _bus = None
                    _params = {}
                    if not options.get("transport"):
                        if v.get("transport"):
                            _transport: TransportInterface = transport_manager.get(v.get("transport"))
                            if not _transport:
                                raise Exception("transport {} not found".format(v.get("transport")))

                            _params["transport"] = v.get("transport")

                    else:
                        if v.get("transport"):
                            if options.get("transport") == v.get("transport"):
                                _transport: TransportInterface = transport_manager.get(v.get("transport"))
                                if not _transport:
                                    raise Exception("transport {} not found".format(v.get("transport")))
                                _params["transport"] = v.get("transport")

                        else:
                            _transport: TransportInterface = transport_manager.get(options.get("transport"))
                            if not _transport:
                                raise Exception("transport {} not found".format(v.get("transport")))
                            _params["transport"] = options.get("transport")

                    if not options.get("bus"):
                        if v.get("bus"):
                            _bus = [i for k, i in self._buses.items() if i.definition.name == v.get("bus")]
                            if not _bus:
                                raise Exception("Bus '{}' not found".format(v.get("bus")))
                            _params["bus"] = v.get("bus")
                            _bus = _bus.pop()

                    else:
                        if v.get("bus"):
                            if options.get("bus") == v.get("bus"):
                                _bus = [i for k, i in self._buses.items() if i.definition.name == v.get("bus")]
                                if not _bus:
                                    raise Exception("Bus '{}' not found".format(v.get("bus")))
                                _params["bus"] = v.get("bus")
                                _bus = _bus.pop()

                        else:
                            _bus = [i for k, i in self._buses.items() if i.definition.name == options.get("bus")]
                            if not _bus:
                                raise Exception("Bus '{}' not found".format(options.get("bus")))

                            _params["bus"] = options.get("bus")
                            _bus = _bus.pop()

                    if _transport or _bus:
                        transports.append((_transport, _bus, _params))

                else:
                    transport: TransportInterface = transport_manager.get(v)
                    transports.append((transport, bus,{}))


        if not len(transports):
            transport: TransportInterface = transport_manager.get(options.get("transport"))
            if not transport:
                transport = transport_manager.get("__default__")
            transports.append((transport, bus,{}))

        _result:Envelope = None
        from copy import copy
        for el in transports:
            _bus = el[1] if el[1] else bus

            _options = copy(options)

            if "stamps" not in _options:
                _options["stamps"] = []

            _options["stamps"] += [
                BusStamp(_bus),
                TransportStamp(el[0])
            ]
            _options.update(el[2])
            envelope:Envelope = el[0].dispatch(message,_options)
            stamp:ResultStamp = envelope.last("ResultStamp")

            if not _result:
                _result = envelope

            else:
                _result = envelope.update(stamp)


        if _result and not _result.last("DispatchAfterCurrentBusStamp"):
            asyncio.run(self.dispatch_pending_events())

        return _result

    async def dispatch_pending_events(self):
        # verifier les events en attente de dispatching
        for _name, _bus in self._buses.items():
            if _bus.has_event():
                while True:
                    try:
                        _envelope:Envelope = next(iter(_bus._events))
                        _bus.remove_event(_envelope)
                        _envelope = _envelope.remove(DispatchAfterCurrentBusStamp)
                        envelope = _bus.run(_envelope)
                    except StopIteration as e:
                        break