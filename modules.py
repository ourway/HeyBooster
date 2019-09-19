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
    text = "*Performance Changes Tracking*"
    attachments = []
    
    metrics = [{'expression': 'ga:ROAS'},
               {'expression': 'ga:CPC'},
               {'expression': 'ga:costPerTransaction'},
               {'expression': 'ga:adCost'},
               ]
    
        
    metricnames = ['ROAS',
                   'CPC',
                   'Cost per Transaction',
                   'Cost'
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
        metricexpression = metrics[i]['expression']
        
        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_new = float(results['reports'][0]['data']['totals'][0]['values'][i])
    
        # WARNING: When the number of metrics is increased, 
        # WARNING: obtain data for other metrics
        data_old = float(results['reports'][0]['data']['totals'][1]['values'][i])
        
        try:
            changerate = str(round(abs(data_old-data_new)/data_old,2)) + '%'
        except:
            changerate = abs(data_old-data_new)
        if(data_new < data_old):
            if ((data_old-data_new) <= (tol*data_old)):
                pass
#                attachments += [{"text": f"Yesterday you got {changerate} {metricname} less than previous day. {metricname} : {round(data_new,2)}\n",
#                    "callback_id": "notification_form",
#                    "attachment_type": "default",
#                }]
            else:
                attachments += [{"text": f"Yesterday you got {changerate} {metricname} less than previous day. {metricname} : {round(data_new,2)}\n",
                    "callback_id": "notification_form",
                    'color': "danger",
                    "attachment_type": "default",
                }]
        else:
            if((data_new-data_old) >= (tol*data_old)):
                pass
#                attachments += [{"text": f"Yesterday you got {changerate} {metricname} more than previous day. {metricname} : {round(data_new,2)}\n",
#                    "callback_id": "notification_form",
#                    "attachment_type": "default",
#                }]
            else:
                attachments += [{"text": f"Yesterday you got {changerate} {metricname} more than previous day. {metricname} : {round(data_new,2)}\n",
                    "callback_id": "notification_form",
                    'color': "good",
                    "attachment_type": "default",
                }]
                    
        if(len(attachments)!=0):
            attachments[0]['pretext'] = text
            attachments[-1]['actions'] = actions
            slack_client = WebClient(token=slack_token)
            resp = slack_client.chat_postMessage(
                channel=channel,
                attachments=attachments)

    return resp['ts']
#def performancechangetracking(slack_token, task):
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
#"""
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
#"""

def shoppingfunnelchangetracking(slack_token, task):
    # Funnel Changes Tracking
    text = "*Shopping Funnel Changes Tracking*"
    attachments = []
    metrics = [
        {'expression': 'ga:sessions'},
        {'expression': 'ga:productDetailViews'},
        {'expression': 'ga:productAddsToCart'},
        {'expression': 'ga:productCheckouts'},
        {'expression': 'ga:transactions'}
    ]
    
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    period = task['period']
    threshold = float(task['threshold']) / 100

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
                    'metrics': metrics
                }]}).execute()

    for i in range(len(metrics)):
        metric = metrics[i]
        sessions_new = float(results['reports'][0]['data']['totals'][0]['values'][i])
        sessions_old = float(results['reports'][0]['data']['totals'][1]['values'][i])
        if (sessions_new < sessions_old * (1 - threshold)):
            if (metric['expression'] == "ga:sessions"):
                attachments += [{"text": "{0} Total Session is less {1}% than {2}. {0} Total session: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new)),
                    # change notification setting
                    "color": "FF0000",
                    "callback_id": "notification_form",
                    "attachment_type": "default",
                    "actions": [{
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
                }]
            elif (metric['expression'] == 'ga:productDetailViews'):
                attachments += [{
                    "text": "{0} Session without any shopping activity is less {1}% than {2}. {0} Session without any shopping activity: {3}\n".format(
                        start_date_1,
                        round(threshold * 100, 2),
                        start_date_2,
                        int(sessions_new)),
                    "callback_id": "notification_form",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [{
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
                }]
            elif (metric['expression'] == 'ga:productAddsToCart'):
                attachments += [{"text": "{0} Add to Cart is less {1}% than {2}. {0} Add to Cart: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new)),
                    "callback_id": "notification_form",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [{
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
                }]
            elif (metric['expression'] == 'ga:productCheckouts'):
                attachments += [{"text": "{0} Checkout is less {1}% than {2}. {0} Checkout: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new)),
                    "callback_id": "notification_form",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [{
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
                }]
            elif (metric['expression'] == 'ga:transactions'):
                attachments += [
                    {"text": "{0} Total Transaction is less {1}% than {2}. {0} Total Transaction: {3}\n".format(
                        start_date_1,
                        round(threshold * 100, 2),
                        start_date_2,
                        int(sessions_new)),
                        "callback_id": "notification_form",
                        "color": "#3AA3E3",
                        "attachment_type": "default",
                        "actions": [{
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
                    }]
    if (len(attachments) > 0):
        attachments[0]['pretext'] = text

    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(
        channel=channel,
        attachments=attachments)
    return resp['ts']

"""
    attachments += [{
        "pretext": "Click *_Track_* to configure *_Shopping Funnel Changes Tracking_* notification",
        "callback_id": "notification_form",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "actions": [{
            "name": "ignore",
            "text": "Ignore",
            "type": "button",
            "value": "ignore"
        },
            {
                "name": "track",
                "text": "Track",
                "type": "button",
                "value": "track"
            }]
    }]

    if (len(attachments) > 1):
        resp = slack_client.chat_postMessage(
            channel=channel,
            attachments=attachments)
        return resp['ts']

"""
def costprediction(slack_token, task):
    # Cost Prediction
    text = "*Cost Prediction*"
    attachments = []
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
                "color": "00FF00",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": [
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
            }]
        else:
            attachments += [{
                "text": "Your monthly adwords total cost is predicted to be more than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
                "color": "FF0000",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": [
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
                        }
                    ]
            }]
    else:
        # Prediction is less than target
        if ((target - prediction < (tol * target))):
            attachments += [{
                "text": "Your monthly adwords total cost is predicted to be less than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
                "color": "00FF00",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": [
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
            }]
        else:
            attachments += [{
                "text": "Your monthly adwords total cost is predicted to be less than monthly budget. Predicted Value: {0} Monthly Budget: {1}".format(
                    round(prediction, 2),
                    round(target, 2)),
                "color": "FF0000",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": [
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
            }]

    slack_client = WebClient(token=slack_token)
    resp = slack_client.chat_postMessage(
        channel=channel,
        attachments=attachments)
    return resp['ts']

"""
    attachments += [{
        "pretext": "Click *_Track_* to configure *_Cost Prediction_* notification",
        "callback_id": "notification_form",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "actions": [{
            "name": "track",
            "text": "Track",
            "type": "button",
            "value": "track"
        },
            {
                "name": "ignore",
                "text": "Ignore",
                "type": "button",
                "value": "ignore"
            }]
    }]

    if (len(attachments) > 1):
        resp = slack_client.chat_postMessage(
            channel=channel,
            attachments=attachments)
        return resp['ts']
"""

def performancegoaltracking(slack_token, task):
    # Funnel Changes Tracking
    text = "*Performance Goal Tracking*"
    attachments = []

    metrics = [
        {'expression': task['metric']},
    ]

    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    target = float(task['target'])

    today = datetime.today()
    start_date = datetime(today.year, today.month, 1)  # First day of current day

    start_date_1 = dtimetostrf(start_date)  # Convert it to string format
    end_date_1 = 'yesterday'

    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics
                }]}).execute()

    query = float(results['reports'][0]['data']['totals'][0]['values'][0])

    if ('ROAS' in task['metric']):
        if (query < target):
            attachments += [{"text": "This month, Adwords ROAS is {0}, Your Target ROAS: {1}".format(
                round(query, 2),
                round(target, 2)),
                "color": "FF0000",
                "pretext": text,
                "callback_id": "notification_form",
                "attachment_type": "default",
                "actions": [
                            {
                                "name": "setmybudget",
                                "text": "Set My Budget",
                                "type": "button",
                                "value": "setmybudget"
                            },
                            {
                                "name": "track",
                                "text": "Change Target Goal",
                                "type": "button",
                                "value": "track"
                            },
                            {
                                "name": "ignore",
                                "text": "Ignore",
                                "type": "button",
                                "value": "ignore"
                            }]
            }]

        else:
            attachments += [{"text": "This month, Adwords ROAS is {0}, Your Target ROAS: {1}".format(
                round(query, 2),
                round(target, 2)),
                "color": "00FF00",
                "pretext": text
            }]

    slack_client = WebClient(token=slack_token)

    resp = slack_client.chat_postMessage(
            channel=channel,
            attachments=attachments)
    return resp['ts']

"""
    attachments += [{
        "pretext": "Click *_Track_* to configure *_Performance Goal Tracking_* notification",
        "callback_id": "notification_form",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "actions": [{
            "name": "track",
            "text": "Track",
            "type": "button",
            "value": "track"
        },
            {
                "name": "ignore",
                "text": "Ignore",
                "type": "button",
                "value": "ignore"
            }]
    }]
    

    if (len(attachments) > 1):
        resp = slack_client.chat_postMessage(
            channel=channel,
            attachments=attachments)
        return resp['ts']
"""
