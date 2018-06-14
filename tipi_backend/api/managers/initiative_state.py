class InitiativeStateManager():

    def __init__(self):
        self.states = [
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
        return self.states
