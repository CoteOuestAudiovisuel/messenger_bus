# messenger_bus

Welcome to the messenger_bus wiki!

# Intallation

    pip install messenger_bus


# Command class

all command class must inherits `messenger_bus.command.CommandInterface`

    from messenger_bus.command import CommandInterface   
 
    class ChangeUserEmailCommand():
        email = None
        def __init__(self, value:str):
            super().__init__({"email":value})



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

    from messenger_bus.service_container import message_bus

    envelope = message_bus.dispatch(ChangeUserEmailCommand({"email":"test@test.test"}), {
        # "transport":"sync",
        # "bus":"command.bus",
    })


if your handler return any value, you can get it back with the code below

    print(envelope.last("ResultStamp").result)
