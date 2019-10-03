import google_analytics
from datetime import datetime, timedelta
from slack import WebClient


def dtimetostrf(x):
    return x.strftime('%Y-%m-%d')


def adwordsAccountConnection(slack_token, task, dataSource):
    #    Performance Changes Tracking
    task['channel'] = dataSource['channelID']
    task['viewId'] = dataSource['viewID']
    text = "*Adwords Account Connection*"
    attachments = []

    metrics = [{
        'expression': 'ga:adClicks'
    }]

    metricnames = [
        'Adwords Account Connection'
    ]

    email = task['email']
    service = google_analytics.build_reporting_api_v4_woutSession(email)
    viewId = task['viewId']
    channel = task['channel']

    #    period = task['period']
    period = 7
    tol = 20

    filters = [
        {
            "dimensionName": "ga:sourceMedium",
            "operator": "CONTAINS",
            "expressions": ["google / cpc"]
        }
    ]

    today = datetime.today()

    if period == 7:
        start_date_1 = dtimetostrf((today - timedelta(days=today.weekday())))  # Convert it to string format
        end_date_1 = dtimetostrf((today - timedelta(days=1)))
        days = 7 - today.weekday()

        results = service.reports().batchGet(
            body={
                'reportRequests': [
                    {
                        'viewId': viewId,
                        'dateRanges': [{'startDate': start_date_1, 'endDate': end_date_1}],
                        'metrics': metrics,
                        'filtersExpression': 'ga:sourceMedium=~google / cpc',
                        'includeEmptyRows': True
                    }]}).execute()

    print(results)
    
    if results < tol:
        attachments += [{
            "text": f"Google Ads Account and Google Analytics don’t link them, to track properly you need to connect your account.",
            "color": "danger",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]
    else:
        attachments += [{
            "text": f"Well done, nothing to worry!",
            "color": "good",
            "pretext": text,
            "callback_id": "notification_form",
            "attachment_type": "default",
        }]

    if len(attachments) != 0:
        attachments[0]['pretext'] = text
        slack_client = WebClient(token=slack_token)
        resp = slack_client.chat_postMessage(
            channel=channel,
            attachments=attachments)

        return resp['ts']
