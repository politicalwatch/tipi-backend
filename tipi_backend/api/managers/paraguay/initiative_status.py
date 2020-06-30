class InitiativeStatusManager():

    def __init__(self):
        self.all_status = [
                'EN TRÁMITE',
                'PUBLICADO',
                'COMUNICADO',
                'CONTESTADO',
                'CONTESTADO PARCIALMENTE',
                'ARCHIVADO',
                'RETIRADO ',
                'NO CONTESTADO',
                'SUSPENDIDO POR FALTA DE TRÁMITE',
                ]

    def get_values(self):
        return self.all_status
