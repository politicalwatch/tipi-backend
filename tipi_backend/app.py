import logging
import logging.config
import os

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from tipi_data import DoesNotExist

from tipi_backend.infrastructure.config.settings import get_settings
from tipi_backend.api.business import get_dataset_updates
from tipi_backend.api.ratelimit import limiter
from tipi_backend.api.endpoints.topics import router as topics_router
from tipi_backend.api.endpoints.deputies import router as deputies_router
from tipi_backend.api.endpoints.parliamentarygroups import router as parliamentarygroups_router
from tipi_backend.api.endpoints.initiatives import router as initiatives_router
from tipi_backend.api.endpoints.initiative_types import router as initiativetypes_router
from tipi_backend.api.endpoints.initiative_status import router as initiativestatus_router
from tipi_backend.api.endpoints.places import router as places_router
from tipi_backend.api.endpoints.stats import router as stats_router
from tipi_backend.api.endpoints.footprint import router as footprint_router
from tipi_backend.api.endpoints.voting import router as voting_router
from tipi_backend.api.endpoints.tagger import router as tagger_router
from tipi_backend.api.endpoints.scanned import router as scanned_router
from tipi_backend.api.endpoints.sessions import router as sessions_router
from tipi_backend.api.endpoints.search import router as search_router
from tipi_backend.api.endpoints.search_ratings import router as search_ratings_router
from tipi_backend.api.endpoints.speeches import router as speeches_router
from tipi_backend.api.endpoints.alerts import router as alerts_router
from tipi_backend.manage_alerts_by_email import router as emails_router


log = logging.getLogger(__name__)

# (namespace name, router) — namespace names preserved for EXCLUDE_NAMESPACES parity.
ROUTERS = [
    ("topics", topics_router),
    ("deputies", deputies_router),
    ("parliamentary-groups", parliamentarygroups_router),
    ("initiatives", initiatives_router),
    ("initiative-types", initiativetypes_router),
    ("initiative-status", initiativestatus_router),
    ("places", places_router),
    ("stats", stats_router),
    ("footprint", footprint_router),
    ("voting", voting_router),
    ("tagger", tagger_router),
    ("scanned", scanned_router),
    ("sessions", sessions_router),
    # search before speeches: both mount under /speeches, and /speeches/{id}
    # would otherwise capture "/speeches/search".
    ("search", search_router),
    ("speeches", speeches_router),
    # "ratings", not "search-ratings": the exclusion check below is a substring test
    # against the whole env string, so a namespace containing "search" would make
    # EXCLUDE_NAMESPACES=search-ratings silently drop the semantic search router too.
    ("ratings", search_ratings_router),
]


def _configure_logging():
    logging_conf_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../logging.conf")
    )
    logging.config.fileConfig(logging_conf_path, disable_existing_loggers=False)


def create_app():
    _configure_logging()

    settings = get_settings()

    name = settings.name
    description = settings.description.format(name)
    version = settings.version

    app = FastAPI(title="{} API Documentation".format(name), description=description, version=version)

    # --- Middleware (CORS mirrors the previous allow-all default; GZip mirrors Flask-Compress) ---
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_content_length:
            return JSONResponse(
                status_code=413, content={"message": "Request entity too large."}
            )
        return await call_next(request)

    # --- Rate limiting (slowapi) ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- Error handlers (parity with the old flask-restx handlers) ---
    @app.exception_handler(DoesNotExist)
    async def database_not_found_error_handler(request: Request, exc):
        log.warning("Resource not found", exc_info=exc)
        return JSONResponse(status_code=404, content={"message": "Resource not found."})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc):
        # flask-restx reqparse returned 400 (not FastAPI's default 422).
        return JSONResponse(
            status_code=400,
            content={"message": "Input payload validation failed", "errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def default_error_handler(request: Request, exc):
        message = "An unhandled exception occurred."
        log.exception(message)
        return JSONResponse(status_code=500, content={"message": message})

    # --- Root status (so `/` returns a friendly 200 instead of 404; docs live at /docs) ---
    @app.get("/", tags=["status"])
    def root():
        """Service status and how fresh the data is: ``last_updated`` is the most
        recent of the per-dataset extraction timestamps in ``datasets`` (null until
        the engine has run once)."""
        return {
            "status": "ok",
            **get_dataset_updates(),
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    # --- Routers (root-mounted; honor EXCLUDE_NAMESPACES) ---
    excluded = settings.exclude_namespaces
    for ns_name, router in ROUTERS:
        if ns_name in excluded:
            continue
        app.include_router(router)

    if settings.use_alerts:
        if "alerts" not in excluded:
            app.include_router(alerts_router)
        app.include_router(emails_router)

    return app


def main():
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "tipi_backend.wsgi:app",
        host=config_host(),
        port=settings.port,
        reload=settings.debug,
    )


def config_host():
    return get_settings().ip


if __name__ == "__main__":
    main()
