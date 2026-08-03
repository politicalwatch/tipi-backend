"""Pydantic request models (replace the flask-restx reqparse parsers + api.model
serializers). Query models are used as FastAPI query-parameter dependencies; body
models as JSON request bodies.

The MongoDB query-building classes (SearchInitiativeParser, InitiativeParser,
ParameterBag, *FieldParser) remain in ``parsers.py`` — they consume the dict produced
by ``query.model_dump()``.
"""

from pydantic import BaseModel, Field


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


class SessionsQuery(BaseModel):
    page: int = 1
    per_page: int = 20
    legislature: str | None = None
    code: str | None = None
    startdate: str | None = None
    enddate: str | None = None


class SpeechesQuery(BaseModel):
    page: int = 1
    per_page: int = 20
    session: str | None = None
    reference: str | None = None
    speaker: str | None = None
    group: str | None = None
    legislature: str | None = None
    startdate: str | None = None
    enddate: str | None = None
    mention: str | None = None


class SpeechSearchQuery(BaseModel):
    """Natural-language semantic search. No ``page``: grouped vector search has no
    offset, so "show more" echoes the already-shown speech ids back as repeated
    ``exclude`` params and gets the next ``per_page`` fresh speeches."""

    q: str = Field(min_length=2)
    per_page: int = Field(default=12, ge=1, le=50)
    highlights: int = Field(default=3, ge=1, le=10)
    exclude: list[str] = Field(default_factory=list, max_length=500)


class SpeechPassagesQuery(BaseModel):
    """Every relevance-floored passage of one speech for a query (detail-page
    highlighting). No count param: the reranker floor bounds the set, not a cap."""

    q: str = Field(min_length=2)


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


class SearchRatingBody(BaseModel):
    """A user's rating of one speech search.

    ``query_meta`` is echoed back verbatim from the search response and stored as an
    opaque dict rather than modelled here: its shape belongs to the query parser, and
    the field we care about (``unresolved`` — the people it failed to recognise) would
    only get flattened by re-declaring it. The caps exist so a public endpoint can't be
    used to write unbounded documents.

    ``results_count`` is deliberately absent: it is derived from ``result_ids`` when
    saving, so a client cannot report a count that disagrees with the ids it sent.
    """

    rating: int = Field(ge=1, le=5)
    query: str = Field(min_length=1, max_length=500)
    query_meta: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list, max_length=10)
    comment: str | None = Field(default=None, max_length=500)
    result_ids: list[str] = Field(default_factory=list, max_length=100)
    corpus: str | None = None


class ScannedBody(BaseModel):
    title: str
    excerpt: str
    result: str
    verified: bool
    expiration: str | None = None
