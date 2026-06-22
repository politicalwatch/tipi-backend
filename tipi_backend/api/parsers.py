"""MongoDB query-building for initiative search.

These classes are NOT request validation (that now lives in ``request_models.py`` as
Pydantic models). They transform a params dict — produced by ``query.model_dump()`` —
into a MongoDB query, and select the response schema. Behavior preserved verbatim from
the previous flask-restx implementation.
"""

import datetime
from importlib import import_module as im

from tipi_data.repositories.parliamentarygroups import ParliamentaryGroups
from tipi_data.repositories.initiativetypes import InitiativeTypes
from tipi_data.repositories.knowledgebases import KnowledgeBases
from tipi_data.schemas.initiative import (
    InitiativeExtendedSchema,
    InitiativeNoContentSchema,
    InitiativeSchema,
)

from tipi_backend.api.validators import validate_date
from tipi_backend.settings import Config


class ParameterBag():

    EMPTY_VALUES = ['', None, []]

    def __init__(self, params):
        self.params = params
        self.clean_params()
        self.kb = False

    def clean_params(self):
        for key, value in self.params.copy().items():
            if value in self.EMPTY_VALUES:
                self.clean_params_for_attr(key)

    def get(self, attrname, type=str, default='', clean=False):
        if attrname in self.params:
            attr = self.params[attrname]
            if clean:
                self.clean_params_for_attr(attrname)
            return type(attr)
        return default

    def clean_params_for_attr(self, attrname=''):
        if attrname in self.params:
            del self.params[attrname]

    def parse(self, field_parsers):

        temp_params = self.params.copy()
        for key, value in temp_params.items():
            del self.params[key]
            if key in field_parsers:
                self.params.update(field_parsers[key].get_search_for(key, value))

    def moveToTagged(self):
        if 'topics' in self.params and 'tags' in self.params:
            self.params['tagged.tags'] = self.params['tags']
            self.params['tagged.tags']['$elemMatch']['topic'] = self.params['topics']
            del self.params['topics']
            del self.params['tags']

        if 'topics' in self.params:
            self.params['tagged.topics'] = self.params['topics']
            del self.params['topics']

        if 'tags' in self.params:
            self.params['tagged.tags'] = self.params['tags']
            del self.params['tags']

    def join_tags(self):
        tags = [] if 'tags' not in self.params else self.params['tags']
        subtopics = [] if 'subtopics' not in self.params else self.params['subtopics']
        self.clean_params_for_attr('tags')
        self.clean_params_for_attr('subtopics')
        self.params['tags'] = {
            'tags': tags,
            'subtopics': subtopics
        }

    def join_dates(self):
        if 'startdate' not in self.params:
            self.params['startdate'] = ''
        if 'enddate' not in self.params:
            self.params['enddate'] = ''
        self.params['date'] = "{}_{}".format(
                self.params['startdate'],
                self.params['enddate']
                )
        self.clean_params_for_attr('startdate')
        self.clean_params_for_attr('enddate')

    def ignore_tagless(self):
        if 'tagged' in self.params and '$elemMatch' in self.params['tagged']:
            kb = self.get_kb()
            self.params['tagged']['$elemMatch']['knowledgebase'] = kb

    @property
    def all(self):
        return self.params

    def get_kb(self):
        if self.kb:
            return self.kb

        kb_param = self.get('knowledgebase', str, "", True)
        is_multiple = ',' in kb_param
        kb = kb_param.split(',') if is_multiple else kb_param
        if not kb:
            kb = KnowledgeBases.get_public()
        self.kb = kb
        return self.kb

class SearchInitiativeParser:

    class DefaultFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {key: value}

    class TextFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'$text': {'$search': "\"{}\"".format(value)}}

    class TypeFieldParser():
        @staticmethod
        def get_search_for(key, value):
            if len(value) > 1:
                codes = []
                for item in value:
                    clean = item.replace("'", "")
                    try:
                        codes.append(InitiativeTypes.get_by_name(clean).id)
                    except Exception:
                        pass
                return {'initiative_type': {'$in': codes}}
            else:
                value = value[0].replace("'", "")
            try:
                code = InitiativeTypes.get_by_name(value).id
            except Exception:
                code = ''
            itm = im('tipi_backend.api.managers.{}.initiative_type'.format(Config.COUNTRY))
            return itm.InitiativeTypeManager().get_search_for(code)

    class TopicFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'topics': value}

    class CombinedTagsFieldParser():
        @staticmethod
        def get_search_for(key, value):
            if not len(value['tags']) and not len(value['subtopics']):
                return {}
            elem_match = dict()
            if len(value['tags']):
                elem_match.update({'tag': {'$in': value['tags']}})
            if len(value['subtopics']):
                elem_match.update({'subtopic': {'$in': value['subtopics']}})
            return {'tags': {'$elemMatch': elem_match}}

    class AuthorFieldParser():
        @staticmethod
        def get_search_for(key, value):
            if not ParliamentaryGroups.get_by_query({"name": value}):
                return {'author_others': value}
            return {'author_parliamentarygroups': value}

    class DeputyFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'author_deputies': value}

    class IgnoreTaglessFieldParser():
        @staticmethod
        def get_search_for(key, value):
            if value:
                return {'tagged': {'$elemMatch': { 'tags.0': {'$exists': True}}}}
            return {}

    class CombinedDateFieldParser():
        @staticmethod
        def get_search_for(key, value):
            def parse_date(str_date):
                array_date = str_date.split('-')
                return datetime.datetime(int(array_date[0]), int(array_date[1]), int(array_date[2]), 0, 0, 0, 0)

            date_interval = value.split('_')
            STARTDATE = 0
            ENDDATE = 1
            if date_interval[STARTDATE] == '' and date_interval[ENDDATE] == '':
                return {}
            date_query = {'created': {}}
            if date_interval[STARTDATE] != '':
                if validate_date(date_interval[STARTDATE]):
                    date_query['created']['$gte'] = parse_date(date_interval[STARTDATE])
            if date_interval[ENDDATE] != '':
                if validate_date(date_interval[ENDDATE]):
                    date_query['created']['$lte'] = parse_date(date_interval[ENDDATE])
            return date_query

    PARSER_BY_PARAMS = {
        'topic': TopicFieldParser,
        'tags': CombinedTagsFieldParser,
        'author': AuthorFieldParser,
        'deputy': DeputyFieldParser,
        'date': CombinedDateFieldParser,
        'place': DefaultFieldParser,
        'reference': DefaultFieldParser(),
        'type': TypeFieldParser(),
        'status': DefaultFieldParser(),
        'text': TextFieldParser(),
        'ignoretagless': IgnoreTaglessFieldParser(),
    }

    def __init__(self, params):
        self._params = ParameterBag(params)
        self._per_page = self._params.get('per_page', int, 20, True)
        self._page = self._params.get('page', int, 1, True)
        self._serializer = self._params.get('serializer', str, '', True)
        self.kb = self._params.get_kb()

        self._params.join_tags()
        self._params.join_dates()
        self._params.parse(self.PARSER_BY_PARAMS)
        self._params.ignore_tagless()
        self._params.moveToTagged()

    @property
    def per_page(self):
        return self._per_page

    @property
    def page(self):
        return self._page

    @property
    def params(self):
        return self._params.all

    @property
    def serializer(self):
        if self._serializer == 'full':
            return InitiativeExtendedSchema
        if self._serializer == 'no-content':
            return InitiativeNoContentSchema
        return InitiativeSchema

class InitiativeParser():

    def __init__(self, params):
        self._params = ParameterBag(params)
        self._serializer = self._params.get('serializer')
        self.kb = self._params.get_kb()

    @property
    def serializer(self):
        if self._serializer == 'simple':
            return InitiativeSchema
        if self._serializer == 'full':
            return InitiativeExtendedSchema
        return InitiativeNoContentSchema
