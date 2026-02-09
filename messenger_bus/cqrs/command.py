from ..message_handler import CommandInterface

class ChangeUserEmailCommand(CommandInterface):
    email = None
    def __init__(self, payload:dict={}):
        super().__init__(payload)

class ChangeUserAdressCommand(CommandInterface):
    address = None
    def __init__(self, payload: dict = {}):
        super().__init__(payload)

