import json
import logging
import os

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from tipi_data.models.alert import Alert


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
        Alert.objects(
            id=hashed_email, searches__hash=hashed_search
        ).update_one(set__searches__S__validated=True, full_result=True)

        alert = Alert.objects(
            id=hashed_email, searches__hash=hashed_search
        ).first()

        if not alert:
            return render(request, "validate/validate_email_timeout.html")
        return render(request, "validate/validate_email_success.html", get_project_name(alert))
    except Exception as e:
        log.error(e)
        return render(request, "validate/validate_email_error.html")


@router.get("/unsubscribe/{hashed_email}/{hashed_search}")
def unsubscribe_email_alert(request: Request, hashed_email: str, hashed_search: str):
    try:
        alert = Alert.objects(
            id=hashed_email, searches__hash=hashed_search
        ).first()
        Alert.objects(
            id=hashed_email, searches__hash=hashed_search
        ).update(pull__searches__hash=hashed_search, full_result=True)
        return render(request, "unsubscribe/unsubscribe_email_success.html", get_project_name(alert))
    except Alert.DoesNotExist:
        log.error("Alert to unsubscribe does not exist")
        return render(request, "unsubscribe/unsubscribe_email_error.html")
    except Alert.MultipleObjectsReturned:
        log.error("Multiple object returned when unsubscribing the alert")
        return render(request, "unsubscribe/unsubscribe_email_error.html")
