import google_analytics
from datetime import datetime, timedelta
from slack import WebClient
import time
from timezonefinder import TimezoneFinder
import ccy
import logging
from database import db


def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def analyticsAudit(slack_token, task, dataSource):
    db.init()
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
                    internalSearchTermConsistency
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
              "internalSearchTermConsistency":2
              }
    attachments = []
    currentStates = {}
    totalScore = 0
    redcount = 0
    for function in subfunctions:
        currentStates[function.__name__] = None
        trycount = 0
        while trycount < 3:
            try:
                attachment = function(slack_token, dataSource)
                if 'color' in attachment[0]:
                    currentState = attachment[0]['color']
                else:
                    currentState = None
                currentStates[function.__name__] = currentState
                if currentState != "danger":
                    totalScore += scores[function.__name__]
                if task:
                    lastState = task['lastStates'][function.__name__]
                    if lastState != currentState:
                        if currentState == "danger":
                            attachments = attachments
                            attachments = attachments[0:redcount] + attachment + attachments[redcount:]
                            redcount += 1
                        else:
                            attachments += attachment
                            
                else:
                    if currentState == "danger":
                        attachments = attachments
                        attachments = attachments[0:redcount] + attachment + attachments[redcount:]
                        redcount += 1
                    else:
                        attachments += attachment
                break
            except Exception as ex:
                logging.error(f"TASK DID NOT RUN --- User Email: {dataSource['email']} Data Source ID: {dataSource['_id']} Task Type: {function.__name__} --- {str(ex)}")
                trycount += 1
                time.sleep(0.2)
    if task:
        db.find_and_modify('notification', query={'_id': task['_id']}, lastStates = currentStates, totalScore = totalScore)
    else:
        db.find_and_modify('notification', query={'datasourceID': dataSource['_id'],
                                              'type': 'analyticsAudit'},  lastStates = currentStates, totalScore = totalScore)
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
    if (task['lastStates']['bounceRateTracking'] == ""):
        text = f"Hey! to trust your analytics data for further insights " + \
                "we strongly recommend you to solve the issues below. " +  \
                "Your analytics health score is calculated *{totalScore}* over 100.\n" +  \
                "Do you wanna get to know when anything change on the audit results?"
        maincolor = "#2eb8a6"
    else:
        lastScore = int(task['lastScore'])
        text = f"Your analytics health score is change from {lastScore} to {totalScore}.\n" + \
                "Here is the list of changes."
        if totalScore > lastScore:
            maincolor = "good"
        elif totalScore < lastScore:
            maincolor = "danger"
        else:
            maincolor = None
    if len(attachments):
        attachments = [{"text": text,
                         "color": maincolor,
                         "pretext": "*Analytics Audit*",
                         "callback_id": "notification_form",
                         "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                         "attachment_type": "default",
                         "actions": actions,
                         "mrkdwn_in": [
                                        "text",
                                        "pretext"
                                    ]}] + [{"blocks": [{"type": "divider"}] + attachments
#        length = len(attachments)
#        for i in range(length-1):
#            attachments.insert(2*i-1, {"blocks": [{"type": "divider"}]})
        
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
        resp = slack_client.chat_postMessage(channel=channel,
                                             attachments=attachments)
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    #                    'filtersExpression': "ga:bounceRate>65,ga:bounceRate<30",
                    'includeEmptyRows': True
                }]}).execute()

    bounceRate = float(results['reports'][0]['data']['totals'][0]['values'][0])

    if bounceRate > 65:
        attachments += [{
            "text": "Bounce rate is more than normal level (avg = %40-%65) , You may need to use adjusted bounce rate to see the real performance of your landing page.",
            "color": "danger",
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
#            "pretext": text,
            "title": text,
            "attachment_type": "default",
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
            "text": "Well done, nothing to worry!",
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': "ga:landingPagePath=@not set",
                    'includeEmptyRows': True
                }]}).execute()

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
            "text": "Well done, nothing to worry!",
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
                    'includeEmptyRows': True
                }]}).execute()

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
            "text": "Well done, nothing to worry!",
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
        {'expression': 'ga:sessions'}
    ]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=7)))  # Convert it to string format
    end_date_1 = dtimetostrf((today - timedelta(days=1)))

    service = google_analytics.build_reporting_api_v4_woutSession(email)
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': 'ga:sourceMedium=@google / cpc',
                    'includeEmptyRows': True
                }]}).execute()

    sessions_result = int(results['reports'][0]['data']['totals'][0]['values'][0])
    adclicks_result = int(results['reports'][0]['data']['totals'][0]['values'][1])

    if adclicks_result > 0 and (adclicks_result > sessions_result * 1.05 or adclicks_result < sessions_result * 1.05):
        attachments += [{
            "text": "There is session click discrepancy, you don’t measure your adwords performans properly.",
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'includeEmptyRows': True
                }]}).execute()

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
    results = service.reports().batchGet(
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
                }]}).execute()

    if 'rows' in results['reports'][0]['data'].keys():
        hostname = results['reports'][0]['data']['rows'][0]['dimensions'][0]

        results = service.reports().batchGet(
            body={
                'reportRequests': [
                    {
                        'viewId': viewId,
                        'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                        'metrics': metrics,
                        'filtersExpression': f'ga:source=={hostname};ga:medium==referral'
                    }]}).execute()

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
            "text": "Well done, nothing to worry!",
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'filtersExpression': 'ga:medium==referral',
                    'includeEmptyRows': True
                }]}).execute()

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

    metrics = [{'expression': 'ga:pageviews'}
               ]

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

    hitsdimensions = []
    for dimension in customDimensions.get('items', []):
        if dimension.get('scope') == 'HIT' and dimension.get('active'):
            hitsdimensions += [dimension.get('id')]

    hasHit = False
    if (hitsdimensions):
        rservice = google_analytics.build_reporting_api_v4_woutSession(email)
        reportRequests = []
        for i in range(len(hitsdimensions) // 5 + 1):  # Reporting API allows us to set maximum 5 reports
            reportRequests = []
            reportRequests += [{
                'viewId': viewId,
                'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                'metrics': metrics,
                'dimensions': [{'name': dimId}],
                'filtersExpression': "ga:hits>0"
            } for dimId in hitsdimensions[i:i + 5]]
            results = rservice.reports().batchGet(
                body={'reportRequests': reportRequests}).execute()
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:searchKeyword'}]
                }]}).execute()

    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            result = int(row['metrics'][0]['values'][0])

    else:
        result = 0

    if result > 0:
        attachments += [{
            "text": "Nothing to worry! You had a great job.",
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:pagePath'}],
                    'filtersExpression': "ga:pagePath=@=email,ga:pagePath=@@"
                }]}).execute()

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
            results = rservice.reports().batchGet(
                body={
                    'reportRequests': [
                        {
                            'viewId': viewId,
                            'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                            'metrics': metrics[i:i + 10],
                            'includeEmptyRows': False
                        }]}).execute()

            hasRow = False
            if 'rows' in results['reports'][0]['data'].keys():
                for row in results['reports'][0]['data']['rows']:
                    if int(row['metrics'][0]['values'][0]) != 0:
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'includeEmptyRows': True
                }]}).execute()

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
            "text": "Internal search term performans may not be measure properly because of case sensitivity of terms, use lowercase filter to get rid of duplicated terms",
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
    results = service.reports().batchGet(
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
                }]}).execute()

    maxHostname = results['reports'][0]['data']['rows'][0]['dimensions'][0]
    maxSession = int(results['reports'][0]['data']['rows'][0]['metrics'][0]['values'][0])
    totalSession = int(results['reports'][0]['data']['totals'][0]['values'][0])
    percentage = maxSession / totalSession * 100
    print(maxHostname, maxSession, totalSession, percentage, '%')
    if (websiteUrl in maxHostname or maxHostname in websiteUrl):
        if percentage > 95:
            attachments += [{
                "text": f"Most of the visits {round(percentage, 2)}% in the view are happening on the domain, specified in the view settings {websiteUrl}.",
                "color": "good",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
        else:
            attachments += [{
                "text": f"Check out the website url specified in view setting because only {round(percentage, 2)}% of session is happening on that domain {websiteUrl}.",
                "color": "danger",
#                "pretext": text,
                "title": text,
                "callback_id": "notification_form",
#                "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
                "attachment_type": "default",
            }]
    else:
        attachments += [{
            "text": f"Check out the website url specified in view setting because {maxHostname} is getting more traffic than specified domain {websiteUrl}.",
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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics
                }]}).execute()

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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:pageTitle'}]
                }]}).execute()

    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            result = int(row['metrics'][0]['values'][0])
            if result == "404" or result == "Page Not Found":
                not_found = 1
    else:
        result = 0

    if result > 0:
        if not_found == 1:
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
    results = rservice.reports().batchGet(
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
                }]}).execute()

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
#            "pretext": text,
            "title": text,
            "callback_id": "notification_form",
#            "footer": f"{dataSource['propertyName']} & {dataSource['viewName']}\n",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": f"Your preset timezone is {currentTimezone} but you are getting traffic mostly from {maxTrafficTimezone}.",
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
    results = rservice.reports().batchGet(
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
                }]}).execute()

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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': dimensions
                }]}).execute()

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
    results = service.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': viewId,
                    'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                    'metrics': metrics,
                    'dimensions': [{'name': 'ga:channelGrouping'}]
                }]}).execute()

    total_session = int(results['reports'][0]['data']['totals'][0]['values'][0])
    other_session = 0
    if 'rows' in results['reports'][0]['data'].keys():
        for row in results['reports'][0]['data']['rows']:
            status = row['dimensions'][0]
            if status == 'Other':
                other_session = int(row['metrics'][0]['values'][0])
                break

    session_result = other_session / total_session * 100
    if 'rows' in results['reports'][0]['data'].keys():
        if session_result > 0.05:
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
