# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:49:15 2019

@author: altun
"""
import google_analytics
from datetime import datetime
from slackclient import SlackClient


def performancechangetracking(slack_token, task):
    # Mobile Performance Changes Tracking
    message = "*Mobile Performance Changes Tracking*\n"
    metrics = [{'expression': 'ga:sessions'}]
    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    period = task['period']
    threshold = task['threshold']
    filters = [
        {
            "dimensionName": "ga:deviceCategory",
            "operator": "EXACT",
            "expressions": ["desktop"]
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
                message += "- {0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))

    # Desktop Performance Changes Tracking
    message += "*Desktop Performance Changes Tracking*\n"
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
                message += "- {0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))

    slack_client = SlackClient(slack_token)
    
    attachments=[{
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
    resp = slack_client.api_call(
                      "chat.postMessage",
                      channel=channel,
                      text=message,
                      attachments=attachments)
    message_ts = resp['ts']
    return message_ts


def shoppingfunnelchangestracking(slack_token, task):
    # Funnel Changes Tracking
    message = "*Shopping Funnel Changes Tracking*\n"
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
    threshold = task['threshold']

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
                message += "- {0} Total Session is less {1}% than {2}. {0} Total session: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))
            elif (metric['expression'] == 'ga:productDetailViews'):
                message += "- {0} Session without any shopping activity is less {1}% than {2}. {0} Session without any shopping activity: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))
            elif (metric['expression'] == 'ga:productAddsToCart'):
                message += "- {0} Add to Cart is less {1}% than {2}. {0} Add to Cart: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))
            elif (metric['expression'] == 'ga:productCheckouts'):
                message += "- {0} Checkout is less {1}% than {2}. {0} Checkout: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))
            elif (metric['expression'] == 'ga:transactions'):
                message += "- {0} Total Transaction is less {1}% than {2}. {0} Total Transaction: {3}\n".format(
                    start_date_1,
                    round(threshold * 100, 2),
                    start_date_2,
                    int(sessions_new))

    slack_client = SlackClient(slack_token)
    
    attachments=[{
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
        
    resp = slack_client.api_call(
                      "chat.postMessage",
                      channel=channel,
                      text=message,
                      attachments=attachments)
    return resp['ts']