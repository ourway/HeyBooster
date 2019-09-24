import flask
from flask import jsonify, session
import googleapiclient.discovery
import google_auth
from database import db

app = flask.Blueprint('google_analytics', __name__)


def build_management_api_v3():
    credentials = google_auth.build_credentials()
    return googleapiclient.discovery.build('analytics', 'v3', credentials=credentials)


def build_management_api_v3_woutSession(email):
    credentials = google_auth.build_credentials_woutSession(email)
    return googleapiclient.discovery.build('analytics', 'v3', credentials=credentials)


def build_reporting_api_v4():
    credentials = google_auth.build_credentials()
    return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)


def build_reporting_api_v4_woutSession(email):
    credentials = google_auth.build_credentials_woutSession(email)
    return googleapiclient.discovery.build('analyticsreporting', 'v4', credentials=credentials)


@app.route("/analytics/accounts")
def get_accounts(email):
    service = build_management_api_v3_woutSession(email)
    # Use the Analytics service object to get the first profile id.
    # Get a list of all Google Analytics accounts for this user
    try:
        accs = service.management().accounts().list().execute()
        accounts = []
        if accs.get('items'):
            for acc in accs.get('items'):
                accounts.append({'id': acc.get('id'), 'name': acc.get('name')})
    except:
        accounts = []
    return {'accounts': accounts}

@app.route("/analytics/properties/<accountId>")
def get_properties(accountId):
    email = session['email']
    service = build_management_api_v3_woutSession(email)
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
    email = session['email']
    service = build_management_api_v3_woutSession(email)
    # Get a list of all views (profiles) for the first property.
    profiles = service.management().profiles().list(
        accountId=accountId,
        webPropertyId=propertyId).execute()
    views = []
    if profiles.get('items'):
        # return the first view (profile) id.
        for prof in profiles.get('items'):
            views.append({'id': prof.get('id')+'\u0007'+prof.get('currency'), 'name': prof.get('name')})
        return jsonify({'views': views})


def get_results(form):
    service = build_management_api_v3()
    viewId = form.view.data
    start_date = form.start_date.data.strftime('%Y-%m-%d')
    end_date = form.end_date.data.strftime('%Y-%m-%d')
    metric = form.metric.data
    dimension = form.dimension.data
    results = service.data().ga().get(
        ids='ga:' + viewId,
        start_date=start_date,
        end_date=end_date,
        metrics=metric,
        dimensions=dimension).execute()
    return str(results.get('rows'))


def get_first_profile_id():
    # Use the Analytics service object to get the first profile id.
    service = build_management_api_v3()
    # Get a list of all Google Analytics accounts for this user
    accounts = service.management().accounts().list().execute()
    if accounts.get('items'):
        # Get the first Google Analytics account.
        account = accounts.get('items')[0].get('id')
        # Get a list of all the properties for the first account.
        properties = service.management().webproperties().list(
            accountId=account).execute()
        if properties.get('items'):
            # Get the first property id.
            property = properties.get('items')[0].get('id')
            # Get a list of all views (profiles) for the first property.
            profiles = service.management().profiles().list(
                accountId=account,
                webPropertyId=property).execute()
            if profiles.get('items'):
                # return the first view (profile) id.
                return profiles.get('items')[0].get('id')
    return None

