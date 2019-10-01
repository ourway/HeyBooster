# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 00:51:15 2019

@author: altun
"""

from database import db
db.init()


alldatasources = db.find('datasource',{})

for datasource in alldatasources:
    dataSourceID = datasource['_id']
    email = datasource['email']
    print(email)
    notification = db.find_one('notification', {'datasourceID':dataSourceID})
    timeofDay = notification['timeofDay']
    print(timeofDay)
    db.insert('notification', data={
            'type': 'performancechangealert',
            'email': email,
            'metric': [],
            'threshold': [],
            'filterExpression': [],
            'period': [],
            'scheduleType': 'daily',
            'frequency': 0,
            'timeofDay': timeofDay,
            'status': '0',
            'lastRunDate': '',
            'datasourceID': dataSourceID
        })