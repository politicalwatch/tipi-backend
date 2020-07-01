class InitiativeTypeManager():

    def __init__(self):
        self.types = [
                'ACUERDO CONSTITUCIONAL',
                'ACUERDO LEGAL',
                'AUTORIZACION CONSTITUCIONAL',
                'CITACIÓN E INTERPELACIÓN',
                'DE LA REFORMA',
                'DECLARACIONES UNICAMERALES',
                'DESIGNACIONES',
                'INTERVENCIÓN',
                'JUICIO POLÍTICO',
                'MOCIÓN DE CENSURA',
                'PROYECTO DE LEY',
                'RESOLUCION CON RESPUESTA A PEDIDO DE INFORMES',
                'RESOLUCIONES BICAMERALES',
                'RESOLUCIONES UNICAMERALES',
                ]

    def get_values(self):
        return self.types

    def get_search_for(self, type):
        return {'initiative_type': {'$regex': type, '$options': 'gi'}}
