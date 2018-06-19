import re
import datetime
from webargs import fields

from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup
from tipi_backend.api.managers.initiative_type import InitiativeTypeManager
from tipi_backend.api.validators import validate_date


detail_args = {
        'id': fields.String(required=True,location='view_args')
        }


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

    class TagFieldParser():
        @staticmethod
        def get_search_for(key, value):
            return {'tags': {'$elemMatch': {'tag': value}}}

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

    parser_by_params = {
            'topic': TopicFieldParser,
            'tags': TagFieldParser,
            'author': AuthorFieldParser,
            'deputy': DeputyFieldParser,
            'date': CombinedDateFieldParser,
            'place': DefaultFieldParser,
            'reference': DefaultFieldParser(),
            'type': TypeFieldParser(),
            'status': DefaultFieldParser(),
            'title': TitleFieldParser(),
            }

    def __init__(self, params):
        self._params = params.to_dict()
        self._limit = self._return_attr_in_params(attrname='limit', type=int, default=20, clean=True)
        self._offset = self._return_attr_in_params(attrname='offset', type=int, default=0, clean=True)
        self._join_dates_in_params()
        self._parse_params()

    def _parse_params(self):
        temp_params = self._params.copy()
        for key, value in temp_params.items():
            del self._params[key]
            self._params.update(self.parser_by_params[key].get_search_for(key, value))

    def _return_attr_in_params(self, attrname='', type=str, default='', clean=False):
        if attrname in self._params:
            attr = self._params[attrname]
            if clean:
                self._clean_params_for_attr(attrname)
            return type(attr)
        return default

    def _clean_params_for_attr(self, attrname=''):
        if attrname in self._params:
            self._params.pop(attrname)

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
    def limit(self):
        return self._limit

    @property
    def offset(self):
        return self._offset

    @property
    def params(self):
        return self._params


