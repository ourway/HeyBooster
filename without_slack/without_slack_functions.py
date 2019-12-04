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
