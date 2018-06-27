import re
import datetime
from flask_restplus import reqparse

from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup
from tipi_backend.api.managers.initiative_type import InitiativeTypeManager
from tipi_backend.api.validators import validate_date


parser_initiative = reqparse.RequestParser()
# Common parameters
parser_initiative.add_argument('page', type=int, default=1, location='args', help='Page number')
parser_initiative.add_argument('per_page', type=int, default=20, location='args', help='Initiatives per page')
# Initiative parameters
parser_initiative.add_argument('title', type=str, location='args')
parser_initiative.add_argument('status', type=str, location='args', help='To get the values, check out /initiative-status')
parser_initiative.add_argument('type', type=str, location='args', help='To get the values, check out /initiative-type')
parser_initiative.add_argument('reference', type=str, location='args')
parser_initiative.add_argument('place', type=str, location='args')
parser_initiative.add_argument('enddate', type=str, location='args', help='Date format must be yyyy-mm-dd')
parser_initiative.add_argument('startdate', type=str, location='args', help='Date format must be yyyy-mm-dd')
parser_initiative.add_argument('deputy', type=str, location='args', help='To get the values, check out /deputies')
parser_initiative.add_argument('author', type=str, location='args', help='To get the values, check out /parliamentary-groups')
parser_initiative.add_argument('subtopics', type=str, action='append', location='args', help='To get the values, check out /topics/id')
parser_initiative.add_argument('topic', type=str, location='args', help='To get the values, check out /topics')



class SearchInitiativeParser:

    class DefaultFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {key: value}

    class TitleFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {key: {'$regex': value, '$options': 'gi'}}

    class TypeFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return InitiativeTypeManager().get_search_for(value)

    class TopicFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'topics': value}

    class SubtopicFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'tags': {'$elemMatch': {'subtopic': {'$in': value}}}}

    class AuthorFieldParser():
        @staticmethod
        def get_search_for(key, value):
            if not ParliamentaryGroup.objects(name=value):
                return {'author_others': value}
            return {'author_parliamentarygroups': value}

    class DeputyFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'author_deputies': value}

    class CombinedDateFieldParser():
        @staticmethod
        def get_search_for(key, value):
            def parse_date(str_date):
                array_date = str_date.split('-')
                return datetime.datetime(int(array_date[0]), int(array_date[1]), int(array_date[2]), 0,0,0,0)

            date_interval = value.split('_')
            STARTDATE = 0
            ENDDATE = 1
            if date_interval[STARTDATE] is '' and date_interval[ENDDATE] is '':
                return {}
            date_query = {'updated': {}}
            if date_interval[STARTDATE] is not '':
                if validate_date(date_interval[STARTDATE]):
                    date_query['updated']['$gte'] = parse_date(date_interval[STARTDATE])
            if date_interval[ENDDATE] is not '':
                if validate_date(date_interval[ENDDATE]):
                    date_query['updated']['$lte'] = parse_date(date_interval[ENDDATE])
            return date_query

    PARSER_BY_PARAMS = {
            'topic': TopicFieldParser,
            'subtopics': SubtopicFieldParser,
            'author': AuthorFieldParser,
            'deputy': DeputyFieldParser,
            'date': CombinedDateFieldParser,
            'place': DefaultFieldParser,
            'reference': DefaultFieldParser(),
            'type': TypeFieldParser(),
            'status': DefaultFieldParser(),
            'title': TitleFieldParser(),
            }

    EMPTY_VALUES = ['', None, []]

    def __init__(self, params):
        self._params = params
        self._clean_params()
        self._per_page = self._return_attr_in_params(attrname='per_page', type=int, default=20, clean=True)
        self._page = self._return_attr_in_params(attrname='page', type=int, default=1, clean=True)
        self._join_dates_in_params()
        self._parse_params()

    def _clean_params(self):
        for key, value in self._params.copy().items():
            if value in self.EMPTY_VALUES:
                self._clean_params_for_attr(key)

    def _parse_params(self):
        temp_params = self._params.copy()
        for key, value in temp_params.items():
            del self._params[key]
            self._params.update(self.PARSER_BY_PARAMS[key].get_search_for(key, value))

    def _return_attr_in_params(self, attrname='', type=str, default='', clean=False):
        if attrname in self._params:
            attr = self._params[attrname]
            if clean:
                self._clean_params_for_attr(attrname)
            return type(attr)
        return default

    def _clean_params_for_attr(self, attrname=''):
        if attrname in self._params:
            del self._params[attrname]

    def _join_dates_in_params(self):
        if not 'startdate' in self._params:
            self._params['startdate'] = ''
        if not 'enddate' in self._params:
            self._params['enddate'] = ''
        self._params['date'] = "{}_{}".format(
                self._params['startdate'],
                self._params['enddate']
                )
        self._clean_params_for_attr('startdate')
        self._clean_params_for_attr('enddate')


    @property
    def per_page(self):
        return self._per_page

    @property
    def page(self):
        return self._page

    @property
    def params(self):
        return self._params
