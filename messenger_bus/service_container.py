import logging
import os
import pathlib
import re
import yaml
from jsonschema import validate

from .serializer import DefaultSerializer
from .bus import MessageBusManager
from .transport import TransportManager


FORMAT = '%(asctime)s %(levelname)s:%(name)s:%(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('messenger')
logger.setLevel(logging.DEBUG)

def class_loader(module_name, class_name):
    import importlib
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    instance = class_()
    return instance

framework_template = {}


messenger_bus_config_file = os.environ.get("MESSENGERBUS_CONFIG_FILE")
with open(messenger_bus_config_file) as f:
    text = f.read()
    for m in re.finditer(r"%env\((.+?)\)%", text):
        key = m.group(1)
        val = os.environ.get(m.group(1))
        text = text.replace('%env('+key+')%',val)

    framework_template = yaml.safe_load(text)


with open(pathlib.Path(__file__).parent / "schema.yml") as f:
    schema = yaml.safe_load(f)

validate(instance=framework_template, schema=schema)

serializer = DefaultSerializer()

for k,v in framework_template["framework"]["messenger"]["buses"].items():
    if v.get("middleware"):
        for i,m in enumerate(v["middleware"]):
            m = m.split(".")
            class_name = m.pop()
            module_name = ".".join(m)
            instance = class_loader(module_name, class_name)
            v["middleware"][i] = instance

bus_defs = framework_template["framework"]["messenger"]["buses"]
message_bus = MessageBusManager(bus_defs)

transport_defs = framework_template["framework"]["messenger"]["transports"]
transport_manager = TransportManager(transport_defs)