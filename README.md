# messenger_bus

Welcome to the messenger_bus wiki!

# Intallation

    pip install messenger_bus


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
these options are available for this annotation:

- priority (int)
- transport (str)
- bus (str)


    import ChangeUserEmailCommand
    from messenger_bus.message_handler import handler
    
    @handler(priority=7)
    class ChangeUserEmailHandler:
        def __call__(self, command:ChangeUserEmailCommand, properties:dict):
            print("__call__ -------------------->",command,properties)
            return {"action":True}
          
        @handler(priority=8)
        def change_user_email_handler(command:ChangeUserEmailCommand):
            print("yes -------------------->",command)

        
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


if your handler return any value, you can get it back with the code below

    print(envelope.last("ResultStamp").result)
