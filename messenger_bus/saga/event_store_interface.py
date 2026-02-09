
class EventStoreInterface:

    def __init__(self, db):
        self._db = db

    def save(self, saga):
        """ ajouter un nouveau saga """
        raise NotImplementedError

    def find(self, uuid:str):
        """ rechercher un saga par son uuid"""
        raise NotImplementedError

    def update_step(self, saga,step):
        """ mise a jour d'une step dans le saga """
        raise NotImplementedError

    def update(self, saga):
        """ mise a jour du saga """
        raise NotImplementedError