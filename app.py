from flask import Flask, render_template, flash, redirect, request, session, url_for, make_response, jsonify, send_file, \
    render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from forms import LoginForm, RegisterForm, DataSourceForm
from flask_dance.contrib.slack import make_slack_blueprint, slack
import google_auth
import google_analytics
from database import db, db2
from slack_auth import authorized
from flask_dance.consumer import OAuth2ConsumerBlueprint
from datetime import datetime, timedelta, timezone
import json
from slack import WebClient
import os
import requests
import time
from modules import performancegoaltracking, costprediction, performancechangealert
from bson.objectid import ObjectId
import babel.numbers
from analyticsAudit import analyticsAudit
from tasks import run_analyticsAudit, run_analyticsAudit_without_slack
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import shutil
import sys
from urllib.request import urlopen
from json import load
import pytz
import logging
from subprocess import call

DOMAIN_NAME = os.environ.get('DOMAIN_NAME').strip()
imageurl = "https://" + DOMAIN_NAME + "/images/{}.png"

OAuth2ConsumerBlueprint.authorized = authorized
URL = "https://slack.com/api/{}"

TOKEN_INFO_URI = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'
ACCESS_TOKEN_URI = 'https://www.googleapis.com/oauth2/v4/token'
CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID').strip()
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET').strip()

logging.basicConfig(filename="appPy.log", filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session or 'auth_token' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))

    return decorated_function


def logout_user(self):
    session.clear()
    g.user = None


app = Flask(__name__)

# Rate Limiting for Incoming Requests
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
)

# Celery for task queue
# celery = Celery(broker=f'redis://localhost:6379/0')
db.init()
db2.init()

app.config['SECRET_KEY'] = 'linuxdegilgnulinux'

app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get('SLACK_CLIENT_ID')
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get('SLACK_CLIENT_SECRET')
# scope=["identify,bot,commands,channels:read,chat:write:bot,links:read,users:read,groups:read,im:read"]
slack_bp = make_slack_blueprint(
    scope=["identify,bot,commands,users:read,groups:read,im:read"],
    redirect_url='/getstarted/get-first-insight')
slack_bp.authorized = authorized
app.register_blueprint(slack_bp, url_prefix="/login")
app.register_blueprint(google_auth.app)
app.register_blueprint(google_analytics.app)


@app.errorhandler(500)
def internal_error(error):
    user = db.find_one('user', query={'email': session['email']})
    if user:
        #        if not session.get('TOKENCHECKED'):
        google_auth.check_tokens(user)
    return redirect('/')


# Force App to expire session after 20minutes of true inactivity.
@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=1)
    session.modified = True


@app.route('/images/<pid>.png')
def get_image(pid):
    return send_file('slackdb/images/%s.png' % pid, mimetype='image/gif')


@app.route('/slack/send_message', methods=['GET', 'POST'])
def send_message():
    #    event  = request.form
    #    return make_response(event['challenge'], 200)
    try:
        response = request.json
        channel = response['event']['channel']
        user = db.find_one('user', {'sl_userid': response['event']['user']})
        slack_token = user['sl_accesstoken']
        slack_client = WebClient(token=slack_token)
        slack_client.chat_postMessage(channel=channel,
                                      text="Hey buddy! For now, i am not able to speak with human being, so can you please ask your question to team behind me via https://drift.me/heybooster")
        return make_response('', 200)
    except:
        return make_response('', 404)


@app.route('/', methods=['GET'])
@login_required
def base():
    #    if not session['email']:
    if not session.get('ga_accesstoken'):
        return redirect('/getstarted/connect-accounts')
    else:
        user = db.find_one('user', query={'email': session['email']})
        if user:
            #            if not session.get('TOKENCHECKED'):
            google_auth.check_tokens(user)
        return redirect('/account/audit-history')


# @app.route('/test', methods=['GET'])
# @login_required
# def test():
#     if request.method == 'GET':
#         call(['python3', 'mail.py'])
#         return render_template('test12.html')


@app.route('/getstarted/connect-accounts', methods=['GET', 'POST'])
@login_required
def home():
    current_analyticsemail = ""
    user = db.find_one('user', {'email': session['email']})
    if user:
        google_auth.check_tokens(user)

    if 'auth_token' in session.keys():
        try:
            if session['ga_accesstoken'] and session['sl_accesstoken']:
                return redirect('/account/audit-history')
            else:
                # Check if user has slack connection
                if session['sl_accesstoken']:
                    slack_confirm = True
                else:
                    slack_confirm = False

                # Check if user has analytics connection
                if session['ga_accesstoken']:
                    user = db.find_one('user', {'email': session['email']})
                    datasource = db.find_one("datasource", {"email": user["email"]})
                    if datasource:
                        return redirect('/account/audit-history')
                    try:
                        current_analyticsemail = user['ga_email']
                    except:
                        current_analyticsemail = ""

                    analytics_confirm = True
                else:
                    analytics_confirm = False
                # Fill the boxes for the value of slack_confirm and analytics_confirm
                return render_template('home.html', slack_confirm=slack_confirm, analytics_confirm=analytics_confirm,
                                       current_analyticsemail=current_analyticsemail)
        except Exception as error:
            logging.error(f"Connect Accounts Failed--- User Email: {session['email']}  --- {str(error)}")
            call(['python3', 'mail.py'])
            return redirect('/logout')
    else:
        return redirect('/login')


@app.route('/without_slack', methods=['GET', 'POST'])
@login_required
def without_slack():
    try:
        if session['ga_accesstoken']:
            return redirect('/getstarted/get-first-insight')
        else:
            return redirect('/account/audit-history')
    except Exception as error:
        logging.error(f"Without Slack Failed--- User Email: {session['email']}  --- {str(error)}")
        call(['python3', 'mail.py'])


@app.route("/getstarted/get-first-insight-without-slack", methods=['GET', 'POST'])
@login_required
def connectaccount_without_slack():
    # if not session['email']:
    #     return redirect('/getstarted/connect-accounts')
    #
    # user = db.find_one('user', {'email': session['email']})
    # datasources = db.find('datasource', query={'email': session['email']})
    #
    # try:
    #     current_analyticsemail = user['ga_email']
    # except:
    #     current_analyticsemail = ""
    #
    # nForm = DataSourceForm(request.form)
    # unsortedargs = []
    # for datasource in datasources:
    #     unsortedargs.append(datasource)
    # #    args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
    # #    tForm = TimeForm(request.form)
    # if request.method == 'POST':
    #     #        data = [('token', session['sl_accesstoken'])]
    #     #        uID = requests.post(URL.format('users.identity'), data).json()['user']['id']
    #     uID = db.find_one("user", query={"email": session["email"]})
    #     ts = time.time()
    #
    #     data = {
    #         'email': session['email'],
    #         'sourceType': "Google Analytics",
    #         'dataSourceName': nForm.data_source_name.data,
    #         'accountID': nForm.account.data.split('\u0007')[0],
    #         'accountName': nForm.account.data.split('\u0007')[1],
    #         'propertyID': nForm.property.data.split('\u0007')[0],
    #         'propertyName': nForm.property.data.split('\u0007')[1],
    #         'viewID': nForm.view.data.split('\u0007')[0],
    #         'currency': nForm.view.data.split('\u0007')[1],
    #         'viewName': nForm.view.data.split('\u0007')[2],
    #         'channelType': "Slack",
    #         'createdTS': ts
    #     }
    #     _id = db.insert_one("datasource", data=data).inserted_id
    #     data['_id'] = _id
    #     unsortedargs.append(data)
    #     if len(unsortedargs) == 1:
    #         insertdefaultnotifications_without_slack(session['email'],
    #                                                  dataSourceID=_id, userID='',
    #                                                  channelID='', sendWelcome=False)
    #         run_analyticsAudit_without_slack.delay(str(data['_id']))
    #     else:
    #         insertdefaultnotifications_without_slack(session['email'], userID='',
    #                                                  dataSourceID=_id,
    #                                                  channelID='')
    #         run_analyticsAudit_without_slack.delay(str(data['_id']))
    #     #        analyticsAudit(slack_token, task=None, dataSource=dataSource)
    #
    # #        args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
    # #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
    # #    else:
    # #        user_info = google_auth.get_user_info()
    # useraccounts = google_analytics.get_accounts(session['email'])['accounts']
    # if (useraccounts):
    #     nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
    #                               useraccounts]
    # else:
    #     nForm.account.choices = [('', 'User does not have Google Analytics Account')]
    #     nForm.property.choices = [('', 'User does not have Google Analytics Account')]
    #     nForm.view.choices = [('', 'User does not have Google Analytics Account')]
    #
    # args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
    # return render_template('datasources_without_slack.html', nForm=nForm, args=args,
    #                        current_analyticsemail=current_analyticsemail)
    return redirect('/getstarted/get-first-insight')


@app.route("/account/audit-history-without-slack-added", methods=['GET', 'POST'])
@login_required
def getaudit_without_slack_added():
    #    if not session['email']:
    if not session.get('ga_accesstoken'):
        return redirect('/getstarted/connect-accounts')

    datasources = db.find('datasource', query={'email': session['email']})
    user = db.find_one('user', {'email': session['email']})
    slack_token = user['sl_accesstoken']
    try:
        current_analyticsemail = user['ga_email']
    except:
        current_analyticsemail = ""

    nForm = DataSourceForm(request.form)
    unsortedargs = []
    for datasource in datasources:
        unsortedargs.append(datasource)
    if request.method == 'POST':
        #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
        #        local_ts = time.asctime(time.localtime(ts))
        ts = time.time()

        data = {
            'email': session['email'],
            'sourceType': "Google Analytics",
            'dataSourceName': nForm.data_source_name.data,
            'accountID': nForm.account.data.split('\u0007')[0],
            'accountName': nForm.account.data.split('\u0007')[1],
            'propertyID': nForm.property.data.split('\u0007')[0],
            'propertyName': nForm.property.data.split('\u0007')[1],
            'viewID': nForm.view.data.split('\u0007')[0],
            'currency': nForm.view.data.split('\u0007')[1],
            'viewName': nForm.view.data.split('\u0007')[2],
            'channelType': "Web",
            'createdTS': ts
        }
        _id = db.insert_one("datasource", data=data).inserted_id
        data['_id'] = _id
        unsortedargs.append(data)
        if len(unsortedargs) == 1:
            insertdefaultnotifications_without_slack(session['email'], userID='',
                                                     dataSourceID=_id,
                                                     channelID='', sendWelcome=False)
            if slack_token:
                run_analyticsAudit.delay(slack_token, str(data['_id']), sendFeedback=True)
            else:
                run_analyticsAudit_without_slack.delay(str(data['_id']))
        else:
            insertdefaultnotifications_without_slack(session['email'], userID='',
                                                     dataSourceID=_id,
                                                     channelID='')
            if slack_token:
                run_analyticsAudit.delay(slack_token, str(data['_id']), sendFeedback=False)
            else:
                run_analyticsAudit_without_slack.delay(str(data['_id']))

        #        analyticsAudit(slack_token, task=None, dataSource=data)
        # flash("Check out your connected slack channel, heybooster even wrote you.")

        #        analyticsAudit(slack_token, task=None, dataSource=data)

        return redirect('/account/audit-history')

    useraccounts = google_analytics.get_accounts(session['email'])['accounts']
    if (useraccounts):
        nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                  useraccounts]
    else:
        nForm.account.choices = [('', 'User does not have Google Analytics Account')]
        nForm.property.choices = [('', 'User does not have Google Analytics Account')]
        nForm.view.choices = [('', 'User does not have Google Analytics Account')]

    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)

    # Sort Order is important, that's why analytics audits are queried
    # after sorting to use their status correctly
    analytics_audits = []
    for arg in args:
        #        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
        #        localTime = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
        #        arg['localTime'] = localTime
        #        if analytics_audit['status'] == '0':
        #            arg['strstat'] = 'passive'
        #        else:
        #            arg['strstat'] = 'active'
        #        arg['totalScore'] = analytics_audit['totalScore']
        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
        # analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
        if analytics_audit['status'] == '0':
            analytics_audit['strstat'] = 'passive'
        else:
            analytics_audit['strstat'] = 'active'
        analytics_audits += [analytics_audit]

    return render_template('new_theme/new_audit.html', args=args, selectedargs=args, nForm=nForm,
                           current_analyticsemail=current_analyticsemail,
                           analytics_audits=analytics_audits)


# @app.route("/account/audit-history-without-slack", methods=['GET', 'POST'])
# @login_required
# def getaudit_without_slack():
#    if not session['email']:
#        return redirect('/getstarted/connect-accounts')
#
#    ip_addr = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
#    user = db.find_one('user', {'email': session['email']})
#    slack_token = user['sl_accesstoken']
#    if ip_addr:
#        url = 'https://ipinfo.io/' + ip_addr + '/json'
#        res = urlopen(url)
#        data = load(res)
#        tz = data['timezone']
#        pst = pytz.timezone(tz)
#        now = datetime.now()
#        now = datetime.strftime(now, '%d/%m/%Y')
#        now = datetime.strptime(now, '%d/%m/%Y')
#        localize = pst.localize(now)
#        tz_offset = int(localize.tzname())
#        db.find_and_modify('user', query={'_id': user['_id']},
#                           tz_offset=tz_offset)
#    #    counter = 0
#    #    dt = db.find('datasource', {'email': session['email']})
#    #    user = db.find_one('user', {'email': session['email']})
#    #    firstDatasourceID = db.find_one('datasource', {'email': session['email']})
#
#    #    for document in dt:
#    #        if document['email']:
#    #            counter = counter + 1
#    #    if counter > 1:
#    #        return redirect('/account/audit-history' + str(firstDatasourceID['_id']))
#
#    try:
#        current_analyticsemail = user['ga_email']
#    except:
#        current_analyticsemail = ""
#
#    datasources = db.find('datasource', query={'email': session['email']})
#    nForm = DataSourceForm(request.form)
#    unsortedargs = []
#    for datasource in datasources:
#        unsortedargs.append(datasource)
#    if request.method == 'POST':
#        #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
#        #        local_ts = time.asctime(time.localtime(ts))
#        ts = time.time()
#
#        data = {
#            'email': session['email'],
#            'sourceType': "Google Analytics",
#            'dataSourceName': nForm.data_source_name.data,
#            'accountID': nForm.account.data.split('\u0007')[0],
#            'accountName': nForm.account.data.split('\u0007')[1],
#            'propertyID': nForm.property.data.split('\u0007')[0],
#            'propertyName': nForm.property.data.split('\u0007')[1],
#            'viewID': nForm.view.data.split('\u0007')[0],
#            'currency': nForm.view.data.split('\u0007')[1],
#            'viewName': nForm.view.data.split('\u0007')[2],
#            'channelType': "Web",
#            'createdTS': ts
#        }
#        _id = db.insert_one("datasource", data=data).inserted_id
#        data['_id'] = _id
#        unsortedargs.append(data)
#        if len(unsortedargs) == 1:
#            insertdefaultnotifications_without_slack(session['email'], userID='',
#                                                     dataSourceID=_id,
#                                                     channelID='', sendWelcome=False)
#            if slack_token:
#                run_analyticsAudit.delay(slack_token, str(data['_id']), sendFeedback = True)
#            else:
#                run_analyticsAudit_without_slack.delay(str(data['_id']))
#        else:
#            insertdefaultnotifications_without_slack(session['email'], userID='',
#                                                     dataSourceID=_id,
#                                                     channelID='')
#            if slack_token:
#                run_analyticsAudit.delay(slack_token, str(data['_id']), sendFeedback = True)
#            else:
#                run_analyticsAudit_without_slack.delay(str(data['_id']))
#
#        #        analyticsAudit(slack_token, task=None, dataSource=data)
#        # flash("Check out your connected slack channel, heybooster even wrote you.")
#
#        #        analyticsAudit(slack_token, task=None, dataSource=data)
#
#        flash("Check out your connected slack channel, heybooster even wrote you.")
#
#    useraccounts = google_analytics.get_accounts(session['email'])['accounts']
#    if (useraccounts):
#        nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
#                                  useraccounts]
#    else:
#        nForm.account.choices = [('', 'User does not have Google Analytics Account')]
#        nForm.property.choices = [('', 'User does not have Google Analytics Account')]
#        nForm.view.choices = [('', 'User does not have Google Analytics Account')]
#
#    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
#
#    # Sort Order is important, that's why analytics audits are queried
#    # after sorting to use their status correctly
#    analytics_audits = []
#    for arg in args:
#        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
#        localTime = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
#        arg['localTime'] = localTime
#        if analytics_audit['status'] == '0':
#            arg['strstat'] = 'passive'
#        else:
#            arg['strstat'] = 'active'
#        arg['totalScore'] = analytics_audit['totalScore']
#        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
#        analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
#        if analytics_audit['status'] == '0':
#            analytics_audit['strstat'] = 'passive'
#        else:
#            analytics_audit['strstat'] = 'active'
#        analytics_audits += [analytics_audit]
#    return render_template('new_theme/new_audit.html', args=args, selectedargs=args, nForm=nForm,
#                           current_analyticsemail=current_analyticsemail,
#                           analytics_audits=analytics_audits)


# @app.route('/account/audit-history-without-slack<datasourceID>')
# def audithistory_without_slack(datasourceID):
#    user = db.find_one('user', {'email': session['email']})
#    #    tz_offset = user['tz_offset']
#    # tz_offset = 1
#    current_analyticsemail = user['ga_email']
#
#    nForm = DataSourceForm(request.form)
#    datasources = db.find('datasource', query={'email': session['email']})
#
#    unsortedargs = []
#    for datasource in datasources:
#        unsortedargs.append(datasource)
#    if request.method == 'POST':
#        #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
#        #        local_ts = time.asctime(time.localtime(ts))
#        ts = time.time()
#
#        data = {
#            'email': session['email'],
#            'sourceType': "Google Analytics",
#            'dataSourceName': nForm.data_source_name.data,
#            'accountID': nForm.account.data.split('\u0007')[0],
#            'accountName': nForm.account.data.split('\u0007')[1],
#            'propertyID': nForm.property.data.split('\u0007')[0],
#            'propertyName': nForm.property.data.split('\u0007')[1],
#            'viewID': nForm.view.data.split('\u0007')[0],
#            'currency': nForm.view.data.split('\u0007')[1],
#            'viewName': nForm.view.data.split('\u0007')[2],
#            'channelType': "Slack",
#            'createdTS': ts
#        }
#        _id = db.insert_one("datasource", data=data).inserted_id
#        data['_id'] = _id
#        unsortedargs.append(data)
#        insertdefaultnotifications_without_slack(session['email'], userID='',
#                                                 dataSourceID=_id,
#                                                 channelID='')
#        #        analyticsAudit(slack_token, task=None, dataSource=data)
#        run_analyticsAudit_without_slack.delay(str(data['_id']))
#        flash("Check out your connected slack channel, heybooster even wrote you.")
#
#    useraccounts = google_analytics.get_accounts(session['email'])['accounts']
#    if (useraccounts):
#        nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
#                                  useraccounts]
#    else:
#        nForm.account.choices = [('', 'User does not have Google Analytics Account')]
#        nForm.property.choices = [('', 'User does not have Google Analytics Account')]
#        nForm.view.choices = [('', 'User does not have Google Analytics Account')]
#
#    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
#    # Sort Order is important, that's why analytics audits are queried
#    # after sorting to use their status correctly
#    selectedargs = [db.find_one("datasource", query={"_id": ObjectId(datasourceID)})]
#    analytics_audits = []
#    for arg in selectedargs:
#        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
#        # analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
#        if analytics_audit['status'] == '0':
#            analytics_audit['strstat'] = 'passive'
#        else:
#            analytics_audit['strstat'] = 'active'
#        analytics_audits += [analytics_audit]
#
#    report = db.find_one('reports', {'datasourceID': ObjectId(datasourceID)})
#    if report:
#        recommendations = report['recommendations']
#        lastStates = report['lastStates']
#        ####  Temporary Add-on ####
#        if lastStates['contentGrouping'] == 'danger':
#            recommendations['contentGrouping'] = ['If you have a blog page with lots of different topic or e-commerce site with various product lists, It is helpful to compare each group in terms of their performance.',
#                            'There are 3 different method to create content grouping; url based, page title based and if you don’t have a clear structure for url and page title, you can use tracking code to define each page’s content group.']
#        ####  Temporary Add-on ####
#        len_issues = list(lastStates.values()).count('danger')
#        len_recommendations = 0
#        for rec in recommendations.values():
#            len_recommendations += len(rec)
#        totalScore = report['totalScore']
#    else:
#        # Old Version
#        notification = db.find_one('notification', query={'datasourceID': ObjectId(datasourceID)})
#        totalScore = notification['totalScore']
#        recommendations = None
#        len_recommendations = 0
#        lastStates = notification['lastStates']
#        len_issues = list(lastStates.values()).count('danger')
#
#    return render_template('new_theme/new_audit.html', args=args, selectedargs=selectedargs, nForm=nForm,
#                           current_analyticsemail=current_analyticsemail,
#                           analytics_audits=analytics_audits,
#                           len_issues=len_issues,
#                           len_recommendations=len_recommendations,
#                           totalScore=totalScore)


@app.route('/account/recommendation<datasourceID>')
def recommendation(datasourceID):
    names = {
        "adwordsAccountConnection": "Adwords Account Connection",
        "paymentReferral": "Payment Referral",
        "gdprCompliant": "GDPR Compliant",
        "dataRetentionPeriod": "Data Retention Period",
        "enhancedECommerceActivity": "Enhanced ECommerce Activity",
        "domainControl": "Domain Control",
        "rawDataView": "Raw Data View",
        "userPermission": "User Permission",
        "bounceRateTracking": "Bounce Rate Tracking",
        "selfReferral": "Self Referral",
        "botSpamExcluding": "Bot Spam Excluding",
        "eventTracking": "Event Tracking",
        "errorPage": "404 Error Page",
        "timezone": "Timezone",
        "currency": "Currency",
        "notSetLandingPage": "Not Set Landing Page",
        "sessionClickDiscrepancy": "Session Click Discrepancy",
        "goalSettingActivity": "Goal Setting Activity",
        "customDimension": "Custom Dimension",
        "siteSearchTracking": "Site Search Tracking",
        "remarketingLists": "Remarketing Lists",
        "defaultPageControl": "Default Page Control",
        "contentGrouping": "Content Grouping",
        "othersInChannelGrouping": "Others In Channel Grouping",
        "customMetric": "Custom Metric",
        "internalSearchTermConsistency": "Internal Search Term Consistency",
        "samplingCheck": "Sampling Check"
    }
    scores = {"adwordsAccountConnection": 5,
              "paymentReferral": 5,
              "gdprCompliant": 5,
              "dataRetentionPeriod": 5,
              "enhancedECommerceActivity": 5,
              "domainControl": 5,
              "rawDataView": 5,
              "userPermission": 5,
              "bounceRateTracking": 4,
              "selfReferral": 4,
              "botSpamExcluding": 4,
              "eventTracking": 4,
              "errorPage": 4,
              "timezone": 4,
              "currency": 4,
              "notSetLandingPage": 3,
              "sessionClickDiscrepancy": 3,
              "goalSettingActivity": 3,
              "customDimension": 3,
              "siteSearchTracking": 3,
              "remarketingLists": 3,
              "defaultPageControl": 3,
              "contentGrouping": 3,
              "othersInChannelGrouping": 3,
              "customMetric": 2,
              "internalSearchTermConsistency": 2,
              "samplingCheck": 1
              }
    #    notification = db.find_one('notification', {'datasourceID': ObjectId(datasourceID)})
    #    lastStates = notification['lastStates']

    report = db.find_one('reports', {'datasourceID': ObjectId(datasourceID)})
    if not report:
        report = db.find_one('reports', {'_id': ObjectId(datasourceID)})

    if report:
        summaries = report['summaries']
        recommendations = report['recommendations']
        lastStates = report['lastStates']
        ####  Temporary Add-on ####
        if lastStates['contentGrouping'] == 'danger':
            recommendations['contentGrouping'] = [
                'If you have a blog page with lots of different topic or e-commerce site with various product lists, It is helpful to compare each group in terms of their performance.',
                'There are 3 different method to create content grouping; url based, page title based and if you don’t have a clear structure for url and page title, you can use tracking code to define each page’s content group.']
        if lastStates['internalSearchTermConsistency'] == 'danger':
            recommendations['internalSearchTermConsistency'] = [
                'Apply lowercase filter under View Setting to enforce all terms to be seen as lowercase.']
        ####  Temporary Add-on ####
        len_issues = list(lastStates.values()).count('danger')
        len_recommendations = 0
        for rec in recommendations.values():
            len_recommendations += len(rec)
        totalScore = report['totalScore']
    else:
        # Old Version
        notification = db.find_one('notification', query={'datasourceID': ObjectId(datasourceID)})
        totalScore = notification['totalScore']
        recommendations = None
        summaries = None
        len_recommendations = 0
        lastStates = notification['lastStates']
        len_issues = list(lastStates.values()).count('danger')
    # tz_offset = user['tz_offset']
    # tz_offset = 1

    selectedargs = [db.find_one("datasource", query={"_id": ObjectId(datasourceID)})]

    for key, value in lastStates.items():
        if value == 'good':
            if scores[key] == 5:
                lastStates[key] = '41_good'
            elif scores[key] == 4:
                lastStates[key] = '42_good'
            elif scores[key] == 3:
                lastStates[key] = '43_good'
            elif scores[key] == 2:
                lastStates[key] = '44_good'
            else:
                lastStates[key] = '45_good'
        elif value == 'danger':
            if scores[key] == 5:
                lastStates[key] = '11_urgent'
            elif scores[key] == 4:
                lastStates[key] = '12_urgent'
            elif scores[key] == 3:
                lastStates[key] = '21_warning'
            elif scores[key] == 2:
                lastStates[key] = '22_warning'
            else:
                lastStates[key] = '23_warning'
        else:
            if scores[key] == 5:
                lastStates[key] = '31_none'
            elif scores[key] == 4:
                lastStates[key] = '32_none'
            elif scores[key] == 3:
                lastStates[key] = '33_none'
            elif scores[key] == 2:
                lastStates[key] = '34_none'
            else:
                lastStates[key] = '35_none'

    sortedLastStates = {k: v for k, v in sorted(lastStates.items(), key=lambda item: item[1])}

    return render_template('new_theme/new_detail.html', selectedargs=selectedargs,
                           lastStates=sortedLastStates,
                           names=names, summaries=summaries,
                           recommendations=recommendations,
                           len_issues=len_issues,
                           len_recommendations=len_recommendations,
                           totalScore=totalScore)


@app.route('/account/insights', methods=['GET', 'POST'])
@login_required
def insights():
    datasources = db.find('datasource', query={'email': session['email']})

    join_private_beta_status = db.find_one('joinPrivateBeta', query={'email': session['email']})
    print(join_private_beta_status)

    unsortedargs = []
    for datasource in datasources:
        unsortedargs.append(datasource)
    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
    datasources = db.find('datasource', query={'email': session['email']})
    insights = []
    images_path = '/home/app/heybooster-v1.2/uploads'
    image_names = []
    new_images_path = '/home/app/HeyBooster/static/uploads'

    if request.method == 'POST':
        try:
            for i in datasources:
                insight = db.find('insight', query={'datasourceID': i['_id']})
                for j in insight:
                    insights.append(j)
        except:
            insights = []

        ts = time.time()
        data = {"email": session['email'],
                "createdTS": ts}
        db.insert('joinPrivateBeta', data=data)
        # flash('Join Private Beta Success', 'success')
        return render_template('new_theme/insights.html', insights=insights, args=args,
                               join_private_beta_status=join_private_beta_status)
    else:
        try:
            for i in datasources:
                insight = db.find('insight', query={'datasourceID': i['_id']})
                for j in insight:
                    insights.append(j)

            # dirList = os.listdir(images_path)

            # for im in dirList:
            #     image_names.append(im)
            #
            # for ins in insights:
            #     for img in image_names:
            #         if str(ins['images']) == f"['{img}']":
            #             try:
            #                 shutil.copyfile(images_path + '/' + img, new_images_path + '/' + img)
            #                 print('***********************************************--------------------------')
            #             except IOError as e:
            #                 print("************** Unable to copy file. %s" % e)
            #             except:
            #                 print("Unexpected error:", sys.exc_info())

            return render_template('new_theme/insights.html', insights=insights, args=args,
                                   join_private_beta_status=join_private_beta_status)
        except:
            return render_template('new_theme/insights.html', insights=insights, args=args,
                                   join_private_beta_status=join_private_beta_status)


@app.route('/account/insights/<datasourceID>', methods=['GET', 'POST'])
@login_required
def insights_for_datasource(datasourceID):
    datasources = db.find('datasource', query={'email': session['email']})
    unsortedargs = []
    for datasource in datasources:
        unsortedargs.append(datasource)
    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
    datasource = db.find_one('datasource', query={'_id': ObjectId(datasourceID)})
    insights = []
    #    images_path = '/home/app/heybooster-v1.2/uploads'
    #    image_names = []
    #    new_images_path = '/home/app/HeyBooster/static/uploads'

    if request.method == 'POST':
        insight = db.find('insight', query={'datasourceID': ObjectId(datasourceID)})
        for j in insight:
            insights.append(j)

        ts = time.time()
        data = {"email": session['email'],
                "createdTS": ts}
        db.insert('joinPrivateBeta', data=data)
        flash('Join Private Beta Success', 'success')
        return render_template('new_theme/insights.html', insights=insights, args=args)
    else:
        insight = db.find('insight', query={'datasourceID': ObjectId(datasourceID)})
        for j in insight:
            insights.append(j)

            # dirList = os.listdir(images_path)

            # for im in dirList:
            #     image_names.append(im)
            #
            # for ins in insights:
            #     for img in image_names:
            #         if str(ins['images']) == f"['{img}']":
            #             try:
            #                 shutil.copyfile(images_path + '/' + img, new_images_path + '/' + img)
            #                 print('***********************************************--------------------------')
            #             except IOError as e:
            #                 print("************** Unable to copy file. %s" % e)
            #             except:
            #                 print("Unexpected error:", sys.exc_info())

        return render_template('new_theme/insights.html', insights=insights, datasource=datasource, args=args)


@app.route('/account/connections-without-slack')
def wrongaccount_without_slack():
    if not session['ga_accesstoken']:
        return redirect('/getstarted/connect-accounts')

    user = db.find_one('user', {'email': session['email']})

    try:
        current_analyticsemail = user['ga_email']
    except:
        current_analyticsemail = ""

    return render_template('new_theme/connected_accounts.html', current_analyticsemail=current_analyticsemail)


# @app.route('/test_analytics_audit', methods=['GET', 'POST'])
# def test_analytics_audit():
#     if not (session['sl_accesstoken'] and session['ga_accesstoken']):
#         return redirect('/')
#     audit = []
#     status = ''
#     user_analytics_audit = db.find('notification', query={"email": session['email'], "type": "analyticsAudit"})
#     user = db.find_one('user', {'email': session['email']})
#     for analytics_audit in user_analytics_audit:
#         audit.append(analytics_audit)
#
#         if analytics_audit['status'] == '0':
#             status = 'passive'
#         else:
#             status = 'active'
#
#     try:
#         if user['ga_accesstoken']:
#             resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
#             if 'error' in resp.keys():
#                 data = [('client_id', CLIENT_ID.strip()),
#                         ('client_secret', CLIENT_SECRET.strip()),
#                         ('refresh_token', user['ga_refreshtoken']),
#                         ('grant_type', 'refresh_token')]
#                 resp = requests.post(ACCESS_TOKEN_URI, data).json()
#             current_analyticsemail = resp['email']
#     except:
#         current_analyticsemail = False
#
#     nForm = DataSourceForm(request.form)
#     datasources = db.find('datasource', query={'email': session['email']})
#     unsortedargs = []
#     for datasource in datasources:
#         unsortedargs.append(datasource)
#     if request.method == 'POST':
#         uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
#         ts = time.time()
#
#         data = {
#             'email': session['email'],
#             'sl_userid': uID,
#             'sourceType': "Google Analytics",
#             'accountID': nForm.account.data.split('\u0007')[0],
#             'accountName': nForm.account.data.split('\u0007')[1],
#             'propertyID': nForm.property.data.split('\u0007')[0],
#             'propertyName': nForm.property.data.split('\u0007')[1],
#             'viewID': nForm.view.data.split('\u0007')[0],
#             'currency': nForm.view.data.split('\u0007')[1],
#             'viewName': nForm.view.data.split('\u0007')[2],
#             'channelType': "Slack",
#             'channelID': nForm.channel.data.split('\u0007')[0],
#             'channelName': nForm.channel.data.split('\u0007')[1],
#             'createdTS': ts
#         }
#         _id = db.insert_one("datasource", data=data).inserted_id
#         data['_id'] = _id
#         unsortedargs.append(data)
#         insertdefaultnotifications(session['email'], userID=uID,
#                                    dataSourceID=_id,
#                                    channelID=nForm.channel.data.split('\u0007')[0])
#         flash("Check out your connected slack channel, heybooster even wrote you.")
#
#     useraccounts = google_analytics.get_accounts(session['email'])['accounts']
#     if (useraccounts):
#         nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
#                                   useraccounts]
#     else:
#         nForm.account.choices = [('', 'User does not have Google Analytics Account')]
#         nForm.property.choices = [('', 'User does not have Google Analytics Account')]
#         nForm.view.choices = [('', 'User does not have Google Analytics Account')]
#     try:
#         channels = get_channels()
#         nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
#                                   in channels]
#     except:
#         nForm.channel.choices = [('', 'User does not have Slack Connection')]
#     args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
#
#     return render_template('audit_table.html', args=args, nForm=nForm, current_analyticsemail=current_analyticsemail,
#                            status=status)


@app.route('/active_audit_test/<UUID>')
@login_required
def active_audit_test(UUID):
    analytics_audit = db.find_one("notification", query={"_id": ObjectId(UUID)})
    if analytics_audit['email'] == session['email']:
        val = int(analytics_audit['status'])
        db.find_and_modify('notification', query={'_id': analytics_audit['_id']},
                           status=str(1 - val))

        return redirect('/account/audit-history')
    else:
        return make_response("", 401)


# @app.route('/test_test_without_slack/<datasourceID>')
# @login_required
# @limiter.limit("20/day")
# @limiter.limit("5/minute")
# def test_test_without_slack(datasourceID):
#    dataSource = db.find_one("datasource", query={"_id": ObjectId(datasourceID)})
#    if dataSource['email'] == session['email']:
#        run_analyticsAudit_without_slack.delay(datasourceID)
#        return redirect('/account/audit-history')
#    else:
#        return make_response("", 401)
#
#
# @app.route('/test_test/<datasourceID>')
# @login_required
# @limiter.limit("20/day")
# @limiter.limit("5/minute")
# def test_test(datasourceID):
#    dataSource = db.find_one("datasource", query={"_id": ObjectId(datasourceID)})
#    if dataSource['email'] == session['email']:
#        user = db.find_one("user", query={"email": dataSource["email"]})
#        slack_token = user['sl_accesstoken']
#        #    analyticsAudit(slack_token, task=None, dataSource=dataSource)
#        run_analyticsAudit.delay(slack_token, datasourceID)
#        return redirect('/account/audit-history')
#    else:
#        return make_response("", 401)


# @celery.task(name='analyticsAudit.run')
# def run_analyticsAudit(slack_token, datasourceID):
#    dataSource = db.find_one("datasource", query={"_id": ObjectId(datasourceID)})
#    analyticsAudit(slack_token, task=None, dataSource=dataSource)
#    return True
#
#
# import random
#
#
# @celery.task
# def slow_proc():
#    NTOTAL = 10
#    for i in range(NTOTAL):
#        time.sleep(random.random())
#        current_task.update_state(state='PROGRESS',
#                                  meta={'current': i, 'total': NTOTAL})
#    return 999
#
#
# @app.route('/progress')
# def progress():
#    jobid = request.values.get('jobid')
#    if jobid:
#        # GOTCHA: if you don't pass app=celery here,
#        # you get "NotImplementedError: No result backend configured"
#        job = Celery.AsyncResult(jobid, app=celery)
#        print(job.state)
#        print(job.result)
#        if job.state == 'PROGRESS':
#            return json.dumps(dict(
#                state=job.state,
#                progress=job.result['current'] * 1.0 / job.result['total'],
#            ))
#        elif job.state == 'SUCCESS':
#            return json.dumps(dict(
#                state=job.state,
#                progress=1.0,
#            ))
#    return '{}'
#
#
# @app.route('/enqueue')
# def enqueue():
#    job = slow_proc.delay()
#    return render_template('test12.html', JOBID=job.id)


@app.route('/account/audit-history<datasourceID>')
def audithistory(datasourceID):
    user = db.find_one('user', {'email': session['email']})
    try:
        tz_offset = user["tz_offset"]
    except:
        tz_offset = 0
    if user['sl_accesstoken'] == '':
        #    tz_offset = user['tz_offset']
        # tz_offset = 1
        current_analyticsemail = user['ga_email']

        nForm = DataSourceForm(request.form)
        datasources = db.find('datasource', query={'email': session['email']})

        unsortedargs = []
        for datasource in datasources:
            unsortedargs.append(datasource)
        if request.method == 'POST':
            #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
            #        local_ts = time.asctime(time.localtime(ts))
            ts = time.time()

            data = {
                'email': session['email'],
                'sourceType': "Google Analytics",
                'dataSourceName': nForm.data_source_name.data,
                'accountID': nForm.account.data.split('\u0007')[0],
                'accountName': nForm.account.data.split('\u0007')[1],
                'propertyID': nForm.property.data.split('\u0007')[0],
                'propertyName': nForm.property.data.split('\u0007')[1],
                'viewID': nForm.view.data.split('\u0007')[0],
                'currency': nForm.view.data.split('\u0007')[1],
                'viewName': nForm.view.data.split('\u0007')[2],
                'channelType': "Web",
                'createdTS': ts
            }
            _id = db.insert_one("datasource", data=data).inserted_id
            data['_id'] = _id
            unsortedargs.append(data)
            insertdefaultnotifications_without_slack(session['email'], userID='',
                                                     dataSourceID=_id,
                                                     channelID='')
            #        analyticsAudit(slack_token, task=None, dataSource=data)
            run_analyticsAudit_without_slack.delay(str(data['_id']))
            flash("Check out your connected slack channel, heybooster even wrote you.")

        useraccounts = google_analytics.get_accounts(session['email'])['accounts']
        if (useraccounts):
            nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                      useraccounts]
        else:
            nForm.account.choices = [('', 'User does not have Google Analytics Account')]
            nForm.property.choices = [('', 'User does not have Google Analytics Account')]
            nForm.view.choices = [('', 'User does not have Google Analytics Account')]

        args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
        # Sort Order is important, that's why analytics audits are queried
        # after sorting to use their status correctly
        selectedargs = [db.find_one("datasource", query={"_id": ObjectId(datasourceID)})]
        analytics_audits = []
        reports = []
        for arg in selectedargs:
            analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            if analytics_audit['status'] == '0':
                analytics_audit['strstat'] = 'passive'
            else:
                analytics_audit['strstat'] = 'active'
            analytics_audits += [analytics_audit]
            # Get reports for this selected datasource
            cursor = db.find('reports', query={'datasourceID': arg['_id']}).sort([('_id', -1)])
            try:
                cursor.next()
            except:
                continue
            for r in cursor:
                r["dataSourceName"] = arg["dataSourceName"]
                r["localTime"] = Timestamp2Date(r['ts'], tz_offset)
                reports.append(r)

        return render_template('new_theme/new_audit.html', args=args, selectedargs=selectedargs, nForm=nForm,
                               current_analyticsemail=current_analyticsemail,
                               analytics_audits=analytics_audits, reports=reports)
    else:
        slack_token = user['sl_accesstoken']
        current_analyticsemail = user['ga_email']
        client = WebClient(token=slack_token)
        response = client.auth_test()
        workspace = response['team']

        #    try:
        #        if user['ga_accesstoken']:
        #            resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
        #            if 'error' in resp.keys():
        #                data = [('client_id', CLIENT_ID.strip()),
        #                        ('client_secret', CLIENT_SECRET.strip()),
        #                        ('refresh_token', user['ga_refreshtoken']),
        #                        ('grant_type', 'refresh_token')]
        #                resp = requests.post(ACCESS_TOKEN_URI, data).json()
        #            current_analyticsemail = resp['email']
        #    except:
        #        current_analyticsemail = False

        nForm = DataSourceForm(request.form)
        datasources = db.find('datasource', query={'email': session['email']})
        unsortedargs = []
        for datasource in datasources:
            unsortedargs.append(datasource)
        if request.method == 'POST':
            #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
            #        local_ts = time.asctime(time.localtime(ts))
            ts = time.time()
            uID = user['sl_userid']

            if request.form.getlist('checkbox_channel'):
                data = {
                    'email': session['email'],
                    'sl_userid': uID,
                    'sourceType': "Google Analytics",
                    'dataSourceName': nForm.data_source_name.data,
                    'accountID': nForm.account.data.split('\u0007')[0],
                    'accountName': nForm.account.data.split('\u0007')[1],
                    'propertyID': nForm.property.data.split('\u0007')[0],
                    'propertyName': nForm.property.data.split('\u0007')[1],
                    'viewID': nForm.view.data.split('\u0007')[0],
                    'currency': nForm.view.data.split('\u0007')[1],
                    'viewName': nForm.view.data.split('\u0007')[2],
                    'channelType': "Slack",
                    'channelID': nForm.channel.data.split('\u0007')[0],
                    'channelName': nForm.channel.data.split('\u0007')[1],
                    'createdTS': ts
                }
            else:
                data = {
                    'email': session['email'],
                    'sourceType': "Google Analytics",
                    'dataSourceName': nForm.data_source_name.data,
                    'accountID': nForm.account.data.split('\u0007')[0],
                    'accountName': nForm.account.data.split('\u0007')[1],
                    'propertyID': nForm.property.data.split('\u0007')[0],
                    'propertyName': nForm.property.data.split('\u0007')[1],
                    'viewID': nForm.view.data.split('\u0007')[0],
                    'currency': nForm.view.data.split('\u0007')[1],
                    'viewName': nForm.view.data.split('\u0007')[2],
                    'channelType': "Web",
                    'createdTS': ts
                }
            _id = db.insert_one("datasource", data=data).inserted_id
            data['_id'] = _id
            unsortedargs.append(data)
            if request.form.getlist('checkbox_channel'):
                insertdefaultnotifications(session['email'], userID=uID,
                                           dataSourceID=_id,
                                           channelID=nForm.channel.data.split('\u0007')[0])
                #        analyticsAudit(slack_token, task=None, dataSource=data)
                run_analyticsAudit.delay(slack_token, str(data['_id']))
            else:
                insertdefaultnotifications_without_slack(session['email'], userID='',
                                                         dataSourceID=_id,
                                                         channelID='')
                #        analyticsAudit(slack_token, task=None, dataSource=data)
                run_analyticsAudit_without_slack.delay(str(data['_id']))
            flash("Check out your connected slack channel, heybooster even wrote you.")

        useraccounts = google_analytics.get_accounts(session['email'])['accounts']
        if (useraccounts):
            nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                      useraccounts]
        else:
            nForm.account.choices = [('', 'User does not have Google Analytics Account')]
            nForm.property.choices = [('', 'User does not have Google Analytics Account')]
            nForm.view.choices = [('', 'User does not have Google Analytics Account')]
        try:
            channels = get_channels()
            nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
                                      in channels]
        except:
            nForm.channel.choices = [('', 'User does not have Slack Connection')]

        args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
        # Sort Order is important, that's why analytics audits are queried
        # after sorting to use their status correctly
        selectedargs = [db.find_one("datasource", query={"_id": ObjectId(datasourceID)})]
        analytics_audits = []
        reports = []
        for arg in selectedargs:
            #        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            #        localTime = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            #        arg['localTime'] = localTime
            #        if analytics_audit['status'] == '0':
            #            arg['strstat'] = 'passive'
            #        else:
            #            arg['strstat'] = 'active'
            #        arg['totalScore'] = analytics_audit['totalScore']
            analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            if analytics_audit['status'] == '0':
                analytics_audit['strstat'] = 'passive'
            else:
                analytics_audit['strstat'] = 'active'
            analytics_audits += [analytics_audit]
            # Get reports for this selected datasource
            cursor = db.find('reports', query={'datasourceID': arg['_id']}).sort([('_id', -1)])
            try:
                cursor.next()
            except:
                continue
            for r in cursor:
                r["dataSourceName"] = arg["dataSourceName"]
                r["localTime"] = Timestamp2Date(r['ts'], tz_offset)
                reports.append(r)

        return render_template('new_theme/new_audit.html', args=args, selectedargs=selectedargs, nForm=nForm,
                               current_analyticsemail=current_analyticsemail, workspace=workspace,
                               analytics_audits=analytics_audits, reports=reports)


@app.route('/account/connections')
def wrongaccount():
    user = db.find_one('user', {'email': session['email']})
    if not user['sl_accesstoken']:
        if not session['ga_accesstoken']:
            return redirect('/getstarted/connect-accounts')

        user = db.find_one('user', {'email': session['email']})

        try:
            current_analyticsemail = user['ga_email']
        except:
            current_analyticsemail = ""

        return render_template('new_theme/connected_accounts.html', current_analyticsemail=current_analyticsemail)

    else:
        #        if not (session['sl_accesstoken'] or session['ga_accesstoken']):
        if not session.get('ga_accesstoken'):
            return redirect('/getstarted/connect-accounts')
        slack_token = user['sl_accesstoken']
        client = WebClient(token=slack_token)
        response = client.auth_test()
        workspace = response['team']

        #    try:
        #        if user['ga_accesstoken']:
        #            resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
        #            if 'error' in resp.keys():
        #                data = [('client_id', CLIENT_ID.strip()),
        #                        ('client_secret', CLIENT_SECRET.strip()),
        #                        ('refresh_token', user['ga_refreshtoken']),
        #                        ('grant_type', 'refresh_token')]
        #                resp = requests.post(ACCESS_TOKEN_URI, data).json()
        #            current_analyticsemail = resp['email']
        #    except:
        #        current_analyticsemail = ""
        try:
            current_analyticsemail = user['ga_email']
        except:
            current_analyticsemail = ""
        #
        #    datasources = db.find('datasource', query={'email': session['email']})
        #    unsortedargs = []
        #    for datasource in datasources:
        #        unsortedargs.append(datasource)
        #
        #    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)

        return render_template('wrongaccount.html', current_analyticsemail=current_analyticsemail,
                               workspace=workspace)


@app.route('/change', methods=['POST'])
def change():
    message_action = request.form
    # Open a slack client
    user = db.find_one('user', {'sl_userid': message_action['user_id']})
    slack_token = user['sl_accesstoken']
    slack_client = WebClient(token=slack_token)
    # text = message_action['original_message']['text']
    if (True):
        houroptions = []
        for i in range(0, 24):
            houroptions.append({'label': str(i), 'value': i})
        minuteoptions = []
        for i in range(0, 60):
            minuteoptions.append({'label': str(i), 'value': i})
        slack_client.dialog_open(
            trigger_id=message_action["trigger_id"],
            dialog={
                "title": "Notification Settings",
                "submit_label": "Submit",
                "callback_id": "notification_form",
                "elements": [
                    {
                        "label": "Hour",
                        "type": "select",
                        "name": "hour",
                        "placeholder": "Select an hour",
                        "options": houroptions
                    },
                    {
                        "label": "Minute",
                        "type": "select",
                        "name": "minute",
                        "placeholder": "Select a minute",
                        "options": minuteoptions
                    }
                ]
            }
        )
    #    return make_response("Time of Day: ", 200)
    return make_response("", 200)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if 'auth_token' in session.keys() and 'sl_accesstoken' in session.keys():
        return redirect('/account/audit-history')
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate:
        user = db.find_one('user', {'email': form.email.data})

        if user:
            if user['password'] != "":
                if check_password_hash(user['password'], form.password.data):

                    session['logged_in'] = True
                    session['email'] = user['email']

                    return redirect(url_for('home'))
                else:
                    return redirect(url_for('login'))

    return render_template('auths/login.html', form=form)


@app.route('/getstarted/register/', methods=['GET', 'POST'])
def register():
    if 'auth_token' in session.keys() and 'sl_accesstoken' in session.keys():
        return redirect('/account/audit-history')
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate:
        user = db.find_one('user', {'email': form.email.data})

        if user:
            if user['password'] != "":
                if check_password_hash(user['password'], form.password.data):

                    session['logged_in'] = True
                    session['email'] = user['email']

                    return redirect(url_for('home'))
                else:
                    return redirect(url_for('login'))

    return render_template('auths/register.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/privacypolicy')
def privacy():
    return render_template('privacy.html')


@app.route("/connect")
@login_required
def connect():
    #    if not slack.authorized:
    #        return redirect(url_for("slack.login"))
    #    return redirect('/')
    return redirect(url_for("slack.login"))


def get_channels():
    #    data = [('token', slack.token['access_token'])]
    if not 'sl_accesstoken' in session.keys():
        session['sl_accesstoken'] = db.find_one('user', query={'email': session['email']})['sl_accesstoken']
    data = [('token', session['sl_accesstoken']),
            ('types', 'public_channel, private_channel'),
            ('limit', 200)]
    channels = []
    try:
        conversationslist = requests.post(URL.format('conversations.list'), data).json()['channels']
        for conv in conversationslist:
            if (conv['is_channel'] or conv['is_group']):
                conv['name'] = '#' + conv['name']
                channels += [conv]
    except Exception as ex:
        print("Conversation List request error %s" % (str(ex)))
    try:
        data = [('token', session['sl_accesstoken']),
                ('limit', 200)]
        userslist = requests.post(URL.format('users.list'), data).json()['members']
        imlist = requests.post(URL.format('im.list'), data).json()['ims']

        for user in userslist:
            if (not user['is_bot'] or user['name'] == 'heybooster'):
                for im in imlist:
                    if (user['id'] == im['user']):
                        #                    print("User ID:", user['id'], '\n', "User Name:", user['name'], '\n', "IM ID:", im['id'])
                        user['id'] = im['id']
                        user['name'] = '@' + user['name']
                        channels += [user]
                        break
    except:
        pass
    return channels


# @app.route("/get_audit", methods=['GET', 'POST'])
# @login_required
# def get_audit():
#     if not (session['sl_accesstoken'] and session['ga_accesstoken']):
#         return redirect('/')
#
#     user = db.find_one('user', {'email': session['email']})
#
#     try:
#         if user['ga_accesstoken']:
#             resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
#             if 'error' in resp.keys():
#                 data = [('client_id', CLIENT_ID.strip()),
#                         ('client_secret', CLIENT_SECRET.strip()),
#                         ('refresh_token', user['ga_refreshtoken']),
#                         ('grant_type', 'refresh_token')]
#                 resp = requests.post(ACCESS_TOKEN_URI, data).json()
#             current_analyticsemail = resp['email']
#     except:
#         current_analyticsemail = ""
#
#     nForm = DataSourceForm(request.form)
#     datasources = db.find('datasource', query={'email': session['email']})
#     unsortedargs = []
#     for datasource in datasources:
#         unsortedargs.append(datasource)
#     if request.method == 'POST':
#         uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
#         ts = time.time()
#
#         data = {
#             'email': session['email'],
#             'sl_userid': uID,
#             'sourceType': "Google Analytics",
#             'accountID': nForm.account.data.split('\u0007')[0],
#             'accountName': nForm.account.data.split('\u0007')[1],
#             'propertyID': nForm.property.data.split('\u0007')[0],
#             'propertyName': nForm.property.data.split('\u0007')[1],
#             'viewID': nForm.view.data.split('\u0007')[0],
#             'currency': nForm.view.data.split('\u0007')[1],
#             'viewName': nForm.view.data.split('\u0007')[2],
#             'channelType': "Slack",
#             'channelID': nForm.channel.data.split('\u0007')[0],
#             'channelName': nForm.channel.data.split('\u0007')[1],
#             'createdTS': ts
#         }
#         _id = db.insert_one("datasource", data=data).inserted_id
#         data['_id'] = _id
#         unsortedargs.append(data)
#         insertdefaultnotifications(session['email'], userID=uID,
#                                    dataSourceID=_id,
#                                    channelID=nForm.channel.data.split('\u0007')[0])
#     useraccounts = google_analytics.get_accounts(session['email'])['accounts']
#     if useraccounts:
#         nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
#                                   useraccounts]
#     else:
#         nForm.account.choices = [('', 'User does not have Google Analytics Account')]
#         nForm.property.choices = [('', 'User does not have Google Analytics Account')]
#         nForm.view.choices = [('', 'User does not have Google Analytics Account')]
#     try:
#         channels = get_channels()
#         nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
#                                   in channels]
#     except:
#         nForm.channel.choices = [('', 'User does not have Slack Connection')]
#
#     args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
#     return render_template('get_audit.html', nForm=nForm, args=args, current_analyticsemail=current_analyticsemail)


@app.route("/getstarted/get-first-insight", methods=['GET', 'POST'])
@login_required
def connectaccount():
    user = db.find_one('user', {'email': session['email']})

    if not user['sl_accesstoken']:
        #        if not session['email']:
        if not session.get('ga_accesstoken'):
            return redirect('/getstarted/connect-accounts')

        user = db.find_one('user', {'email': session['email']})
        datasources = db.find('datasource', query={'email': session['email']})

        try:
            current_analyticsemail = user['ga_email']
        except:
            current_analyticsemail = ""

        nForm = DataSourceForm(request.form)
        unsortedargs = []
        for datasource in datasources:
            unsortedargs.append(datasource)
        #    args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
        #    tForm = TimeForm(request.form)
        if request.method == 'POST':
            #        data = [('token', session['sl_accesstoken'])]
            #        uID = requests.post(URL.format('users.identity'), data).json()['user']['id']
            uID = db.find_one("user", query={"email": session["email"]})
            ts = time.time()

            data = {
                'email': session['email'],
                'sourceType': "Google Analytics",
                'dataSourceName': nForm.data_source_name.data,
                'accountID': nForm.account.data.split('\u0007')[0],
                'accountName': nForm.account.data.split('\u0007')[1],
                'propertyID': nForm.property.data.split('\u0007')[0],
                'propertyName': nForm.property.data.split('\u0007')[1],
                'viewID': nForm.view.data.split('\u0007')[0],
                'currency': nForm.view.data.split('\u0007')[1],
                'viewName': nForm.view.data.split('\u0007')[2],
                'channelType': "Web",
                'createdTS': ts
            }
            _id = db.insert_one("datasource", data=data).inserted_id
            data['_id'] = _id
            unsortedargs.append(data)
            if len(unsortedargs) == 1:
                insertdefaultnotifications_without_slack(session['email'],
                                                         dataSourceID=_id, userID='',
                                                         channelID='', sendWelcome=False)
                run_analyticsAudit_without_slack.delay(str(data['_id']))
            else:
                insertdefaultnotifications_without_slack(session['email'], userID='',
                                                         dataSourceID=_id,
                                                         channelID='')
                run_analyticsAudit_without_slack.delay(str(data['_id']))
            #        analyticsAudit(slack_token, task=None, dataSource=dataSource)

        #        args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
        #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
        #    else:
        #        user_info = google_auth.get_user_info()
        useraccounts = google_analytics.get_accounts(session['email'])['accounts']
        if (useraccounts):
            nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                      useraccounts]
        else:
            nForm.account.choices = [('', 'User does not have Google Analytics Account')]
            nForm.property.choices = [('', 'User does not have Google Analytics Account')]
            nForm.view.choices = [('', 'User does not have Google Analytics Account')]

        args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
        return render_template('datasources_without_slack.html', nForm=nForm, args=args,
                               current_analyticsemail=current_analyticsemail)

    else:
        #        if not (session['sl_accesstoken'] and session['ga_accesstoken']):
        if not session.get('ga_accesstoken'):
            return redirect('/getstarted/connect-accounts')

        slack_token = user['sl_accesstoken']
        client = WebClient(token=slack_token)
        response = client.auth_test()
        workspace = response['team']

        #    try:
        #        if user['ga_accesstoken']:
        #            resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
        #            if 'error' in resp.keys():
        #                data = [('client_id', CLIENT_ID.strip()),
        #                        ('client_secret', CLIENT_SECRET.strip()),
        #                        ('refresh_token', user['ga_refreshtoken']),
        #                        ('grant_type', 'refresh_token')]
        #                resp = requests.post(ACCESS_TOKEN_URI, data).json()
        #            current_analyticsemail = resp['email']
        #    except:
        #        current_analyticsemail = ""
        try:
            current_analyticsemail = user['ga_email']
        except:
            current_analyticsemail = ""

        nForm = DataSourceForm(request.form)
        datasources = db.find('datasource', query={'email': session['email']})
        unsortedargs = []
        for datasource in datasources:
            unsortedargs.append(datasource)
        #    args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
        #    tForm = TimeForm(request.form)
        if request.method == 'POST':
            #        data = [('token', session['sl_accesstoken'])]
            #        uID = requests.post(URL.format('users.identity'), data).json()['user']['id']
            uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
            ts = time.time()

            if request.form.getlist('checkbox_channel'):
                data = {
                    'email': session['email'],
                    'sl_userid': uID,
                    'sourceType': "Google Analytics",
                    'dataSourceName': nForm.data_source_name.data,
                    'accountID': nForm.account.data.split('\u0007')[0],
                    'accountName': nForm.account.data.split('\u0007')[1],
                    'propertyID': nForm.property.data.split('\u0007')[0],
                    'propertyName': nForm.property.data.split('\u0007')[1],
                    'viewID': nForm.view.data.split('\u0007')[0],
                    'currency': nForm.view.data.split('\u0007')[1],
                    'viewName': nForm.view.data.split('\u0007')[2],
                    'channelType': "Slack",
                    'channelID': nForm.channel.data.split('\u0007')[0],
                    'channelName': nForm.channel.data.split('\u0007')[1],
                    'createdTS': ts
                }
            else:
                data = {
                    'email': session['email'],
                    'sourceType': "Google Analytics",
                    'dataSourceName': nForm.data_source_name.data,
                    'accountID': nForm.account.data.split('\u0007')[0],
                    'accountName': nForm.account.data.split('\u0007')[1],
                    'propertyID': nForm.property.data.split('\u0007')[0],
                    'propertyName': nForm.property.data.split('\u0007')[1],
                    'viewID': nForm.view.data.split('\u0007')[0],
                    'currency': nForm.view.data.split('\u0007')[1],
                    'viewName': nForm.view.data.split('\u0007')[2],
                    'channelType': "Web",
                    'createdTS': ts
                }
            _id = db.insert_one("datasource", data=data).inserted_id
            data['_id'] = _id
            unsortedargs.append(data)
            if len(unsortedargs) == 1:
                if request.form.getlist('checkbox_channel'):
                    insertdefaultnotifications(session['email'], userID=uID,
                                               dataSourceID=_id,
                                               channelID=nForm.channel.data.split('\u0007')[0], sendWelcome=True)
                    run_analyticsAudit.delay(slack_token, str(data['_id']), sendFeedback=True)
                else:
                    insertdefaultnotifications_without_slack(session['email'], userID='',
                                                             dataSourceID=_id,
                                                             channelID='')
                    run_analyticsAudit_without_slack.delay(str(data['_id']))
            else:
                if request.form.getlist('checkbox_channel'):
                    insertdefaultnotifications(session['email'], userID=uID,
                                               dataSourceID=_id,
                                               channelID=nForm.channel.data.split('\u0007')[0])
                    run_analyticsAudit.delay(slack_token, str(data['_id']))
                else:
                    insertdefaultnotifications_without_slack(session['email'], userID='',
                                                             dataSourceID=_id,
                                                             channelID='')
                    run_analyticsAudit_without_slack.delay(str(data['_id']))

            #        analyticsAudit(slack_token, task=None, dataSource=dataSource)

        #        args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
        #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
        #    else:
        #        user_info = google_auth.get_user_info()
        useraccounts = google_analytics.get_accounts(session['email'])['accounts']
        if (useraccounts):
            nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                      useraccounts]
        else:
            nForm.account.choices = [('', 'User does not have Google Analytics Account')]
            nForm.property.choices = [('', 'User does not have Google Analytics Account')]
            nForm.view.choices = [('', 'User does not have Google Analytics Account')]
        try:
            channels = get_channels()
            nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
                                      in channels]
        except:
            nForm.channel.choices = [('', 'User does not have Slack Connection')]
        # incoming_webhook = slack.token['incoming_webhook']
        #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
        args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)

        return render_template('datasources.html', nForm=nForm, args=args,
                               current_analyticsemail=current_analyticsemail,
                               workspace=workspace)


@app.route("/removedatasources/<datasourceID>", methods=['GET', 'POST'])
@login_required
def removedatasources(datasourceID):
    db.DATABASE['datasource'].remove({"_id": ObjectId(datasourceID)})
    db.DATABASE['notification'].remove({'datasourceID': ObjectId(datasourceID)})

    return redirect('/account/audit-history')


@app.route("/removeslackaccount", methods=['GET', 'POST'])
def removeslackaccount():
    user = db.find_one('user', {'email': session['email']})

    db.DATABASE['datasource'].update_many(
        {'email': user['email']},
        {'$set': {
            "channelName": ""
        }}
    )

    db.DATABASE['user'].update_one(
        {'_id': user['_id']},
        {'$set': {
            "sl_accesstoken": "",
            "sl_userid": ""
        }}
    )

    return redirect('/connect')


def Timestamp2Date(ts, tz_offset):
    if ts:
        if tz_offset > 0:
            date = datetime.utcfromtimestamp(ts) + timedelta(hours=tz_offset)
        else:
            date = datetime.utcfromtimestamp(ts) - timedelta(hours=tz_offset)
        return date.strftime("%B %d, %Y at %I:%M %p").lstrip("0").replace(" 0", " ")
    else:
        return ""


@app.route("/account/")
@login_required
def account():
    return redirect('/account/audit-history')


@app.route("/account/audit-history", methods=['GET', 'POST'])
@login_required
def getaudit():
    user = db.find_one('user', {'email': session['email']})
    if user:
        #        if not session.get('TOKENCHECKED'):
        google_auth.check_tokens(user)
    try:
        tz_offset = user["tz_offset"]
    except:
        tz_offset = 0
    #        db.find_and_modify('user', query={'_id': user['_id']}, tz_offset=tz_offset)
    if user['sl_accesstoken'] == '':
        #        if not session['email']:
        if not session.get('ga_accesstoken'):
            return redirect('/getstarted/connect-accounts')

        #        ip_addr = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        #        #user = db.find_one('user', {'email': session['email']})
        #
        #        if ip_addr:
        #            url = 'https://ipinfo.io/' + ip_addr + '/json'
        #            res = urlopen(url)
        #            data = load(res)
        #            tz = data['timezone']
        #            pst = pytz.timezone(tz)
        #            now = datetime.now()
        #            now = datetime.strftime(now, '%d/%m/%Y')
        #            now = datetime.strptime(now, '%d/%m/%Y')
        #            localize = pst.localize(now)
        #            tz_offset = int(localize.tzname())
        #            db.find_and_modify('user', query={'_id': user['_id']},
        #                               tz_offset=tz_offset)

        #        counter = 0
        #        dt = db.find('datasource', {'email': session['email']})
        #        user = db.find_one('user', {'email': session['email']})
        #        firstDatasourceID = db.find_one('datasource', {'email': session['email']})

        #        for document in dt:
        #            if document['email']:
        #                counter = counter + 1
        #        if counter > 1:
        #            return redirect('/account/audit-history' + str(firstDatasourceID['_id']))

        try:
            current_analyticsemail = user['ga_email']
        except:
            current_analyticsemail = ""

        datasources = db.find('datasource', query={'email': session['email']})
        nForm = DataSourceForm(request.form)
        unsortedargs = []
        unsortedreports = []
        for datasource in datasources:
            cursor = db.find('reports', query={'datasourceID': datasource['_id']}).sort([('_id', -1)])
            try:
                cursor.next()
            except:
                continue
            for r in cursor:
                r["dataSourceName"] = datasource["dataSourceName"]
                unsortedreports.append(r)
            unsortedargs.append(datasource)
        try:
            if request.method == 'POST':
                #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
                #        local_ts = time.asctime(time.localtime(ts))
                ts = time.time()

                data = {
                    'email': session['email'],
                    'sourceType': "Google Analytics",
                    'dataSourceName': nForm.data_source_name.data,
                    'accountID': nForm.account.data.split('\u0007')[0],
                    'accountName': nForm.account.data.split('\u0007')[1],
                    'propertyID': nForm.property.data.split('\u0007')[0],
                    'propertyName': nForm.property.data.split('\u0007')[1],
                    'viewID': nForm.view.data.split('\u0007')[0],
                    'currency': nForm.view.data.split('\u0007')[1],
                    'viewName': nForm.view.data.split('\u0007')[2],
                    'channelType': "Web",
                    'createdTS': ts
                }
                _id = db.insert_one("datasource", data=data).inserted_id
                data['_id'] = _id
                unsortedargs.append(data)
                if len(unsortedargs) == 1:
                    insertdefaultnotifications_without_slack(session['email'], userID='',
                                                             dataSourceID=_id,
                                                             channelID='', sendWelcome=False)
                    run_analyticsAudit_without_slack.delay(str(data['_id']))
                else:
                    insertdefaultnotifications_without_slack(session['email'], userID='',
                                                             dataSourceID=_id,
                                                             channelID='')
                    run_analyticsAudit_without_slack.delay(str(data['_id']))

                #        analyticsAudit(slack_token, task=None, dataSource=data)
                # flash("Check out your connected slack channel, heybooster even wrote you.")

                #        analyticsAudit(slack_token, task=None, dataSource=data)

                flash("Check out your connected slack channel, heybooster even wrote you.")
        except Exception as error:
            logging.error(f"Get Audit Failed--- User Email: {session['email']}  --- {str(error)}")
            call(['python3', 'mail.py'])

        useraccounts = google_analytics.get_accounts(session['email'])['accounts']
        if (useraccounts):
            nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                      useraccounts]
        else:
            nForm.account.choices = [('', 'User does not have Google Analytics Account')]
            nForm.property.choices = [('', 'User does not have Google Analytics Account')]
            nForm.view.choices = [('', 'User does not have Google Analytics Account')]

        args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
        reports = sorted(unsortedreports, key=lambda i: i['ts'], reverse=True)
        # Sort Order is important, that's why analytics audits are queried
        # after sorting to use their status correctly
        analytics_audits = []
        for arg in args:
            #        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            #        localTime = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            #        arg['localTime'] = localTime
            #        if analytics_audit['status'] == '0':
            #            arg['strstat'] = 'passive'
            #        else:
            #            arg['strstat'] = 'active'
            #        arg['totalScore'] = analytics_audit['totalScore']
            analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            if analytics_audit['status'] == '0':
                analytics_audit['strstat'] = 'passive'
            else:
                analytics_audit['strstat'] = 'active'
            analytics_audits += [analytics_audit]
        for report in reports:
            report['localTime'] = Timestamp2Date(report['ts'], tz_offset)

        return render_template('new_theme/new_audit.html', args=args, selectedargs=args, nForm=nForm,
                               current_analyticsemail=current_analyticsemail,
                               analytics_audits=analytics_audits, reports=reports)

    else:
        #        if not (session['sl_accesstoken'] or session['ga_accesstoken']):
        if not session.get('ga_accesstoken'):
            return redirect('/getstarted/connect-accounts')
        slack_token = user['sl_accesstoken']
        client = WebClient(token=slack_token)
        response = client.auth_test()
        workspace = response['team']

        #    try:
        #        if user['ga_accesstoken']:
        #            resp = requests.get(TOKEN_INFO_URI.format(user['ga_accesstoken'])).json()
        #            if 'error' in resp.keys():
        #                data = [('client_id', CLIENT_ID.strip()),
        #                        ('client_secret', CLIENT_SECRET.strip()),
        #                        ('refresh_token', user['ga_refreshtoken']),
        #                        ('grant_type', 'refresh_token')]
        #                resp = requests.post(ACCESS_TOKEN_URI, data).json()
        #            current_analyticsemail = resp['email']
        #    except:
        #        current_analyticsemail = False
        try:
            current_analyticsemail = user['ga_email']
        except:
            current_analyticsemail = ""

        nForm = DataSourceForm(request.form)
        datasources = db.find('datasource', query={'email': session['email']})
        unsortedargs = []
        unsortedreports = []
        for datasource in datasources:
            cursor = db.find('reports', query={'datasourceID': datasource['_id']}).sort([('_id', -1)])
            try:
                cursor.next()
            except:
                continue
            for r in cursor:
                r["dataSourceName"] = datasource["dataSourceName"]
                unsortedreports.append(r)
            unsortedargs.append(datasource)
        try:
            if request.method == 'POST':
                #        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
                #        local_ts = time.asctime(time.localtime(ts))
                ts = time.time()
                uID = user['sl_userid']

                if request.form.getlist('checkbox_channel'):
                    data = {
                        'email': session['email'],
                        'sl_userid': uID,
                        'sourceType': "Google Analytics",
                        'dataSourceName': nForm.data_source_name.data,
                        'accountID': nForm.account.data.split('\u0007')[0],
                        'accountName': nForm.account.data.split('\u0007')[1],
                        'propertyID': nForm.property.data.split('\u0007')[0],
                        'propertyName': nForm.property.data.split('\u0007')[1],
                        'viewID': nForm.view.data.split('\u0007')[0],
                        'currency': nForm.view.data.split('\u0007')[1],
                        'viewName': nForm.view.data.split('\u0007')[2],
                        'channelType': "Slack",
                        'channelID': nForm.channel.data.split('\u0007')[0],
                        'channelName': nForm.channel.data.split('\u0007')[1],
                        'createdTS': ts
                    }
                else:
                    data = {
                        'email': session['email'],
                        'sourceType': "Google Analytics",
                        'dataSourceName': nForm.data_source_name.data,
                        'accountID': nForm.account.data.split('\u0007')[0],
                        'accountName': nForm.account.data.split('\u0007')[1],
                        'propertyID': nForm.property.data.split('\u0007')[0],
                        'propertyName': nForm.property.data.split('\u0007')[1],
                        'viewID': nForm.view.data.split('\u0007')[0],
                        'currency': nForm.view.data.split('\u0007')[1],
                        'viewName': nForm.view.data.split('\u0007')[2],
                        'channelType': "Web",
                        'createdTS': ts
                    }

                _id = db.insert_one("datasource", data=data).inserted_id
                data['_id'] = _id
                unsortedargs.append(data)
                if len(unsortedargs) == 1:
                    if request.form.getlist('checkbox_channel'):
                        insertdefaultnotifications(session['email'], userID=uID,
                                                   dataSourceID=_id,
                                                   channelID=nForm.channel.data.split('\u0007')[0], sendWelcome=True)
                    else:
                        # Without Slack
                        insertdefaultnotifications_without_slack(session['email'], userID='',
                                                                 dataSourceID=_id,
                                                                 channelID='')
                        run_analyticsAudit_without_slack.delay(str(data['_id']))
                    run_analyticsAudit.delay(slack_token, str(data['_id']), sendFeedback=True)
                else:
                    if request.form.getlist('checkbox_channel'):
                        insertdefaultnotifications(session['email'], userID=uID,
                                                   dataSourceID=_id,
                                                   channelID=nForm.channel.data.split('\u0007')[0])
                        run_analyticsAudit.delay(slack_token, str(data['_id']))
                    else:
                        # Without Slack
                        insertdefaultnotifications_without_slack(session['email'], userID='',
                                                                 dataSourceID=_id,
                                                                 channelID='')
                        run_analyticsAudit_without_slack.delay(str(data['_id']))

                #        analyticsAudit(slack_token, task=None, dataSource=data)
                # flash("Check out your connected slack channel, heybooster even wrote you.")

                #        analyticsAudit(slack_token, task=None, dataSource=data)

                flash("Check out your connected slack channel, heybooster even wrote you.")
        except Exception as error:
            logging.error(f"Connect Accounts Failed--- User Email: {session['email']}  --- {str(error)}")
            call(['python3', 'mail.py'])

        useraccounts = google_analytics.get_accounts(session['email'])['accounts']
        if (useraccounts):
            nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                      useraccounts]
        else:
            nForm.account.choices = [('', 'User does not have Google Analytics Account')]
            nForm.property.choices = [('', 'User does not have Google Analytics Account')]
            nForm.view.choices = [('', 'User does not have Google Analytics Account')]
        try:
            channels = get_channels()
            nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
                                      in channels]
        except:
            nForm.channel.choices = [('', 'User does not have Slack Connection')]
        args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
        reports = sorted(unsortedreports, key=lambda i: i['ts'], reverse=True)
        # Sort Order is important, that's why analytics audits are queried
        # after sorting to use their status correctly
        analytics_audits = []
        for arg in args:
            #        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            #        localTime = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            #        arg['localTime'] = localTime
            #        if analytics_audit['status'] == '0':
            #            arg['strstat'] = 'passive'
            #        else:
            #            arg['strstat'] = 'active'
            #        arg['totalScore'] = analytics_audit['totalScore']
            analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
            analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
            if analytics_audit['status'] == '0':
                analytics_audit['strstat'] = 'passive'
            else:
                analytics_audit['strstat'] = 'active'
            analytics_audits += [analytics_audit]
        for report in reports:
            report['localTime'] = Timestamp2Date(report['ts'], tz_offset)
        return render_template('new_theme/new_audit.html', args=args, selectedargs=args, nForm=nForm,
                               current_analyticsemail=current_analyticsemail, workspace=workspace,
                               analytics_audits=analytics_audits, reports=reports)


@app.route("/gatest/<email>")
def gatest(email):
    service = google_analytics.build_management_api_v3_woutSession(email)
    accs = service.management().accounts().list().execute()
    accounts = []
    if accs.get('items'):
        for acc in accs.get('items'):
            accounts.append({'id': acc.get('id'), 'name': acc.get('name')})
    return {'accounts': accounts}


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    # Parse the request payload
    message_action = json.loads(request.form["payload"])
    sl_userid = message_action['user']['id']
    # Open a slack client
    if message_action["type"] == "view_submission":
        user = db.find_one('user', {'sl_userid': sl_userid})
        if user:
            slack_token = user['sl_accesstoken']
            slack_client = WebClient(token=slack_token)
            userdataSources = db.find("datasource", query={'sl_userid': sl_userid})
            dataSources = [dataSource for dataSource in userdataSources]
            datasourceIDs = [dataSource['_id'] for dataSource in dataSources]
        else:
            print("User is not registered to app")
            return make_response("", 200)
    else:
        channel = message_action['channel']['id']
        user = db.find_one('user', {'sl_userid': sl_userid})
        if user:
            slack_token = user['sl_accesstoken']
            email = user['email']
            slack_client = WebClient(token=slack_token)
            userdataSources = db.find("datasource", query={'sl_userid': sl_userid,
                                                           'channelID': channel})
            dataSources = [dataSource for dataSource in userdataSources]
            datasourceIDs = [dataSource['_id'] for dataSource in dataSources]
        else:
            print("User is not registered to app")
            dataSources = []
            datasourceIDs = []
    if message_action["type"] == "interactive_message":
        messagevalue = message_action['actions'][-1]['value']
        messagename = message_action['actions'][-1]['name']
        if ('_' in messagevalue):
            datasourceID = messagevalue.split('_')[-1]
            print(datasourceID)
            datasourceID = ObjectId(datasourceID)
        else:
            datasourceID = datasourceIDs[0]
        # Check if the datasource owner clicked the button
        if (datasourceID in datasourceIDs):
            dataSource = dataSources[datasourceIDs.index(datasourceID)]
        else:
            print("Data Source is not owned by this user")
            buttons = ['showgraph', 'viewmore', 'giveFeedback']
            foralluser = any([True if x in messagename else False for x in buttons])
            if foralluser:
                dS = db.find_one("datasource", {"_id": datasourceID})
                usr = db.find_one("user", {"email": dS['email']})
                slack_client = WebClient(token=usr['sl_accesstoken'])
            else:
                return make_response("", 200)
        #        if (message_action['actions'][-1]['value'] == 'track'):
        #            houroptions = []
        #            for i in range(0, 24):
        #                houroptions.append({'label': str(i), 'value': i})
        #            minuteoptions = []
        #            for i in range(0, 60):
        #                minuteoptions.append({'label': str(i), 'value': i})
        #            text = message_action['original_message']['attachments'][0]['pretext']
        #            if (("performance" in text.lower()) and ("change" in text.lower())):
        #                slack_client.dialog_open(
        #                    trigger_id=message_action["trigger_id"],
        #                    dialog={
        #                        "title": "Notification Settings",
        #                        "submit_label": "Submit",
        #                        "callback_id": "notification_form",
        #                        "elements": [
        #                            {
        #                                "label": "Module Type",
        #                                "type": "select",
        #                                "name": "module_types",
        #                                "placeholder": "Select a module type",
        #                                "value": "performancechangetracking",
        #                                "options": [
        #                                    {
        #                                        "label": "Performance Changes Tracking",
        #                                        "value": "performancechangetracking"
        #                                    }
        #                                ]
        #                            },
        #                            #                            {
        #                            #                                "label": "Schedule Type",
        #                            #                                "type": "select",
        #                            #                                "name": "schedule_types",
        #                            #                                "placeholder": "Select a schedule type",
        #                            #                                "options": [
        #                            #                                    {
        #                            #                                        "label": "Daily",
        #                            #                                        "value": "daily"
        #                            #                                    },
        #                            #                                    {
        #                            #                                        "label": "Weekly",
        #                            #                                        "value": "weekly"
        #                            #                                    }
        #                            #                                ]
        #                            #                            },
        #                            {
        #                                "label": "Hour",
        #                                "type": "select",
        #                                "name": "hour",
        #                                "placeholder": "Select an hour",
        #                                "options": houroptions
        #                            },
        #                            {
        #                                "label": "Minute",
        #                                "type": "select",
        #                                "name": "minute",
        #                                "placeholder": "Select a minute",
        #                                "options": minuteoptions
        #                            },
        #                            #                            {
        #                            #                                "label": "Threshold (%)",
        #                            #                                "name": "threshold",
        #                            #                                "type": "text",
        #                            #                                "subtype": "number",
        #                            #                                "placeholder": "Enter a number"
        #                            #                            }
        #                        ]
        #                    }
        #                )
        #            elif (("funnel" in text.lower()) and ("change" in text.lower())):
        #                slack_client.dialog_open(
        #                    trigger_id=message_action["trigger_id"],
        #                    dialog={
        #                        "title": "Notification Settings",
        #                        "submit_label": "Submit",
        #                        "callback_id": "notification_form",
        #                        "elements": [
        #                            {
        #                                "label": "Module Type",
        #                                "type": "select",
        #                                "name": "module_types",
        #                                "placeholder": "Select a module type",
        #                                "value": "shoppingfunnelchangetracking",
        #                                "options": [
        #                                    {
        #                                        "label": "Shopping Funnel Changes Tracking",
        #                                        "value": "shoppingfunnelchangetracking"
        #                                    }
        #                                ]
        #                            },
        #                            #                            {
        #                            #                                "label": "Schedule Type",
        #                            #                                "type": "select",
        #                            #                                "name": "schedule_types",
        #                            #                                "placeholder": "Select a schedule type",
        #                            #                                "options": [
        #                            #                                    {
        #                            #                                        "label": "Daily",
        #                            #                                        "value": "daily"
        #                            #                                    },
        #                            #                                    {
        #                            #                                        "label": "Weekly",
        #                            #                                        "value": "weekly"
        #                            #                                    }
        #                            #                                ]
        #                            #                            },
        #                            {
        #                                "label": "Hour",
        #                                "type": "select",
        #                                "name": "hour",
        #                                "placeholder": "Select an hour",
        #                                "options": houroptions
        #                            },
        #                            {
        #                                "label": "Minute",
        #                                "type": "select",
        #                                "name": "minute",
        #                                "placeholder": "Select a minute",
        #                                "options": minuteoptions
        #                            },
        #                            #                            {
        #                            #                                "label": "Threshold (%)",
        #                            #                                "name": "threshold",
        #                            #                                "type": "text",
        #                            #                                "subtype": "number",
        #                            #                                "placeholder": "Enter a number"
        #                            #                            }
        #                        ]
        #                    }
        #                )
        #            elif (("cost" in text.lower()) and ("prediction" in text.lower())):
        #                slack_client.dialog_open(
        #                    trigger_id=message_action["trigger_id"],
        #                    dialog={
        #                        "title": "Notification Settings",
        #                        "submit_label": "Submit",
        #                        "callback_id": "notification_form",
        #                        "elements": [
        #                            {
        #                                "label": "Module Type",
        #                                "type": "select",
        #                                "name": "module_types",
        #                                "placeholder": "Select a module type",
        #                                "value": "costprediction",
        #                                "options": [
        #                                    {
        #                                        "label": "Cost Prediction",
        #                                        "value": "costprediction"
        #                                    }
        #                                ]
        #                            },
        #                            #                            {
        #                            #                                "label": "Schedule Type",
        #                            #                                "type": "select",
        #                            #                                "name": "schedule_types",
        #                            #                                "placeholder": "Select a schedule type",
        #                            #                                "options": [
        #                            #                                    {
        #                            #                                        "label": "Daily",
        #                            #                                        "value": "daily"
        #                            #                                    },
        #                            #                                    {
        #                            #                                        "label": "Weekly",
        #                            #                                        "value": "weekly"
        #                            #                                    }
        #                            #                                ]
        #                            #                            },
        #                            {
        #                                "label": "Hour",
        #                                "type": "select",
        #                                "name": "hour",
        #                                "placeholder": "Select an hour",
        #                                "options": houroptions
        #                            },
        #                            {
        #                                "label": "Minute",
        #                                "type": "select",
        #                                "name": "minute",
        #                                "placeholder": "Select a minute",
        #                                "options": minuteoptions
        #                            },
        #                            #                            {
        #                            #                                "label": "Monthly Adwords Budget",
        #                            #                                "name": "target",
        #                            #                                "type": "text",
        #                            #                                "subtype": "number",
        #                            #                                "placeholder": "Enter a number"
        #                            #                            }
        #                        ]
        #                    }
        #                )
        #            elif (("performance" in text.lower()) and ("goal" in text.lower())):
        #                slack_client.dialog_open(
        #                    trigger_id=message_action["trigger_id"],
        #                    dialog={
        #                        "title": "Notification Settings",
        #                        "submit_label": "Submit",
        #                        "callback_id": "notification_form",
        #                        "elements": [
        #                            {
        #                                "label": "Module Type",
        #                                "type": "select",
        #                                "name": "module_types",
        #                                "placeholder": "Select a module type",
        #                                "value": "performancegoaltracking",
        #                                "options": [
        #                                    {
        #                                        "label": "Performance Goal Tracking",
        #                                        "value": "performancegoaltracking"
        #                                    }
        #                                ]
        #                            },
        #                            {
        #                                "label": "Schedule Type",
        #                                "type": "select",
        #                                "name": "schedule_types",
        #                                "placeholder": "Select a schedule type",
        #                                "options": [
        #                                    {
        #                                        "label": "Daily",
        #                                        "value": "daily"
        #                                    },
        #                                    {
        #                                        "label": "Weekly",
        #                                        "value": "weekly"
        #                                    }
        #                                ]
        #                            },
        #                            {
        #                                "label": "Hour",
        #                                "type": "select",
        #                                "name": "hour",
        #                                "placeholder": "Select an hour",
        #                                "options": houroptions
        #                            },
        #                            {
        #                                "label": "Minute",
        #                                "type": "select",
        #                                "name": "minute",
        #                                "placeholder": "Select a minute",
        #                                "options": minuteoptions
        #                            },
        #                            {
        #                                "label": "Metric Type",
        #                                "type": "select",
        #                                "name": "metric",
        #                                "placeholder": "Select a metric type",
        #                                "options": [
        #                                    {
        #                                        "label": "ROAS",
        #                                        "value": "ga:ROAS"
        #                                    },
        #                                    {
        #                                        "label": "CPC",
        #                                        "value": "ga:CPC"
        #                                    },
        #                                    {
        #                                        "label": "Revenue",
        #                                        "value": "ga:transactionRevenue"
        #                                    }
        #                                ]
        #                            },
        #                            {
        #                                "label": "Goal",
        #                                "name": "target",
        #                                "type": "text",
        #                                "subtype": "number",
        #                                "placeholder": "Enter a number"
        #                            }
        #                        ]
        #                    }
        #                )
        #        # Update the message to show that we're in the process of taking their order
        #        resp = slack_client.api_call(
        #            "chat.update",
        #            channel=channel,
        #            ts=message_ts,
        #            text=message_action['original_message']['text'] + ":pencil: Taking your order...",
        #            attachments=[]
        #        )

        #        elif (message_action['actions'][-1]['value'] == 'change'):
        if ('change' in messagevalue):
            text = message_action['original_message']['text']
            if (True):
                houroptions = []
                for i in range(0, 24):
                    houroptions.append({'label': str(i), 'value': i})
                minuteoptions = []
                for i in range(0, 60):
                    minuteoptions.append({'label': str(i), 'value': i})
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Notification Settings",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "state": str(datasourceID),
                        "elements": [
                            {
                                "label": "Hour",
                                "type": "select",
                                "name": "hour",
                                "placeholder": "Select an hour",
                                "options": houroptions
                            },
                            {
                                "label": "Minute",
                                "type": "select",
                                "name": "minute",
                                "placeholder": "Select a minute",
                                "options": minuteoptions
                            }
                        ]
                    }
                )

        #        elif (message_action['actions'][-1]['value'] == 'setmygoal'):
        elif ('setmygoal' in messagevalue):
            text = message_action['original_message']['text']
            mservice = google_analytics.build_management_api_v3_woutSession(email)
            goals = mservice.management().goals().list(accountId=dataSource['accountID'],
                                                       webPropertyId=dataSource['propertyID'],
                                                       profileId=dataSource['viewID']).execute()
            goaloptions = []
            for goal in goals.get('items', []):
                goalnumber = goal.get('id')
                goalname = goal.get('name')
                goaloptions += [{'label': f'{goalname} (Goal {goalnumber} Completions)',
                                 'value': f'ga:goal{goalnumber}Completions'}]
            if (True):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Set My Goal",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "state": str(datasourceID),
                        "elements": [
                            {
                                "label": "Metric",
                                "type": "select",
                                "name": "metric",
                                "placeholder": "Select a metric",
                                "options": [
                                               {
                                                   "label": "ROAS",
                                                   "value": "ga:ROAS"
                                               },
                                               {
                                                   "label": "CPC",
                                                   "value": "ga:CPC"
                                               },
                                               {
                                                   "label": "Session",
                                                   "value": "ga:sessions",
                                               },
                                               {
                                                   "label": "Cost Per Transaction",
                                                   "value": "ga:costPerTransaction",
                                               },
                                               {
                                                   "label": "Adwords Cost",
                                                   "value": "ga:adCost",
                                               },
                                               {
                                                   "label": "Revenue",
                                                   "value": "ga:transactionRevenue"
                                               },
                                               {
                                                   "label": "Impressions",
                                                   "value": "ga:impressions"
                                               },
                                               {
                                                   "label": "Clicks",
                                                   "value": "ga:adClicks"
                                               },
                                               {
                                                   "label": "New Users",
                                                   "value": "ga:newUsers"
                                               },
                                           ] + goaloptions
                            },
                            {
                                "label": "Filter : Dimension",
                                "type": "select",
                                "name": "dimension",
                                "placeholder": "Select a dimension",
                                "optional": True,
                                "hint": "This will be used for filtering",
                                "options": [
                                    {
                                        "label": "Campaign",
                                        "value": "ga:campaign"
                                    },
                                    {
                                        "label": "Source / Medium",
                                        "value": "ga:sourceMedium"
                                    },
                                    {
                                        "label": "Device Category",
                                        "value": "ga:deviceCategory",
                                    },
                                    {
                                        "label": "Event Category",
                                        "value": "ga:eventCategory",
                                    },
                                    {
                                        "label": "Event Action",
                                        "value": "ga:eventAction",
                                    },
                                    {
                                        "label": "Event Label",
                                        "value": "ga:eventLabel",
                                    },
                                    {
                                        "label": "Channel Grouping",
                                        "value": "ga:channelGrouping",
                                    }
                                ]
                            },
                            {
                                "label": "Operator",
                                "type": "select",
                                "name": "operator",
                                "placeholder": "Select an operator",
                                "optional": True,
                                "hint": "This will be used for filtering",
                                "options": [
                                    {
                                        "label": "Exact Match",
                                        "value": "=="
                                    },
                                    {
                                        "label": "Does Not Match",
                                        "value": "!="
                                    },
                                    {
                                        "label": "Contains",
                                        "value": "=@"
                                    },
                                    {
                                        "label": "Does Not Contain",
                                        "value": "!@",
                                    },
                                ]
                            },
                            {
                                "label": "Expression",
                                "type": "text",
                                "name": "expression",
                                "placeholder": "Enter an expression",
                                "hint": "This will be used for filtering",
                                "optional": True
                            },
                            {
                                "label": "Interval Type",
                                "type": "select",
                                "name": "period",
                                "placeholder": "Select a interval type",
                                "options": [
                                    {
                                        "label": "Daily",
                                        "value": 1
                                    },
                                    {
                                        "label": "Weekly",
                                        "value": 7
                                    },
                                    {
                                        "label": "Monthly",
                                        "value": 30
                                    }
                                ]
                            },
                            {
                                "label": "Target",
                                "type": "text",
                                "name": "target",
                                "subtype": "number",
                                "placeholder": "Enter a target"
                            }
                        ]
                    }
                )
        #        elif (message_action['actions'][-1]['value'] == 'setmyalert'):
        elif ('setmyalert' in messagevalue):
            text = message_action['original_message']['text']
            if (True):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Set My Daily Alert",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "state": str(datasourceID),
                        "elements": [
                            {
                                "label": "Metric",
                                "type": "select",
                                "name": "metric",
                                "placeholder": "Select a metric",
                                "options": [
                                    {
                                        "label": "ROAS",
                                        "value": "ga:ROAS"
                                    },
                                    {
                                        "label": "CPC",
                                        "value": "ga:CPC"
                                    },
                                    {
                                        "label": "Cost Per Transaction",
                                        "value": "ga:costPerTransaction",
                                    },
                                    {
                                        "label": "Cost",
                                        "value": "ga:adCost"
                                    }
                                ]
                            },
                            {
                                "label": "Filter : Dimension",
                                "type": "select",
                                "name": "dimension",
                                "placeholder": "Select a dimension",
                                "optional": True,
                                "hint": "This will be used for filtering",
                                "options": [
                                    {
                                        "label": "Campaign",
                                        "value": "ga:campaign"
                                    },
                                    {
                                        "label": "Source / Medium",
                                        "value": "ga:sourceMedium"
                                    },
                                    {
                                        "label": "Device Category",
                                        "value": "ga:deviceCategory",
                                    },
                                    {
                                        "label": "Event Category",
                                        "value": "ga:eventCategory",
                                    },
                                    {
                                        "label": "Event Action",
                                        "value": "ga:eventAction",
                                    },
                                    {
                                        "label": "Event Label",
                                        "value": "ga:eventLabel",
                                    },
                                    {
                                        "label": "Channel Grouping",
                                        "value": "ga:channelGrouping",
                                    }
                                ]
                            },
                            {
                                "label": "Operator",
                                "type": "select",
                                "name": "operator",
                                "placeholder": "Select an operator",
                                "optional": True,
                                "hint": "This will be used for filtering",
                                "options": [
                                    {
                                        "label": "Exact Match",
                                        "value": "=="
                                    },
                                    {
                                        "label": "Does Not Match",
                                        "value": "!="
                                    },
                                    {
                                        "label": "Contains",
                                        "value": "=@"
                                    },
                                    {
                                        "label": "Does Not Contain",
                                        "value": "!@",
                                    },
                                ]
                            },
                            {
                                "label": "Expression",
                                "type": "text",
                                "name": "expression",
                                "placeholder": "Enter an expression",
                                "hint": "This will be used for filtering",
                                "optional": True
                            },
                            {
                                "label": "Threshold (%)",
                                "type": "text",
                                "name": "threshold",
                                "subtype": "number",
                                "placeholder": "Enter a threshold"
                            }
                        ]
                    }
                )

        #        elif (message_action['actions'][-1]['value'] == 'setmybudget'):
        elif ('setmybudget' in messagevalue):
            text = message_action['original_message']['text']
            currency = babel.numbers.format_currency(0, dataSource['currency']).replace('0.00', '')
            if (True):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Set My Budget",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "state": str(datasourceID),
                        "elements": [
                            {
                                "label": "Interval Type",
                                "type": "select",
                                "name": "period",
                                "placeholder": "Select a interval type",
                                "options": [
                                    {
                                        "label": "Weekly",
                                        "value": 7
                                    },
                                    {
                                        "label": "Monthly",
                                        "value": 30
                                    }
                                ]
                            },
                            {
                                "label": "Filter : Dimension",
                                "type": "select",
                                "name": "dimension",
                                "placeholder": "Select a dimension",
                                "optional": True,
                                "hint": "This will be used for filtering",
                                "options": [
                                    {
                                        "label": "Campaign",
                                        "value": "ga:campaign"
                                    },
                                    {
                                        "label": "Google Ad Account ID",
                                        "value": "ga:adwordsCustomerID",
                                    },
                                    {
                                        "label": "Ad Group",
                                        "value": "ga:adGroup",
                                    },
                                    {
                                        "label": "Keyword",
                                        "value": "ga:keyword",
                                    }
                                ]
                            },
                            {
                                "label": "Operator",
                                "type": "select",
                                "name": "operator",
                                "placeholder": "Select an operator",
                                "optional": True,
                                "hint": "This will be used for filtering",
                                "options": [
                                    {
                                        "label": "Exact Match",
                                        "value": "=="
                                    },
                                    {
                                        "label": "Does Not Match",
                                        "value": "!="
                                    },
                                    {
                                        "label": "Contains",
                                        "value": "=@"
                                    },
                                    {
                                        "label": "Does Not Contain",
                                        "value": "!@",
                                    },
                                ]
                            },
                            {
                                "label": "Expression",
                                "type": "text",
                                "name": "expression",
                                "placeholder": "Enter an expression",
                                "hint": "This will be used for filtering",
                                "optional": True
                            },
                            {
                                "label": f"Adwords Budget ({currency.strip()})",
                                "name": "budget",
                                "type": "text",
                                "subtype": "number",
                                "placeholder": "Enter a number"
                            }
                        ]
                    }
                )
        #        elif message_action['actions'][-1]['value'] == 'analyticsAudit':
        elif ('analyticsAudit' in messagevalue):
            #            dataSource = db.find_one("datasource", query={'sl_userid': sl_userid,
            #                                                          'channelID': channel})
            analyticsAudit(slack_token, task=None, dataSource=dataSource)

        elif ('ignoreone' in messagevalue):
            metric = message_action['actions'][-1]['value'].split(' ')[-1]
            metric = metric.split('_')[0]
            message_ts = message_action['message_ts']
            attachment_id = message_action['attachment_id']
            print("Message TS:", message_ts)
            print("Attachment ID:", attachment_id)
            i = 0
            attachments = message_action['original_message']['attachments']
            for att in attachments:
                if (att['id'] == attachment_id):
                    del attachments[i]
                    break
                i += 1
            print("First Attachments:", attachments)
            if (i == 0):
                attachments[1]["pretext"] = attachments[0]["pretext"]
            del attachments[int(attachment_id) - 1]
            for att in attachments:
                for act in att["actions"]:
                    del act["id"]
                    del act["style"]
                del att["id"]
                del att["fallback"]
                if (not "text" in att.keys()):
                    att["text"] = ""

            print("Last Attachments:", attachments)
            #            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid,
            #                                                            'channelID': channel})['_id']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'performancegoaltracking'})
            module_id = module['_id']
            metricindex = module['metric'].index(metric)
            db.DATABASE['notification'].update_one({"_id": module["_id"]}, {"$unset": {"metric." + str(metricindex): 1,
                                                                                       "target." + str(metricindex): 1,
                                                                                       "filterExpression." + str(
                                                                                           metricindex): 1,
                                                                                       "period." + str(
                                                                                           metricindex): 1}})
            db.DATABASE['notification'].update_one({"_id": module["_id"]}, {"$pull": {"metric": None,
                                                                                      "target": None,
                                                                                      "filterExpression": None,
                                                                                      "period": None}})
            slack_client.chat_update(channel=channel,
                                     ts=message_ts,
                                     text="",
                                     attachments=attachments)
        elif ('ignoreanalert' in messagevalue):
            metric = message_action['actions'][-1]['value'].split(' ')[-1]
            metric = metric.split('_')[0]
            message_ts = message_action['message_ts']
            attachment_id = message_action['attachment_id']
            print("Message TS:", message_ts)
            print("Attachment ID:", attachment_id)
            i = 0
            attachments = message_action['original_message']['attachments']
            for att in attachments:
                if (att['id'] == attachment_id):
                    del attachments[i]
                    break
                i += 1
            print("First Attachments:", attachments)
            if (i == 0):
                attachments[1]["pretext"] = attachments[0]["pretext"]
            del attachments[int(attachment_id) - 1]
            for att in attachments:
                for act in att["actions"]:
                    del act["id"]
                    del act["style"]
                del att["id"]
                del att["fallback"]
                if (not "text" in att.keys()):
                    att["text"] = ""

            print("Last Attachments:", attachments)
            #            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid,
            #                                                            'channelID': channel})['_id']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'performancechangealert'})
            module_id = module['_id']
            metricindex = module['metric'].index(metric)
            db.DATABASE['notification'].update_one({"_id": module["_id"]}, {"$unset": {"metric." + str(metricindex): 1,
                                                                                       "threshold." + str(
                                                                                           metricindex): 1,
                                                                                       "filterExpression." + str(
                                                                                           metricindex): 1,
                                                                                       "period." + str(
                                                                                           metricindex): 1}})
            db.DATABASE['notification'].update_one({"_id": module["_id"]}, {"$pull": {"metric": None,
                                                                                      "threshold": None,
                                                                                      "filterExpression": None,
                                                                                      "period": None}})
            slack_client.chat_update(channel=channel,
                                     ts=message_ts,
                                     text="",
                                     attachments=attachments)
        #        elif (message_action['actions'][-1]['value'] == 'ignore'):
        elif messagename == 'ignore':
            text = message_action['original_message']['attachments'][0]['pretext']
            #            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid, 'channelID': channel})['_id']
            if (("performance" in text.lower()) and ("tracking" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'performancechangetracking'},
                                   status='0')
            elif (("performance" in text.lower()) and ("alert" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'performancechangealert'},
                                   status='0')
            elif (("funnel" in text.lower()) and ("change" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'shoppingfunnelchangetracking'},
                                   status='0')
            elif (("cost" in text.lower()) and ("prediction" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'costprediction'},
                                   status='0')
            elif (("performance" in text.lower()) and ("goal" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'performancegoaltracking'},
                                   status='0')
        elif messagename == 'trackAnalyticsAudit':
            db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                      'type': 'analyticsAudit'},
                               status='1')
            slack_client.chat_postMessage(channel=channel,
                                          text="We will audit your account weekly " + \
                                               "and get to know you about changes.")
        elif messagename == 'ignoreAnalyticsAudit':
            db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                      'type': 'analyticsAudit'},
                               status='0')
            slack_client.chat_postMessage(channel=channel,
                                          text="Got it! You can call analytics audit" + \
                                               "whenever you want via app.heybooster.ai")
        #        elif message_action['actions'][-1]['name'] == "showgraph":
        elif "showgraph" in messagename:
            imageId = message_action['actions'][-1]['value'].split('_')[0]
            message_ts = message_action['message_ts']
            attachment_id = message_action['attachment_id']
            attachments = message_action['original_message']['attachments']
            if not 'image_url' in attachments[int(attachment_id) - 1]:
                attachments[int(attachment_id) - 1]['image_url'] = imageurl.format(imageId)
                for index in range(len(attachments[int(attachment_id) - 1]['actions'])):
                    if (attachments[int(attachment_id) - 1]['actions'][index]['name'] == 'showgraph'):
                        attachments[int(attachment_id) - 1]['actions'][index]['text'] = "Close Graph"
            else:
                for index in range(len(attachments[int(attachment_id) - 1]['actions'])):
                    if (attachments[int(attachment_id) - 1]['actions'][index]['name'] == 'showgraph'):
                        del attachments[int(attachment_id) - 1]['image_url']
                        attachments[int(attachment_id) - 1]['actions'][index]['text'] = "Show Graph"

            for att in attachments:
                for act in att["actions"]:
                    del act["id"]
                    del act["style"]
                del att["id"]
                del att["fallback"]
                if (not "text" in att.keys()):
                    att["text"] = ""

            slack_client.chat_update(channel=channel,
                                     ts=message_ts,
                                     text="",
                                     attachments=attachments)
        #        elif message_action['actions'][-1]['name'] == "viewmore":
        elif "viewmore" in messagename:
            UUID = ObjectId(message_action['actions'][-1]['value'].split('_')[0])
            message_ts = message_action['message_ts']
            button = attachments = message_action['original_message']['attachments'][-1]['actions'][-1]
            if 'More' in button['text']:
                attachments = db2.find_one('attachment', query={'_id': UUID})
                actions = [{"name": "viewmore",
                            "text": "View Less",
                            "type": "button",
                            "value": message_action['actions'][-1]['value']}]
                attachments['attachments'][-1]['actions'] += actions
                upd_attachments = attachments['attachments']
            else:
                attachments = db2.find_one('attachment', query={'_id': UUID})
                upd_attachments = attachments['attachments_short']
            slack_client.chat_update(channel=channel,
                                     ts=message_ts,
                                     text="",
                                     attachments=upd_attachments)

        elif "giveFeedback" in messagename:
            slack_client.views_open(trigger_id=message_action["trigger_id"],
                                    view={
                                        "type": "modal",
                                        "title": {
                                            "type": "plain_text",
                                            "text": "Send us your feedback",
                                            "emoji": True
                                        },
                                        "submit": {
                                            "type": "plain_text",
                                            "text": "Submit",
                                            "emoji": True
                                        },
                                        "close": {
                                            "type": "plain_text",
                                            "text": "Cancel",
                                            "emoji": True
                                        },
                                        "private_metadata": str(datasourceID),
                                        "callback_id": "notification_form",
                                        "blocks": [
                                            {
                                                "type": "section",
                                                "text": {
                                                    "type": "plain_text",
                                                    "text": "Tell us about your experience.",
                                                    "emoji": True
                                                }
                                            },
                                            {
                                                "type": "input",
                                                "block_id": "multi-line",
                                                "element": {
                                                    "type": "plain_text_input",
                                                    "multiline": True,
                                                    "action_id": "ml-value"
                                                },
                                                "label": {
                                                    "type": "plain_text",
                                                    "text": " ",
                                                    "emoji": True
                                                }
                                            }
                                        ]
                                    })

    elif message_action["type"] == "dialog_submission":
        submission = message_action['submission']
        try:
            datasourceID = ObjectId(message_action['state'])
        except:
            datasourceID = datasourceIDs[0]
        # Check if the datasource owner clicked the button
        if (datasourceID in datasourceIDs):
            dataSource = dataSources[datasourceIDs.index(datasourceID)]
        else:
            return make_response("", 200)
        if ('module_types' in submission.keys()):
            lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
            #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
            usr_tz_offset = slack_client.users_info(user=message_action['user']['id'])['user']['tz_offset'] // 3600
            selectedhour = int(submission['hour'])
            selectedminute = str(submission['minute']).zfill(2)
            # writtenhour = str(selectedhour - (usr_tz_offset - lc_tz_offset)).zfill(2)
            if (selectedhour > (usr_tz_offset - lc_tz_offset)):
                writtenhour = str(selectedhour - (usr_tz_offset - lc_tz_offset)).zfill(2)
            else:
                writtenhour = str(24 + (selectedhour - (usr_tz_offset - lc_tz_offset))).zfill(2)
            moduleType = submission['module_types']
            if (moduleType == 'performancechangetracking'):
                #                scheduleType = submission['schedule_types']
                #                threshold = float(submission['threshold'])
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType
                                                                     },
                                   #                                                               scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # threshold=threshold,
                                   # status='1'
                                   )
            elif (moduleType == 'shoppingfunnelchangetracking'):
                #                scheduleType = submission['schedule_types']
                #                threshold = float(submission['threshold'])
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType
                                                                     },
                                   #                                                               scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # threshold=threshold,
                                   # status='1'
                                   )
            elif (moduleType == 'costprediction'):
                #                scheduleType = submission['schedule_types']
                #                target = float(submission['target'])
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType
                                                                     },
                                   #                                                                   scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # target=target,
                                   # status='1'
                                   )
            elif (moduleType == 'performancegoaltracking'):
                #                scheduleType = submission['schedule_types']
                #                target = float(submission['target'])
                #                metric = submission['metric']
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType},
                                   #                                                                       scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # target=target,
                                   # metric=metric,
                                   # status='1'
                                   )
        elif ('hour' in submission.keys() and 'minute' in submission.keys()):
            #            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid,
            #                                                            'channelID': channel})['_id']
            modules = db.find("notification", query={'datasourceID': datasourceID})
            lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
            #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
            usr_tz_offset = slack_client.users_info(user=message_action['user']['id'])['user']['tz_offset'] // 3600
            selectedhour = int(submission['hour'])
            selectedminute = str(submission['minute']).zfill(2)
            # writtenhour = str(selectedhour - (usr_tz_offset - lc_tz_offset)).zfill(2)
            if (selectedhour > (usr_tz_offset - lc_tz_offset)):
                writtenhour = str(selectedhour - (usr_tz_offset - lc_tz_offset)).zfill(2)
            else:
                writtenhour = str(24 + (selectedhour - (usr_tz_offset - lc_tz_offset))).zfill(2)
            for module in modules:
                db.find_and_modify("notification", query={'_id': module['_id']},
                                   timeofDay="%s.%s" % (writtenhour, selectedminute))
            slack_client.chat_postMessage(channel=channel,
                                          text=f"Time of Day is set to {str(selectedhour).zfill(2)}:{selectedminute}  ")
        elif ('metric' in submission.keys() and 'target' in submission.keys()):
            #            dataSource = db.find_one("datasource", query={'sl_userid': sl_userid,
            #                                                          'channelID': channel})
            #            datasourceID = dataSource['_id']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'performancegoaltracking'})
            module_id = module['_id']
            if (submission['dimension'] != None and submission['operator'] != None and submission[
                'expression'] != None):
                filterExpression = submission['dimension'] + submission['operator'] + submission['expression']
            else:
                filterExpression = ''
            if (submission['metric'] in module['metric']):
                metricindex = module['metric'].index(submission['metric'])
                module['metric'] = [submission['metric']]
                module['target'] = [submission['target']]
                module['filterExpression'] = [filterExpression]
                module['period'] = [submission['period']]
                try:
                    performancegoaltracking(slack_token, module, dataSource)
                except Exception as ex:
                    if "Selected dimensions and metrics cannot be queried together" in str(ex):
                        slack_client.chat_postMessage(channel=channel,
                                                      text=":exclamation:ERROR - Selected dimensions and metrics cannot be queried together")
                        return make_response("", 200)
                    raise ex
                db.DATABASE['notification'].update_one(
                    {'_id': module_id},
                    {'$set': {
                        "target." + str(metricindex): submission['target'],
                        "filterExpression." + str(metricindex): filterExpression,
                        "period." + str(metricindex): submission['period']}}
                )
            else:
                module['metric'] = [submission['metric']]
                module['target'] = [submission['target']]
                module['filterExpression'] = [filterExpression]
                module['period'] = [submission['period']]
                try:
                    performancegoaltracking(slack_token, module, dataSource)
                except Exception as ex:
                    if "Selected dimensions and metrics cannot be queried together" in str(ex):
                        slack_client.chat_postMessage(channel=channel,
                                                      text=":exclamation:ERROR - Selected dimensions and metrics cannot be queried together")
                        return make_response("", 200)
                    raise ex
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'metric': submission['metric']}}
                #                )
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'target': submission['target']}}
                #                )
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'filterExpression': filterExpression}}
                #                )
                db.DATABASE['notification'].update_one(
                    {'_id': module_id},
                    {'$push': {'metric': submission['metric'],
                               'target': submission['target'],
                               'filterExpression': filterExpression,
                               'period': submission['period']}}
                )
            db.find_and_modify("notification", query={'_id': module['_id']},
                               status='1')
        elif ('budget' in submission.keys()):
            if (submission['dimension'] != None and submission['operator'] != None and submission[
                'expression'] != None):
                filterExpression = submission['dimension'] + submission['operator'] + submission['expression']
            else:
                filterExpression = ''
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'costprediction'})

            module['target'] = submission['budget']
            module['filterExpression'] = filterExpression
            module['period'] = submission['period']
            costprediction(slack_token, module, dataSource)
            db.find_and_modify(collection='notification', query={'_id': module['_id']},
                               target=submission['budget'],
                               period=submission['period'],
                               filterExpression=filterExpression,
                               status='1'
                               )


        elif ('threshold' in submission.keys()):
            #            dataSource = db.find_one("datasource", query={'sl_userid': sl_userid,
            #                                                          'channelID': channel})
            #            datasourceID = dataSource['_id']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'performancechangealert'})
            module_id = module['_id']

            if (submission['dimension'] != None and submission['operator'] != None and submission[
                'expression'] != None):
                filterExpression = submission['dimension'] + submission['operator'] + submission['expression']
            else:
                filterExpression = ''
            if (submission['metric'] in module['metric']):
                metricindex = module['metric'].index(submission['metric'])
                module['metric'] = [submission['metric']]
                module['threshold'] = [submission['threshold']]
                module['filterExpression'] = [filterExpression]
                #                module['period'] = [submission['period']]
                #                module['period'] = [1]  ## FOR TESTING, PERIOD NOT ADDED YET
                try:
                    performancechangealert(slack_token, module, dataSource)
                except Exception as ex:
                    if "Selected dimensions and metrics cannot be queried together" in str(ex):
                        slack_client.chat_postMessage(channel=channel,
                                                      text=":exclamation:ERROR - Selected dimensions and metrics cannot be queried together")
                        return make_response("", 200)
                    raise ex
                db.DATABASE['notification'].update_one(
                    {'_id': module_id},
                    {'$set': {
                        "threshold." + str(metricindex): submission['threshold'],
                        "filterExpression." + str(metricindex): filterExpression,
                        "period." + str(metricindex): 1}}
                )
            else:
                module['metric'] = [submission['metric']]
                module['threshold'] = [submission['threshold']]
                module['filterExpression'] = [filterExpression]
                #                module['period'] = [submission['period']]
                #                module['period'] = [1]  ## FOR TESTING, PERIOD NOT ADDED YET
                try:
                    performancechangealert(slack_token, module, dataSource)
                except Exception as ex:
                    if "Selected dimensions and metrics cannot be queried together" in str(ex):
                        slack_client.chat_postMessage(channel=channel,
                                                      text=":exclamation:ERROR - Selected dimensions and metrics cannot be queried together")
                        return make_response("", 200)
                    raise ex
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'metric': submission['metric']}}
                #                )
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'threshold': submission['threshold']}}
                #                )
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'filterExpression': filterExpression}}
                #                )
                #                db.DATABASE['notification'].update(
                #                    {'_id': module_id},
                #                    {'$push': {'period': 1}}
                #                )
                db.DATABASE['notification'].update_one(
                    {'_id': module_id},
                    {'$push': {'metric': submission['metric'],
                               'threshold': submission['threshold'],
                               'filterExpression': filterExpression,
                               'period': 1}}
                )
            db.find_and_modify("notification", query={'_id': module['_id']},
                               status='1')
    elif message_action["type"] == "view_submission":
        view = message_action['view']
        feedback = view['state']['values']['multi-line']['ml-value']['value']
        datasourceID = view['private_metadata'].split('_')[-1]
        datasourceID = ObjectId(datasourceID)
        # Check if the datasource owner clicked the button
        if (datasourceID in datasourceIDs):
            dataSource = dataSources[datasourceIDs.index(datasourceID)]
        else:
            dataSource = db.find_one('datasource', {'_id': datasourceID})
        #            return make_response("", 200)
        db.insert_one("feedback",
                      data={"email": dataSource['email'], "datasourceID": datasourceID, "feedback": feedback,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")})
    return make_response("", 200)


def insertdefaultnotifications(email, userID, dataSourceID, channelID, sendWelcome=False):
    # Default Notifications will be inserted here
    #    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['sl_accesstoken']}
    #    requests.post(URL.format('chat.postMessage'), data=json.dumps(data), headers=headers)
    lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
    #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
    #    data = [('token', session['sl_accesstoken']),
    #            ('user', userID)]
    #    usr_tz_offset = requests.post(URL.format('users.info'), data).json()['user']['tz_offset'] // 3600
    user = db.find_one("user", {"email": email})
    usr_tz_offset = user["tz_offset"]
    if (7 >= (usr_tz_offset - lc_tz_offset)):
        default_time = str(7 - (usr_tz_offset - lc_tz_offset)).zfill(2)
    else:
        default_time = str(24 + (7 - (usr_tz_offset - lc_tz_offset))).zfill(2)
    dataSource = db.find_one("datasource", query={"_id": dataSourceID})
    #    db.insert('notification', data={
    #        'type': 'performancechangetracking',
    #        'email': email,
    #        'period': 1,
    #        'threshold': 10,
    #        'scheduleType': 'daily',
    #        'frequency': 0,
    #        'timeofDay': "%s.00" % (default_time),
    #        'status': '1',
    #        'lastRunDate': '',
    #        'datasourceID': dataSourceID
    #    })
    #    db.insert('notification', data={
    #        'type': 'shoppingfunnelchangetracking',
    #        'email': email,
    #        'period': 1,
    #        'threshold': 10,
    #        'scheduleType': 'daily',
    #        'frequency': 0,
    #        'timeofDay': "%s.00" % (default_time),
    #        'status': '1',
    #        'lastRunDate': '',
    #        'datasourceID': dataSourceID
    #    })
    #    db.insert('notification', data={
    #        'type': 'costprediction',
    #        'email': email,
    #        'period': 30,
    #        'target': 100,
    #        'scheduleType': 'daily',
    #        'frequency': 0,
    #        'timeofDay': "%s.00" % (default_time),
    #        'status': '0',
    #        'lastRunDate': '',
    #        'datasourceID': dataSourceID
    #    })
    #    db.insert('notification', data={
    #        'type': 'performancegoaltracking',
    #        'email': email,
    #        'period': [],
    #        'metric': [],
    #        'target': [],
    #        'filterExpression': [],
    #        'scheduleType': 'daily',
    #        'frequency': 0,
    #        'timeofDay': "%s.00" % (default_time),
    #        'status': '0',
    #        'lastRunDate': '',
    #        'datasourceID': dataSourceID
    #    })
    #    db.insert('notification', data={
    #        'type': 'performancechangealert',
    #        'email': email,
    #        'metric': [],
    #        'threshold': [],
    #        'filterExpression': [],
    #        'period': [],
    #        'scheduleType': 'daily',
    #        'frequency': 0,
    #        'timeofDay': "%s.00" % (default_time),
    #        'status': '0',
    #        'lastRunDate': '',
    #        'datasourceID': dataSourceID
    #    })
    db.insert('notification', data={
        'type': 'analyticsAudit',
        'email': email,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': "%s.01" % (default_time),
        'status': '1',
        'lastRunDate': '',
        'datasourceID': dataSourceID,
        'lastStates': {"bounceRateTracking": "",
                       "notSetLandingPage": "",
                       "adwordsAccountConnection": "",
                       "sessionClickDiscrepancy": "",
                       "selfReferral": "",
                       "paymentReferral": "",
                       "goalSettingActivity": "",
                       "botSpamExcluding": "",
                       "customDimension": "",
                       "siteSearchTracking": "",
                       "gdprCompliant": "",
                       "dataRetentionPeriod": "",
                       "remarketingLists": "",
                       "enhancedECommerceActivity": "",
                       "customMetric": "",
                       "samplingCheck": "",
                       "internalSearchTermConsistency": "",
                       "defaultPageControl": "",
                       "domainControl": "",
                       "eventTracking": "",
                       "errorPage": "",
                       "timezone": "",
                       "currency": "",
                       "rawDataView": "",
                       "contentGrouping": "",
                       "userPermission": "",
                       "othersInChannelGrouping": "",
                       },
        "totalScore": 0
    })
    # When the slack connection is completed send notification user to set time
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['sl_accesstoken']}
    #    data = {
    #        "channel": channelID,
    #        "attachments": [{
    #            # "title": "Blog Yazıları",
    #            # "title_link": "https://blog.boostroas.com/tr/"
    #        },
    #            {
    #                "text": "Welcome to Heybooster, I am your digital buddy to support " +
    #                        "you to boost your website by analyzing your data with marketing perspective." +
    #                        "You will get first insights tomorrow at 7 am",
    #                "callback_id": "notification_form",
    #                "color": "#3AA3E3",
    #                "attachment_type": "default",
    #                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
    #                "actions": [
    #                    {
    #                        "name": "change",
    #                        "text": "Reschedule",
    #                        "type": "button",
    #                        "value": f"change_{dataSourceID}"
    #                    },
    #                    {
    #                        "name": "setmygoal",
    #                        "text": "Set My Goal",
    #                        "type": "button",
    #                        "value": f"setmygoal_{dataSourceID}"
    #                    },
    #                    {
    #                        "name": "setmybudget",
    #                        "text": "Set My Budget",
    #                        "type": "button",
    #                        "value": f"setmybudget_{dataSourceID}"
    #                    },
    #                    {
    #                        "name": "setmyalert",
    #                        "text": "Set My Alert",
    #                        "type": "button",
    #                        "value": f"setmyalert_{dataSourceID}"
    #                    },
    #                    {
    #                        "name": "analyticsAudit",
    #                        "text": "Analytics Audit",
    #                        "type": "button",
    #                        "value": f"analyticsAudit_{dataSourceID}"
    #                    },
    #                ]
    #            }]}
    #    text = "Welcome to Heybooster, I am your digital buddy to support " + \
    #            "you to boost your website by analyzing your data with marketing perspective." + \
    #            "You will get first insights tomorrow at 7 am"
    if sendWelcome:
        text1 = "Welcome to heybooster :tada:\n" + \
                "Your Analytics Audit Insights is preparing :coffee: "
        data1 = {
            "channel": channelID,
            "attachments": [
                {
                    "text": text1,
                    "color": "#2eb8a6",
                    "attachment_type": "default",
                    "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n"
                }]}
        requests.post(URL.format('chat.postMessage'), data=json.dumps(data1), headers=headers)


#        #THERE MAY BE A PROBLEM, IF ANALYTICS AUDIT LASTS LONGER THAN EXPECTED
#        post_at = str(int(time.time() + 300)) # 5 minutes later
#        text2 = "Your feedbacks make us stronger :muscle: " + \
#                "Can you share your experience and thoughts with us?"
#        data2 = {
#            "channel": channelID,
#            "attachments": [
#                {
#                    "text": text2,
#                    "callback_id": "notification_form",
#                    "color": "#2eb8a6",
#                    "attachment_type": "default",
#                    "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#                    "actions": [
#                        {
#                            "name": "giveFeedback",
#                            "text": "Give Feedback",
#                            "type": "button",
#                            "value": f"giveFeedback_{dataSourceID}"
#                        },
#                    ]
#                }],
#            "post_at": post_at}
#        requests.post(URL.format('chat.scheduleMessage'), data=json.dumps(data2), headers=headers)


def insertdefaultnotifications_without_slack(email, userID, dataSourceID, channelID, sendWelcome=False):
    # Default Notifications will be inserted here
    #    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['sl_accesstoken']}
    #    requests.post(URL.format('chat.postMessage'), data=json.dumps(data), headers=headers)
    lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
    user = db.find_one("user", {"email": email})
    usr_tz_offset = user["tz_offset"]
    if (6 >= (usr_tz_offset - lc_tz_offset)):
        default_time = str(6 - (usr_tz_offset - lc_tz_offset)).zfill(2)
    else:
        default_time = str(24 + (6 - (usr_tz_offset - lc_tz_offset))).zfill(2)

    dataSource = db.find_one("datasource", query={"_id": dataSourceID})

    db.insert('notification', data={
        'type': 'analyticsAudit',
        'email': email,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': "%s.01" % (default_time),
        'status': '1',
        'lastRunDate': '',
        'datasourceID': dataSourceID,
        'lastStates': {"bounceRateTracking": "",
                       "notSetLandingPage": "",
                       "adwordsAccountConnection": "",
                       "sessionClickDiscrepancy": "",
                       "selfReferral": "",
                       "paymentReferral": "",
                       "goalSettingActivity": "",
                       "botSpamExcluding": "",
                       "customDimension": "",
                       "siteSearchTracking": "",
                       "gdprCompliant": "",
                       "dataRetentionPeriod": "",
                       "remarketingLists": "",
                       "enhancedECommerceActivity": "",
                       "customMetric": "",
                       "samplingCheck": "",
                       "internalSearchTermConsistency": "",
                       "defaultPageControl": "",
                       "domainControl": "",
                       "eventTracking": "",
                       "errorPage": "",
                       "timezone": "",
                       "currency": "",
                       "rawDataView": "",
                       "contentGrouping": "",
                       "userPermission": "",
                       "othersInChannelGrouping": "",
                       },
        "totalScore": 0
    })
    # When the slack connection is completed send notification user to set time
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['ga_accesstoken']}

    if sendWelcome:
        text1 = "Welcome to heybooster :tada:\n" + \
                "Your Analytics Audit Insights is preparing :coffee: "
        data1 = {
            "channel": channelID,
            "attachments": [
                {
                    "text": text1,
                    "color": "#2eb8a6",
                    "attachment_type": "default",
                    "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n"
                }]}
        requests.post(URL.format('chat.postMessage'), data=json.dumps(data1), headers=headers)
