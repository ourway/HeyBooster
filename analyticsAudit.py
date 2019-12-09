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
    is_orchestrated = True if task else False
    if not is_orchestrated:
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
        task = db.find_one('notification', {'datasourceID':dataSource['_id']})
    else:
        actions = []
    actions_button = [
            {
    			"name": "learnmore",
    			"text": "Learn More",
    			"type": "button",
    			"value": f"learnmore_{dataSource['_id']}",
                "url": "https://medium.com/@neslio/google-analytics-audit-checklist-ff784e589243"
    		}
        ]
    attachment_button = [
                            {
                            "text": "",
                            "color": "#2eb8a6",
                            "callback_id": "notification_form",
                            "attachment_type": "default",
                            "actions": actions_button
                            }
                        ]
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
                attachment, recommendation = function(dataSource)
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
                    if is_orchestrated:
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
    db.find_and_modify('notification', query={'_id': task['_id']}, lastStates = currentStates, 
                                                                  totalScore = totalScore, 
                                                                  lastRunDate = time.time())
    text_totalScore = totalScorewithEmoji(totalScore)
    if not is_orchestrated:
        text = "Hey! :raised_hand_with_fingers_splayed: To trust your analytics data for further insights, " + \
                " we strongly recommend you first solve the issues below. " +  \
                f"Your analytics health score is calculated {text_totalScore} over 100.\n" +  \
                "Do you wanna get to know when anything change on the audit results?"
        maincolor = "#2eb8a6"
    else:
        lastScore = int(task['totalScore'])
        text_lastScore = totalScorewithEmoji(lastScore)
        text = f"Your analytics health score is changed from {text_lastScore} to {text_totalScore}.\n" + \
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
                for n in range(0,5):
                    try:    
                        resp = slack_client.chat_postMessage(blocks = blocks,
                                                         channel=channel,
                                                         attachments=attachments[i*10:i*10 + 9])
                        break
                    except Exception as error:
                        logging.error(f"SLACK POST MESSAGE FAILED --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: Analytics Audit --- {str(error)}")
                        if 'missing' in str(error) or 'scope' in str(error):
                            return
                        if n==4:
                            return
                        time.sleep((2 ** n) + random.random())
            else:
                for n in range(0,5):
                    if i == len(attachments)//10:
                        try:
                            new_attachments = attachments[i*10:i*10 + 10]
                            new_attachments += attachment_button
                            resp = slack_client.chat_postMessage(channel=channel,
                                                         attachments=new_attachments)
                            break
                        except Exception as error:
                            logging.error(f"SLACK POST MESSAGE FAILED --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: Analytics Audit --- {str(error)}")
                            time.sleep((2 ** n) + random.random())
                    else:
                        try:
                            resp = slack_client.chat_postMessage(channel=channel,
                                                         attachments=attachments[i*10:i*10 + 10])
                            break
                        except Exception as error:
                            logging.error(f"SLACK POST MESSAGE FAILED --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: Analytics Audit --- {str(error)}")
                            time.sleep((2 ** n) + random.random())
#                    try:
#                        resp = slack_client.chat_postMessage(channel=channel,
#                                                     attachments=attachments[i*10:i*10 + 10])
#                        break
#                    except Exception as error:
#                        logging.error(f"SLACK POST MESSAGE FAILED --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: Analytics Audit --- {str(error)}")
#                        time.sleep((2 ** n) + random.random())
            stop_time = time.time()
            if(stop_time - start_time < 1):
                time.sleep(1- (stop_time - start_time))
        
        #IF ANALYTICS AUDIT CANNOT BE SENT WITHIN 5 MINUTES (NOT FOR NOW!)
        #After sending analytics Audit, schedule a "give feedback" message 5 minutes later
        if sendFeedback:
            post_at = str(int(time.time() + 300)) # 5 minutes later
            sch_text = "Your feedback makes us stronger. :muscle: " + \
                    "Please share your experience and thoughts with us?"
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
            for n in range(0,5):
                try:
                    slack_client.chat_scheduleMessage(text="", channel = channel, 
                                                      attachments = sch_attachments,
                                                      post_at = post_at)
                    break
                except Exception as error:
                    logging.error(f"SLACK SCHEDULE MESSAGE FAILED --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: Analytics Audit --- {str(error)}")
                    time.sleep((2 ** n) + random.random())
#        return resp['ts']


def analyticsAudit_without_slack(task, dataSource):
    db.init()
    is_orchestrated = True if task else False
    if not is_orchestrated:
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
        task = db.find_one('notification',{'datasourceID':dataSource['_id']})
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
    allattachments = []
    changedattachments = []
    currentStates = {}
    recommendations = {}
    summaries = {}
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
                attachment, recommendation = function(dataSource)
                if attachment:
                    if 'color' in attachment[0]:
                        currentState = attachment[0]['color']
                    else:
                        currentState = None
                    currentStates[function.__name__] = currentState
                    recommendations[function.__name__] = recommendation
                    summaries[function.__name__] = attachment[0]['text']
                    if currentState != "danger":
                        totalScore += scores[function.__name__]
    #                    attachment[0]['text'] = ":heavy_check_mark: | " + attachment[0]['text']
                        attachment[0]['text'] = attachment[0]['text']
                    else:
    #                    attachment[0]['text'] = f":x: *{scoretoText(scores[function.__name__])}* | " + attachment[0]['text']
                        attachment[0]['text'] = f"*{scoretoText(scores[function.__name__])}* | " + attachment[0]['text']
                    lastState = task['lastStates'][function.__name__]
                    if lastState != currentState:
                        if currentState == "danger":
                            allattachments = allattachments[0:redcount] + attachment + allattachments[redcount:]
                            changedattachments = allattachments[0:redcount] + attachment + allattachments[redcount:]
                            redcount += 1
                        else:
                            allattachments += attachment
                            changedattachments = allattachments[0:redcount] + attachment + allattachments[redcount:]
                    else:
                        if currentState == "danger":
                            allattachments = allattachments[0:redcount] + attachment + allattachments[redcount:]
                            redcount += 1
                        else:
                            allattachments += attachment
                break
            except HttpError as ex:
                logging.error(f"TASK DID NOT RUN --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: {function.__name__} --- {str(ex)}")
                #https://developers.google.com/analytics/devguides/reporting/core/v4/errors
                if ex.resp.reason in ['userRateLimitExceeded', 'quotaExceeded',
                                      'internalServerError', 'backendError']:
                    time.sleep((2 ** trycount) + random.random())
                trycount += 1
    
    db.find_and_modify('notification', query={'_id': task['_id']}, lastStates = currentStates,
                                                                      totalScore = totalScore,
                                                                      lastRunDate = time.time())
    text_totalScore = totalScorewithEmoji(totalScore)
    if not is_orchestrated:
        text = "Hey! :raised_hand_with_fingers_splayed: To trust your analytics data for further insights, " + \
                " we strongly recommend you first solve the issues below. " +  \
                f"Your analytics health score is calculated {text_totalScore} over 100.\n" +  \
                "Do you wanna get to know when anything change on the audit results?"
        maincolor = "#2eb8a6"
    else:
        lastScore = int(task['totalScore'])
        text_lastScore = totalScorewithEmoji(lastScore)
        text = f"Your analytics health score is changed from {text_lastScore} to {text_totalScore}.\n" + \
                "Here is the list of changes."
        if totalScore > lastScore:
            maincolor = "good"
        elif totalScore < lastScore:
            maincolor = "danger"
        else:
            maincolor = None
    if len(allattachments):
        blocks = [{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "*Analytics Audit*"
        			}
        		}]
        allattachments = [{"text": text,
                         "color": maincolor,
#                         "pretext": "*Analytics Audit*",
                         "callback_id": "notification_form",
                         "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                         "attachment_type": "default",
                         "actions": actions}] + allattachments
      
        length = len(allattachments)
        for i in range(length-1):
            allattachments.insert(2*i-1, {"blocks": [{"type": "divider"}]})
            
        if changedattachments:
            db.insert('reports', data={ 'datasourceID': dataSource['_id'],
                                        'message':{'blocks': blocks,
                                                   'attachments': allattachments
                                                  },
                                        'summaries': summaries,
                                        'recommendations': recommendations,
                                        'lastStates': currentStates,
                                        'ts': time.time()})        
        else:
            reports = db.find('report', query={'datasourceID':dataSource['_id']}).sort([('_id', -1)])
            report = reports.next()
            db.find_and_modify('report', query={'_id':report['_id']}, ts = time.time())
            

def bounceRateTracking(dataSource):
    text = "Bounce Rate Tracking"
    attachments = []
    recommendations = []

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
                            
#    results = makeRequestWithExponentialBackoff(service, body=body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)

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
        recommendations += ["Bad design, device / browser compatibility issue, non-closable popup windows can be the reason behind high bounce rates.",
                            "When pages are getting traffic from unrelated keywords, audiences or campaigns, it is quite normal to have a high bounce rate, checkout your traffic sources and linked URL."]
    elif bounceRate < 30:
        attachments += [{
            "text": "Bounce rate is less than normal level (avg = %40-%65) , You may need to check for an event which affected the health measurement of your bounce rate.",
            "color": "danger",
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "pretext": text,
            "title": text,
            "attachment_type": "default",
        }]
        recommendations += ["Events are counted as interactions by default however some events shouldn’t be. These type of events can be changed to ‘non-interaction hit: true’ to ensure the calculation of the rate of users who exit the page quickly.",
                            "Google analytics pixel, may have been inserted twice and triggered subsequently triggered this action. When you remove one of them, the bounce rate will move back to the normal level."]
    else:
        attachments += [{
            "text": "If your bounce rate remains average, you must keep in mind that it may be affected by any changes you make to your website. So remember to keep track of your changes.",
            "color": "good",
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "pretext": text,
            "title": text,
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def notSetLandingPage(dataSource):
    text = "Not Set Landing Page Tracking"
    attachments = []
    recommendations = []
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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    
    pageviews = float(results['reports'][0]['data']['totals'][0]['values'][0])

    if pageviews > 0:
        attachments += [{
            "text": "(not set) landing pages are seen on your landing page report, it indicated that there is an issue in your page tracking.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Be sure that Google Analytics pixel is triggered on all pages of your website.",
                            "Hits sent to Google Analytics before the pageview code causes not set landing page problem. Pageview should be the first of all Google Analytics code.",
                            "Default session duration (30 min) may not be the optimum duration for your website, change this from Google Analytics property settings."]
    else:
        attachments += [{
            "text": "Good for you! There are no sessions that landed on an unknown page.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def adwordsAccountConnection(dataSource):
    text = "Adwords Account Connection"
    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']    
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
    req = mservice.management().webPropertyAdWordsLinks().list(
                                        accountId=accountId,
                                        webPropertyId=propertyId
                                        )
    adWordsLinks = makeRequestWithExponentialBackoff(req)

    hasAdwordsAccount = False
    for link in adWordsLinks.get('items', []):
        # Get the Google Ads accounts.
        adWordsAccounts = link.get('adWordsAccounts', [])
        for account in adWordsAccounts:
            hasAdwordsAccount = True
            break
        if hasAdwordsAccount:
            break
#    print(hasAdwordsAccount)
    
    if hasAdwordsAccount:
        attachments += [{
            "text": " Google Analytics and Google Ads have linked successfully.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Should your Google Ads Account and Google Analytics not be linked, link them. To track properly, you need to connect your accounts.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]       
        recommendations += ["To boost your adwords performance and keep track of full picture of your investment and return, connect your adwords and analytics account from Google Analytics property setting.",
                            ]
                            
#    viewId = dataSource['viewID']
#
#    today = datetime.today()
#
#    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
#    end_date_1 = dtimetostrf((today - timedelta(days=1)))
#
#    service = google_analytics.build_reporting_api_v4_woutSession(email)
##    results = service.reports().batchGet(
##        body={
##            'reportRequests': [
##                {
##                    'viewId': viewId,
##                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
##                    'metrics': metrics,
##                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
##                    'includeEmptyRows': True
##                }]}).execute()
#    body = {
#            'reportRequests': [
#                {
#                    'viewId': viewId,
#                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
#                    'metrics': metrics,
#                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
#                    'includeEmptyRows': True
#                }]}
#    results = makeRequestWithExponentialBackoff(service, body)                       
#    result = int(results['reports'][0]['data']['totals'][0]['values'][0])
#
#    if result < 20:
#        attachments += [{
#            "text": "Should your Google Ads Account and Google Analytics not be linked, link them. To track properly, you need to connect your accounts.",
#            "color": "danger",
##            "pretext": text,
#            "title": text,
#            "callback_id": "notification_form",
##            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "attachment_type": "default",
#        }]
#    else:
#        attachments += [{
#            "text": " Google Analytics and Google Ads have linked successfully.",
#            "color": "good",
##            "pretext": text,
#            "title": text,
#            "callback_id": "notification_form",
##            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "attachment_type": "default",
#        }]
    

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def sessionClickDiscrepancy(dataSource):
    text = "Session Click Discrepancy"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    
    try:
        sessions_result = int(results['reports'][0]['data']['totals'][0]['values'][0])
    except:
        sessions_result = 0
    try:
        adclicks_result = int(results['reports'][0]['data']['totals'][0]['values'][1])
    except:
        adclicks_result = 0
    
    if sessions_result > 0 :
        if adclicks_result > 0:
            if adclicks_result < sessions_result * 0.95 or adclicks_result > sessions_result * 1.05:
                attachments += [{
                    "text": "There is something like session click discrepancy. If you don’t measure your adwords performance properly.",
                    "color": "danger",
        #            "pretext": text,
                    "title": text,
                    "callback_id": "notification_form",
        #            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                    "attachment_type": "default",
                }]
                if adclicks_result < sessions_result:
                    recommendations += ["There may be a problem with your Google Ads account where you got traffic, be sure all accounts are connected to your Google Analytics."]
                else:
                    recommendations += ["If you don’t use automatic tagging to track Google Ads traffic, you may have trouble with utm building.",
                                        "Referral from final ads URL to landing page cause the lose of main sources and count as direct traffic instead of Google Ads.",
                                        "Broken Google Analytics pixel on the landing page may also cause less session."]
            else:
                attachments += [{
                    "text": "Nothing to worry! The number of Google Ads sessions and clicks are almost the same.",
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
        return attachments, recommendations
    else:
        return []


def goalSettingActivity(dataSource):
    text = "Goal Setting Activity"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body) 
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if result < 20:
        attachments += [{
            "text": "When your goals are not yet set up, you should configure your macro and micro goals.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Critical points to your business should be set as goals in Google Analytics to keep track and optimize your marketing activities.",
                            "There are four ways to set up goals; URL visited, time spent on website, number of pages seen per session and events triggered",
                            "For an e-commerce account, each step of the shopping funnel should be setup as a goal. Best and healthiest way is to use events triggered on each."]
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
        return attachments, recommendations
    else:
        return []


def selfReferral(dataSource):
    text = "Self Referral"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    
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
#        results = makeRequestWithExponentialBackoff(service, body)
        req = service.reports().batchGet(body=body)
        results = makeRequestWithExponentialBackoff(req)

    if 'rows' in results['reports'][0]['data'].keys():
        attachments += [{
            "text": "Your own domain shows up in your referral report, this causes one visitor to trigger multiple sessions, that should only be a single session.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["All pages have to be tagged with Google Analytics pixels to prevent the self referral when a user passes from one page without Google Analytics code to the second page which is tracked.",
                            "If your analytics account is tracking cross sub-domains, referral exclusion have to be implemented for your domain under Property → Tracking Info → Referral Exclusion",
                            "Other than cross sub-domain, if you want to track cross-domains in one Google Analytics property, it is not enough to apply referral exclusion, you will need additional special configurations."]
    else:
        attachments += [{
            "text": "Well done! Nothing to worry about.  A self referral issue isn’t seen in your account recently.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def paymentReferral(dataSource):
    text = "Payment Referral"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    
    newUsers = int(results['reports'][0]['data']['totals'][0]['values'][0])
    sessions = int(results['reports'][0]['data']['totals'][0]['values'][1])
    transactionsPerSession = float(results['reports'][0]['data']['totals'][0]['values'][2])

    if newUsers < sessions * 0.001 and transactionsPerSession > 0.20:
        attachments += [{
            "text": "You get traffic from payment referral gateways, this causes you to lose the original traffic sources which brought you transactions.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "No worries, you did a good job, but don’t forget to track your payment referrals if any new payment method is added.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["To prevent the loss of traffic sources of users generated revenue, the payment gateway domain has to be excluded under Property → Tracking Info → Referral Exclusion."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def botSpamExcluding(dataSource):
    text = "Bot & Spam Excluding"

    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    req = mservice.management().profiles().get(accountId=accountId,
                                                   webPropertyId=propertyId,
                                                   profileId=viewId
                                                   )
    profile = makeRequestWithExponentialBackoff(req)
#    profile = mservice.management().profiles().get(accountId=accountId,
#                                                   webPropertyId=propertyId,
#                                                   profileId=viewId
#                                                   ).execute()
    botFilteringEnabled = profile.get('botFilteringEnabled')

    if botFilteringEnabled:
        attachments += [{
            "text": "Well done, you already switched on the bot filtering feature on google analytics.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "You need to switch on the bot filtering feature on google analytics, in order to get rid of traffic from bots, spiders and computer programs.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Enable bot & spam traffic exclusion under Google Analytics View Setting"]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def customDimension(dataSource):
    text = "Custom Dimension"
    attachments = []
    recommendations = []
    
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
    
#    customDimensions = mservice.management().customDimensions().list(
#        accountId=accountId,
#        webPropertyId=propertyId,
#    ).execute()
    
    req = mservice.management().customDimensions().list(
        accountId=accountId,
        webPropertyId=propertyId)
    customDimensions = makeRequestWithExponentialBackoff(req)
    
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
#            results = makeRequestWithExponentialBackoff(rservice, body)
            req = rservice.reports().batchGet(body=body)
            results = makeRequestWithExponentialBackoff(req)
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
            "text": "Well done! You’re using custom dimensions. Do you know how you can boost your performance by using them all?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Custom dimensions are not yet enabled. You are missing the chance to use google analytics advanced version effectively.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Add custom dimensions to analyze performance from different perspectives and not only the Google Analytics default.",
                            "You can add custom dimensions by using GTM or asking IT to change the Google Analytics code from the source code.",
                            "Custom dimension can be about hit, user, session, or products like user-id, product size, product color, A/B test option etc."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def siteSearchTracking(dataSource):
    text = "Site Search Tracking"
    attachments = []
    recommendations = []

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
                    'dimensions': [{'name': 'ga:searchKeyword'}],
                    "includeEmptyRows": False
                }]}
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    
    if 'rows' in results['reports'][0]['data'].keys():
        result = 1
    else:
        result = 0

    if result > 0:
        attachments += [{
            "text": "You can analyze which keywords your user searched on your website and which of them are most convertible.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Do you ever wonder what users search on your website? You can track site search data via google analytics.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Site search parameter specified under Google Analytics View Setting should be the same as the parameter in your search result page link. eg. if the link configured as /search?q=tshirt  , you should also enter query parameter as ‘q’"]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def gdprCompliant(dataSource):
    text = "GDPR Compliant"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    if 'rows' in results['reports'][0]['data'].keys():
        attachments += [{
            "text": "Check your page paths, there are information which aren’t compatible with GDPR.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Personal information like email, phone number, name are not allowed to be collected in Google Analytics. Ask your IT department to remove the personal information from URL. URL’s with personal information mostly observe in ‘forget password’ or ‘signup’ pages."
                            "Filter the page URL, which including personal info, by using the Search&Replace filter.",
                            "Don’t miss the create data deletion request in order to get a review from Google."]
    else:
        attachments += [{
            "text": "Nothing to worry about, there is no risky page path in terms of GDPR.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def dataRetentionPeriod(dataSource):
    text = "Data Retention Period"

    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    webproperty = mservice.management().webproperties().get(accountId=accountId,
#                                                            webPropertyId=propertyId
#                                                            ).execute()
    req = mservice.management().webproperties().get(accountId=accountId,
                                                            webPropertyId=propertyId
                                                            )
    webproperty = makeRequestWithExponentialBackoff(req)

    dataRetentionTtl = webproperty.get('dataRetentionTtl')

    if dataRetentionTtl != 'INDEFINITE':
        attachments += [{
            "text": "If you wanna play safe, that’s okay. Your user and event data will be deleted at the end of the data retention period, otherwise change it to an indefinite one.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Your data will be deleted if all time ranges are more than the data retention period you specified. So we recommend you change it to indefinite after you made sure about the GDPR compatibility of your account."]
    else:
        attachments += [{
            "text": "If your data retention period is already set as indefinite, you will never lose your user and event data but be sure about GDPR Compliancy.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def remarketingLists(dataSource):
    text = "Remarketing Lists"

    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    remarketingAudiences = mservice.management().remarketingAudience().list(
#        accountId=accountId,
#        webPropertyId=propertyId,
#    ).execute()
    req = mservice.management().remarketingAudience().list(
        accountId=accountId,
        webPropertyId=propertyId)
    remarketingAudiences = makeRequestWithExponentialBackoff(req)

    remarketingAudiences = remarketingAudiences.get('items', [])

    if remarketingAudiences:
        attachments += [{
            "text": "You have at least one re-marketing list, do you know how you can use it to boost your performance?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Sorry, there is no re-marketing list, check out the re-marketing lists which doubles up on the revenue you get.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Create re-marketing lists to track the performance of specific audiences and also empower Google Ads to retarget them.",
                            "You can create unlimited differing lists with any condition, however, only 20 lists can be published and their performance is trackable on Google Analytics Audience report.",
                            "Remarketing list for Google Ads should be created considering organizational goals"]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def enhancedECommerceActivity(dataSource):
    text = "Enhanced Ecommerce Activity"

    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    profile = mservice.management().profiles().get(accountId=accountId,
#                                                   webPropertyId=propertyId,
#                                                   profileId=viewId
#                                                   ).execute()
    req = mservice.management().profiles().get(accountId=accountId,
                                                   webPropertyId=propertyId,
                                                   profileId=viewId)
    profile = makeRequestWithExponentialBackoff(req)
    
    enhancedECommerceTracking = profile.get('enhancedECommerceTracking')

    if enhancedECommerceTracking:
        attachments += [{
            "text": "Your enhanced eCommerce setting is active but how can you ensure that it’s implemented correctly? heybooster will make sure.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Enhanced eCommerce is not active for related view, switch it on to track your eCommerce.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Even if your website has all the necessary pixel codes, if you don’t enable enhanced ecommerce activity under View → Ecommerce Setting, you can’t track the enhanced ecommerce module."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def customMetric(dataSource):
    text = "Custom Metric"
    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    today = datetime.today()
    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    customMetrics = mservice.management().customMetrics().list(
#        accountId=accountId,
#        webPropertyId=propertyId,
#    ).execute()
    req = customMetrics = mservice.management().customMetrics().list(
        accountId=accountId,
        webPropertyId=propertyId)
    customMetrics = makeRequestWithExponentialBackoff(req)
    
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
#            results = makeRequestWithExponentialBackoff(rservice, body)
            req = rservice.reports().batchGet(body=body)
            results = makeRequestWithExponentialBackoff(req)
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
        recommendations += ["Custom metrics help you to collect the numbers, this is crucial for your business but it’s not defined in Google Analytics by default.",
                            "Custom metric is a version of event tracking in this context because when you create custom metrics it’s easier to track and get detailed reports.",
                            "As an example, if you have more than one event like add to cart, add to favorite, product view etc. it is not straightforward to analyze by which traffic source these events are triggered, however, with custom metrics you can recollect how many times it happened."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def samplingCheck(dataSource):
    text = "Sampling Check"
    attachments = []
    recommendations = []

    metrics = [
        {'expression': 'ga:sessions'}
    ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    sessions_result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if sessions_result > 500000:
        attachments += [{
            "text": "Your analytics reports are sampling when you try to create a monthly report because there are more than 500000 session without any filters.",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["In Google Analytics 360, You can export the unsampled version of reports after a short preparation period."]
    else:
        attachments += [{
            "text": "No worries for now, however sampling occurs at 500000 sessions for the date range you are using.",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def internalSearchTermConsistency(dataSource):
    text = "Internal Search Term Consistency"
    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    filters = mservice.management().filters().list(accountId=accountId).execute()
    req = mservice.management().filters().list(accountId=accountId)
    filters = makeRequestWithExponentialBackoff(req)
    
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
            "text": "No worries! There is no duplicated internal search term because of case sensitivity.",
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
        return attachments, recommendations
    else:
        return []


def defaultPageControl(dataSource):
    text = "Default Page Control"
    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    profile = mservice.management().profiles().get(
#        accountId=accountId,
#        webPropertyId=propertyId,
#        profileId=viewId).execute()
    req = mservice.management().profiles().get(
        accountId=accountId,
        webPropertyId=propertyId,
        profileId=viewId)
    profile = makeRequestWithExponentialBackoff(req)
    
    try:
        defaultPage = profile['defaultPage']
    except Exception:
        defaultPage = None

    if defaultPage != None:
        attachments += [{
            "text": "Don’t use default page settings, it is moderately error prone when used to fix data splitting issues.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Don’t fill the default page field on Google Analytics Setting."]
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
        return attachments, recommendations
    else:
        return []


def domainControl(dataSource):
    text = "Domain Control"
    attachments = []
    recommendations = []

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
    
#    webProperty = mservice.management().webproperties().get(
#        accountId=accountId,
#        webPropertyId=propertyId,
#    ).execute()
    req = mservice.management().webproperties().get(
        accountId=accountId,
        webPropertyId=propertyId)
    webProperty = makeRequestWithExponentialBackoff(req)
    
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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
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
                recommendations += ["Change the website URL specified on Google Analytics Setting to the domain you got the most traffic from.",
                                    "If you don’t want to see any other domain traffic from your Analytics you can filter the domain name by including only your own hostname."]
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
            recommendations += ["Change the website URL specified on Google Analytics Setting to the domain you got the most traffic from.",
                                "If you don’t want to see any other domain traffic from your Analytics you can filter the domain name by including only your own hostname."]
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
        return attachments, recommendations
    else:
        return []


def eventTracking(dataSource):
    text = "Event Tracking"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    result = int(results['reports'][0]['data']['totals'][0]['values'][0])

    if result > 0:
        attachments += [{
            "text": "You are using event tracking but do you know that every action users take can measure as an event and then re-targeting?",
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
        recommendations += ["You can track any movement of your users with eventsi. You just need to ask your IT team to implement a piece of code or add a tag from Google Tag Manager without any technical support.",
                            "Events are mostly used for tracking button click, scroll, video watch and impression of anything on page."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def errorPage(dataSource):
    text = "404 Error Page"
    attachments = []
    recommendations = []

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
#                    'filtersExpression':'ga:pageTitle=@Page%20Not%20Found,ga:pageTitle=@404',
#                }]}).execute()
    body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression':'ga:pageTitle=@Page%20Not%20Found,ga:pageTitle=@404',
                }]}
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    if 'rows' in results['reports'][0]['data'].keys():
        not_found = True
    else:
        not_found = False

    if not_found:
        attachments += [{
            "text": "You are tracking how many people ended up on the 404 page, set custom alerts to let you know about spikes on these pages.",
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
        recommendations += ["Change title description of your error page with ’404 Not Found’ or ’404 Error Page’",
                            "Set an alert to better understand when the number of session from error page is increased."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def timezone(dataSource):
    text = "Timezone"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(rservice, body)
    req = rservice.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
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
        
#        profile = mservice.management().profiles().get(accountId=accountId,
#                                                       webPropertyId=propertyId,
#                                                       profileId=viewId
#                                                       ).execute()
        req = mservice.management().profiles().get(accountId=accountId,
                                                       webPropertyId=propertyId,
                                                       profileId=viewId
                                                       )
        profile = makeRequestWithExponentialBackoff(req)
        
        currentTimezone = profile['timezone'].replace('_', ' ')
    
        if currentTimezone == maxTrafficTimezone:
            attachments += [{
                "text": f"It is okay, time-zones where you get the most traffic from, it is the same as the timezone set on your google analytics account({currentTimezone}).",
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
            recommendations += ["To get the most accurate data on your Google Analytics, you need to change the timezone from Google Analytics View Setting."]
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
        return attachments, recommendations
    else:
        return []


def currency(dataSource):
    text = "Currency"
    attachments = []
    recommendations = []

    metrics = [{
        'expression': 'ga:sessions'
    }]

    dimensions = [{'name': 'ga:countryIsoCode'}]

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']
    viewId = dataSource['viewID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
#    profile = mservice.management().profiles().get(accountId=accountId,
#                                                   webPropertyId=propertyId,
#                                                   profileId=viewId
#                                                   ).execute()
    req = mservice.management().profiles().get(accountId=accountId,
                                                   webPropertyId=propertyId,
                                                   profileId=viewId
                                                   )
    profile = makeRequestWithExponentialBackoff(req)
    
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
#    results = makeRequestWithExponentialBackoff(rservice, body)
    req = rservice.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
    if 'rows' in results['reports'][0]['data'].keys():
        countryIsoCode = results['reports'][0]['data']['rows'][0]['dimensions'][0]
        maxCurrency = ccy.countryccy(countryIsoCode.lower())

        if currentCurrency == maxCurrency:
            attachments += [{
                "text": f"It is okay, the currency which you get the most traffic from, is the same as the currency set on your google analytics account({currentCurrency}).",
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
            recommendations += ["It is important to track revenue and cost metrics properly, change the currency under the Google Analytics View setting."]
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
        return attachments, recommendations
    else:
        return []


def rawDataView(dataSource):
    text = "Raw Data View"

    attachments = []
    recommendations = []

    email = dataSource['email']
    accountId = dataSource['accountID']
    propertyId = dataSource['propertyID']

    mservice = google_analytics.build_management_api_v3_woutSession(email)

#    views = mservice.management().profiles().list(accountId=accountId,
#                                                  webPropertyId=propertyId
#                                                  ).execute()
    req = mservice.management().profiles().list(accountId=accountId,
                                                  webPropertyId=propertyId
                                                  )
    views = makeRequestWithExponentialBackoff(req)
    
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
            "text": "Raw data view is correctly set, it is your backup view against any wrong filter changes.",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "You must set the raw data view to protect your data from any wrong filter changes and have a backup view.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Create a raw data view without any filter or modification. It is a backup against the data loss on your working account because of wrong configuration."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def contentGrouping(dataSource):
    text = "Content Grouping"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
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
            "text": "You have made content groupings before, but do you know the alternative usage of content grouping?",
            "color": "good",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "There is no content grouping in your account, to compare related group pages like men t-shirts and woman dresses create your own grouping.",
            "color": "danger",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []


def othersInChannelGrouping(dataSource):
    text = "Others in Channel Grouping"
    attachments = []
    recommendations = []

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
#    results = makeRequestWithExponentialBackoff(service, body)
    req = service.reports().batchGet(body=body)
    results = makeRequestWithExponentialBackoff(req)
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
                "text": "Default channel grouping is not suitable for analysis since there is *(other)* channels which are collecting non-group traffic sources.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
            recommendations += ["The traffic you got from the sources which Google Analytics do not define by default appears under the group named as ‘other’.  Adjust the default channel grouping rules to allocate all sources to a channel under View → Channel Setting",
                                "When adjusting the default group channel, pay attention to rules with AND / OR expression and the order of channels."]
        else:
            attachments += [{
                "text": "A negligible percentage of your total traffic is collecting under other channels.",
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
        return attachments, recommendations
    else:
        return []


def userPermission(dataSource):
    text = "User Permission"
    accountId = dataSource['accountID']
    attachments = []
    recommendations = []

    email = dataSource['email']

    mservice = google_analytics.build_management_api_v3_woutSession(email)
    
    isPermitted = True
    
    try:
        req = mservice.management().accountUserLinks().list(accountId = accountId)
        account_links = makeRequestWithExponentialBackoff(req)
#        account_links = mservice.management().accountUserLinks().list(
#                                                            accountId = accountId).execute()
        numberofLinks = len(account_links.get('items', []))
    except Exception as ex:
        if "Insufficient Permission" in str(ex):
            isPermitted = False
    
    if not isPermitted:
        attachments += [{
            "text": "You don’t have enough permission to view which users had access to your analytics account.",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": f"There are {numberofLinks} users who can access your analytics account. The best practice is to keep the number of users who have full access to a minimum.",
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
        recommendations += ["Remove the users access who are not part of your organization or your support organizations."]
    if len(attachments) != 0:
#        attachments[0]['pretext'] = text
        return attachments, recommendations
    else:
        return []
