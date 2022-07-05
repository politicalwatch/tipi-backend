import json

from os import environ as env
from flask import Blueprint, render_template 
from tipi_data.models.alert import Alert, Search


alerts_by_email_blueprint = Blueprint('manage_alerts_by_email', __name__)

def custom_render_template(template, name='QHLD'):
    return render_template(
            template,
            name=name
            )

def get_project_name(alert):
    searches = alert.searches
    search_str = searches[0].search
    search = json.loads(search_str)
    kb = search['knowledgebase']

    names = {
        'politicas': 'QHLD',
        'ods': 'Parlamento2030'
    }

    return names[kb]


@alerts_by_email_blueprint.route('/emails/validate/<hashed_email>/<hashed_search>', methods=['GET'])
def validate_email_alert(hashed_email, hashed_search):
    try:
        Alert.objects(
                id=hashed_email,
                searches__hash=hashed_search
            ).update_one(
                set__searches__S__validated=True,
                full_result=True
            )

        alert = Alert.objects(
                id=hashed_email,
                searches__hash=hashed_search
        ).first()

        if not alert:
            return custom_render_template('validate/validate_email_timeout.html')
        return custom_render_template('validate/validate_email_success.html', get_project_name(alert))
    except:
        return custom_render_template('validate/validate_email_error.html')


@alerts_by_email_blueprint.route('/emails/unsubscribe/<hashed_email>/<hashed_search>', methods=['GET'])
def unsubscribe_email_alert(hashed_email, hashed_search):
    try:
        Alert.objects(
                id=hashed_email,
                searches__hash=hashed_search
            ).update(
                pull__searches__hash=hashed_search,
                full_result=True
            )
        updated = Alert.objects(
                id=hashed_email,
                searches__hash=hashed_search
        ).first()
        if not updated:
            return custom_render_template('unsubscribe/unsubscribe_email_error.html')
        return custom_render_template('unsubscribe/unsubscribe_email_success.html', get_project_name(alert))
    except Alert.DoesNotExist:
        return custom_render_template('unsubscribe/unsubscribe_email_error.html')
    except Alert.MultipleObjectsReturned:
        return custom_render_template('unsubscribe/unsubscribe_email_error.html')
