class InitiativeTypeManager():

    def __init__(self):
        self.types = {
                'Comparecencias': ["210", "212", "213", "219"],
                'Convenios internacionales': ["110", "111", "112"],
                'Creación de comisiones, subcomisiones y ponencias': ["151", "152", "153", "154", "155", "156", "157", "158"],
                'Interpelación y su respuesta': ["170", "172"],
                'Moción consecuencia de interpelación y sus enmiendas': ["173"],
                'Otros actos y sus enmiendas': ["200", "140", "120", "095", "189", "187", "410", "156", "193"],
                'Planes, programas y dictámenes': ["043"],
                'Pregunta oral y su respuesta': ["180", "181"],
                'Pregunta para respuesta escrita y su respuesta': ["184"],
                'Proposición de ley y sus enmiendas': ["122", "123", "124", "125"],
                'Proposición no de ley y sus enmiendas': ["161", "162"],
                'Proyecto de Ley y sus enmiendas': ["121"],
                'Real decreto legislativo': ["132"],
                'Real decreto-ley': ["130"],
                }

    def get_values(self):
        return list(self.types.keys())

    def get_search_for(self, type):
        try:
            return {'initiative_type': {'$in': self.types[type]}}
        except:
            return {}
