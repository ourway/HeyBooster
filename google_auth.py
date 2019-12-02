import functools

import flask
import os
from models.user import User
from authlib.client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery
import google_analytics
from database import db
import requests
import segmentationOfAnalytics


TOKEN_INFO_URI = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'
ACCESS_TOKEN_URI = 'https://www.googleapis.com/oauth2/v4/token'
AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent'

GA_CONNECT_AUTHORIZATION_SCOPE = ['profile', 'email', 'https://www.googleapis.com/auth/analytics.readonly']
GSC_CONNECT_AUTHORIZATION_SCOPE = ['profile', 'email', 'https://www.googleapis.com/auth/webmasters.readonly']
ADW_CONNECT_AUTHORIZATION_SCOPE = ['profile', 'email', 'https://www.googleapis.com/auth/adwords']
LOGIN_AUTHORIZATION_SCOPE = ['profile', 'email']

DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

LOGINAUTH_REDIRECT_URI = "https://{DOMAIN_NAME}/google/loginauth"
GA_CONNECTAUTH_REDIRECT_URI = "https://{DOMAIN_NAME}/google/connectauth"
GSC_CONNECTAUTH_REDIRECT_URI = "https://{DOMAIN_NAME}/google/gscconnectauth"
ADW_CONNECTAUTH_REDIRECT_URI = "https://{DOMAIN_NAME}/google/adwconnectauth"
BASE_URI = "https://{DOMAIN_NAME}/getstarted/connect-accounts"

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID').strip()
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET').strip()

AUTH_TOKEN_KEY = 'auth_token'
AUTH_STATE_KEY = 'auth_state'

app = flask.Blueprint('google_auth', __name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


def is_logged_in():
    return True if AUTH_TOKEN_KEY in flask.session else False


def build_credentials():
    if not is_logged_in():
        raise Exception('User must be logged in')

    oauth2_tokens = flask.session[AUTH_TOKEN_KEY]

    return google.oauth2.credentials.Credentials(
        oauth2_tokens['access_token'],
        refresh_token=oauth2_tokens['refresh_token'],
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri=ACCESS_TOKEN_URI)



def build_credentials_woutSession(email):
    oauth2_tokens = {}
    user = db.find_one('user', {'email': email})
    
    
    resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken']))
    if ('error' in resp.json().keys()):
        data = [('client_id', CLIENT_ID.strip()),
                ('client_secret', CLIENT_SECRET.strip()),
                ('refresh_token', user['ga_refreshtoken']),
                ('grant_type', 'refresh_token')]
        resp = requests.post(ACCESS_TOKEN_URI, data).json()
        print(resp)
        db.find_and_modify('user', query={'email': email}, ga_accesstoken=resp['access_token'])
        oauth2_tokens['access_token'] = resp['access_token']
    else:
        oauth2_tokens['access_token'] = user['ga_accesstoken']

    oauth2_tokens['refresh_token'] = user['ga_refreshtoken']

    return google.oauth2.credentials.Credentials(
        oauth2_tokens['access_token'],
        refresh_token=oauth2_tokens['refresh_token'],
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri=ACCESS_TOKEN_URI)


def get_user_info():
    credentials = build_credentials()

    oauth2_client = googleapiclient.discovery.build(
        'oauth2', 'v2',
        credentials=credentials)

    return oauth2_client.userinfo().get().execute()

def get_user_info_woutSession(email):
    credentials = build_credentials_woutSession(email)

    oauth2_client = googleapiclient.discovery.build(
        'oauth2', 'v2',
        credentials=credentials)

    return oauth2_client.userinfo().get().execute()

def no_cache(view):
    @functools.wraps(view)
    def no_cache_impl(*args, **kwargs):
        response = flask.make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return functools.update_wrapper(no_cache_impl, view)


@app.route('/google/login')
#@no_cache
def login():
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=LOGIN_AUTHORIZATION_SCOPE,
                            redirect_uri=LOGINAUTH_REDIRECT_URI)

    uri, state = session.authorization_url(AUTHORIZATION_URL)
    flask.session[AUTH_STATE_KEY] = state
    flask.session.permanent = True

    return flask.redirect(uri, code=302)


@app.route('/google/loginauth')
#@no_cache
def google_loginauth_redirect():
    req_state = flask.request.args.get('state', default=None, type=None)
    if req_state != flask.session[AUTH_STATE_KEY]:
        response = flask.make_response('Invalid state parameter', 401)
        return response

    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=LOGIN_AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=LOGINAUTH_REDIRECT_URI)

    oauth2_tokens = session.fetch_access_token(
        ACCESS_TOKEN_URI,
        authorization_response=flask.request.url)

    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens
    user_info = get_user_info()
    flask.session['email'] = user_info['email']
#    new_user = User(name=user_info['name'], email=flask.session['email'], password="")
    try:
        name = user_info['name']
    except:
        name = ""
    try:
        firstname = user_info['given_name']
    except:
        firstname = ""
    try:
        lastname = user_info['family_name']
    except:
        lastname = ""
    new_user = User(name = name,
                    firstname=firstname, 
                    lastname = lastname, 
                    email=flask.session['email'], 
                    password="")
    new_user.insert()
    user = db.find_one('user', {'email': user_info['email']})
    flask.session['sl_accesstoken'] = user['sl_accesstoken']
    flask.session['ga_accesstoken'] = user['ga_accesstoken']
    return flask.redirect(BASE_URI, code=302)


@app.route('/google/connect')
#@no_cache
def gaconnect():
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=GA_CONNECT_AUTHORIZATION_SCOPE,
                            redirect_uri=GA_CONNECTAUTH_REDIRECT_URI)

    uri, state = session.authorization_url(AUTHORIZATION_URL)
    flask.session[AUTH_STATE_KEY] = state
    flask.session.permanent = True

    return flask.redirect(uri, code=302)


@app.route('/google/connectauth')
#@no_cache
def google_gaconnectauth_redirect():
    req_state = flask.request.args.get('state', default=None, type=None)
    if req_state != flask.session[AUTH_STATE_KEY]:
        response = flask.make_response('Invalid state parameter', 401)
        return response

    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=GA_CONNECT_AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=GA_CONNECTAUTH_REDIRECT_URI)
    try:
        oauth2_tokens = session.fetch_access_token(
            ACCESS_TOKEN_URI,
            authorization_response=flask.request.url)
    except:
        return flask.redirect(BASE_URI, code=302)

    # Obtain current analytics account email
    user = db.find_one('user', {'email': flask.session['email']})
    if (user['ga_accesstoken']):
#        resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
#        if ('error' in resp.keys()):
#            data = [('client_id', CLIENT_ID.strip()),
#                    ('client_secret', CLIENT_SECRET.strip()),
#                    ('refresh_token', user['ga_refreshtoken']),
#                    ('grant_type', 'refresh_token')]
#            resp = requests.post(ACCESS_TOKEN_URI, data).json()
#            resp = requests.get(TOKEN_INFO_URI.format(resp['access_token'])).json()
#        current_analyticsemail = resp['email']
        current_analyticsemail = user['ga_email']

#        # Obtain new analytics account email and
#        user_info = get_user_info()
#        new_analyticsemail = user_info['email']
        resp = requests.get(TOKEN_INFO_URI.format(oauth2_tokens['access_token'])).json()
        new_analyticsemail = resp['email']
        # Compare them
        if (current_analyticsemail != new_analyticsemail):
            # If emails are not same, remove old datasources
            db.DATABASE['datasource'].remove({'email': user['email']})
            db.DATABASE['notification'].remove({'email': user['email']})
    else:
        resp = requests.get(TOKEN_INFO_URI.format(oauth2_tokens['access_token'])).json()
        new_analyticsemail = resp['email']
    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens
    db.find_and_modify(collection='user', query={'_id': user['_id']},
                       ga_accesstoken=oauth2_tokens['access_token'],
                       ga_refreshtoken=oauth2_tokens['refresh_token'],
                       ga_email = new_analyticsemail)
    flask.session['ga_accesstoken'] = oauth2_tokens['access_token']
    #    viewId = google_analytics.get_first_profile_id()
    #    db.find_and_modify(collection='user', query={'email': flask.session['email']}, viewId=viewId)
    
    #User Segmentation
#    segmentationOfAnalytics.segmentationOfAnalytics(flask.session['email'])
    return flask.redirect(BASE_URI, code=302)


@app.route('/google/gscconnect')
#@no_cache
def gscconnect():
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=GSC_CONNECT_AUTHORIZATION_SCOPE,
                            redirect_uri=GSC_CONNECTAUTH_REDIRECT_URI)

    uri, state = session.authorization_url(AUTHORIZATION_URL)
    flask.session[AUTH_STATE_KEY] = state
    flask.session.permanent = True

    return flask.redirect(uri, code=302)


@app.route('/google/gscconnectauth')
#@no_cache
def google_gscconnectauth_redirect():
    req_state = flask.request.args.get('state', default=None, type=None)
    if req_state != flask.session[AUTH_STATE_KEY]:
        response = flask.make_response('Invalid state parameter', 401)
        return response

    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=GSC_CONNECT_AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=GSC_CONNECTAUTH_REDIRECT_URI)
    try:
        oauth2_tokens = session.fetch_access_token(
            ACCESS_TOKEN_URI,
            authorization_response=flask.request.url)
    except:
        return flask.redirect(BASE_URI, code=302)

    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens
    db.find_and_modify(collection='user', query={'email': flask.session['email']},
                       gsc_accesstoken=oauth2_tokens['access_token'],
                       gsc_refreshtoken=oauth2_tokens['refresh_token'])
    return flask.redirect(BASE_URI, code=302)


@app.route('/google/adwconnect')
#@no_cache
def adwconnect():
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=ADW_CONNECT_AUTHORIZATION_SCOPE,
                            redirect_uri=ADW_CONNECTAUTH_REDIRECT_URI)

    uri, state = session.authorization_url(AUTHORIZATION_URL)
    flask.session[AUTH_STATE_KEY] = state
    flask.session.permanent = True

    return flask.redirect(uri, code=302)


@app.route('/google/adwconnectauth')
#@no_cache
def google_adwconnectauth_redirect():
    req_state = flask.request.args.get('state', default=None, type=None)
    if req_state != flask.session[AUTH_STATE_KEY]:
        response = flask.make_response('Invalid state parameter', 401)
        return response

    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=ADW_CONNECT_AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=ADW_CONNECTAUTH_REDIRECT_URI)
    try:
        oauth2_tokens = session.fetch_access_token(
            ACCESS_TOKEN_URI,
            authorization_response=flask.request.url)
    except:
        return flask.redirect(BASE_URI, code=302)

    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens
    db.find_and_modify(collection='user', query={'email': flask.session['email']},
                       adw_accesstoken=oauth2_tokens['access_token'],
                       adw_refreshtoken=oauth2_tokens['refresh_token'])
    return flask.redirect(BASE_URI, code=302)


@app.route('/google/logout')
#@no_cache
def logout():
    flask.session.pop(AUTH_TOKEN_KEY, None)
    flask.session.pop(AUTH_STATE_KEY, None)

    return flask.redirect(BASE_URI, code=302)
