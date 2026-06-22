"""Serialize Pydantic output schemas to plain JSON-ready structures.

``exclude_none=True`` reproduces the old marshmallow ``model_skip_values=[None]``
(drop ``None`` scalars; keep empty lists). Returning plain dicts/lists from routes
(instead of using a ``response_model``) avoids Pydantic union mis-coercion across the
deputy/group compact-vs-full and the three initiative serializer variants. FastAPI's
JSON encoder still renders datetimes as ISO strings, matching the previous output.
"""

from pydantic import BaseModel


def serialize(value):
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True)
    if isinstance(value, list):
        return [serialize(v) for v in value]
    return value
