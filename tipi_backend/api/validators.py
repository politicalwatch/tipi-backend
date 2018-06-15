import re

from werkzeug.exceptions import BadRequest


def validate_id_as_hash(get_func):
    """
    IDs are generated by the crawlers. They are 40 hexadecimal characters long
    """
    def wrapper_func(self, id):
        if re.match(r'^[a-f0-9]{40}$', id) is None:
            raise BadRequest('ID format is invalid')
        return get_func(self, id)
    return wrapper_func

def validate_date(date_str):
    if re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date_str) is None:
        raise BadRequest('Date format is invalid')
    return date_str
