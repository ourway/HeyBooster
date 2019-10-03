import google_analytics
from datetime import datetime, timedelta
from slack import WebClient


def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def analyticsAudit(slack_token, dataSource):
    channel = dataSource['channelID']

    attachments = []
    attachments += bounceRateTracking(slack_token, dataSource)
    attachments += notSetLandingPage(slack_token, dataSource)
    attachments += adwordsAccountConnection(slack_token, dataSource)

    if (len(attachments)):
        slack_client = WebClient(token=slack_token)
        resp = slack_client.chat_postMessage(channel=channel,
                                             attachments=attachments)
        return resp['ts']


def bounceRateTracking(slack_token, dataSource):
    #    Performance Changes Tracking
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
    #    Performance Changes Tracking
    text = "*Not Set Landing Page Tracking*"
    attachments = []

    metrics = [{'expression': 'ga:pageviews'}
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


def adwordsAccountConnection(slack_token, dataSource):
    text = "*Adwords Account Connection*"
    attachments = []

    metrics = [{
        'expression': 'ga:adClicks'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=1)))  # Convert it to string format
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

    metrics = [{
        'expression': 'ga:sessions',
        'expression': 'ga:adClicks'
    }]

    email = dataSource['email']
    viewId = dataSource['viewID']

    today = datetime.today()

    start_date_1 = dtimetostrf((today - timedelta(days=1)))  # Convert it to string format
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
    adcliks_result = int(results['reports'][0]['data']['totals'][0]['values'][1])

    if adcliks_result > 0 and adcliks_result > sessions_result * 1.05 or adcliks_result < sessions_result * 1.05:
        attachments += [{
            "text": "There is session click discrepancy, you don’t measure your adwords performans properly.",
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
