#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import db
import google_analytics
import time
from apiclient.errors import HttpError
import random
import logging
import requests as rq
import os


logging.basicConfig(level=logging.DEBUG, filename="/var/log/HeyBooster/eCommerceActivityUpdater.log", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")


AUTOPILOT_APIKEY = os.environ.get('AUTOPILOT_APIKEY').strip()

get_headers = {
  'autopilotapikey': AUTOPILOT_APIKEY,
}

addToListLink = "https://api2.autopilothq.com/v1/list/{list_id}/contact/{contact_id}"

ECOMMERCE_LIST_ID = 'contactlist_2d5bb510-19f6-4cb7-bfd6-aef780040bfc'


def makeRequestWithExponentialBackoff(req):
    for n in range(0, 5):
        try:
            return req.execute()
        except HttpError as error:
            loopError = error
            if error.resp.reason in ['userRateLimitExceeded', 'quotaExceeded',
                                     'internalServerError', 'backendError']:
                time.sleep((2 ** n) + random.random())
            else:
                break
#                time.sleep((2 ** n) + random.random())
        except Exception as error:
            loopError = error
            if 'timeout' in str(error).lower() or 'timed out' in str(error).lower():
                time.sleep((2 ** n) + random.random())
            else:
                break
    #There has been an error, the request never succeeded.
    raise loopError
    

def autoPilotRequestwithExponentialBackoff(contact_id):
    for i in range(5):
        try:
            resp = rq.post(addToListLink.format(list_id = ECOMMERCE_LIST_ID,
                                        contact_id = contact_id), headers = get_headers, timeout = 2)
            return resp
        except Exception as err:
            error = err
            time.sleep((2 ** i) + random.random())
    raise error
    
    
db.init()


cursor = db.find('user', {}).sort('_id', -1)
allusers = []
for user in cursor:
    if not 'eCommerceActivity' in list(user.keys()):
        allusers += [user]
    else:
        break
#    allusers += [user]
    
    
cursor = db.find('user', {'ga_accesstoken': {'$ne': ''}}).sort('_id', -1)
users = []
for user in cursor:
    if not 'eCommerceActivity' in user.keys():
        users += [user]
    else:
        break
    
eCommerceList = []
#nonECommerceList = []
nullECommerceList = []
counter = 0
exusers = {}
for user in users:
    try:
        email = user['email']
        passUser = False
        service = google_analytics.build_management_api_v3_woutSession(email)
        req = service.management().accounts().list()
        accounts = makeRequestWithExponentialBackoff(req)
        for account in accounts.get('items'):
            accountId = account.get('id')
            accountName = account.get('name')
            req = service.management().webproperties().list(accountId=accountId)
            properties = makeRequestWithExponentialBackoff(req)
            for webProperty in properties.get('items'):
                propertyId = webProperty.get('id')
                propertyName = webProperty.get('name')
                req = service.management().profiles().list(accountId=accountId,
                                                            webPropertyId=propertyId)
                views = makeRequestWithExponentialBackoff(req)
                for view in views.get('items'):
                    viewId = view.get('id')
                    viewName = view.get('id')
                    req = service.management().profiles().get(accountId=accountId,
                                                      webPropertyId=propertyId,
                                                      profileId=viewId)
                    view = makeRequestWithExponentialBackoff(req)
                    eCommerceTracking = view.get('eCommerceTracking'),
                    enhancedECommerceTracking = view.get('enhancedECommerceTracking')
                    if eCommerceTracking[0] or enhancedECommerceTracking:
                        eCommerceList += [email]
                        passUser = True
                        print('Found')
                    else:
                        print('Not Found')
                    if passUser:
                        break
                if passUser:
                    break
            if passUser:
                print(email + ' is passed: ', eCommerceTracking[0], enhancedECommerceTracking)
                break
        print(email + ' is finished: ', eCommerceTracking, enhancedECommerceTracking)
        counter += 1
        print('%s/%s'%(counter,len(users)))
    except Exception as ex:
        counter += 1
        exusers[email] = ex
        nullECommerceList += [email]
        
        

for user in allusers:
    email = user.get('email')
    if user.get('ga_accesstoken'):
        if email in eCommerceList:
            db.find_and_modify('user', {'email':email}, eCommerceActivity = True)
            print('%s in eCommerceList'%email)
            logging.info('%s in eCommerceList'%email)
            resp = autoPilotRequestwithExponentialBackoff(contact_id  = email)
            if resp.status_code == 200:
                logging.info("SUCCESS - {} is inserted into ECommerce List for Autopilot".format(email))
            else:
                logging.info("ERROR - {} cannot be inserted into ECommerce List for Autopilot - Status Code: {} ".format(email, resp.status_code))
        elif email in nullECommerceList:
            db.find_and_modify('user', {'email':email}, eCommerceActivity = None)
            print('%s not GA user anymore'%email)
            logging.info('%s not GA user anymore'%email)
        else:
            db.find_and_modify('user', {'email':email}, eCommerceActivity = False)
            print('%s not in eCommerceList'%email)
            logging.info('%s not in eCommerceList'%email)
    else:
        db.find_and_modify('user', {'email':email}, eCommerceActivity = None)
        print('%s not GA user'%email)
        logging.info('%s not GA user'%email)
        
        
        