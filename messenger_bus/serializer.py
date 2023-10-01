import json

from phoenix.messenger.bus import MessageBus
from phoenix.messenger.envelope import Envelope
from phoenix.messenger.stamp import NonSendableStampInterface, AmqpStamp, SignatureStamp, BusStamp, TransportStamp
from phoenix.messenger.transport import ClientServerTransport


class SerializerInterface:

    def __init__(self):
        pass

    def decode(self, encoded_envelope:dict) -> Envelope:
        """
        Decodes an envelope and its message from an encoded-form.

        The `encoded_envelope` parameter is a key-value array that
        describes the envelope and its content, that will be used by the different transports.

        The most common keys are:
        - `body` (string) - the message body
        - `headers` (string<string>) - a key/value pair of headers

        :param encoded_envelope:
        :return:
        """
        raise NotImplementedError

    def encode(self, envelope:Envelope) -> dict:
        """
        Encodes an envelope content (message & stamps) to a common format understandable by transports.
        The encoded array should only contain scalars and arrays.

        Stamps that implement NonSendableStampInterface should
        not be encoded.

        The most common keys of the encoded array are:
        - `body` (string) - the message body
        - `headers` (string<string>) - a key/value pair of headers
        :param envelope:
        :return:
        """
        raise NotImplementedError

class DefaultSerializer(SerializerInterface):

    def __init__(self):
        super(DefaultSerializer, self).__init__()

    def decode(self, encoded_envelope:dict) -> Envelope:
        from .service_container import message_bus
        from .service_container import transport_manager
        message = encoded_envelope['body']
        headers = encoded_envelope['headers']
        stamps = []
        body = json.loads(message)

        if "SignatureStamp" in headers:
            stamps.append(SignatureStamp(headers["SignatureStamp"]["producerId"],headers["SignatureStamp"]["payloadToken"]))

        if "BusStamp" in headers:
            bus = message_bus.get(headers.get("BusStamp"))
            stamps.append(BusStamp(bus))

        if "TransportStamp" in headers:
            transport = transport_manager.get(headers.get("TransportStamp"))
            stamps.append(TransportStamp(transport))

        return Envelope(body, stamps)

    def encode(self, envelope:Envelope) -> dict:
        headers = {}
        message = envelope.message

        stamp:AmqpStamp = envelope.last("AmqpStamp")

        # on ajoute en entête les stamps
        for k, v in envelope.all().items():
            last = v[-1]

            if isinstance(last, BusStamp):
                bus:MessageBus = last.bus
                headers[k] = bus.definition.name

            if isinstance(last, TransportStamp):
                transport:ClientServerTransport = last.transport
                headers[k] = transport.definition.name

            if isinstance(last, NonSendableStampInterface):
                continue
            headers[k] = last.__dict__

        headers["x-routing-key"] = stamp.routing_key
        body = json.dumps(message)

        return {
            'body':body,
            'headers':headers,
        }