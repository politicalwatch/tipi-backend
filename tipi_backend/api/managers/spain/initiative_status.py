class InitiativeStatusManager():

    def __init__(self):
        self.all_status = [
                'Aprobada',
                'Respondida',
                'Celebrada',
                'Convalidada',
                'Convertida en otra',
                'Acumulada en otra',
                'En tramitación',
                'No admitida a trámite',
                'No debatida',
                'Caducada',
                'Rechazada',
                'Derogada',
                'Retirada',
                ]

    def get_values(self):
        return self.all_status
