class InitiativeStatusManager():

    def __init__(self):
        self.all_status = [
                'Aprobada',
                'Respondida',
                'Celebrada',
                'Convertida en otra',
                'Acumulada en otra',
                'En tramitación',
                'No admitida a trámite',
                'No debatida',
                'Rechazada',
                'Retirada',
                ]

    def get_values(self):
        return self.all_status
