from ..message_handler import CommandInterface

class GetUserAllXQuery(CommandInterface):
    user_id = None
    def __init__(self, query: dict = {}):
        super().__init__(query)