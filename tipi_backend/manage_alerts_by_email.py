import json
import logging
import os

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from tipi_data.repositories.alerts import Alerts


log = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"], include_in_schema=False)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


def render(request, template, name="QHLD"):
    return templates.TemplateResponse(request, template, {"name": name})


def get_project_name(alert):
    searches = alert.searches
    search_str = searches[0].search
    search = json.loads(search_str)
    kb = search["knowledgebase"]

    names = {
        "politicas": "QHLD",
        "ods": "Parlamento2030",
    }

    return names[kb]


@router.get("/validate/{hashed_email}/{hashed_search}")
def validate_email_alert(request: Request, hashed_email: str, hashed_search: str):
    try:
        Alerts.validate_search(hashed_email, hashed_search)
        alert = Alerts.get_by_id_and_search(hashed_email, hashed_search)

        if not alert:
            return render(request, "validate/validate_email_timeout.html")
        return render(request, "validate/validate_email_success.html", get_project_name(alert))
    except Exception as e:
        log.error(e)
        return render(request, "validate/validate_email_error.html")


@router.get("/unsubscribe/{hashed_email}/{hashed_search}")
def unsubscribe_email_alert(request: Request, hashed_email: str, hashed_search: str):
    alert = Alerts.get_by_id_and_search(hashed_email, hashed_search)
    if not alert:
        log.error("Alert to unsubscribe does not exist")
        return render(request, "unsubscribe/unsubscribe_email_error.html")
    Alerts.remove_search(hashed_search)
    return render(request, "unsubscribe/unsubscribe_email_success.html", get_project_name(alert))
