# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:49:15 2019

@author: altun
"""
import google_analytics
from datetime import datetime
from slack import WebClient


def performancechangetracking(slack_token, task):
    # Mobile Performance Changes Tracking
    text_m= "*Mobile Performance Changes Tracking*"
    attachments_m = []
    metrics = [{'expression': 'ga:sessions'}]
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    period = task['period']
    threshold = float(task['threshold'])/100
    filters = [
        {
            "dimensionName": "ga:deviceCategory",
            "operator": "EXACT",
            "expressions": ["mobile"]
        }
    ]

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
                    "dimensionFilterClauses": [
                        {
                            "filters": filters
                        }]}]}).execute()

    # WARNING: When the number of metrics is increased, 
    # WARNING: obtain data for other metrics
    sessions_new = float(results['reports'][0]['data']['totals'][0]['values'][0])

    # WARNING: When the number of metrics is increased, 
    # WARNING: obtain data for other metrics
    sessions_old = float(results['reports'][0]['data']['totals'][1]['values'][0])

    for metric in metrics:
        if (metric == "ga:sessions"):
            if (sessions_new < sessions_old * (1 - threshold)):
                attachments_m += {"text": "- {0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
                                            start_date_1,
                                            round(threshold * 100, 2),
                                            start_date_2,
                                            int(sessions_new)),
                                "color": "#FF0000"}

    # Desktop Performance Changes Tracking
    text_d = "*Desktop Performance Changes Tracking*"
    attachments_d = []
    
    filters = [
        {
            "dimensionName": "ga:deviceCategory",
            "operator": "EXACT",
            "expressions": ["desktop"]
        }
    ]

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

    # WARNING: When the number of metrics is increased, 
    # WARNING: obtain data for other metrics
    sessions_new = float(results['reports'][0]['data']['totals'][0]['values'][0])

    # WARNING: When the number of metrics is increased, 
    # WARNING: obtain data for other metrics
    sessions_old = float(results['reports'][0]['data']['totals'][1]['values'][0])

    for metric in metrics:  # Only one metric for now
        if (metric['expression'] == "ga:sessions"):
            if (sessions_new < sessions_old * (1 - threshold)):
                attachments_d += {"text": "- {0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
                                            start_date_1,
                                            round(threshold * 100, 2),
                                            start_date_2,
                                            int(sessions_new)),
                                "color": "FF0000"}
    
    attachments_d+=[{
        "text": "",
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
        
    slack_client = WebClient(token = slack_token)
    
    slack_client.chat_postMessage(
                      channel=channel,
                      text=text_m,
                      attachments=attachments_m)

    resp = slack_client.chat_postMessage(
                      channel=channel,
                      text=text_d,
                      attachments=attachments_d)
    message_ts = resp['ts']
    return message_ts


def shoppingfunnelchangestracking(slack_token, task):
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
    threshold = float(task['threshold'])/100

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
                attachments += {"text": "{0} Total Session is less {1}% than {2}. {0} Total session: {3}\n".format(
                            start_date_1,
                            round(threshold * 100, 2),
                            start_date_2,
                            int(sessions_new)),
                            "color": "FF0000"
                            }
            elif (metric['expression'] == 'ga:productDetailViews'):
                attachments += {"text": "{0} Session without any shopping activity is less {1}% than {2}. {0} Session without any shopping activity: {3}\n".format(
                                            start_date_1,
                                            round(threshold * 100, 2),
                                            start_date_2,
                                            int(sessions_new)),
                                "color": "FF0000"
                                }
            elif (metric['expression'] == 'ga:productAddsToCart'):
                attachments += {"text": "{0} Add to Cart is less {1}% than {2}. {0} Add to Cart: {3}\n".format(
                                        start_date_1,
                                        round(threshold * 100, 2),
                                        start_date_2,
                                        int(sessions_new)),
                                "color": "FF0000"
                                }
            elif (metric['expression'] == 'ga:productCheckouts'):
                attachments += {"text": "{0} Checkout is less {1}% than {2}. {0} Checkout: {3}\n".format(
                                        start_date_1,
                                        round(threshold * 100, 2),
                                        start_date_2,
                                        int(sessions_new)),
                                "color": "FF0000"
                                }
            elif (metric['expression'] == 'ga:transactions'):
                attachments += {"text": "{0} Total Transaction is less {1}% than {2}. {0} Total Transaction: {3}\n".format(
                                        start_date_1,
                                        round(threshold * 100, 2),
                                        start_date_2,
                                        int(sessions_new)),
                                "color": "FF0000"
                                }

    slack_client = WebClient(token=slack_token)
    
    attachments+=[{
        "text": "",
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
        
    resp = slack_client.chat_postMessage(
                      channel=channel,
                      text=text,
                      attachments=attachments)
    return resp['ts']