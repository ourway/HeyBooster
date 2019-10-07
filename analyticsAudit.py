import google_analytics
from datetime import datetime, timedelta
from slack import WebClient


###TIME ISSUES##
# - reporting and management service is created within each function.
# - attachments are running in a row. This can be done using multithreading 
#   and then sorting can be applied

###ERROR##
# File "/home/app/HeyBooster/app.py", line 1042, in message_actions
# Oct 07 08:19:41 heybooster gunicorn[1953]:     analyticsAudit(slack_token, dataSource)
# Oct 07 08:19:41 heybooster gunicorn[1953]:   File "/home/app/HeyBooster/analyticsAudit.py", line 22, in analyticsAudit
# Oct 07 08:19:41 heybooster gunicorn[1953]:     attachments += bounceRateTracking(slack_token, dataSource)
# Oct 07 08:19:41 heybooster gunicorn[1953]:   File "/home/app/HeyBooster/analyticsAudit.py", line 66, in bounceRateTracking
# Oct 07 08:19:41 heybooster gunicorn[1953]:     'includeEmptyRows': True
# Oct 07 08:19:41 heybooster gunicorn[1953]:   File "/home/app/HeyBooster/env/lib/python3.6/site-packages/googleapiclient/_helpers.py", line 130, in positional_wrapper
# Oct 07 08:19:41 heybooster gunicorn[1953]:     return wrapped(*args, **kwargs)
# Oct 07 08:19:41 heybooster gunicorn[1953]:   File "/home/app/HeyBooster/env/lib/python3.6/site-packages/googleapiclient/http.py", line 855, in execute
# Oct 07 08:19:41 heybooster gunicorn[1953]:     raise HttpError(resp, content, uri=self.uri)
# Oct 07 08:19:41 heybooster gunicorn[1953]: googleapiclient.errors.HttpError: <HttpError 403 when requesting https://analyticsreporting.googleapis.com/v4/reports:batchGet?alt=json returned

def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def analyticsAudit(slack_token, dataSource):
    channel = dataSource['channelID']

    attachments = []
#    attachments += bounceRateTracking(slack_token, dataSource)
    attachments += notSetLandingPage(slack_token, dataSource)
    attachments += adwordsAccountConnection(slack_token, dataSource)
    attachments += sessionClickDiscrepancy(slack_token, dataSource)
    attachments += selfReferral(slack_token, dataSource)
    attachments += paymentReferral(slack_token, dataSource)
    attachments += goalSettingActivity(slack_token, dataSource)
    attachments += botSpamExcluding(slack_token, dataSource)
    attachments += customDimension(slack_token, dataSource)
    attachments += siteSearchTracking(slack_token, dataSource)
    attachments += gdprCompliant(slack_token, dataSource)
    attachments += remarketingLists(slack_token, dataSource)
    attachments += enhancedECommerceActivity(slack_token, dataSource)
    attachments += customMetric(slack_token, dataSource)
    if len(attachments):
        slack_client = WebClient(token=slack_token)
        resp = slack_client.chat_postMessage(channel=channel,
                                             attachments=attachments)
        return resp['ts']


def bounceRateTracking(slack_token, dataSource):
    text = "*Bounce Rate Tracking*"
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
                    'filtersExpression': "ga:bounceRate>65,ga:bounceRate<30",
                    'includeEmptyRows': True
                }]}).execute()

    bounceRate = float(results['reports'][0]['data']['totals'][0]['values'][0])

    if bounceRate > 65:
        attachments += [{
            "text": "Bounce rate is more than normal level (avg = %40-%65) , You may need to use adjusted bounce rate to see the real performance of your landing page.",
            "color": "danger",
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    elif bounceRate < 30:
        attachments += [{
            "text": "Bounce rate is less than normal level (avg = %40-%65) , You may need to check your event which affected the healthy measurement of bounce rate.",
            "color": "danger",
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Well done, nothing to worry!",
            "color": "good",
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def notSetLandingPage(slack_token, dataSource):
    text = "*Not Set Landing Page Tracking*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Well done, nothing to worry!",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def adwordsAccountConnection(slack_token, dataSource):
    text = "*Adwords Account Connection*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Well done, nothing to worry!",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def sessionClickDiscrepancy(slack_token, dataSource):
    text = "*Session Click Discrepancy*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def goalSettingActivity(slack_token, dataSource):
    text = "*Goal Setting Activity*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def selfReferral(slack_token, dataSource):
    text = "*Self Referral*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Well done, nothing to worry!",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def paymentReferral(slack_token, dataSource):
    text = "*Payment Referral*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "No worries, you had good job, but don’t forget to track your payment referral if any payment method is added.",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def botSpamExcluding(slack_token, dataSource):
    text = "*Bot & Spam Excluding*"

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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "You need to switch on bot filtering feature on google analytics to get rid of traffic from bots, spiders and computer programs",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def customDimension(slack_token, dataSource):
    text = "*Custom Dimension*"
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
    if(hitsdimensions):
        rservice = google_analytics.build_reporting_api_v4_woutSession(email)
        for i in range(len(hitsdimensions) // 9 + 1): #Reporting API allows us to set maximum 9 metrics 
            results = rservice.reports().batchGet(
                body={
                    'reportRequests': [
                        {
                            'viewId': viewId,
                            'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                            'metrics': metrics,
                            'dimensions': [{'name': dimId} for dimId in hitsdimensions[i:i + 9]],
                            'filtersExpression': "ga:hits>0"
                        }]}).execute()
    
            hasHit = False
            if 'rows' in results['reports'][0]['data'].keys():
                for row in results['reports'][0]['data']['rows']:
                    if int(row['metrics'][0]['values'][0]) != 0:
                        hasHit = True
                        break
            if (hasHit):
                break

    if hasHit:
        attachments += [{
            "text": "Well done! You are using custom dimensions, do you know about how you can boost your performance to use them all?",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Custom dimensions are not set yet, you are missing the chance to use google analytics advance version effectively.",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def siteSearchTracking(slack_token, dataSource):
    text = "*Site Search Tracking*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Do you wonder what user searching on your website? You can track site search data via google analytics.",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def gdprCompliant(slack_token, dataSource):
    text = "*GDPR Compliant*"
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Nothing to worry, there is no risky page path in terms of GDPR.",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def remarketingLists(slack_token, dataSource):
    text = "*Remarketing Lists*"

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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Sorry, there is no remarketing list, check out remarketing lists which double up revenue you get",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []


def enhancedECommerceActivity(slack_token, dataSource):
    text = "*Enhanced Ecommerce Activity*"

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
    
    enhancedECommerceTracking  = profile.get('enhancedECommerceTracking')

    if enhancedECommerceTracking:
        attachments += [{
            "text": "Your enhanced ecommerce setting is active but how you can sure that it is implemented correctly. heybooster will be sure for you soon",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "Enhanced ecommerce is not active for related view, to track your all ecommerce switch it on.",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []
    

def customMetric(slack_token, dataSource):
    text = "*Custom Metric*"
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
    if(metrics):
        rservice = google_analytics.build_reporting_api_v4_woutSession(email)
        for i in range(len(metrics) // 10 + 1): ## Reporting API allows us to set maximum 10 metrics 
            results = rservice.reports().batchGet(
                body={
                    'reportRequests': [
                        {
                            'viewId': viewId,
                            'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                            'metrics': metrics[i:i+10],
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
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": "There is no custom metric set up on your google analytics account",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        return attachments
    else:
        return []