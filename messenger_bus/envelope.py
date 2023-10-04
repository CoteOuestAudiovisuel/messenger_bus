from .stamp import (StampInterface,  AMQPBasicProperties)


class AMQPEnvelope(AMQPBasicProperties):

    def __init__(self):
        super(AMQPEnvelope, self).__init__()

class Envelope:
    """
    Envelope à transmettre
    """
    def __init__(self, message, stamps:list):
        self.stamps = {}
        self.message = message

        for stamp in stamps:
            if type(stamp) == StampInterface:
                continue
            self.stamps[stamp.__class__.__name__] = [stamp]


    def update(self,*stamps):
        from copy import deepcopy,copy

        cloned = copy(self)

        for stamp in stamps:
            if stamp.__class__.__name__ not in cloned.stamps:
                cloned.stamps[stamp.__class__.__name__] = []
            cloned.stamps[stamp.__class__.__name__].append(stamp)
        return cloned

    def remove(self,*stamp_cls):
        from copy import copy

        cloned = copy(self)

        for stamp in stamp_cls:
            del cloned.stamps[stamp.__name__]
        return cloned

    def last(self,stampFqnc:str) -> StampInterface:
        "renvoi le dernier stamp stampFqnc ajouté"
        return self.stamps[stampFqnc][-1] if stampFqnc in self.stamps else None

    def all(self,stampFqnc:str=None) -> list:
        "renvoi tout les stamps"

        if stampFqnc:
            return self.stamps[stampFqnc] if stampFqnc in self.stamps else []
        return self.stamps