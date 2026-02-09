from ..stamp import StampInterface


class SagaStamp(StampInterface):
    """
    Stamp ajoutant la signature numeric des données transportées
    """
    def __init__(self, saga_id:str):
        super(SagaStamp, self).__init__()
        self.saga_id = saga_id
