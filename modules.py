# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:49:15 2019

@author: altun
"""
import google_analytics
from datetime import datetime, timedelta
from slack import WebClient


def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def performancechangetracking(slack_token, task):
    #    Performance Changes Tracking
    text = "Performance Changes Tracking"
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

    tol = 0.20

    filters = [
        {
            "dimensionName": "ga:sourceMedium",
            "operator": "EXACT",
            "expressions": ["google / cpc"]
        }
    ]

    if (period == 1):
        start_date_1 = 'yesterday'
        str_start_date_1 = 'Yesterday'
        end_date_1 = start_date_1
        start_date_2 = '2daysAgo'
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

    actions = [{
        "name": "track",
        "text": "Reschedule",
        "type": "button",
        "value": "track"
    },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": "ignore"
        }]

    for i in range(len(metrics)):
        metricname = metricnames[i]

        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_new = float(results['reports'][0]['data']['totals'][0]['values'][i])

        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_old = float(results['reports'][0]['data']['totals'][1]['values'][i])

        try:
            changerate = str(round(abs(data_old - data_new) / data_old * 100, 2)) + '%'
        except:
            changerate = abs(data_old - data_new)
        if (data_new < data_old):
            if ((data_old - data_new) <= (tol * data_old)):
                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} {metricname} less than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                attachments += [{
                                    "text": f"Yesterday you got {changerate} {metricname} less than previous day. {metricname} : {round(data_new, 2)}\n",
                                    "callback_id": "notification_form",
                                    'color': "danger",
                                    "attachment_type": "default",
                                    }]
        else:
            if ((data_new - data_old) >= (tol * data_old)):
                pass
            #                attachments += [{"text": f"Yesterday you got {changerate} {metricname} more than previous day. {metricname} : {round(data_new,2)}\n",
            #                    "callback_id": "notification_form",
            #                    "attachment_type": "default",
            #                }]
            else:
                attachments += [{
                                    "text": f"Yesterday you got {changerate} {metricname} more than previous day. {metricname} : {round(data_new, 2)}\n",
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

def shoppingfunnelchangetracking(slack_token, task):
    # Funnel Changes Tracking
    text = "Shopping Funnel Changes Tracking"
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
    actions = [{
        "name": "track",
        "text": "Reschedule",
        "type": "button",
        "value": "track"
    },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": "ignore"
        }]
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']
    period = task['period']

    tol = 0.20

    if (period == 1):
        start_date_1 = 'yesterday'
        end_date_1 = start_date_1
        start_date_2 = '2daysAgo'
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

    dims_new = [row['dimensions'][0] for row in results['reports'][0]['data']['rows']]
    dims_old = [row['dimensions'][0] for row in results['reports'][0]['data']['rows']]

    datas_new = [float(row['metrics'][0]['values'][0]) for row in results['reports'][0]['data']['rows']]
    datas_old = [float(row['metrics'][1]['values'][0]) for row in results['reports'][0]['data']['rows']]

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
                #                attachments += [{"text": f"Yesterday {dimname} is {changerate} less than previous day. {dimname} : {int(data_new)}\n",
                #                    "callback_id": "notification_form",
                #                    "attachment_type": "default",
                #                }]
                else:

                    attachments += [{
                                        "text": f"Yesterday {dimname} is {changerate} less than previous day. {dimname} : {int(data_new)}\n",
                                        "callback_id": "notification_form",
                                        'color': "danger",
                                        "attachment_type": "default",
                                        }]
            else:
                if ((data_new - data_old) >= (tol * data_old)):
                    pass
                #                attachments += [{"text": f"Yesterday {dimname} is {changerate} more than previous day. {dimname} : {int(data_new)}\n",
                #                    "callback_id": "notification_form",
                #                    "attachment_type": "default",
                #                }]
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


def costprediction(slack_token, task):
    # Cost Prediction
    text = "Cost Prediction"
    attachments = []
    actions = [
        {
            "name": "setmybudget",
            "text": "Set My Budget",
            "type": "button",
            "value": "setmybudget"
        },
        {
            "name": "track",
            "text": "Reschedule",
            "type": "button",
            "value": "track"
        },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": "ignore"
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

    target = float(task['target'])

    today = datetime.today()
    start_date = datetime(today.year, today.month, 1)
    try:
        end_date = datetime(today.year, today.month + 1, 1)
    except:
        end_date = datetime(today.year + 1, 1, 1)

    days = (end_date - today + timedelta(days=1)).days

    start_date_1 = dtimetostrf(start_date)
    end_date_1 = 'yesterday'

    start_date_2 = 'yesterday'
    end_date_2 = 'yesterday'

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
    print("Target:", target)
    print("Prediction:", prediction)
    if (prediction > target):
        # Prediction is more than target
        if ((prediction - target < (tol * target))):
            attachments += [{
                "text": "Your monthly adwords total cost is predicted to be more than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
                "color": "good",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": actions
            }]
        else:
            attachments += [{
                "text": "Your monthly adwords total cost is predicted to be more than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
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
                "text": "Your monthly adwords total cost is predicted to be less than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
                "color": "good",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": actions
            }]
        else:
            attachments += [{
                "text": "Your monthly adwords total cost is predicted to be less than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
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


def performancegoaltracking(slack_token, task):
    # Funnel Changes Tracking
    text = "Performance Goal Tracking"
    attachments = []
    actions = [
        {
            "name": "setmygoal",
            "text": "Change My Goal",
            "type": "button",
            "value": "setmygoal"
        },
        {
            "name": "track",
            "text": "Reschedule",
            "type": "button",
            "value": "track"
        },
        {
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": "ignore"
        }]
    metricdict = {'ga:ROAS': 'Adwords ROAS',
                  'ga:CPC': 'CPC',
                  'ga:sessions': 'Session',
                  'ga:costPerTransaction': 'Cost Per Transaction',
                  'ga:transactionRevenue': 'Revenue'}
    metrics = []
    metricnames = []
    targets = []
    filters = []
    for i in range(len(task['metric'])):
        metrics += [{'expression': task['metric'][i]}]
        metricnames += [metricdict[task['metric'][i]]]
        targets += [float(task['target'][i])]
        filters += [task['filterExpression'][i]]

    email = task['email']
    viewId = task['viewId']
    channel = task['channel']

    today = datetime.today()
    start_date = datetime(today.year, today.month, 1)  # First day of current day

    start_date_1 = dtimetostrf(start_date)  # Convert it to string format
    end_date_1 = 'yesterday'

    service = google_analytics.build_reporting_api_v4_woutSession(email)
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics
                }]}).execute()

    for i in range(len(metrics)):
        metricname = metricnames[i]
        target = targets[i]
        filterExpression = filters[i]
        results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': filterExpression
                }]}).execute()
        query = float(results['reports'][0]['data']['totals'][0]['values'][i])
        if (str("%.2f" % (round(query, 2))).split('.')[1] == '00'):
            query = int(query)
        if (str("%.2f" % (round(target, 2))).split('.')[1] == '00'):
            target = int(target)
        if (query < target):
            attachments += [{"text": f"This month, {metricname} is {query}, Your Target {metricname}: {target}",
                             "color": "danger",
                             "callback_id": "notification_form",
                             "attachment_type": "default"
                             }]

        else:
            attachments += [{"text": f"This month, {metricname} is {query}, Your Target {metricname}: {target}",
                             "color": "good",
                             "callback_id": "notification_form",
                             "attachment_type": "default"
                             }]

    attachments[0]['pretext'] = text
    attachments[-1]['actions'] = actions

    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(
        channel=channel,
        attachments=attachments)
    return resp['ts']
