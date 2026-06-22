import re

from fastapi import HTTPException


def validate_date(date_str):
    if re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date_str) is None:
        raise HTTPException(status_code=400, detail='Date format is invalid')
    return date_str
