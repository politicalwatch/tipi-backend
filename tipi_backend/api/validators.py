import re

from werkzeug.exceptions import BadRequest


def validate_date(date_str):
    if re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date_str) is None:
        raise BadRequest('Date format is invalid')
    return date_str
