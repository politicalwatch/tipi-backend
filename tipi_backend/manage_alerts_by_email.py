from os import environ as env
from flask import Blueprint, render_template 
from tipi_data.models.alert import Alert, Search


alerts_by_email_blueprint = Blueprint('manage_alerts_by_email', __name__)

def custom_render_template(template):
    return render_template(
            template,
            name=env.get('NAME', 'test')
            )


@alerts_by_email_blueprint.route('/emails/validate/<hashed_email>/<hashed_search>', methods=['GET'])
def validate_email_alert(hashed_email, hashed_search):
    try:
        updated_documents = Alert.objects(
                id=hashed_email,
                searches__hash=hashed_search
            ).update_one(
                set__searches__S__validated=True
            )

        if not updated_documents:
            return custom_render_template('validate/validate_email_timeout.html')
        return custom_render_template('validate/validate_email_success.html')
    except:
        return custom_render_template('validate/validate_email_error.html')


@alerts_by_email_blueprint.route('/emails/unsubscribe/<hashed_email>/<hashed_search>', methods=['GET'])
def unsubscribe_email_alert(hashed_email, hashed_search):
    try:
        alert = Alert.objects.get(
                id=hashed_email,
                searches__hash=hashed_search
                )
        updated = alert.update(pull__searches__hash=hashed_search)
        if not updated:
            return custom_render_template('unsubscribe/unsubscribe_email_error.html')
        return custom_render_template('unsubscribe/unsubscribe_email_success.html')
    except Alert.DoesNotExist:
        return custom_render_template('unsubscribe/unsubscribe_email_error.html')
    except Alert.MultipleObjectsReturned:
        return custom_render_template('unsubscribe/unsubscribe_email_error.html')
