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


imagefile = "slackdb/images/{}.png"
imageurl = "https://app.heybooster.ai/images/{}.png"

def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def performancechangetracking(slack_token, task, dataSource):
    #    Performance Changes Tracking
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    text = "*Performance Changes Tracking*"
    attachments = []

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

    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    period = task['period']

    tol = 0.10

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
        str_start_date_1 = 'Yesterday'
        end_date_1 = start_date_1
        twodaysAgo = today - timedelta(days=2)
        start_date_2 = dtimetostrf(twodaysAgo)
        str_start_date_2 = 'previous day'
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
            "value": "ignore",
            "confirm": {
                        "title": "Warning",
                        "text": "Are you sure you want to close your Performance Change Tracking notifications?",
                        "ok_text": "Yes",
                        "dismiss_text": "No"
                    }
        }]

    for i in range(len(metrics)):
        metricname = metricnames[i]

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
        if (data_new < data_old):
            if ((data_old - data_new) <= (tol * data_old)):
                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} less {metricname} than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                attachments += [{
                                    "text": f"Yesterday you got {changerate} less {metricname} than previous day. {metricname} : {round(data_new, 2)}\n",
                                    "callback_id": "notification_form",
                                    'color': "danger",
                                    "attachment_type": "default",
                                    }]
        else:
            if ((data_new - data_old) <= (tol * data_old)):
                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} more {metricname} than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                attachments += [{
                                    "text": f"Yesterday you got {changerate} more {metricname} than previous day. {metricname} : {round(data_new, 2)}\n",
                                    "callback_id": "notification_form",
                                    'color': "good",
                                    "attachment_type": "default",
                                    }]

        if (len(attachments) != 0):
            attachments[0]['pretext'] = text
            attachments[-1]['actions'] = actions
            slack_client = WebClient(token=slack_token)
            resp = slack_client.chat_postMessage(
                channel=channel,
                attachments=attachments)

            return resp['ts']


# def performancechangetracking(slack_token, task):
#    # Mobile Performance Changes Tracking
#    text_m = "*Mobile Performance Changes Tracking*"
#    attachments_m = []
#    metrics = [{'expression': 'ga:sessions'}]
#    email = task['email']
#    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    viewId = task['viewId']
#    channel = task['channel']
#
#    period = task['period']
#    threshold = float(task['threshold']) / 100
#    filters = [
#        {
#            "dimensionName": "ga:deviceCategory",
#            "operator": "EXACT",
#            "expressions": ["mobile"]
#        }
#    ]
#
#    if (period == 1):
#        start_date_1 = 'yesterday'
#        end_date_1 = start_date_1
#        start_date_2 = '2daysAgo'
#        end_date_2 = start_date_2
#
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1},
#                                   {'startDate': start_date_2, 'endDate': end_date_2}],
#                    'metrics': metrics,
#                    "dimensionFilterClauses": [
#                        {
#                            "filters": filters
#                        }]}]}).execute()
#
#    # WARNING: When the number of metrics is increased, 
#    # WARNING: obtain data for other metrics
#    sessions_new = float(results['reports'][0]['data']['totals'][0]['values'][0])
#
#    # WARNING: When the number of metrics is increased, 
#    # WARNING: obtain data for other metrics
#    sessions_old = float(results['reports'][0]['data']['totals'][1]['values'][0])
#
#    if (sessions_new < sessions_old * (1 - threshold)):
#        attachments_m += [{"text": "{0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
#            start_date_1,
#            round(threshold * 100, 2),
#            start_date_2,
#            int(sessions_new)),
#            "color": "#FF0000",
#            "pretext": text_m}]
#
#    # Desktop Performance Changes Tracking
#    text_d = "*Desktop Performance Changes Tracking*"
#    attachments_d = []
#
#    filters = [
#        {
#            "dimensionName": "ga:deviceCategory",
#            "operator": "EXACT",
#            "expressions": ["desktop"]
#        }
#    ]
#
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1},
#                                   {'startDate': start_date_2, 'endDate': end_date_2}],
#                    'metrics': metrics,
#                    "dimensionFilterClauses": [
#                        {
#                            "filters": filters
#                        }]}]}).execute()
#
#    # WARNING: When the number of metrics is increased, 
#    # WARNING: obtain data for other metrics
#    sessions_new = float(results['reports'][0]['data']['totals'][0]['values'][0])
#
#    # WARNING: When the number of metrics is increased, 
#    # WARNING: obtain data for other metrics
#    sessions_old = float(results['reports'][0]['data']['totals'][1]['values'][0])
#
#    if (sessions_new < sessions_old * (1 - threshold)):
#        attachments_d += [{"text": "{0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
#            start_date_1,
#            round(threshold * 100, 2),
#            start_date_2,
#            int(sessions_new)),
#            "color": "FF0000",
#            "pretext": text_d,
#            "callback_id": "notification_form",
#            "attachment_type": "default",
#            "actions": [{
#                "name": "track",
#                "text": "Reschedule",
#                "type": "button",
#                "value": "track"
#            },
#                {
#                    "name": "ignore",
#                    "text": "Ignore",
#                    "type": "button",
#                    "value": "ignore"
#                }]
#        }]
#
#        slack_client = WebClient(token=slack_token)
#        resp = slack_client.chat_postMessage(
#            channel=channel,
#            attachments=attachments_m + attachments_d)
#
#        return resp['ts']
# """
#    attachments_d += [{
#        "pretext": "Click *_Track_* to configure *_Performance Changes Tracking_* notification",
#        "callback_id": "notification_form",
#        "color": "#3AA3E3",
#        "attachment_type": "default",
#        "actions": [{
#            "name": "ignore",
#            "text": "Ignore",
#            "type": "button",
#            "value": "ignore"
#        },
#            {
#                "name": "track",
#                "text": "Reschedule",
#                "type": "button",
#                "value": "track"
#            }]
#    }]
#    
#    if (len(attachments_m + attachments_d) > 1):
#        resp = slack_client.chat_postMessage(
#            channel=channel,
#            attachments=attachments_m + attachments_d)
#
#        return resp['ts']
# """

def shoppingfunnelchangetracking(slack_token, task, dataSource):
    # Funnel Changes Tracking
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    text = "*Shopping Funnel Changes Tracking*"
    attachments = []
    metrics = [
        {'expression': 'ga:sessions'}
    ]
    metricnames = [
        'Session'
    ]
    dimensions = {'ALL_VISITS': 'Number of session',
                  'PRODUCT_VIEW': 'Number of session with product view',
                  'ADD_TO_CART': 'Number of session with add to cart',
                  'CHECKOUT': 'Number of session with checkout',
                  'TRANSACTION': 'Number of session with transaction'
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
            "value": "ignore",
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

    tol = 0.10
    
    today = datetime.today()
    
    if (period == 1):
        yesterday = today - timedelta(days = 1)
        start_date_1 = dtimetostrf(yesterday)
        end_date_1 = start_date_1
        twodaysAgo = today - timedelta(days = 2)
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
                    'dimensions': [{'name': 'ga:shoppingStage'}]
                }]}).execute()
    try:    
        dims_new = [row['dimensions'][0] for row in results['reports'][0]['data']['rows']]
        datas_new = [float(row['metrics'][0]['values'][0]) for row in results['reports'][0]['data']['rows']]
    except:
        dims_new = []
        datas_new = []
    try:
        dims_old = [row['dimensions'][0] for row in results['reports'][0]['data']['rows']]
        datas_old = [float(row['metrics'][1]['values'][0]) for row in results['reports'][0]['data']['rows']]
    except:
        dims_old = []
        datas_old = []

    for i in range(len(metrics)):
        metricname = metricnames[i]
        for dim in dimensions.keys():
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

            dimname = dimensions[dim]

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

                    attachments += [{
                                        "text": f"Yesterday {dimname} is {changerate} less than previous day. {dimname} : {int(data_new)}\n",
                                        "callback_id": "notification_form",
                                        'color': "danger",
                                        "attachment_type": "default",
                                        }]
            else:
                if ((data_new - data_old) <= (tol * data_old)):
                    pass
#                    attachments += [{"text": f"Yesterday {dimname} is {changerate} more than previous day. {dimname} : {int(data_new)}\n",
#                        "callback_id": "notification_form",
#                        "attachment_type": "default",
#                    }]
                else:
                    attachments += [{
                                        "text": f"Yesterday {dimname} is {changerate} more than previous day. {dimname} : {int(data_new)}\n",
                                        "callback_id": "notification_form",
                                        'color': "good",
                                        "attachment_type": "default",
                                        }]
    if (len(attachments) > 0):
        attachments[0]['pretext'] = text
        attachments[-1]['actions'] = actions
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
    text = "*Cost Prediction*"
    attachments = []
    actions = [
        {
            "name": "setmybudget",
            "text": "Set My Budget",
            "type": "button",
            "value": "setmybudget"
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
            "value": "ignore",
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

    filters = [
        {
            "dimensionName": "ga:sourceMedium",
            "operator": "EXACT",
            "expressions": ["google / cpc"]
        }
    ]

    tol = 0.10
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    target = float(str(task['target']).replace(',','.'))

    today = datetime.today()
    start_date = datetime(today.year, today.month, 1)
    try:
        end_date = datetime(today.year, today.month + 1, 1)
    except:
        end_date = datetime(today.year + 1, 1, 1)

    days = (end_date - today + timedelta(days=1)).days

    start_date_1 = dtimetostrf(start_date)
    
    yesterday = today - timedelta(days=1)
    end_date_1 = dtimetostrf(yesterday)

    start_date_2 = dtimetostrf(yesterday)
    end_date_2 = dtimetostrf(yesterday)

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
                        }]
                }]}).execute()

    subquery1 = float(results['reports'][0]['data']['totals'][0]['values'][0])
    subquery2 = float(results['reports'][0]['data']['totals'][1]['values'][0])
    prediction = subquery2 * days + subquery1
    targettext = babel.numbers.format_currency(decimal.Decimal(str(target)), task['currency'])
    predtext = babel.numbers.format_currency(decimal.Decimal(str(prediction)), task['currency'])
    print("Target:", targettext)
    print("Prediction:", predtext)
    if (prediction > target):
        # Prediction is more than target
        if ((prediction - target < (tol * target))):
            attachments += [{
                "text": f"Your monthly adwords total cost is predicted to be more than monthly budget. Predicted Value: {predtext} Monthly Budget: {targettext}",
                "color": "good",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": actions
            }]
        else:
            attachments += [{
                "text": f"Your monthly adwords total cost is predicted to be more than monthly budget. Predicted Value: {predtext} Monthly Budget: {targettext}",
                "color": "danger",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": actions
            }]
    else:
        # Prediction is less than target
        if ((target - prediction < (tol * target))):
            attachments += [{
                "text": f"Your monthly adwords total cost is predicted to be less than monthly budget. Predicted Value: {predtext} Monthly Budget: {targettext}",
                "color": "good",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": actions
            }]
        else:
            attachments += [{
                "text": f"Your monthly adwords total cost is predicted to be less than monthly budget. Predicted Value: {predtext} Monthly Budget: {targettext}",
                "color": "danger",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": actions
            }]

    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(
        channel=channel,
        attachments=attachments)
    return resp['ts']


def performancegoaltracking(slack_token, task, dataSource):
    # Funnel Changes Tracking
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    task['currency'] = dataSource['currency']
    text = "*Performance Goal Tracking*"
    attachments = []
    actions = [
        {
            "name": "setmygoal",
            "text": "Track More/Change",
            "type": "button",
            "value": "setmygoal"
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
    metricdict = {'ga:ROAS': 'Adwords ROAS',
                  'ga:CPC': 'Adwords CPC',
                  'ga:sessions': 'Session',
                  'ga:costPerTransaction': 'Adwords Cost Per Transaction',
                  'ga:transactionRevenue': 'Revenue'}
    metrics = []
    metricnames = []
    targets = []
    filters = []
    tol = 0.05
    for i in range(len(task['metric'])):
        metrics += [{'expression': task['metric'][i]}]
        metricnames += [metricdict[task['metric'][i]]]
        targets += [float(str(task['target'][i]).replace(',','.'))]
        filters += [task['filterExpression'][i]]

    email = task['email']
    viewId = task['viewId']
    channel = task['channel']

    today = datetime.today()
    start_date = datetime(today.year, today.month, 1)  # First day of current day

    start_date_1 = dtimetostrf(start_date)  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)

    for i in range(len(metrics)):
        metricname = metricnames[i]
        target = targets[i]
        filterExpression = filters[i]
        if('Adwords' in metricname):
            if filterExpression != '':
                filterExpression = "ga:sourceMedium==google / cpc;" + filterExpression
            else:
                filterExpression = 'ga:sourceMedium==google / cpc'
        
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
        xval = list(range(1, len(yval)))
        plt.plot(xval, yval, marker = 'o')
        plt.xlabel('Day')
        plt.ylabel(metricname)
        imageId = uuid.uuid4().hex
        plt.savefig(imagefile.format(imageId))
        plt.clf()
        if ( (abs(querytotal - target) / target) <= tol):
            attachments += [{"text": f"This month, {metricname} is {round(querytotal,2)}, Your Target {metricname}: {target}",
                             "color": "good",
                             "callback_id": "notification_form",
                             "attachment_type": "default",
                             "image_url": imageurl.format(imageId),
                             "actions": [{
                                            "name": "ignore",
                                            "text": "Remove",
                                            "type": "button",
                                            "value": "ignoreone " + metrics[i]['expression'],
                                            "confirm": {
                                            "title": "Warning",
                                            "text": f"If you remove {metricname} notification, you will not track your {metricname} goal anymore. Are you still sure you want to remove it?",
                                            "ok_text": "Yes",
                                            "dismiss_text": "No"
                                        }
                                        }],
                            
                             }]

        else:
            attachments += [{"text": f"This month, {metricname} is {round(querytotal,2)}, Your Target {metricname}: {target}",
                             "color": "danger",
                             "callback_id": "notification_form",
                             "attachment_type": "default",
                             "image_url": imageurl.format(imageId),
                             "actions": [{
                                            "name": "ignore",
                                            "text": "Remove",
                                            "type": "button",
                                            "value": "ignoreone " + metrics[i]['expression'],
                                            "confirm": {
                                            "title": "Warning",
                                            "text": f"If you remove {metricname} notification, you will not track your {metricname} goal anymore. Are you still sure you want to remove it?",
                                            "ok_text": "Yes",
                                            "dismiss_text": "No"
                                        }
                                        }]
                             }]
        
        
    attachments[0]['pretext'] = text
#    attachments[-1]['actions'] = actions
    attachments += [{"text": "",
                    "color": "FFFFFF",
                    "callback_id": "notification_form",
                    "attachment_type": "default",
                    "actions": actions}]

    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(channel=channel,
                                         attachments=attachments)
    
#    time.sleep(0.5)
#    slack_client.chat_postMessage(
#        channel=channel,
#        attachments=[{"text": "",
#                     "color": "FFFFFF",
#                     "callback_id": "notification_form",
#                     "attachment_type": "default",
#                     "actions": [{
#                                    "name": "change",
#                                    "text": "Reschedule",
#                                    "type": "button",
#                                    "value": "change"
#                                }]
#                    }])
    return resp['ts']


