class InitiativeTypeManager():

    def __init__(self):
        self.types = []

    def get_values(self):
        return self.types

    def get_search_for(self, type):
        return {'initiative_type': type}
