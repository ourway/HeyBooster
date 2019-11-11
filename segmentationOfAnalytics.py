# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 12:34:12 2019

@author: altun
"""
import google_analytics
from database import db
from datetime import datetime, timedelta
import time

def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def getNumberofUsers(rservice, viewId):
    metrics = [{'expression': 'ga:users'}] 
    
    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=30)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))
    
    
    results = rservice.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'includeEmptyRows': True
                }]}).execute()
    try:  
        numberOfUsers = int(results['reports'][0]['data']['totals'][0]['values'][0])
    except:
        numberOfUsers = 0
        
    return numberOfUsers
    

def segmentOf(numberOfUsers):
    
    if numberOfUsers > 10000000:
        return "A"
    elif numberOfUsers > 1000000:
        return "B"
    elif numberOfUsers > 100000:
        return "C"
    elif numberOfUsers > 10000:
        return "D"
    elif numberOfUsers > 1000:
        return "E"
    else:
        return "F"

def segmentationOfAnalytics(email):
    db.init()
    mservice = google_analytics.build_management_api_v3_woutSession(email)
    rservice = google_analytics.build_reporting_api_v4_woutSession(email)
    NoU_array = []
    dS_array = []
    counter = 0
    start_time = time.time()
    accounts = mservice.management().accounts().list().execute()
    for acc in accounts.get('items'):
        time.sleep(1)
        accountId = acc.get('id')
        accountName = acc.get('name')
        webproperties = mservice.management().webproperties().list(accountId=accountId
                                                                ).execute()
        for webproperty in webproperties.get('items'):
            time.sleep(1)
            propertyId = webproperty.get('id')
            propertyName = webproperty.get('name')
            views = mservice.management().profiles().list(accountId=accountId,
                                                          webPropertyId=propertyId
                                                          ).execute()
            for view in views.get('items'):
                time.sleep(1)
                viewId = view.get('id')
                viewName = view.get('name')
                try:
                    numberOfUsers = getNumberofUsers(rservice, viewId)
                except Exception as ex:
                    if "sufficient permissions" in str(ex):
                        continue
                    else:
                        raise ex
                counter += 1
                print("Requests Number: %s"%counter)
                if counter == 9: #Limit is 10 requests
                    print("Approached to Limit")
                    stop_time = time.time()
                    sleeptime = 11 - (stop_time - start_time) 
                    print("Waiting for %s seconds"%sleeptime)
                    time.sleep(sleeptime) #10 requests per 10 seconds
                    counter = 0
                    start_time = time.time()
                NoU_array += [numberOfUsers]
                dS_array += [{"accountID": accountId,
                            "accountName": accountName,
                            "propertyID": propertyId,
                            "propertyName": propertyName,
                            "viewID": viewId,
                            "viewName": viewName}]
#                print("Number Of Users: %s"%numberOfUsers)
#                print("Segments: %s"%segments)
    maxNoU =  max(NoU_array)
    index = NoU_array.index(maxNoU)
    selectedsegment = segmentOf(maxNoU)
    segmentationSource = dS_array[index]
#    print("Selected Segments: %s"%selectedsegment)
    db.find_and_modify("user", query = {"email":email}, segment = selectedsegment, segmentationSource = segmentationSource)
    
