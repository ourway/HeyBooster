# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 20:49:15 2019

@author: altun
"""
import google_analytics
import google_auth
from datetime import datetime
import slack

def performancechangetracking(slack_token, task):
    email = task['email']
    service = google_analytics.build_management_api_v3_woutSession(email)
    
    viewId = "ga:"+task['viewId']
    metrics = task['metric']
    channel = task['channel']
    if(task['segment']=='mobile'):
        filters = 'ga:deviceCategory==mobile'
    
    
    period = task['period']
    
    if(period==1):
        start_date_1 = 'yesterday'
        end_date_1 = start_date_1
        start_date_2 = '2daysAgo'
        end_date_2 = start_date_2
    
    results = service.data().ga().get(
            ids=viewId,
            start_date=start_date_1,
            end_date=end_date_1,
            metrics=metrics,
            filters=filters).execute()
    
    sessions_new = float(results.get('rows')[0][0])
    
    results = service.data().ga().get(
            ids=viewId,
            start_date=start_date_2,
            end_date=end_date_2,
            metrics=metrics,
            filters=filters).execute()
    
    sessions_old = float(results.get('rows')[0][0])
    
    if(metrics=="ga:sessions"):
        message = "{0} {1} session is less 10% than {2}. {0} {1} session: {3}".format(
                start_date_1,
                task['segment'],
                start_date_2,
                sessions_new)
        
    client = slack.WebClient(token=slack_token)
    
    if(sessions_new<sessions_old*0.90):
        client.chat_postMessage(channel=channel, text=message)
        return message
    