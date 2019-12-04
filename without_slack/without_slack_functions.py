from flask import Flask, render_template, flash, redirect, request, session
from forms import DataSourceForm
import google_analytics
from database import db
from datetime import datetime, timedelta, timezone
import json
import requests
import time
from bson.objectid import ObjectId
from tasks import run_analyticsAudit


def new_without_slack():
    if session['ga_accesstoken']:
        return redirect('/getstarted/get-first-insight-without-slack')


def new_connectaccount_without_slack():
    if not (session['ga_accesstoken']):
        return redirect('/getstarted/connect-accounts')

    user = db.find_one('user', {'email': session['email']})

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
            'channelType': "Slack",
            'createdTS': ts
        }
        _id = db.insert_one("datasource", data=data).inserted_id
        data['_id'] = _id
        unsortedargs.append(data)
        if len(unsortedargs) == 1:
            insertdefaultnotifications_without_slack(session['email'],
                                                     dataSourceID=_id, userID='',
                                                     channelID='', sendWelcome=False)
            run_analyticsAudit.delay('', str(data['_id']), sendFeedback=True)
        else:
            insertdefaultnotifications_without_slack(session['email'], userID='',
                                                     dataSourceID=_id,
                                                     channelID='')
            run_analyticsAudit.delay('', str(data['_id']))
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


def new_getaudit_without_slack():
    if not (session['ga_accesstoken']):
        return redirect('/getstarted/connect-accounts')

    user = db.find_one('user', {'email': session['email']})
    # tz_offset = user['tz_offset']
    tz_offset = 1
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
            run_analyticsAudit.delay('', str(data['_id']), sendFeedback=True)
        else:
            insertdefaultnotifications_without_slack(session['email'], userID='',
                                                     dataSourceID=_id,
                                                     channelID='')
            run_analyticsAudit.delay('', str(data['_id']))

        #        analyticsAudit(slack_token, task=None, dataSource=data)
        # flash("Check out your connected slack channel, heybooster even wrote you.")

        #        analyticsAudit(slack_token, task=None, dataSource=data)

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
    return render_template('audit_table_without_slack.html', args=args, selectedargs=args, nForm=nForm,
                           current_analyticsemail=current_analyticsemail,
                           analytics_audits=analytics_audits)


def new_audithistory_without_slack(datasourceID):
    user = db.find_one('user', {'email': session['email']})
    #    tz_offset = user['tz_offset']
    tz_offset = 1
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
            'channelType': "Slack",
            'createdTS': ts
        }
        _id = db.insert_one("datasource", data=data).inserted_id
        data['_id'] = _id
        unsortedargs.append(data)
        insertdefaultnotifications_without_slack(session['email'], userID='',
                                                 dataSourceID=_id,
                                                 channelID='')
        #        analyticsAudit(slack_token, task=None, dataSource=data)
        run_analyticsAudit.delay('', str(data['_id']))
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
    for arg in selectedargs:
        analytics_audit = db.find_one('notification', query={"datasourceID": arg['_id'], "type": "analyticsAudit"})
        analytics_audit['localTime'] = Timestamp2Date(analytics_audit['lastRunDate'], tz_offset)
        if analytics_audit['status'] == '0':
            analytics_audit['strstat'] = 'passive'
        else:
            analytics_audit['strstat'] = 'active'
        analytics_audits += [analytics_audit]
    return render_template('audit_table.html', args=args, selectedargs=selectedargs, nForm=nForm,
                           current_analyticsemail=current_analyticsemail,
                           analytics_audits=analytics_audits)


def Timestamp2Date(ts, tz_offset):
    if ts:
        if tz_offset > 0:
            date = datetime.utcfromtimestamp(ts) + timedelta(hours=tz_offset)
        else:
            date = datetime.utcfromtimestamp(ts) - timedelta(hours=tz_offset)
        return date.strftime("%B %d, %Y at %I:%M %p").lstrip("0").replace(" 0", " ")
    else:
        return ""


def insertdefaultnotifications_without_slack(email, userID, dataSourceID, channelID, sendWelcome=False):
    # Default Notifications will be inserted here
    #    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['sl_accesstoken']}
    #    requests.post(URL.format('chat.postMessage'), data=json.dumps(data), headers=headers)
    lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
    #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
    data = [('token', session['ga_accesstoken']),
            ('user', session['ga_accesstoken'])]

    default_time = 2

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
