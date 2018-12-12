from flask import Blueprint, render_template 

from tipi_backend.database.models.alert import Alert, Search
from tipi_backend import settings


validate_emails_blueprint = Blueprint('validate_emails', __name__)

@validate_emails_blueprint.route('/validate-email/<hashed_email>/<hashed_search>', methods=['GET'])
def validate_email_alert(hashed_email, hashed_search):
    alert = Alert.objects(
            id=hashed_email,
            searches__hash=hashed_search
            )

    if not alert:
        return render_template( 'validate_email_timedout.html', name=settings.NAME)

    result = Alert.objects(
            id=hashed_email,
            searches__hash=hashed_search
        ).update_one(
            set__searches__S__validated=True
        )

    if not result:
        return render_template( 'validate_email_error.html', name=settings.NAME)
    return render_template( 'validate_email_success.html', name=settings.NAME)

