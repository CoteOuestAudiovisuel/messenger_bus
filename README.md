# messenger_bus

This project started when using symfony 5 messenger package with CQRS pattern on a project.
I found this package very interesting and wanted to have something similar in python.

# Intallation

    pip install messenger_bus


![Image from Symfony docs](https://symfony.com/doc/current/_images/components/messenger/overview.svg)
# Command class

All command class must inherits `messenger_bus.command.CommandInterface`

    from messenger_bus.command import CommandInterface   
 
    class ChangeUserEmailCommand():
        email = None
        def __init__(self, payload:dict):
            super().__init__(payload)


# Handler class

when message is dispatched in a bus, you can handle it, creating a Handler class.

use the handler annotation on a class definition or on a class method or both.

these options are available for this annotation: priority (int), transport (str), bus (str)

## Class level handler


    import ChangeUserEmailCommand
    from messenger_bus.message_handler import handler
    
    @handler(priority=7)
    class ChangeUserEmailHandler:
        def __call__(self, command:ChangeUserEmailCommand):
            print(command)
            return {"action":True}
          



## Function level handler


    import ChangeUserEmailCommand
    from messenger_bus.message_handler import handler
    
    class ChangeUserEmailHandler:
          
        @handler(priority=8)
        def change_user_email_handler(command:ChangeUserEmailCommand):
            print(command)

        
# File configuration.

This package support 2 transports: **amqp** (RabbitMQ) and **sync://** (good for CQRS needs).

Create a yaml file in your project with the value below.

for example purpose we create 3 buses, _**command bus**_, _**query bus**_ and _**event bus**_

    framework:
        messenger:
            buses:
                command.bus:
                    middleware:
                        - messenger_bus.middleware.SignatureMiddleware
    
                query.bus:
                    middleware:
                        - messenger_bus.middleware.SignatureMiddleware
    
                event.bus:
                    middleware:
                        - messenger_bus.middleware.SignatureMiddleware
    
            transports:
    
                async:
                    dsn: '%env(MESSENGER_TRANSPORT_DSN)%'
                    options:
                        exchange:
                            name: '%env(RABBITMQ_EXCHANGE_NAME)%'
                            type: '%env(RABBITMQ_EXCHANGE_TYPE)%'
                            durable: true
    
                        queue:
                            name: '%env(RABBITMQ_QUEUE)%'
                            binding: '%env(RABBITMQ_BINDING_KEYS)%'
                            durable: true
    
                sync:
                    dsn: 'sync://'
    
          
    
            routing:
                'ChangeUserEmailCommand': sync
                'messenger_bus.message_handler.DefaultCommand': async




Then create environment variable `MESSENGERBUS_CONFIG_FILE` with the config file absolute path.

# Send a message

to send a message in a bus use the code below.

    from messenger_bus.service_container import message_bus as bus

    envelope = bus.dispatch(ChangeUserEmailCommand({"email":"test@test.test"}), {
        # "transport":"sync",
        # "bus":"command.bus",
    })


if your handler return any value, you can get it back, useful on query handler in CQRS pattern.

    envelope.last("ResultStamp").result


# Middlewares

When a message is sent via the bus, it is intercepted by built-in middleware.

You can create your own middleware to manipulate the message sent via the bus.
Let's create a custom middleware to add a delay.

    from messenger_bus.middleware import MiddlewareInterface
    from messenger_bus.envelope import Envelope
    import time
    
    class CustomMiddleware(MiddlewareInterface):
    
        def __init__(self):
           super().__init__()
        
        def handle(self,envelope:Envelope, stack) -> Envelope:
        
            if envelope.last("SendingStamp"):
                time.sleep(5)
        
            return stack.next().handle(envelope, stack)



This middleware is added to a bus via the yaml configuration file.
The custom middleware adds a delay before the message is sent on the bus.

    ...
    command.bus:
        middleware:
            - messenger_bus.middleware.SignatureMiddleware
            - path.to.the.middleware.CustomMiddleware
    ...

# Bus

Buses are created via the configuration file.
You can create as many buses as you like.

When using the message bus, the following middleware are configured for you:

`SendMiddleware` (enables synchronous and asynchronous processing, logs the processing of your messages if you provide a logger)

`MessageHandlerMiddleware` (calls the registered handler(s))


To dispatch a command on a specific bus, see the example below.

    from messenger_bus.service_container import message_bus as bus

    envelope = bus.dispatch(ChangeUserEmailCommand({"email":"test@test.test"}), {
        "bus":"custom-bus-name",
    })

# Transport

all commands are sent in a bus throw a transport. when the transport is not specified when dispatching a message in a bus, th default transport i used.
the default transport is synchrone.

you can add an asynchrone transport with the **AMQP Transport**
other transports will be supported in later versions of this library.

just like messaging buses, transports are configured via the yaml configuration file as follows:


    framework:
        messenger:
           
            transports:
    
                async:
                    dsn: '%env(MESSENGER_TRANSPORT_DSN)%'
                    options:
                        exchange:
                            name: '%env(RABBITMQ_EXCHANGE_NAME)%'
                            type: '%env(RABBITMQ_EXCHANGE_TYPE)%'
                            durable: true
    
                        queue:
                            name: '%env(RABBITMQ_QUEUE)%'
                            binding: '%env(RABBITMQ_BINDING_KEYS)%'
                            durable: true
    
                my_custom_transport:
                    dsn: 'sync://'


To dispatch a command using a specific transport, see the example below.


    from messenger_bus.service_container import message_bus as bus

    envelope = bus.dispatch(ChangeUserEmailCommand({"email":"test@test.test"}), {
        "transport":"my_custom_transport",
    })

## Routing

so that a command sent on the bus can be processed in a handler, 
it should be indicated in the yaml configuration file, by which means it will be transported.

Each command created must appear under the heading `routing` in the configuration file.

    ...
     routing:
        'ChangeUserEmailCommand': my_custom_transport
        'messenger_bus.message_handler.DefaultCommand': async
        'CustomCommand': [my_custom_transport, async]
    ...


# Adding Metadata to Messages (Envelopes)

If you need to add metadata or some configuration to a message, use `stamps` option key in le second argument when dispatching message. 
For example, to set the serialization groups used when the message goes through the transport layer.

    from messenger_bus.service_container import message_bus as bus

    envelope = bus.dispatch(ChangeUserEmailCommand({"email":"test@test.test"}), {
        "stamps":[
            DelayStamp(30)
        ],
    })

Here are some important envelope stamps that are shipped with the Messenger Bus:

`DelayStamp`, to delay handling of an asynchronous message.

`DispatchAfterCurrentBusStamp`, to make the message be handled after the current bus has executed.

`HandledStamp`, a stamp that marks the message as handled by a specific handler. Allows accessing the handler returned value and the handler name.

`ReceivedStamp`, an internal stamp that marks the message as received from a transport.

`SentStamp`, a stamp that marks the message as sent by a specific sender.


Instead of dealing directly with the messages in the middleware you receive the envelope. Hence you can inspect the envelope content and its stamps, or add any:

    from messenger_bus.middleware import MiddlewareInterface

    class CustomMiddleware(MiddlewareInterface):

        def __init__(self):
            super().__init__(0)
    
        def handle(self,envelope:Envelope, stack) -> Envelope:
    
            if envelope.last("ReceivedStamp"):
                envelope = envelope.update("AnotherStamp")
    
            return stack.next().handle(envelope,stack)


The above example will forward the message to the next middleware with an additional stamp if the message has just been received (i.e. has at least one `ReceivedStamp` stamp). You can create your own stamps by implementing `StampInterface`.

If you want to examine all stamps on an envelope, use the `envelope.all()` method, which returns all stamps grouped by type (FQCN). Alternatively, you can iterate through all stamps of a specific type by using the FQCN as first parameter of this method (e.g. `envelope.all('ReceivedStamp')`).

