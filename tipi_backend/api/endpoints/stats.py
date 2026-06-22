import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api.business import (
    get_overall_stats,
    get_lastdays_stats,
    get_deputies_stats,
    get_parliamentarygroups_stats,
    get_places_stats,
    get_topics_by_parliamentarygroup_stats,
    get_by_week_stats,
    get_topics_by_week_stats,
)
from tipi_backend.api.request_models import KbQuery, StatsQuery, StatsByTopicQuery, StatsByGroupQuery


log = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overall")
def overall_stats(query: Annotated[KbQuery, Query()]):
    """Returns overall stats."""
    return get_overall_stats(query.model_dump())


@router.get("/lastdays")
def lastdays_stats(query: Annotated[KbQuery, Query()]):
    """Returns last days stats."""
    return get_lastdays_stats(query.model_dump())


@router.get("/deputies")
def deputies_stats(query: Annotated[StatsQuery, Query()]):
    """Returns top ten deputies by topics (and/or subtopics)."""
    return get_deputies_stats(query.model_dump())


@router.get("/parliamentarygroups")
def parliamentarygroups_stats(query: Annotated[StatsQuery, Query()]):
    """Returns ranking of parliamentary groups by topics (and/or subtopics)."""
    return get_parliamentarygroups_stats(query.model_dump())


@router.get("/places")
def places_stats(query: Annotated[StatsQuery, Query()]):
    """Returns top five places by topics (and/or subtopics)."""
    return get_places_stats(query.model_dump())


@router.get("/topics-by-parliamentarygroup")
def topics_by_parliamentarygroup_stats(query: Annotated[StatsByGroupQuery, Query()]):
    """Returns ranking of topics by parliamentary group."""
    result = get_topics_by_parliamentarygroup_stats(query.model_dump())
    if isinstance(result, tuple):
        body, status = result
        return JSONResponse(status_code=status, content=body)
    return result


@router.get("/by-week")
def by_week_stats():
    """Returns initiatives by week stats."""
    return get_by_week_stats()


@router.get("/topics-by-week")
def topics_by_week_stats(query: Annotated[StatsByTopicQuery, Query()]):
    """Returns topics' initiatives by week stats."""
    return get_topics_by_week_stats(query.model_dump())
