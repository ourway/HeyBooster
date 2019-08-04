import flask
from flask import jsonify
import googleapiclient.discovery
from google_auth import build_credentials, get_user_info

app = flask.Blueprint('google_analytics', __name__)


def build_management_api_v3():
    credentials = build_credentials()
    return googleapiclient.discovery.build('analytics', 'v3', credentials=credentials)


def build_reporting_api_v4():
    credentials = build_credentials()
    return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)


@app.route("/analytics/accounts")
def get_accounts():
    service = build_management_api_v3()
    # Use the Analytics service object to get the first profile id.
    # Get a list of all Google Analytics accounts for this user
    accs = service.management().accounts().list().execute()
    accounts = []
    if accs.get('items'):
        for acc in accs.get('items'):
            accounts.append({'id': acc.get('id'), 'name': acc.get('name')})
    return {'accounts': accounts}


@app.route("/analytics/properties/<accountId>")
def get_properties(accountId):
    service = build_management_api_v3()
    # Get a list of all the properties for the first account.
    props = service.management().webproperties().list(
        accountId=accountId).execute()
    properties = []
    if props.get('items'):
        # Get the first property id.
        for prop in props.get('items'):
            properties.append({'id': prop.get('id'), 'name': prop.get('name')})
        return jsonify({'properties': properties})


@app.route("/analytics/views/<accountId>/<propertyId>")
def get_views(accountId, propertyId):
    service = build_management_api_v3()
    # Get a list of all views (profiles) for the first property.
    profiles = service.management().profiles().list(
        accountId=accountId,
        webPropertyId=propertyId).execute()
    views = []
    if profiles.get('items'):
        # return the first view (profile) id.
        for prof in profiles.get('items'):
            views.append({'id': prof.get('id'), 'name': prof.get('name')})
        return jsonify({'views': views})


def get_results(profile_id):
    service = build_management_api_v3()
    # Use the Analytics Service Object to query the Core Reporting API
    # for the number of sessions within the last seven days.
    return service.data().ga().get(
        ids='ga:' + profile_id,
        start_date='6daysAgo',
        end_date='today',
        metrics='ga:sessions').execute()
