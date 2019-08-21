# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:49:15 2019

@author: altun
"""
import google_analytics
from datetime import datetime
import slack

def performancechangetracking(slack_token, task):
    
    #Mobile Performance Changes Tracking
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
    
    if(period==1):
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
        if(metric=="ga:sessions"):
            if(sessions_new<sessions_old*(1-threshold)):
                message += "- {0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
                        start_date_1,
                        round(threshold*100,2),
                        start_date_2,
                        int(sessions_new))
    
    #Desktop Performance Changes Tracking
    
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
    
    for metric in metrics: #Only one metric for now
        if(metric=="ga:sessions"):
            if(sessions_new<sessions_old*(1-threshold)):
                message += "- {0} mobile session is less {1}% than {2}. {0} mobile session: {3}\n".format(
                        start_date_1,
                        round(threshold*100,2),
                        start_date_2,
                        int(sessions_new))
            
    client = slack.WebClient(token=slack_token)
    client.chat_postMessage(channel=channel, text=message)
    
    return message