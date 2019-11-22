import google_analytics
from datetime import datetime, timedelta
from slack import WebClient
import time
from timezonefinder import TimezoneFinder
import ccy
import logging
from database import db
from apiclient.errors import HttpError
import random


PERMISSION_ERROR = "User does not have sufficient permissions for this account."
TIMEDOUT_ERROR = "The read operation timed out"


def makeRequestWithExponentialBackoff(rservice, body):
    for n in range(0, 5):
        try:
            return rservice.reports().batchGet(body=body).execute()
        except HttpError as error:
            loopError = error
            if error.resp.reason in ['userRateLimitExceeded', 'quotaExceeded',
                                     'internalServerError', 'backendError']:
                time.sleep((2 ** n) + random.random())
            else:
                break
    #There has been an error, the request never succeeded.
    raise loopError

def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def scoretoText(score):
    if score == 5:
        return "URGENT"
    elif score in [3, 4]:
        return "IMPORTANT"
    else:
        return "MODERATE"
    
def totalScorewithEmoji(totalScore):
    if totalScore > 85:
        return f":first_place_medal: *{totalScore}*"
    elif totalScore > 75:
        return f":medal: *{totalScore}*"
    elif totalScore > 65:
        return f":nerd_face: *{totalScore}*"
    elif totalScore > 50:
        return f":eyes: *{totalScore}*"
    elif totalScore > 30:
        return f":zipper_mouth_face: *{totalScore}*"
    else:
        return f":scream: *{totalScore}*"

def analyticsAudit(slack_token, task, dataSource, sendFeedback=False):
    db.init()
    if not task:
        actions = [
            {
    			"name": "trackAnalyticsAudit",
    			"text": "Yes",
    			"type": "button",
                "style": "primary",
    			"value": f"trackAnalyticsAudit_{dataSource['_id']}"
    		},
            {
    			"name": "ignoreAnalyticsAudit",
    			"text": "No",
    			"type": "button",
    			"value": f"ignoreAnalyticsAudit_{dataSource['_id']}",
                "style": "danger",
    			"confirm": {
    						"title": "Warning",
    						"text": "Are you sure you want to close your Analytics Audit Notifications?",
    						"ok_text": "Yes",
    						"dismiss_text": "No"
    					}
    		}
        ]
    else:
        actions = []
#    actions = {
#    			"type": "actions",
#                "block_id": "notification_form",
#    			"elements": [
#    				{
#    					"type": "button",
#                        "style": "primary",
#    					"text": {
#    						"type": "plain_text",
#    						"text": "Yes",
#    						"emoji": True
#    					},
#    					"value": f"trackAnalyticsAudit_{dataSource['_id']}"
#    				},
#                    {
#    					"type": "button",
#                        "style": "danger",
#    					"text": {
#    						"type": "plain_text",
#    						"text": "No",
#    						"emoji": True
#    					},
#                        "confirm": {
#                              "title": {
#                                  "type": "plain_text",
#                                  "text": "Warning"
#                              },
#                              "text": {
#                                  "type": "mrkdwn",
#                                  "text": "Are you sure you want to close your Analytics Audit Notifications?"
#                              },
#                              "confirm": {
#                                  "type": "plain_text",
#                                  "text": "Yes"
#                              },
#                              "deny": {
#                                  "type": "plain_text",
#                                  "text": "No"
#                              }
#                        },
#    					"value": f"ignoreAnalyticsAudit_{dataSource['_id']}"
#    				}
#    			]
#    		}
    logging.basicConfig(filename="analyticsAudit.log", filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    channel = dataSource['channelID']
    subfunctions = [adwordsAccountConnection,
                    paymentReferral,
                    gdprCompliant,
                    dataRetentionPeriod,
                    enhancedECommerceActivity,
                    domainControl,
                    rawDataView,
                    userPermission,
                    bounceRateTracking,
                    selfReferral,
                    botSpamExcluding,
                    eventTracking,
                    errorPage,
                    timezone,
                    currency,
                    notSetLandingPage,
                    sessionClickDiscrepancy,
                    goalSettingActivity,
                    customDimension,
                    siteSearchTracking,
                    remarketingLists,
                    defaultPageControl,
                    contentGrouping,
                    othersInChannelGrouping,
                    customMetric,
                    internalSearchTermConsistency,
                    samplingCheck
                    ]
    scores = {"adwordsAccountConnection":5,
              "paymentReferral":5,
              "gdprCompliant":5,
              "dataRetentionPeriod":5,
              "enhancedECommerceActivity":5,
              "domainControl":5,
              "rawDataView":5,
              "userPermission":5,
              "bounceRateTracking":4,
              "selfReferral":4,
              "botSpamExcluding":4,
              "eventTracking":4,
              "errorPage":4,
              "timezone":4,
              "currency":4,
              "notSetLandingPage":3,
              "sessionClickDiscrepancy":3,
              "goalSettingActivity":3,
              "customDimension":3,
              "siteSearchTracking":3,
              "remarketingLists":3,
              "defaultPageControl":3,
              "contentGrouping":3,
              "othersInChannelGrouping":3,
              "customMetric":2,
              "internalSearchTermConsistency":2,
              "samplingCheck":1
              }
    attachments = []
    currentStates = {}
    totalScore = 0
    redcount = 0
    isPermitted = True
    for function in subfunctions:
        if not isPermitted:
            return
        currentStates[function.__name__] = None
        trycount = 0
        while trycount < 5:
            try:
                attachment = function(slack_token, dataSource)
                if attachment:
                    if 'color' in attachment[0]:
                        currentState = attachment[0]['color']
                    else:
                        currentState = None
                    currentStates[function.__name__] = currentState
                    if currentState != "danger":
                        totalScore += scores[function.__name__]
    #                    attachment[0]['text'] = ":heavy_check_mark: | " + attachment[0]['text']
                        attachment[0]['text'] = attachment[0]['text']
                    else:
    #                    attachment[0]['text'] = f":x: *{scoretoText(scores[function.__name__])}* | " + attachment[0]['text']
                        attachment[0]['text'] = f"*{scoretoText(scores[function.__name__])}* | " + attachment[0]['text']
                    if task:
                        lastState = task['lastStates'][function.__name__]
                        if lastState != currentState:
                            if currentState == "danger":
                                attachments = attachments[0:redcount] + attachment + attachments[redcount:]
                                redcount += 1
                            else:
                                attachments += attachment
                                
                    else:
                        if currentState == "danger":
                            attachments = attachments[0:redcount] + attachment + attachments[redcount:]
                            redcount += 1
                        else:
                            attachments += attachment
                break
            except HttpError as ex:
                logging.error(f"TASK DID NOT RUN --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: {function.__name__} --- {str(ex)}")
                #https://developers.google.com/analytics/devguides/reporting/core/v4/errors
                if ex.resp.reason in ['userRateLimitExceeded', 'quotaExceeded',
                                      'internalServerError', 'backendError']:
                    time.sleep((2 ** trycount) + random.random())
                    trycount += 1
    if task:
        db.find_and_modify('notification', query={'_id': task['_id']}, lastStates = currentStates, totalScore = totalScore, lastRunDate = time.time())
    else:
        db.find_and_modify('notification', query={'datasourceID': dataSource['_id'],
                                              'type': 'analyticsAudit'},  lastStates = currentStates, totalScore = totalScore, lastRunDate = time.time())
    #    attachments += bounceRateTracking(slack_token, dataSource)
    #    attachments += notSetLandingPage(slack_token, dataSource)
    #    attachments += adwordsAccountConnection(slack_token, dataSource)
    #    attachments += sessionClickDiscrepancy(slack_token, dataSource)
    #    attachments += selfReferral(slack_token, dataSource)
    #    attachments += paymentReferral(slack_token, dataSource)
    #    attachments += goalSettingActivity(slack_token, dataSource)
    #    attachments += botSpamExcluding(slack_token, dataSource)
    #    attachments += customDimension(slack_token, dataSource)
    #    attachments += siteSearchTracking(slack_token, dataSource)
    #    attachments += gdprCompliant(slack_token, dataSource)
    #    attachments += dataRetentionPeriod(slack_token, dataSource)
    #    attachments += remarketingLists(slack_token, dataSource)
    #    attachments += enhancedECommerceActivity(slack_token, dataSource)
    #    attachments += customMetric(slack_token, dataSource)
    #    attachments += samplingCheck(slack_token, dataSource)
    text_totalScore = totalScorewithEmoji(totalScore)
    if not task:
        text = "Hey! :raised_hand_with_fingers_splayed: To trust your analytics data for further insights " + \
                "we strongly recommend you to solve the issues below. " +  \
                f"Your analytics health score is calculated {text_totalScore} over 100.\n" +  \
                "Do you wanna get to know when anything change on the audit results?"
        maincolor = "#2eb8a6"
    else:
        lastScore = int(task['totalScore'])
        text_lastScore = totalScorewithEmoji(lastScore)
        text = f"Your analytics health score is change from {text_lastScore} to {text_totalScore}.\n" + \
                "Here is the list of changes."
        if totalScore > lastScore:
            maincolor = "good"
        elif totalScore < lastScore:
            maincolor = "danger"
        else:
            maincolor = None
    if len(attachments):
        blocks = [{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "*Analytics Audit*"
        			}
        		}]
        attachments = [{"text": text,
                         "color": maincolor,
#                         "pretext": "*Analytics Audit*",
                         "callback_id": "notification_form",
                         "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                         "attachment_type": "default",
                         "actions": actions}] + attachments
        
        length = len(attachments)
        for i in range(length-1):
            attachments.insert(2*i-1, {"blocks": [{"type": "divider"}]})
        
#        attachments = [{"blocks": [
#                		{
#                			"type": "section",
#                			"text": {
#                				"type": "mrkdwn",
#                				"text": "*Analytics Audit*"
#                			}
#                		},
#                        {
#                			"type": "section",
#                			"text": {
#                				"type": "mrkdwn",
#                				"text": text
#                			}
#                		},
#                        actions,
#                        {
#                			"type": "context",
#                			"elements": [
#                				{
#                					"type": "mrkdwn",
#                					"text": f"{dataSource['propertyName']} & {dataSource['viewName']}"
#                				}
#                			]
#                		},
#                        {
#                			"type": "divider"
#                		}],
#                        "color": "#2eb8a6" }]  + attachments
        slack_client = WebClient(token=slack_token)
        
        #Send Analytics Audit without showing "Show More" label
        for i in range(len(attachments)//10 + 1):
            start_time = time.time()
            if i==0:   
                resp = slack_client.chat_postMessage(blocks = blocks,
                                                     channel=channel,
                                                     attachments=attachments[i*10:i*10 + 9])
            else:
                resp = slack_client.chat_postMessage(channel=channel,
                                                     attachments=attachments[i*10:i*10 + 10])
            stop_time = time.time()
            if(stop_time - start_time < 1):
                time.sleep(1- (stop_time - start_time))
        
        #IF ANALYTICS AUDIT CANNOT BE SENT WITHIN 5 MINUTES (NOT FOR NOW!)
        #After sending analytics Audit, schedule a "give feedback" message 5 minutes later
        if sendFeedback:
            post_at = str(int(time.time() + 300)) # 5 minutes later
            sch_text = "Your feedbacks make us stronger :muscle: " + \
                    "Can you share your experience and thoughts with us?"
            sch_attachments = [
                    {
                        "text": sch_text,
                        "callback_id": "notification_form",
                        "color": "#2eb8a6",
                        "attachment_type": "default",
                        "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                        "actions": [
                            {
                                "name": "giveFeedback",
                                "text": "Give Feedback",
                                "type": "button",
                                "value": f"giveFeedback_{dataSource['_id']}"
                            },
                        ]
                    }]
            slack_client.chat_scheduleMessage(text="", channel = channel, 
                                              attachments = sch_attachments,
                                              post_at = post_at)
        return resp['ts']


def bounceRateTracking(slack_token, dataSource):
    text = "Bounce Rate Tracking"
    attachments = []

    metrics = [{'expression': 'ga:bounceRate'}
               ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    #                    'filtersExpression': "ga:bounceRate>65,ga:bounceRate<30",
#                    'includeEmptyRows': True
#                }]}).execute()
    body = {
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    #                    'filtersExpression': "ga:bounceRate>65,ga:bounceRate<30",
                    'includeEmptyRows': True
                }]}
                            
    results = makeRequestWithExponentialBackoff(service, body=body)

    bounceRate = float(results['reports'][0]['data']['totals'][0]['values'][0])

    if bounceRate > 65:
        attachments += [{
                "text": "Bounce rate is more than normal level (avg = %40-%65) , You may need to use adjusted bounce rate to see the real performance of your landing page.",
                "color": "danger",
                "callback_id": "notification_form",
    #            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
    #            "pretext": text,
                "title": text,
                "attachment_type": "default"
                    }]  
    elif bounceRate < 30:
        attachments += [{
            "text": "Bounce rate is less than normal level (avg = %40-%65) , You may need to check your event which affected the healthy measurement of bounce rate.",
            "color": "danger",
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "pretext": text,
            "title": text,
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Bounce rate is average however it may be affected by any changes on your website, keep track of it",
            "color": "good",
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "pretext": text,
            "title": text,
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def notSetLandingPage(slack_token, dataSource):
    text = "Not Set Landing Page Tracking"
    attachments = []

    metrics = [{
        'expression': 'ga:sessions'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'filtersExpression': "ga:landingPagePath=@not set",
#                    'includeEmptyRows': True
#                }]}).execute()
    body = {
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': "ga:landingPagePath=@not set",
                    'includeEmptyRows': True
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    pageviews = float(results['reports'][0]['data']['totals'][0]['values'][0])

    if pageviews > 0:
        attachments += [{
            "text": "(not set) landing pages are seen on your landing page report, it is indicated that there is an issue in your page tracking.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Good for you! There is no session landed to unknown page",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def adwordsAccountConnection(slack_token, dataSource):
    text = "Adwords Account Connection"
    attachments = []

    metrics = [{
        'expression': 'ga:adClicks'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
#                    'includeEmptyRows': True
#                }]}).execute()
    body = {
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
                    'includeEmptyRows': True
                }]}
    results = makeRequestWithExponentialBackoff(service, body)                       
    result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if result < 20:
        attachments += [{
            "text": "Google Ads Account and Google Analytics don’t link them, to track properly you need to connect your account.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Google Analytics account is linked with Google Ads, you can analyze Ads performance.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def sessionClickDiscrepancy(slack_token, dataSource):
    text = "Session Click Discrepancy"
    attachments = []

    metrics = [
        {'expression': 'ga:sessions'},
        {'expression': 'ga:adClicks'}
    ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
#                    'includeEmptyRows': True
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
                    'includeEmptyRows': True
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    try:
        sessions_result = int(results['reports'][0]['data']['totals'][0]['values'][0])
    except:
        sessions_result = 0
    try:
        adclicks_result = int(results['reports'][0]['data']['totals'][0]['values'][1])
    except:
        adclicks_result = 0
    
    if adclicks_result > 0:
        if adclicks_result > sessions_result * 1.05 or adclicks_result < sessions_result * 1.05:
            attachments += [{
                "text": "There is session click discrepancy, you don’t measure your adwords performance properly.",
                "color": "danger",
    #            "pretext": text,
                "title": text,
                "callback_id": "notification_form",
    #            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        else:
            attachments += [{
                "text": "Nothing to worry! Number of Google Ads sessions and clicks is almost same.",
                "color": "good",
    #            "pretext": text,
                "title": text,
                "callback_id": "notification_form",
    #            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
    else:
        attachments += [{
                "text": "You don’t have any session from Google Ads campaigns.",
                "color": "danger",
    #            "pretext": text,
                "title": text,
                "callback_id": "notification_form",
    #            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def goalSettingActivity(slack_token, dataSource):
    text = "Goal Setting Activity"
    attachments = []

    metrics = [{
        'expression': 'ga:goalCompletionsAll'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'includeEmptyRows': True
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'includeEmptyRows': True
                }]}
    results = makeRequestWithExponentialBackoff(service, body) 
    result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if result < 20:
        attachments += [{
            "text": "Goals are not set up yet, you should configure your macro and micro goals.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "There are goals set up on your account, but be sure to track all micro and macro conversion.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def selfReferral(slack_token, dataSource):
    text = "Self Referral"
    attachments = []

    metrics = [{
        'expression': 'ga:sessions'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': [{'name': 'ga:hostname'}],
#                    "orderBys": [
#                        {
#                            "fieldName": metrics[0]['expression'],
#                            "sortOrder": "DESCENDING"
#                        }]
#                }]}).execute()
    body = {
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:hostname'}],
                    "orderBys": [
                        {
                            "fieldName": metrics[0]['expression'],
                            "sortOrder": "DESCENDING"
                        }]
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    if 'rows' in results['reports'][0]['data'].keys():
        hostname = results['reports'][0]['data']['rows'][0]['dimensions'][0]
#        results = service.reports().batchGet(
#            body={
#                'reportRequests': [
#                    {
#                        'viewId': viewId,
#                        'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                        'metrics': metrics,
#                        'filtersExpression': f'ga:source=={hostname};ga:medium==referral'
#                    }]}).execute()
        body={
                'reportRequests': [
                    {
                        'viewId': viewId,
                        'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                        'metrics': metrics,
                        'filtersExpression': f'ga:source=={hostname};ga:medium==referral'
                    }]}
        results = makeRequestWithExponentialBackoff(service, body)

    if 'rows' in results['reports'][0]['data'].keys():
        attachments += [{
            "text": "Your own domain shows up in your referral report, it causes one visitor to trigger multiple sessions when there should only be one.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Well done Nothing to worry!\nSelf referral issue is not seen in your account recently,  no worries.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def paymentReferral(slack_token, dataSource):
    text = "Payment Referral"
    attachments = []

    metrics = [{'expression': 'ga:newUsers'},
               {'expression': 'ga:sessions'},
               {'expression': 'ga:transactionsPerSession'}
               ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'filtersExpression': 'ga:medium==referral',
#                    'includeEmptyRows': True
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': 'ga:medium==referral',
                    'includeEmptyRows': True
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    newUsers = int(results['reports'][0]['data']['totals'][0]['values'][0])
    sessions = int(results['reports'][0]['data']['totals'][0]['values'][1])
    transactionsPerSession = float(results['reports'][0]['data']['totals'][0]['values'][2])

    if newUsers < sessions * 0.001 and transactionsPerSession > 0.20:
        attachments += [{
            "text": "You got traffic from payment referral gateway, it causes to lose the original traffic sources which brings you transaction.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "No worries, you had good job, but don’t forget to track your payment referral if any payment method is added.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def botSpamExcluding(slack_token, dataSource):
    text = "Bot & Spam Excluding"

    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    profile = mservice.management().profiles().get(accountId=accountId,
                                                   webPropertyId=propertyId,
                                                   profileId=viewId
                                                   ).execute()
    botFilteringEnabled = profile.get('botFilteringEnabled')

    if botFilteringEnabled:
        attachments += [{
            "text": "Well done, you already switch on bot filtering feature of google analytics.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "You need to switch on bot filtering feature on google analytics to get rid of traffic from bots, spiders and computer programs",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def customDimension(slack_token, dataSource):
    text = "Custom Dimension"
    attachments = []
    
    metrics = {'HIT': [{'expression': 'ga:hits'}
                       ],
               'SESSION':[{'expression': 'ga:sessions'}
                       ],
               'USER': [{'expression': 'ga:users'}
                       ],
               'PRODUCT':[{'expression': 'ga:productDetailViews'}
                       ]}

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    customDimensions = mservice.management().customDimensions().list(
        accountId=accountId,
        webPropertyId=propertyId,
    ).execute()

    dimensionsNmetrics = []
    for dimension in customDimensions.get('items', []):
        if dimension.get('active'):
            dimensionsNmetrics += [(dimension.get('id'), metrics[dimension.get('scope')])]

    hasHit = False
    if (dimensionsNmetrics):
        rservice = google_analytics.build_reporting_api_v4_woutSession(email)
        reportRequests = []
        for i in range(len(dimensionsNmetrics) // 5 + 1):  # Reporting API allows us to set maximum 5 reports
            reportRequests = []
            reportRequests += [{
                'viewId': viewId,
                'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                'metrics': DnM[1],
                'dimensions': [{'name': DnM[0]}],
                'filtersExpression': "ga:hits>0"
            } for DnM in dimensionsNmetrics[i*5:i*5 + 5]]
#            results = rservice.reports().batchGet(
#                body={'reportRequests': reportRequests}).execute()
            body = {'reportRequests': reportRequests}
            results = makeRequestWithExponentialBackoff(rservice, body)
            for report in results['reports']:
                if 'rows' in results['reports'][0]['data'].keys():
                    for row in results['reports'][0]['data']['rows']:
                        if int(row['metrics'][0]['values'][0]) != 0:
                            hasHit = True
                            break
                if (hasHit):
                    break
            if (hasHit):
                break

    if hasHit:
        attachments += [{
            "text": "Well done! You are using custom dimensions, do you know about how you can boost your performance to use them all?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Custom dimensions are not set yet, you are missing the chance to use google analytics advance version effectively.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def siteSearchTracking(slack_token, dataSource):
    text = "Site Search Tracking"
    attachments = []

    metrics = [{'expression': 'ga:sessions'}
               ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': [{'name': 'ga:searchKeyword'}]
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:searchKeyword'}]
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            result = int(row['metrics'][0]['values'][0])

    else:
        result = 0

    if result > 0:
        attachments += [{
            "text": "You can analyze which keywords your user searched on your website and which of them is most convertible .",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Do you wonder what users search on your website? You can track site search data via google analytics.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def gdprCompliant(slack_token, dataSource):
    text = "GDPR Compliant"
    attachments = []

    metrics = [{
        'expression': 'ga:sessions'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': [{'name': 'ga:pagePath'}],
#                    'filtersExpression': "ga:pagePath=@=email,ga:pagePath=@@"
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:pagePath'}],
                    'filtersExpression': "ga:pagePath=@=email,ga:pagePath=@@"
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    if 'rows' in results['reports'][0]['data'].keys():
        attachments += [{
            "text": "Check your page paths, there is information which is not compatible with GDPR.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Nothing to worry, there is no risky page path in terms of GDPR.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def dataRetentionPeriod(slack_token, dataSource):
    text = "Data Retention Period"

    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    webproperty = mservice.management().webproperties().get(accountId=accountId,
                                                            webPropertyId=propertyId
                                                            ).execute()

    dataRetentionTtl = webproperty.get('dataRetentionTtl')

    if dataRetentionTtl != 'INDEFINITE':
        attachments += [{
            "text": "If you wanna play safe, it is okay your user and event data will be deleted at the end of data retention period, otherwise change it to indefinite one.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Data retention period is already set as indefinite, you will never lose your user and event data but be sure about GDPR Compliancy.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def remarketingLists(slack_token, dataSource):
    text = "Remarketing Lists"

    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    remarketingAudiences = mservice.management().remarketingAudience().list(
        accountId=accountId,
        webPropertyId=propertyId,
    ).execute()

    remarketingAudiences = remarketingAudiences.get('items', [])

    if remarketingAudiences:
        attachments += [{
            "text": "You have at least one remarketing list, do you know how you can use them to boost your performance?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Sorry, there is no remarketing list, check out remarketing lists which double up revenue you get",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def enhancedECommerceActivity(slack_token, dataSource):
    text = "Enhanced Ecommerce Activity"

    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    profile = mservice.management().profiles().get(accountId=accountId,
                                                   webPropertyId=propertyId,
                                                   profileId=viewId
                                                   ).execute()

    enhancedECommerceTracking = profile.get('enhancedECommerceTracking')

    if enhancedECommerceTracking:
        attachments += [{
            "text": "Your enhanced ecommerce setting is active but how you can sure that it is implemented correctly. heybooster will be sure for you soon",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Enhanced ecommerce is not active for related view, to track your all ecommerce switch it on.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def customMetric(slack_token, dataSource):
    text = "Custom Metric"
    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    customMetrics = mservice.management().customMetrics().list(
        accountId=accountId,
        webPropertyId=propertyId,
    ).execute()

    metrics = []
    for metric in customMetrics.get('items', []):
        if metric.get('active'):
            metrics += [{'expression': metric.get('id')}]

    hasRow = False
    if (metrics):
        rservice = google_analytics.build_reporting_api_v4_woutSession(email)
        for i in range(len(metrics) // 10 + 1):  ## Reporting API allows us to set maximum 10 metrics
#            results = rservice.reports().batchGet(
#                        body={
#                            'reportRequests': [
#                                {
#                                    'viewId': viewId,
#                                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                                    'metrics': metrics[i*10:i*10 + 10],
#                                    'includeEmptyRows': False
#                                }]}).execute()
            body = {
                        'reportRequests': [
                            {
                                'viewId': viewId,
                                'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                                'metrics': metrics[i*10:i*10 + 10],
                                'includeEmptyRows': False
                            }]}
            results = makeRequestWithExponentialBackoff(rservice, body)
            hasRow = False
            if 'rows' in results['reports'][0]['data'].keys():
                for row in results['reports'][0]['data']['rows']:
                    if float(row['metrics'][0]['values'][0]) != 0:
                        hasRow = True
                        break
            if (hasRow):
                break

    if hasRow:
        attachments += [{
            "text": "Great! You are using custom metrics",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "There is no custom metric set up on your google analytics account",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def samplingCheck(slack_token, dataSource):
    text = "Sampling Check"
    attachments = []

    metrics = [
        {'expression': 'ga:sessions'}
    ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date = datetime(today.year, today.month, 1)

    start_date_1 = dtimetostrf((today - timedelta(days=30)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'includeEmptyRows': True
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'includeEmptyRows': True
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    sessions_result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if sessions_result > 500000:
        attachments += [{
            "text": "Your analytics reports are sampling when you try to create monthly report because there is more than 500000 session without any filter.",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "No worries for now, however sampling occurs at 500000 session for the date range you are using",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def internalSearchTermConsistency(slack_token, dataSource):
    text = "Internal Search Term Consistency"
    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    filters = mservice.management().filters().list(accountId=accountId).execute()

    hasISTC = False
    for filter in filters.get('items', []):
        print(filter)
        filterType = filter.get('type')
        if filterType == 'LOWERCASE':
            details = filter.get('lowercaseDetails', {})
        elif filterType == 'UPPERCASE':
            details = filter.get('uppercaseDetails', {})
        else:
            continue
        field = details.get('field')
        if field == "INTERNAL_SEARCH_TERM":
            hasISTC = True
            break

    if hasISTC:
        attachments += [{
            "text": "No worries! There is no duplicated internal search term because of case sensitivity",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Internal search term performance may not be measure properly because of case sensitivity of terms, use lowercase filter to get rid of duplicated terms",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def defaultPageControl(slack_token, dataSource):
    text = "Default Page Control"
    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    profile = mservice.management().profiles().get(
        accountId=accountId,
        webPropertyId=propertyId,
        profileId=viewId).execute()

    try:
        defaultPage = profile['defaultPage']
    except Exception:
        defaultPage = None

    if defaultPage != None:
        attachments += [{
            "text": "Don’t use default page setting, it is moderately error prone method to fix splitting data issue.",
            "color": "red",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Default page is not set as it should be.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def domainControl(slack_token, dataSource):
    text = "Domain Control"
    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    metrics = [{'expression': 'ga:sessions'}]

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    # Obtain websiteURL
    mservice = google_analytics.build_management_api_v3_woutSession(email)
    webProperty = mservice.management().webproperties().get(
        accountId=accountId,
        webPropertyId=propertyId,
    ).execute()
    websiteUrl = webProperty['websiteUrl'].replace('https://', '')

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': [{'name': 'ga:hostname'}],
#                    "orderBys": [
#                        {
#                            "fieldName": metrics[0]['expression'],
#                            "sortOrder": "DESCENDING"
#                        }]
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:hostname'}],
                    "orderBys": [
                        {
                            "fieldName": metrics[0]['expression'],
                            "sortOrder": "DESCENDING"
                        }]
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    if 'rows' in results['reports'][0]['data'].keys():
        maxHostname = results['reports'][0]['data']['rows'][0]['dimensions'][0]
        maxSession = int(results['reports'][0]['data']['rows'][0]['metrics'][0]['values'][0])
        totalSession = int(results['reports'][0]['data']['totals'][0]['values'][0])
        percentage = maxSession / totalSession * 100
#        print(maxHostname, maxSession, totalSession, percentage, '%')
        if (websiteUrl in maxHostname or maxHostname in websiteUrl):
            if percentage > 95:
                attachments += [{
                    "text": f"Most of the visits {round(percentage, 2)}% in the view are happening on the domain, specified in the view settings {websiteUrl}.",
                    "color": "good",
#                    "pretext": text,
                    "title": text,
                    "callback_id": "notification_form",
#                    "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                    "attachment_type": "default",
                }]
            else:
                attachments += [{
                    "text": f"Check out the website url specified in view setting because only {round(percentage, 2)}% of session is happening on that domain {websiteUrl}.",
                    "color": "danger",
#                    "pretext": text,
                    "title": text,
                    "callback_id": "notification_form",
#                    "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                    "attachment_type": "default",
                }]
        else:
            attachments += [{
                "text": f"Check out the website url specified in view setting because {maxHostname} is getting more traffic than specified domain {websiteUrl}.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
    else:
        attachments += [{
                "text": f"There is no session happening on the domain you specified in your view settings.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def eventTracking(slack_token, dataSource):
    text = "Event Tracking"
    attachments = []

    email = dataSource['email']
    viewId = dataSource['viewID']

    metrics = [{'expression': 'ga:totalEvents'}]

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if result > 0:
        attachments += [{
            "text": "You are using event tracking but do you know that every action users take can measure as event and then retargeting?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": " You are missing the opportunity to measure and optimize actions users take on your website like video watching, button clicking, error page views etc.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def errorPage(slack_token, dataSource):
    text = "404 Error Page"
    attachments = []
    not_found = 0

    email = dataSource['email']
    viewId = dataSource['viewID']

    metrics = [{'expression': 'ga:pageviews'}]

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'filterExpression':'ga:pageTitle=@Page%20Not%20Found,ga:pageTitle=@404',
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filterExpression':'ga:pageTitle=@Page%20Not%20Found,ga:pageTitle=@404',
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    if 'rows' in results['reports'][0]['data'].keys():
        not_found = True
    else:
        not_found = False

    if not_found:
        attachments += [{
            "text": "You are tracking how many people ended up in 404 page, set custom alert to let know about spikes in these pages.",
            "color": "good",
#                "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "You are not tracking 404 error pages which might hurt your conversion, brand recognition and Google ranking.",
            "color": "danger",
#                "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def timezone(slack_token, dataSource):
    text = "Timezone"
    attachments = []

    metrics = [{
        'expression': 'ga:sessions'
    }]

    dimensions = [{'name': 'ga:longitude'},
                  {'name': 'ga:latitude'},
                  {'name': 'ga:countryIsoCode'},
                  {'name': 'ga:region'},
                  {'name': 'ga:city'}]

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    rservice = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = rservice.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': dimensions,
#                    "orderBys": [
#                        {
#                            "fieldName": metrics[0]['expression'],
#                            "sortOrder": "DESCENDING"
#                        }],
#                    "pageSize": 100000,
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': dimensions,
                    "orderBys": [
                        {
                            "fieldName": metrics[0]['expression'],
                            "sortOrder": "DESCENDING"
                        }],
                    "pageSize": 100000,
                }]}
    results = makeRequestWithExponentialBackoff(rservice, body)
    tf = TimezoneFinder(in_memory=True)
    mapping = {}
    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            sessions = int(row['metrics'][0]['values'][0])
            longitude = float(row['dimensions'][0])
            latitude = float(row['dimensions'][1])
            #            countryIsoCode = row['dimensions'][2]
            region = row['dimensions'][3]
            #            city = row['dimensions'][4]
            timezone = tf.timezone_at(lng=longitude, lat=latitude)
            if timezone:
                if timezone in mapping.keys():
                    mapping[timezone] += sessions
                else:
                    mapping[timezone] = sessions
            else:
                print('Timezone Yok')
                if region in mapping.keys():
                    mapping[region] += sessions
                else:
                    mapping[region] = sessions
        inversemapping = [(value, key) for key, value in mapping.items()]
        maxTrafficTimezone = max(inversemapping)[1].replace('_', ' ')  # Google uses '_' instead of ' '
    
        mservice = google_analytics.build_management_api_v3_woutSession(email)
        profile = mservice.management().profiles().get(accountId=accountId,
                                                       webPropertyId=propertyId,
                                                       profileId=viewId
                                                       ).execute()
        currentTimezone = profile['timezone'].replace('_', ' ')
    
        if currentTimezone == maxTrafficTimezone:
            attachments += [{
                "text": f"It is okay, timezone which you get the most traffic is same with timezone set on your google analytics account({currentTimezone}).",
                "color": "good",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        else:
            attachments += [{
                "text": f"Your preset timezone is {currentTimezone} but you are getting traffic mostly from {maxTrafficTimezone}.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
    else:
        attachments += [{
                "text": f"Because there is no session recorded on your account, We couldn’t check the timezone setting. Checkout Google Analytics pixel code.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def currency(slack_token, dataSource):
    text = "Currency"
    attachments = []

    metrics = [{
        'expression': 'ga:sessions'
    }]

    dimensions = [{'name': 'ga:countryIsoCode'}]

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    profile = mservice.management().profiles().get(accountId=accountId,
                                                   webPropertyId=propertyId,
                                                   profileId=viewId
                                                   ).execute()
    currentCurrency = profile['currency']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    rservice = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = rservice.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': dimensions,
#                    "orderBys": [
#                        {
#                            "fieldName": metrics[0]['expression'],
#                            "sortOrder": "DESCENDING"
#                        }]
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': dimensions,
                    "orderBys": [
                        {
                            "fieldName": metrics[0]['expression'],
                            "sortOrder": "DESCENDING"
                        }]
                }]}
    results = makeRequestWithExponentialBackoff(rservice, body)
    if 'rows' in results['reports'][0]['data'].keys():
        countryIsoCode = results['reports'][0]['data']['rows'][0]['dimensions'][0]
        maxCurrency = ccy.countryccy(countryIsoCode.lower())

        if currentCurrency == maxCurrency:
            attachments += [{
                "text": f"It is okay, currency which you get the most traffic is same with currency set on your google analytics account({currentCurrency}).",
                "color": "good",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        else:
            attachments += [{
                "text": f"Your preset currency is {currentCurrency} but you are getting traffic mostly from {maxCurrency}.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
    else:
        attachments += [{
                "text": f"Because there is no session recorded on your account, We couldn’t check the currency setting. Checkout Google Analytics pixel code.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def rawDataView(slack_token, dataSource):
    text = "Raw Data View"

    attachments = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)


    views = mservice.management().profiles().list(accountId=accountId,
                                                  webPropertyId=propertyId
                                                  ).execute()
    
    unfilteredView = False
    for view in views.get('items', []):
        viewId = view.get('id')
        filterLinks = mservice.management().profileFilterLinks().list(
                                                  accountId=accountId,
                                                  webPropertyId=propertyId,
                                                  profileId=viewId
                                              ).execute()
        if not filterLinks.get('items', []): # If there is a view which does not have any filter
            unfilteredView = True # there is raw data
            break
    if unfilteredView:
        attachments += [{
            "text": "Raw data view is correctly set, it is your backup view against to any wrong filter changes.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "You must set the raw data view to protect your data from any wrong filter changes and have backup view.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def contentGrouping(slack_token, dataSource):
    text = "Content Grouping"
    attachments = []

    metrics = [
        {'expression': 'ga:sessions'}
    ]

    dimensions = [{'name': 'ga:landingContentGroup1'},
                  {'name': 'ga:landingContentGroup2'},
                  {'name': 'ga:landingContentGroup3'},
                  {'name': 'ga:landingContentGroup4'},
                  {'name': 'ga:landingContentGroup5'}]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': dimensions
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': dimensions
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    cond = False
    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            group1 = row['dimensions'][0]
            group2 = row['dimensions'][1]
            group3 = row['dimensions'][2]
            group4 = row['dimensions'][3]
            group5 = row['dimensions'][4]
            for group in [group1, group2, group3, group4, group5]:
                if not 'not set' in group:
                    cond = True
                    break
            if cond:
                break

    if cond:
        attachments += [{
            "text": "You have made content grouping before, but do you know the alternative usage of content grouping?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "There is no content grouping in your account, to compare related group pages like men tshirts and woman dresses create your own grouping.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def othersInChannelGrouping(slack_token, dataSource):
    text = "Others in Channel Grouping"
    attachments = []

    email = dataSource['email']
    viewId = dataSource['viewID']

    metrics = [{'expression': 'ga:sessions'}]

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
#    results = service.reports().batchGet(
#        body={
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'dimensions': [{'name': 'ga:channelGrouping'}]
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:channelGrouping'}]
                }]}
    results = makeRequestWithExponentialBackoff(service, body)
    total_session = int(results['reports'][0]['data']['totals'][0]['values'][0])
    other_session = 0
    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            status = row['dimensions'][0]
            if status == 'Other':
                other_session = int(row['metrics'][0]['values'][0])
                break

        session_result = other_session / total_session * 100
        if session_result > 0.0005:
            attachments += [{
                "text": "Default channel grouping is not suitable for analysis since there is *(other)* channel which is collecting non-group traffic sources.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        else:
            attachments += [{
                "text": "Negligible percentage of your total traffic is collecting under other channel.",
                "color": "good",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
    else:
        attachments += [{
                "text": f"There is no session happening in your view.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def userPermission(slack_token, dataSource):
    text = "User Permission"
    attachments = []

    email = dataSource['email']
    result = 1
    i = 0

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    try:
        account_links = mservice.management().accountUserLinks().list(
            accountId='123456'
        ).execute()
        for accountUserLink in account_links.get('items', []):
            totalResults = accountUserLink.get('totalResults')
            i += 1

    except Exception:
        result = 0

    if result == 0:
        attachments += [{
            "text": "You don’t have enough permission to view users had access to your analytics account.",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "There are {} users can access and your analytics account. Best practices is keeping the number of users who has full access minimum.".format(
                i),
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments
    else:
        return []
