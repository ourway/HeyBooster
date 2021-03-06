# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:49:15 2019

@author: altun
"""
import google_analytics
from datetime import datetime, timedelta
from slack import WebClient
import time
from matplotlib import pyplot as plt
import uuid
import decimal
import babel.numbers
from flask import session, request
from database import db, db2
from forms import DataSourceForm
from bson.objectid import ObjectId

# from analyticsAudit import adwordsAccountConnection


imagefile = "slackdb/images/{}.png"
imageurl = "https://app.heybooster.ai/images/{}.png"


def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def performancechangetracking(slack_token, task, dataSource):
    #    Performance Changes Tracking
    text_r = "Checkout website performans metrics, something is going down click view more for details."
    text_g = "You are on the right track, everything is superamazing!"
    viewmoretext = text_g
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    dataSourceID = dataSource['_id']
    text = "*Performance Changes Tracking*"
    attachments = []
    actions = []
    metrics = [{'expression': 'ga:ROAS'},
               {'expression': 'ga:CPC'},
               {'expression': 'ga:costPerTransaction'},
               {'expression': 'ga:adCost'},
               ]

    metricnames = ['Adwords ROAS',
                   'Adwords CPC',
                   'Adwords Cost Per Transaction',
                   'Adwords Cost'
                   ]

    conditions = ['More',
                  'Less',
                  'Less',
                  "Equal"]

    currencies = [False,
                  False,
                  True,
                  True]

    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    #    period = task['period']
    period = 1
    tol = 0.30

    filters = [
        {
            "dimensionName": "ga:sourceMedium",
            "operator": "EXACT",
            "expressions": ["google / cpc"]
        }
    ]

    today = datetime.today()

    if (period == 1):
        yesterday = today - timedelta(days=1)
        start_date_1 = dtimetostrf(yesterday)
        str_period_1 = 'Yesterday'
        end_date_1 = start_date_1
        twodaysAgo = today - timedelta(days=2)
        start_date_2 = dtimetostrf(twodaysAgo)
        str_period_2 = 'previous day'
        end_date_2 = start_date_2

    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1},
                                   {'startDate': start_date_2, 'endDate': end_date_2}],
                    'metrics': metrics,
                    "dimensionFilterClauses": [
                        {
                            "filters": filters
                        }]}]}).execute()

    actions = [
        #        {
        #        "name": "track",
        #        "text": "Reschedule",
        #        "type": "button",
        #        "value": "track"
        #    },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": f"ignore_{dataSourceID}",
            "confirm": {
                "title": "Warning",
                "text": "Are you sure you want to close your Performance Change Tracking notifications?",
                "ok_text": "Yes",
                "dismiss_text": "No"
            }
        }]

    for i in range(len(metrics)):
        metricname = metricnames[i]
        currency = currencies[i]
        condition = conditions[i]
        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_new = float(results['reports'][0]['data']['totals'][0]['values'][i])
        print(str(data_new))
        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_old = float(results['reports'][0]['data']['totals'][1]['values'][i])
        print(str(data_old))
        try:
            changerate = str(round(abs(data_old - data_new) / data_old * 100, 2)) + '%'
        except:
            changerate = abs(data_old - data_new)
        if (currency):
            datanewtext = babel.numbers.format_currency(decimal.Decimal(str(data_new)), task['currency'])
        else:
            datanewtext = round(data_new, 2)
        if (data_new < data_old):
            if ((data_old - data_new) <= (tol * data_old)):
                color = "good"
            #                attachments += [{"text": f"Yesterday you got {changerate} less {metricname} than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                if (condition == "Equal"):
                    color = None
                elif (condition == "More"):
                    color = "danger"
                    viewmoretext = text_r
                elif (condition == "Less"):
                    color = "good"

                if (color != "good"):
                    attachments += [{
                        "text": f"{str_period_1} you got {changerate} less {metricname} than {str_period_2}. {metricname} : {datanewtext}\n",
                        "callback_id": "notification_form",
                        'color': color,
                        "attachment_type": "default",
                        "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                    }]
        else:
            if ((data_new - data_old) <= (tol * data_old)):
                color = "good"
            #                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} more {metricname} than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                if (condition == "Equal"):
                    color = None
                elif (condition == "More"):
                    color = "good"
                elif (condition == "Less"):
                    color = "danger"
                    viewmoretext = text_r
                if (color != "good"):
                    attachments += [{
                        "text": f"{str_period_1} you got {changerate} more {metricname} than {str_period_2}. {metricname} : {datanewtext}\n",
                        "callback_id": "notification_form",
                        'color': color,
                        "attachment_type": "default",
                        "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                    }]

    if (len(attachments) != 0):
        attachments[0]['pretext'] = text
        attachments[-1]['actions'] = actions
        if (len(attachments) > 0):
            # If there is more than one message, compress it and send with View More
            UUID = str(db2.insert_one("attachment", data={'attachments': attachments,
                                                          'datasourceID': dataSource['_id'],
                                                          'ts': time.time()
                                                          }).inserted_id)
            actions = [{"name": "viewmore",
                        "text": "View More",
                        "type": "button",
                        "value": f"{UUID}_{dataSourceID}"}]  # + actions
            attachments = [{"text": viewmoretext,
                            "pretext": text,
                            "color": "danger" if viewmoretext == text_r else "good",
                            "callback_id": "notification_form",
                            "attachment_type": "default",
                            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                            "actions": actions
                            }]
            db2.find_and_modify("attachment", query={'_id': ObjectId(UUID)}, attachments_short=attachments)
        slack_client = WebClient(token=slack_token)
        resp = slack_client.chat_postMessage(channel=channel,
                                             attachments=attachments)
        return resp['ts']


def performancechangealert(slack_token, task, dataSource):
    # Custom Performance Change Tracking
    text_r = "You need to check the status, something unexpected happened."
    text_g = "You are on the right track, everything is superamazing!"
    viewmoretext = text_g
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    dataSourceID = dataSource['_id']
    text = "*Custom Performance Change Alerts*"
    attachments = []
    actions = [
        {
            "name": "setmyalert",
            "text": "Set/Change Alert",
            "type": "button",
            "value": f"setmyalert_{dataSourceID}"
        },
        #        {
        #            "name": "track",
        #            "text": "Reschedule",
        #            "type": "button",
        #            "value": "track"
        #        }
        #        {
        #            "name": "ignore",
        #            "text": "Ignore",
        #            "type": "button",
        #            "value": "ignore",
        #            "confirm": {
        #                        "title": "Warning",
        #                        "text": "Are you sure you want to close your Custom Performance Changes Alerts?",
        #                        "ok_text": "Yes",
        #                        "dismiss_text": "No"
        #                    }
        #        }
    ]

    metricdict = {'ga:ROAS': 'Adwords ROAS',
                  'ga:CPC': 'Adwords CPC',
                  'ga:costPerTransaction': 'Adwords Cost Per Transaction',
                  'ga:adCost': 'Adwords Cost'}

    currencydict = {'ga:ROAS': False,
                    'ga:CPC': False,
                    'ga:costPerTransaction': True,
                    'ga:adCost': True}

    metrics = []
    metricnames = []
    thresholds = []
    filters = []
    periods = []
    currencies = []
    for i in range(len(task['metric'])):
        metrics += [{'expression': task['metric'][i]}]
        metricnames += [metricdict[task['metric'][i]]]
        currencies += [currencydict[task['metric'][i]]]
        thresholds += [float(str(task['threshold'][i]).replace(',', '.')) / 100]
        filters += [task['filterExpression'][i]]
        #        periods += [int(task['period'][i])]
        periods += [1]

    email = task['email']
    viewId = task['viewId']
    channel = task['channel']

    today = datetime.today()

    service = google_analytics.build_reporting_api_v4_woutSession(email)

    for i in range(len(metrics)):
        metricname = metricnames[i]
        threshold = thresholds[i]
        filterExpression = filters[i]
        period = periods[i]
        currency = currencies[i]
        if ('Adwords' in metricname):
            if filterExpression != '':
                filterExpression = "ga:sourceMedium==google / cpc;" + filterExpression
            else:
                filterExpression = 'ga:sourceMedium==google / cpc'

        if (period == 1):
            yesterday = today - timedelta(days=1)
            start_date_1 = dtimetostrf(yesterday)
            str_period_1 = 'Yesterday'
            end_date_1 = start_date_1
            twodaysAgo = today - timedelta(days=2)
            start_date_2 = dtimetostrf(twodaysAgo)
            str_period_2 = 'previous day'
            end_date_2 = start_date_2

        results = service.reports().batchGet(
            body={
                'reportRequests': [
                    {
                        'viewId': viewId,
                        'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1},
                                       {'startDate': start_date_2, 'endDate': end_date_2}],
                        'metrics': metrics[i],
                        'filtersExpression': filterExpression,
                        #                    'dimensions': [{'name': 'ga:day'}],
                        'includeEmptyRows': True
                    }]}).execute()

        data_new = float(results['reports'][0]['data']['totals'][0]['values'][0])
        print(str(data_new))
        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_old = float(results['reports'][0]['data']['totals'][1]['values'][0])
        print(str(data_old))

        try:
            changerate = str(round(abs(data_old - data_new) / data_old * 100, 2)) + '%'
        except:
            changerate = abs(data_old - data_new)
        if (currency):
            datanewtext = babel.numbers.format_currency(decimal.Decimal(str(data_new)), task['currency'])
        else:
            datanewtext = round(data_new, 2)
        if (data_new < data_old):
            if ((data_old - data_new) <= (threshold * data_old)):
                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} less {metricname} than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                viewmoretext = text_r
                attachments += [{
                    "text": f"{str_period_1} you got {changerate} less {metricname} than {str_period_2}. {metricname} : {datanewtext}\n",
                    "callback_id": "notification_form",
                    'color': "danger",
                    "attachment_type": "default",
                    "actions": [{
                        "name": "ignore",
                        "text": "Remove",
                        "type": "button",
                        "value": f"ignoreanalert {metrics[i]['expression']}_{dataSourceID}",
                        "confirm": {
                            "title": "Warning",
                            "text": f"If you remove {metricname} performance change alert, you will not track your {metricname} performance change alert anymore. Are you still sure you want to remove it?",
                            "ok_text": "Yes",
                            "dismiss_text": "No"
                        }
                    }]
                }]
        else:
            if ((data_new - data_old) <= (threshold * data_old)):
                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} more {metricname} than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                pass
    #                attachments += [{
    #                    "text": f"{str_period_1} you got {changerate} more {metricname} than {str_period_2}. {metricname} : {datanewtext}\n",
    #                    "callback_id": "notification_form",
    #                    'color': "good",
    #                    "attachment_type": "default",
    #                    "actions": [{
    #                        "name": "ignore",
    #                        "text": "Remove",
    #                        "type": "button",
    #                        "value": "ignoreanalert " + metrics[i]['expression'],
    #                        "confirm": {
    #                            "title": "Warning",
    #                            "text": f"If you remove {metricname} performance change alert, you will not track your {metricname} performance change alert anymore. Are you still sure you want to remove it?",
    #                            "ok_text": "Yes",
    #                            "dismiss_text": "No"
    #                        }
    #                    }]
    #                }]

    if (len(attachments) != 0):
        attachments[0]['pretext'] = text
        attachments += [{"text": "",
                         "color": "FFFFFF",
                         "callback_id": "notification_form",
                         "attachment_type": "default",
                         "actions": actions}]
        if (len(attachments) > 0):
            # If there is more than one message, compress it and send with View More
            UUID = str(db2.insert_one("attachment", data={'attachments': attachments,
                                                          'datasourceID': dataSource['_id'],
                                                          'ts': time.time()
                                                          }).inserted_id)
            actions = [{"name": "viewmore",
                        "text": "View More",
                        "type": "button",
                        "value": f"{UUID}_{dataSourceID}"}]  # + actions
            attachments = [{"text": viewmoretext,
                            "pretext": text,
                            "color": "danger" if viewmoretext == text_r else "good",
                            "callback_id": "notification_form",
                            "attachment_type": "default",
                            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                            "actions": actions
                            }]
            db2.find_and_modify("attachment", query={'_id': ObjectId(UUID)}, attachments_short=attachments)
        slack_client = WebClient(token=slack_token)
        resp = slack_client.chat_postMessage(channel=channel,
                                             attachments=attachments)
        return resp['ts']


def shoppingfunnelchangetracking(slack_token, task, dataSource):
    # Funnel Changes Tracking
    text_r = "There is significant changes on shopping funnel activities in mobile , click view more for details."
    text_g = "You are on the right track, everything is superamazing!"
    viewmoretext = text_g
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    dataSourceID = dataSource['_id']
    text = {}
    text['desktop'] = "*Desktop Shopping Funnel Changes Tracking*"
    text['mobile'] = "* Mobile Shopping Funnel Changes Tracking*"
    attachments = {}
    totalattachments = []
    attachments['mobile'] = []
    attachments['desktop'] = []
    metrics = [
        {'expression': 'ga:sessions'}
    ]

    dimensions = {}
    dimensions['desktop'] = {'ALL_VISITS': 'Number of desktop session',
                             'PRODUCT_VIEW': 'Number of desktop session with product view',
                             'ADD_TO_CART': 'Number of desktop session with add to cart',
                             'CHECKOUT': 'Number of desktop session with checkout',
                             'TRANSACTION': 'Number of desktop session with transaction'
                             }
    dimensions['mobile'] = {'ALL_VISITS': 'Number of mobile session',
                            'PRODUCT_VIEW': 'Number of mobile session with product view',
                            'ADD_TO_CART': 'Number of mobile session with add to cart',
                            'CHECKOUT': 'Number of mobile session with checkout',
                            'TRANSACTION': 'Number of mobile session with transaction'
                            }
    actions = [
        #            {
        #        "name": "track",
        #        "text": "Reschedule",
        #        "type": "button",
        #        "value": "track"
        #    },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": f"ignore_{dataSourceID}",
            "confirm": {
                "title": "Warning",
                "text": "Are you sure you want to close your Shopping Funnel Changes Tracking notifications?",
                "ok_text": "Yes",
                "dismiss_text": "No"
            }
        }]
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']
    period = task['period']

    tol = 0.30
    today = datetime.today()

    if (period == 1):
        yesterday = today - timedelta(days=1)
        start_date_1 = dtimetostrf(yesterday)
        end_date_1 = start_date_1
        twodaysAgo = today - timedelta(days=2)
        start_date_2 = dtimetostrf(twodaysAgo)
        end_date_2 = start_date_2

    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1},
                                   {'startDate': start_date_2, 'endDate': end_date_2}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:shoppingStage'},
                                   {'name': 'ga:deviceCategory'}]
                }]}).execute()

    for seg in ['desktop', 'mobile']:
        try:
            dims_new = [row['dimensions'][0] for row in results['reports'][0]['data']['rows'] if
                        row['dimensions'][1] == seg]
            datas_new = [float(row['metrics'][0]['values'][0]) for row in results['reports'][0]['data']['rows'] if
                         row['dimensions'][1] == seg]
        except:
            dims_new = []
            datas_new = []
        try:
            dims_old = [row['dimensions'][0] for row in results['reports'][0]['data']['rows'] if
                        row['dimensions'][1] == seg]
            datas_old = [float(row['metrics'][1]['values'][0]) for row in results['reports'][0]['data']['rows'] if
                         row['dimensions'][1] == seg]
        except:
            dims_old = []
            datas_old = []

        for i in range(len(metrics)):
            for dim in dimensions[seg].keys():
                try:
                    j1 = dims_new.index(dim)
                    data_new = datas_new[j1]
                except:
                    data_new = 0

                try:
                    j2 = dims_old.index(dim)
                    data_old = datas_old[j2]
                except:
                    data_old = 0

                dimname = dimensions[seg][dim]

                #            sessions_new = float(results['reports'][0]['data']['rows'][j]['metrics'][0]['values'][0])
                #            sessions_old = float(['reports'][0]['data']['rows'][j]['metrics'][1]['values'][0])
                try:
                    changerate = str(round(abs(data_old - data_new) / data_old * 100, 2)) + '%'
                except:
                    changerate = abs(data_old - data_new)
                if (data_new < data_old):
                    if ((data_old - data_new) <= (tol * data_old)):
                        pass
                    #                    attachments += [{"text": f"Yesterday {dimname} is {changerate} less than previous day. {dimname} : {int(data_new)}\n",
                    #                        "callback_id": "notification_form",
                    #                        "attachment_type": "default",
                    #                    }]
                    else:
                        viewmoretext = text_r
                        attachments[seg] += [{
                            "text": f"Yesterday {dimname} is {changerate} less than previous day. {dimname} : {int(data_new)}\n",
                            "callback_id": "notification_form",
                            'color': "danger",
                            "attachment_type": "default",
                            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                        }]
                else:
                    if ((data_new - data_old) <= (tol * data_old)):
                        pass
                    #                    attachments += [{"text": f"Yesterday {dimname} is {changerate} more than previous day. {dimname} : {int(data_new)}\n",
                    #                        "callback_id": "notification_form",
                    #                        "attachment_type": "default",
                    #                    }]
                    else:
                        pass
        #                        attachments[seg] += [{
        #                            "text": f"Yesterday {dimname} is {changerate} more than previous day. {dimname} : {int(data_new)}\n",
        #                            "callback_id": "notification_form",
        #                            'color': "good",
        #                            "attachment_type": "default",
        #                            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
        #                        }]
        if (len(attachments[seg]) > 0):
            attachments[seg][0]['pretext'] = text[seg]

        totalattachments += attachments[seg]

    if (len(totalattachments) > 0):
        totalattachments += [{"text": "",
                              "color": "FFFFFF",
                              "callback_id": "notification_form",
                              "attachment_type": "default",
                              "actions": actions}]
        if len(totalattachments) > 0:
            # If there is more than one message, compress it and send with View More
            UUID = str(db2.insert_one("attachment", data={'attachments': totalattachments,
                                                          'datasourceID': dataSource['_id'],
                                                          'ts': time.time()
                                                          }).inserted_id)
            actions = [{"name": "viewmore",
                        "text": "View More",
                        "type": "button",
                        "value": f"{UUID}_{dataSourceID}"}]  # + actions
            attachments = [{"text": viewmoretext,
                            "pretext": "*Shopping Funnel Changes Tracking*",
                            "color": "danger" if viewmoretext == text_r else "good",
                            "callback_id": "notification_form",
                            "attachment_type": "default",
                            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                            "actions": actions
                            }]
            db2.find_and_modify("attachment", query={'_id': ObjectId(UUID)}, attachments_short=attachments)
        slack_client = WebClient(token=slack_token)
        resp = slack_client.chat_postMessage(
            channel=channel,
            attachments=attachments)
        return resp['ts']


def costprediction(slack_token, task, dataSource):
    # Cost Prediction
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    dataSourceID = dataSource['_id']
    text = "*Cost Prediction*"
    attachments = []
    actions = [
        {
            "name": "setmybudget",
            "text": "Set My Budget",
            "type": "button",
            "value": f"setmybudget_{dataSourceID}"
        },
        #        {
        #            "name": "track",
        #            "text": "Reschedule",
        #            "type": "button",
        #            "value": "track"
        #        },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": f"ignore_{dataSourceID}",
            "confirm": {
                "title": "Warning",
                "text": "Are you sure you want to close your Cost Prediction notification?",
                "ok_text": "Yes",
                "dismiss_text": "No"
            }
        }]
    metrics = [
        {'expression': 'ga:adCost'},
    ]

    tol = 0.30
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    target = float(str(task['target']).replace(',', '.'))
    period = int(task['period'])
    if 'filterExpression' in task.keys():
        filterExpression = task['filterExpression']
    else:
        filterExpression = ''

    if filterExpression != '':
        filterExpression = "ga:sourceMedium==google / cpc;" + filterExpression
    else:
        filterExpression = 'ga:sourceMedium==google / cpc'

    today = datetime.today()

    if period == 7:
        start_date_1 = dtimetostrf((today - timedelta(days=today.weekday())))  # Convert it to string format
        end_date_1 = dtimetostrf((today - timedelta(days=1)))
        days = 7 - today.weekday()
        str_period = "weekly"
    elif period == 30:
        start_date = datetime(today.year, today.month, 1)
        try:
            end_date = datetime(today.year, today.month + 1, 1)
        except:
            end_date = datetime(today.year + 1, 1, 1)
        days = (end_date - today + timedelta(days=1)).days
        start_date_1 = dtimetostrf(start_date)
        end_date_1 = dtimetostrf((today - timedelta(days=1)))
        str_period = "monthly"

    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    #                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1},
                    #                                   {'startDate': start_date_2, 'endDate': end_date_2}],
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': filterExpression,
                    'dimensions': [{'name': 'ga:day'}],
                    'includeEmptyRows': True
                }]}).execute()

    #    subquery1 = float(results['reports'][0]['data']['totals'][0]['values'][0])
    #    subquery2 = float(results['reports'][0]['data']['totals'][1]['values'][0])
    #    prediction = subquery2 * days + subquery1
    #    targettext = babel.numbers.format_currency(decimal.Decimal(str(target)), task['currency'])
    #    predtext = babel.numbers.format_currency(decimal.Decimal(str(prediction)), task['currency'])
    #    print("Target:", targettext)
    #    print("Prediction:", predtext)
    yval = [float(row['metrics'][0]['values'][0]) for row in results['reports'][0]['data']['rows']]
    #        xval = list(range(1, today.day)) #It is applied for preventing graph dimension error
    xval = list(range(1, len(yval) + 1))
    plt.plot(xval, yval, marker='o')
    plt.xlabel('Day')
    plt.ylabel(metrics)
    imageId = uuid.uuid4().hex
    plt.savefig(imagefile.format(imageId))
    plt.clf()
    subquery1 = float(results['reports'][0]['data']['totals'][0]['values'][0])
    subquery2 = yval[-1]
    prediction = subquery2 * days + subquery1
    targettext = babel.numbers.format_currency(decimal.Decimal(str(target)), task['currency'])
    predtext = babel.numbers.format_currency(decimal.Decimal(str(prediction)), task['currency'])
    print("Target:", targettext)
    print("Prediction:", predtext)

    actions += [{"name": "showgraph",
                 "text": "Show Graph",
                 "type": "button",
                 "value": f"{imageId}_{dataSourceID}"}]
    if (prediction > target):
        # Prediction is more than target
        if ((prediction - target < (tol * target))):
            attachments += [{
                "text": f"Your {str_period} adwords total cost is predicted to be more than {str_period} budget. Predicted Value: {predtext} {str_period[0].upper() + str_period[1:]} Budget: {targettext}",
                "color": "good",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                #                "image_url": imageurl.format(imageId),
                "actions": actions
            }]
        else:
            attachments += [{
                "text": f"Your {str_period} adwords total cost is predicted to be more than {str_period} budget. Predicted Value: {predtext} {str_period[0].upper() + str_period[1:]} Budget: {targettext}",
                "color": "danger",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                #                "image_url": imageurl.format(imageId),
                "actions": actions
            }]
    else:
        # Prediction is less than target
        if ((target - prediction < (tol * target))):
            attachments += [{
                "text": f"Your {str_period} adwords total cost is predicted to be less than {str_period} budget. Predicted Value: {predtext} {str_period[0].upper() + str_period[1:]} Budget: {targettext}",
                "color": "good",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                #                "image_url": imageurl.format(imageId),
                "actions": actions
            }]
        else:
            attachments += [{
                "text": f"Your {str_period} adwords total cost is predicted to be less than {str_period} budget. Predicted Value: {predtext} {str_period[0].upper() + str_period[1:]} Budget: {targettext}",
                "color": "danger",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                #                "image_url": imageurl.format(imageId),
                "actions": actions
            }]

    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(
        channel=channel,
        attachments=attachments)
    #    adwordsAccountConnection(slack_token, task, dataSource)
    return resp['ts']


def performancegoaltracking(slack_token, task, dataSource):
    # Performance Goal Tracking
    # text_r = "You need to check the status, something unexpected happened."
    # text_g = "You are on the right track, everything is superamazing!"
    # viewmoretext = text_g
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    dataSourceID = dataSource['_id']
    text = "*Performance Goal Tracking*"
    attachments = []
    actions = [
        {
            "name": "setmygoal",
            "text": "Track More/Change",
            "type": "button",
            "value": f"setmygoal_{dataSourceID}"
        },
        #        {
        #            "name": "track",
        #            "text": "Reschedule",
        #            "type": "button",
        #            "value": "track"
        #        }
        #        {
        #            "name": "ignore",
        #            "text": "Ignore",
        #            "type": "button",
        #            "value": "ignore",
        #            "confirm": {
        #                        "title": "Warning",
        #                        "text": "Are you sure you want to close your Performance Goal Tracking notifications?",
        #                        "ok_text": "Yes",
        #                        "dismiss_text": "No"
        #                    }
        #        }
    ]
    ##FASTER BUT STATIC SOLUTION
    #    goalCompletions = []
    #    for i in range(1,21):
    #        goalCompletions += [{f'ga:goal{i}Completion': 'Goal {} Completions'}]

    mservice = google_analytics.build_management_api_v3_woutSession(dataSource['email'])
    goals = mservice.management().goals().list(accountId=dataSource['accountID'],
                                               webPropertyId=dataSource['propertyID'],
                                               profileId=dataSource['viewID']).execute()

    metricdict = {'ga:ROAS': 'Adwords ROAS',
                  'ga:CPC': 'Adwords CPC',
                  'ga:sessions': 'Session',
                  'ga:costPerTransaction': 'Adwords Cost Per Transaction',
                  'ga:adCost': "Adwords Cost",
                  'ga:transactionRevenue': 'Revenue',
                  'ga:impressions': 'Impression',
                  'ga:adClicks': 'Click',
                  'ga:newUsers': 'New User'}

    conditiondict = {'ga:ROAS': 'More',
                     'ga:CPC': 'Less',
                     'ga:sessions': 'More',
                     'ga:costPerTransaction': 'Less',
                     'ga:adCost': "Equal",
                     'ga:transactionRevenue': 'More',
                     'ga:impressions': 'More',
                     'ga:adClicks': 'More',
                     'ga:newUsers': 'More'}

    currencydict = {'ga:ROAS': False,
                    'ga:CPC': False,
                    'ga:sessions': False,
                    'ga:costPerTransaction': True,
                    'ga:adCost': True,
                    'ga:transactionRevenue': True,
                    'ga:impressions': False,
                    'ga:adClicks': False,
                    'ga:newUsers': False}
    ##SLOW BUT DYNAMIC SOLUTION
    for goal in goals.get('items', []):
        goalnumber = goal.get('id')
        goalname = goal.get('name')
        metricdict[f'ga:goal{goalnumber}Completions'] = f'{goalname} (Goal {goalnumber} Completions)'
        conditiondict[f'ga:goal{goalnumber}Completions'] = "More"
        currencydict[f'ga:goal{goalnumber}Completions'] = False

    metrics = []
    metricnames = []
    targets = []
    filters = []
    periods = []
    conditions = []
    currencies = []
    tol = 0.05
    for i in range(len(task['metric'])):
        metrics += [{'expression': task['metric'][i]}]
        metricnames += [metricdict[task['metric'][i]]]
        conditions += [conditiondict[task['metric'][i]]]
        currencies += [currencydict[task['metric'][i]]]
        targets += [float(str(task['target'][i]).replace(',', '.'))]
        filters += [task['filterExpression'][i]]
        periods += [int(task['period'][i])]

    email = task['email']
    viewId = task['viewId']
    channel = task['channel']

    today = datetime.today()
    #    start_date = datetime(today.year, today.month, 1)  # First day of current day
    #
    #    start_date_1 = dtimetostrf(start_date)  # Convert it to string format
    #    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)

    for i in range(len(metrics)):
        metricname = metricnames[i]
        target = targets[i]
        filterExpression = filters[i]
        period = periods[i]
        condition = conditions[i]
        currency = currencies[i]
        if ('Adwords' in metricname):
            if filterExpression != '':
                filterExpression = "ga:sourceMedium==google / cpc;" + filterExpression
            else:
                filterExpression = 'ga:sourceMedium==google / cpc'

        if (period == 1):
            start_date_1 = dtimetostrf((today - timedelta(days=1)))
            end_date_1 = start_date_1
            str_period = "Yesterday"
        elif (period == 7):
            start_date_1 = dtimetostrf((today - timedelta(days=today.weekday())))  # Convert it to string format
            end_date_1 = dtimetostrf((today - timedelta(days=1)))
            str_period = "This week"
            if (start_date_1 > end_date_1):
                start_date_1 = dtimetostrf(today)  # Convert it to string format
                end_date_1 = start_date_1
        elif (period == 30):
            start_date = datetime(today.year, today.month, 1)  # First day of current day
            start_date_1 = dtimetostrf(start_date)  # Convert it to string format
            end_date_1 = dtimetostrf((today - timedelta(days=1)))
            str_period = "This month"
            if (start_date_1 > end_date_1):
                start_date_1 = dtimetostrf(today)  # Convert it to string format
                end_date_1 = start_date_1

        results = service.reports().batchGet(
            body={
                'reportRequests': [
                    {
                        'viewId': viewId,
                        'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                        'metrics': metrics[i],
                        'filtersExpression': filterExpression,
                        'dimensions': [{'name': 'ga:day'}],
                        'includeEmptyRows': True
                    }]}).execute()
        querytotal = float(results['reports'][0]['data']['totals'][0]['values'][0])
        if (str("%.2f" % (round(querytotal, 2))).split('.')[1] == '00'):
            querytotal = int(querytotal)
        if (str("%.2f" % (round(target, 2))).split('.')[1] == '00'):
            target = int(target)
        yval = [float(row['metrics'][0]['values'][0]) for row in results['reports'][0]['data']['rows']]
        #        xval = list(range(1, today.day)) #It is applied for preventing graph dimension error
        xval = list(range(1, len(yval) + 1))
        plt.plot(xval, yval, marker='o')
        plt.xlabel('Day')
        plt.ylabel(metricname)
        imageId = uuid.uuid4().hex
        plt.savefig(imagefile.format(imageId))
        plt.clf()
        if ((abs(querytotal - target) / target) <= tol):
            color = "good"
        else:
            if (condition == "Equal"):
                color = "danger"
                # viewmoretext = text_r
            elif (condition == "More"):
                if (querytotal > target):
                    if (querytotal < target * (1 + 0.81)):
                        color = "good"
                    else:
                        color = None
                else:
                    color = "danger"
                    # viewmoretext = text_r
            elif (condition == "Less"):
                if (querytotal < target):
                    if (querytotal > target * (1 - 0.81)):
                        color = "good"
                    else:
                        color = None
                else:
                    color = "danger"
                    # viewmoretext = text_r
            else:
                color = None
        if (currency):
            querytotaltext = babel.numbers.format_currency(decimal.Decimal(str(querytotal)), task['currency'])
            targettext = babel.numbers.format_currency(decimal.Decimal(str(target)), task['currency'])
        else:
            querytotaltext = round(querytotal, 2)
            targettext = round(target, 2)

        if filterExpression:
            filterExpressionText = "Filter: {}".format(filterExpression)
        else:
            filterExpressionText = ""

        attachments += [
            {"text": f"{str_period}, {metricname} is {querytotaltext}, Your Target {metricname}: {targettext}",
             "color": color,
             "callback_id": "notification_form",
             "attachment_type": "default",
             "footer": f"{filterExpressionText}\n{dataSource['propertyName']} & {dataSource['viewName']}\n",
             #                             "image_url": imageurl.format(imageId),
             "actions": [{
                 "name": "ignore",
                 "text": "Remove",
                 "type": "button",
                 "value": f"ignoreone {metrics[i]['expression']}_{dataSourceID}",
                 "confirm": {
                     "title": "Warning",
                     "text": f"If you remove {metricname} notification, you will not track your {metricname} goal anymore. Are you still sure you want to remove it?",
                     "ok_text": "Yes",
                     "dismiss_text": "No"
                 }
             },
                 {"name": "showgraph",
                  "text": "Show Graph",
                  "type": "button",
                  "value": f"{imageId}_{dataSourceID}"}],

             }]
    #        if ((abs(querytotal - target) / target) <= tol):
    #            attachments += [
    #                {"text": f"{str_period}, {metricname} is {round(querytotal, 2)}, Your Target {metricname}: {target}",
    #                 "color": "good",
    #                 "callback_id": "notification_form",
    #                 "attachment_type": "default",
    #                 "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
    #                 #                             "image_url": imageurl.format(imageId),
    #                 "actions": [{
    #                     "name": "ignore",
    #                     "text": "Remove",
    #                     "type": "button",
    #                     "value": "ignoreone " + metrics[i]['expression'],
    #                     "confirm": {
    #                         "title": "Warning",
    #                         "text": f"If you remove {metricname} notification, you will not track your {metricname} goal anymore. Are you still sure you want to remove it?",
    #                         "ok_text": "Yes",
    #                         "dismiss_text": "No"
    #                     }
    #                 },
    #                     {"name": "showgraph",
    #                      "text": "Show Graph",
    #                      "type": "button",
    #                      "value": f"{imageId}"}],
    #
    #                 }]
    #
    #        else:
    #            attachments += [
    #                {"text": f"{str_period}, {metricname} is {round(querytotal, 2)}, Your Target {metricname}: {target}",
    #                 "color": "danger",
    #                 "callback_id": "notification_form",
    #                 "attachment_type": "default",
    #                 "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
    #                 #                             "image_url": imageurl.format(imageId),
    #                 "actions": [{
    #                     "name": "ignore",
    #                     "text": "Remove",
    #                     "type": "button",
    #                     "value": "ignoreone " + metrics[i]['expression'],
    #                     "confirm": {
    #                         "title": "Warning",
    #                         "text": f"If you remove {metricname} notification, you will not track your {metricname} goal anymore. Are you still sure you want to remove it?",
    #                         "ok_text": "Yes",
    #                         "dismiss_text": "No"
    #                     }
    #                 },
    #                     {"name": "showgraph",
    #                      "text": "Show Graph",
    #                      "type": "button",
    #                      "value": f"{imageId}"}]
    #                 }]

    attachments[0]['pretext'] = text
    attachments += [{"text": "",
                     "color": "FFFFFF",
                     "callback_id": "notification_form",
                     "attachment_type": "default",
                     "actions": actions}]
    # if(len(attachments) > 2):
    #     UUID = str(db2.insert_one("attachment", data = {'attachments': attachments}).inserted_id)
    #     actions = [{"name": "viewmore",
    #              "text": "View More",
    #              "type": "button",
    #              "value": f"{UUID}"}] # + actions
    #     attachments = [{"text": "",
    #                     "pretext": text,
    #                     "color": "danger",
    #                     "callback_id": "notification_form",
    #                     "attachment_type": "default",
    #                     "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
    #                     "actions": actions
    #                     }]
    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(channel=channel,
                                         attachments=attachments)

    return resp['ts']
