"""Pydantic request models (replace the flask-restx reqparse parsers + api.model
serializers). Query models are used as FastAPI query-parameter dependencies; body
models as JSON request bodies.

The MongoDB query-building classes (SearchInitiativeParser, InitiativeParser,
ParameterBag, *FieldParser) remain in ``parsers.py`` — they consume the dict produced
by ``query.model_dump()``.
"""

from pydantic import BaseModel


class InitiativesQuery(BaseModel):
    page: int = 1
    per_page: int = 20
    text: str | None = None
    status: str | None = None
    type: list[str] | None = None
    reference: str | None = None
    place: str | None = None
    enddate: str | None = None
    startdate: str | None = None
    deputy: str | None = None
    author: str | None = None
    tags: list[str] | None = None
    subtopics: list[str] | None = None
    topic: str | None = None
    serializer: str | None = None
    knowledgebase: str | None = None
    ignoretagless: bool = False


class InitiativeQuery(BaseModel):
    serializer: str | None = None
    knowledgebase: str | None = None


class StatsQuery(BaseModel):
    topic: str
    subtopic: str | None = None
    knowledgebase: str | None = None


class StatsByTopicQuery(BaseModel):
    topic: str
    knowledgebase: str | None = None


class StatsByGroupQuery(BaseModel):
    parliamentarygroup: str
    knowledgebase: str | None = None


class AuthorsQuery(BaseModel):
    name: str | None = None
    compact: bool = False


class KbQuery(BaseModel):
    knowledgebase: str | None = None


class FootprintByTopicQuery(BaseModel):
    topic: str


class FootprintByDeputyQuery(BaseModel):
    deputy: str


class FootprintByParliamentaryGroupQuery(BaseModel):
    parliamentarygroup: str


class AlertBody(BaseModel):
    email: str
    search: str


class ScannedBody(BaseModel):
    title: str
    excerpt: str
    result: str
    verified: bool
    expiration: str | None = None
