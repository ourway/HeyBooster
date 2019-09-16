from flask import Flask, render_template, flash, redirect, request, session, url_for, make_response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from forms import LoginForm, RegisterForm, NotificationForm, TimeForm
from flask_dance.contrib.slack import make_slack_blueprint, slack
import google_auth
import google_analytics
from database import db
from models.user import User
from slack_auth import authorized
from flask_dance.consumer import OAuth2ConsumerBlueprint
from datetime import datetime, timedelta, timezone
import json
from slack import WebClient
import os

OAuth2ConsumerBlueprint.authorized = authorized


# Kullanıcı Giriş Decorator'ı

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session or 'auth_token' in session:
            return f(*args, **kwargs)
        else:
            flash('Bu sayfayı görüntülemek için lütfen giriş yapın.', 'danger')
            return redirect(url_for('login'))

    return decorated_function


app = Flask(__name__)
db.init()

app.config['SECRET_KEY'] = 'linuxdegilgnulinux'

app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get('SLACK_CLIENT_ID')
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get('SLACK_CLIENT_SECRET')

slack_bp = make_slack_blueprint(
    scope=["identify,bot,commands,incoming-webhook,channels:read,chat:write:bot,links:read,users:read"])
slack_bp.authorized = authorized
app.register_blueprint(slack_bp, url_prefix="/login")
app.register_blueprint(google_auth.app)
app.register_blueprint(google_analytics.app)

SLACK_BUTTONS = [
    {
        'name': 'lead_story',
        'display': 'Daily',
        'value': 'True',
        'url': 'http://127.0.0.1:5000/scheduleType/daily'
    },
    {
        'name': 'head_deck',
        'display': 'Weekly',
        'value': 'True',
        'url': 'http://127.0.0.1:5000/scheduleType/weekly'
    },
    {
        'name': 'sidebar',
        'display': 'Button Sidebar',
        'value': 'True',
        'url': 'https://google.com'

    }
]


@app.route('/', methods=['GET', 'POST'])
def home():
    # slack_message()
    return render_template('index.html')


@app.route('/change', methods=['POST'])
def change():
    message_action = request.form
    # Open a slack client
    user = db.find_one('user', {'user_id': message_action['user_id']})
    slack_token = user['sl_accesstoken']
    slack_client = WebClient(token=slack_token)
    # text = message_action['original_message']['text']
    if (True):
        houroptions = []
        for i in range(0, 24):
            houroptions.append({'label': str(i), 'value': i})
        minuteoptions = []
        for i in range(0, 60):
            minuteoptions.append({'label': str(i), 'value': i})
        slack_client.dialog_open(
            trigger_id=message_action["trigger_id"],
            dialog={
                "title": "Notification Settings",
                "submit_label": "Submit",
                "callback_id": "notification_form",
                "elements": [
                    {
                        "label": "Hour",
                        "type": "select",
                        "name": "hour",
                        "placeholder": "Select an hour",
                        "options": houroptions
                    },
                    {
                        "label": "Minute",
                        "type": "select",
                        "name": "minute",
                        "placeholder": "Select a minute",
                        "options": minuteoptions
                    }
                ]
            }
        )
    return make_response("Time of Day: ", 200)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate:
        user = db.find_one('user', {'email': form.email.data})
        
        if user:
            if user['password']!= "":
                if check_password_hash(user['password'], form.password.data):
                    flash("Başarıyla Giriş Yaptınız", "success")
    
                    session['logged_in'] = True
                    session['email'] = user['email']
    
                    return redirect(url_for('home'))
                else:
                    flash("Kullanıcı Adı veya Parola Yanlış", "danger")
                    return redirect(url_for('login'))

    return render_template('auths/login.html', form=form)


@app.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(name=form.name.data, email=form.email.data, password=hashed_password)
        new_user.insert()
#        insertdefaultnotifications(email=form.email.data)
        return redirect(url_for('login'))
    else:
        return render_template('auths/register.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route("/connect")
@login_required
def connect():
    if not slack.authorized:
        return redirect(url_for("slack.login"))
    return redirect('/')


@app.route("/notifications", methods=['GET', 'POST'])
@login_required
def notifications():
    nForm = NotificationForm(request.form)
    tForm = TimeForm(request.form)
    if request.method == 'POST':
        # message = google_analytics.get_results(nForm)
        # slack_message()
        return redirect('/')
    else:
        user_info = google_auth.get_user_info()
        nForm.account.choices += [(acc['id'], acc['name']) for acc in google_analytics.get_accounts(user_info['email'])['accounts']]
        # incoming_webhook = slack.token['incoming_webhook']
        return render_template('notifications.html', nForm=nForm, tForm=tForm)


@app.route("/gatest/<email>")
def gatest(email):
    service = google_analytics.build_management_api_v3_woutSession(email)
    accs = service.management().accounts().list().execute()
    accounts = []
    if accs.get('items'):
        for acc in accs.get('items'):
            accounts.append({'id': acc.get('id'), 'name': acc.get('name')})
    return {'accounts': accounts}


"""
@app.route("/save", methods=['GET', 'POST'])
def save():
    tForm = TimeForm(request.form)

    scheduleType = tForm.scheduleType.data
    frequency = tForm.frequency.data
    timeofDay = tForm.timeofDay.data

    db.find_and_modify(collection='notification',
                       query={'email': session['email']},
                       scheduleType=scheduleType,
                       frequency=frequency,
                       timeofDay=timeofDay)

    return redirect('/')


@app.route('/scheduleType/daily', methods=['POST'])
def scheduleTypeDaily():
    scheduleType = "daily"
    db.find_and_modify(collection='notification',
                       query={'email': session['email']},
                       scheduleType=scheduleType)
    return make_response()


@app.route('/scheduleType/weekly', methods=['GET', 'POST'])
def scheduleTypeWeekly():
    scheduleType = "weekly"
    db.find_and_modify(collection='notification',
                       query={'email': session['email']},
                       scheduleType=scheduleType)
    return make_response()


def slack_message():
    if not slack.authorized:
        return redirect(url_for("slack.login"))

    attachments = [
        {
            'title': 'Title',
            'title_link': 'https://title-link.com',
            'callback_id': 'button_test',
            'actions': [],
            'fields': [
                {
                    'value': 'Field1'
                },
                {
                    'title': 'Field2 Title',
                    'value': 'Field2 Value',
                    'short': True
                },
            ]
        }
    ]
    for button_dict in SLACK_BUTTONS:
        button = {
            'type': 'button',
            'name': button_dict['name'],
            'text': button_dict['display'],
            'value': button_dict['value'],
            'url': button_dict['url'],
            'style': 'primary',
        }
        attachments[0]['actions'].append(button)
    slack.post("chat.postMessage", data={
        "channel": "#general",
        "icon_emoji": ":male-technologist:",
        "text": "Would you like some coffee? :coffee:",
        'attachments': json.dumps(attachments)
    })

    return redirect('/')

"""


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    # Parse the request payload
    message_action = json.loads(request.form["payload"])
    # Open a slack client
    user = db.find_one('user', {'user_id': message_action['user']['id']})
    slack_token = user['sl_accesstoken']
    email = user['email']
    slack_client = WebClient(token=slack_token)
    if message_action["type"] == "interactive_message":
        if (message_action['actions'][0]['value'] == 'track'):
            text = message_action['original_message']['attachments'][-1]['pretext']
            if (("performance" in text.lower()) and ("change" in text.lower())):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Notification Settings",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Module Type",
                                "type": "select",
                                "name": "module_types",
                                "placeholder": "Select a module type",
                                "value": "performancechangetracking",
                                "options": [
                                    {
                                        "label": "Performance Changes Tracking",
                                        "value": "performancechangetracking"
                                    }
                                ]
                            },
                            {
                                "label": "Schedule Type",
                                "type": "select",
                                "name": "schedule_types",
                                "placeholder": "Select a schedule type",
                                "options": [
                                    {
                                        "label": "Daily",
                                        "value": "daily"
                                    },
                                    {
                                        "label": "Weekly",
                                        "value": "weekly"
                                    }
                                ]
                            },
                            {
                                "label": "Threshold (%)",
                                "name": "threshold",
                                "type": "text",
                                "subtype": "number",
                                "placeholder": "Enter a number"
                            }
                        ]
                    }
                )
            elif (("funnel" in text.lower()) and ("change" in text.lower())):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Notification Settings",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Module Type",
                                "type": "select",
                                "name": "module_types",
                                "placeholder": "Select a module type",
                                "value": "shoppingfunnelchangetracking",
                                "options": [
                                    {
                                        "label": "Shopping Funnel Changes Tracking",
                                        "value": "shoppingfunnelchangetracking"
                                    }
                                ]
                            },
                            {
                                "label": "Schedule Type",
                                "type": "select",
                                "name": "schedule_types",
                                "placeholder": "Select a schedule type",
                                "options": [
                                    {
                                        "label": "Daily",
                                        "value": "daily"
                                    },
                                    {
                                        "label": "Weekly",
                                        "value": "weekly"
                                    }
                                ]
                            },
                            {
                                "label": "Threshold (%)",
                                "name": "threshold",
                                "type": "text",
                                "subtype": "number",
                                "placeholder": "Enter a number"
                            }
                        ]
                    }
                )
            elif (("cost" in text.lower()) and ("prediction" in text.lower())):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Notification Settings",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Module Type",
                                "type": "select",
                                "name": "module_types",
                                "placeholder": "Select a module type",
                                "value": "costprediction",
                                "options": [
                                    {
                                        "label": "Cost Prediction",
                                        "value": "costprediction"
                                    }
                                ]
                            },
                            {
                                "label": "Schedule Type",
                                "type": "select",
                                "name": "schedule_types",
                                "placeholder": "Select a schedule type",
                                "options": [
                                    {
                                        "label": "Daily",
                                        "value": "daily"
                                    },
                                    {
                                        "label": "Weekly",
                                        "value": "weekly"
                                    }
                                ]
                            },
                            {
                                "label": "Monthly Budget",
                                "name": "target",
                                "type": "text",
                                "subtype": "number",
                                "placeholder": "Enter a number"
                            }
                        ]
                    }
                )
            elif (("performance" in text.lower()) and ("goal" in text.lower())):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Notification Settings",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Module Type",
                                "type": "select",
                                "name": "module_types",
                                "placeholder": "Select a module type",
                                "value": "performancegoaltracking",
                                "options": [
                                    {
                                        "label": "Performance Goal Tracking",
                                        "value": "performancegoaltracking"
                                    }
                                ]
                            },
                            {
                                "label": "Schedule Type",
                                "type": "select",
                                "name": "schedule_types",
                                "placeholder": "Select a schedule type",
                                "options": [
                                    {
                                        "label": "Daily",
                                        "value": "daily"
                                    },
                                    {
                                        "label": "Weekly",
                                        "value": "weekly"
                                    }
                                ]
                            },
                            {
                                "label": "Metric Type",
                                "type": "select",
                                "name": "metric_types",
                                "placeholder": "Select a metric type",
                                "options": [
                                    {
                                        "label": "ROAS",
                                        "value": "ga:ROAS"
                                    },
                                    {
                                        "label": "CPC",
                                        "value": "ga:CPC"
                                    },
                                    {
                                        "label": "Revenue",
                                        "value": "ga:transactionRevenue"
                                    }
                                ]
                            },
                            {
                                "label": "Goal",
                                "name": "target",
                                "type": "text",
                                "subtype": "number",
                                "placeholder": "Enter a number"
                            }
                        ]
                    }
                )
        #        # Update the message to show that we're in the process of taking their order
        #        resp = slack_client.api_call(
        #            "chat.update",
        #            channel=channel,
        #            ts=message_ts,
        #            text=message_action['original_message']['text'] + ":pencil: Taking your order...",
        #            attachments=[]
        #        )
        elif (message_action['actions'][0]['value'] == 'ignore'):
            text = message_action['original_message']['attachments'][-1]['pretext']
            if (("performance" in text.lower()) and ("change" in text.lower())):
                db.find_and_modify('notification', query={'email': email,
                                                          'type': 'performancechangetracking'},
                                   status='0')
            elif (("funnel" in text.lower()) and ("change" in text.lower())):
                db.find_and_modify('notification', query={'email': email,
                                                          'type': 'shoppingfunnelchangetracking'},
                                   status='0')
            elif (("cost" in text.lower()) and ("prediction" in text.lower())):
                db.find_and_modify('notification', query={'email': email,
                                                          'type': 'costprediction'},
                                   status='0')
            elif (("performance" in text.lower()) and ("goal" in text.lower())):
                db.find_and_modify('notification', query={'email': email,
                                                          'type': 'performancegoaltracking'},
                                   status='0')
        elif (message_action['actions'][0]['value'] == 'change'):
            text = message_action['original_message']['text']
            if (True):
                houroptions = []
                for i in range(0, 24):
                    houroptions.append({'label': str(i), 'value': i})
                minuteoptions = []
                for i in range(0, 60):
                    minuteoptions.append({'label': str(i), 'value': i})
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Notification Settings",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Hour",
                                "type": "select",
                                "name": "hour",
                                "placeholder": "Select an hour",
                                "options": houroptions
                            },
                            {
                                "label": "Minute",
                                "type": "select",
                                "name": "minute",
                                "placeholder": "Select a minute",
                                "options": minuteoptions
                            }
                        ]
                    }
                )

    elif message_action["type"] == "dialog_submission":
        submission = message_action['submission']
        if ('module_types' in submission.keys()):
            moduleType = submission['module_types']
            if (moduleType == 'performancechangetracking'):
                scheduleType = submission['schedule_types']
                threshold = float(submission['threshold'])
                db.find_and_modify(collection='notification', query={'email': email, 'type': moduleType},
                                   scheduleType=scheduleType, threshold=threshold, status='1')
            elif (moduleType == 'shoppingfunnelchangetracking'):
                scheduleType = submission['schedule_types']
                threshold = float(submission['threshold'])
                db.find_and_modify(collection='notification', query={'email': email, 'type': moduleType},
                                   scheduleType=scheduleType, threshold=threshold, status='1')
            elif (moduleType == 'costprediction'):
                scheduleType = submission['schedule_types']
                target = float(submission['target'])
                db.find_and_modify(collection='notification', query={'email': email, 'type': moduleType},
                                   scheduleType=scheduleType, target=target, status='1')
            elif (moduleType == 'performancegoaltracking'):
                scheduleType = submission['schedule_types']
                target = float(submission['target'])
                metric = submission['metric']
                db.find_and_modify(collection='notification', query={'email': email, 'type': moduleType},
                                   scheduleType=scheduleType, target=target, metric=metric, status='1')
        else:
            modules = db.find("notification", query={'email': email})
            lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
            #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
            usr_tz_offset = slack_client.users_info(user=message_action['user']['id'])['user']['tz_offset'] // 3600
            selectedhour = int(submission['hour'])
            selectedminute = str(submission['minute']).zfill(2)
            # writtenhour = str(selectedhour - (usr_tz_offset - lc_tz_offset)).zfill(2)
            if (selectedhour > (usr_tz_offset - lc_tz_offset)):
                writtenhour = str(selectedhour - (usr_tz_offset - lc_tz_offset)).zfill(2)
            else:
                writtenhour = str(24 + (selectedhour - (usr_tz_offset - lc_tz_offset))).zfill(2)
            for module in modules:
                db.find_and_modify("notification", query={'_id': module['_id']},
                                   timeofDay="%s.%s" % (writtenhour, selectedminute))
    return make_response("", 200)


def insertdefaultnotifications(email):
    # Default Notifications will be inserted here
    db.insert('notification', data={
        'type': 'performancechangetracking',
        'email': email,
        'period': 1,
        'threshold': 10,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': '07.00',
        'channel': '#general',
        'status': '1',
        'lastRunDate': '',
        'viewId': ''
    })
    db.insert('notification', data={
        'type': 'shoppingfunnelchangetracking',
        'email': email,
        'period': 1,
        'threshold': 10,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': '07.00',
        'channel': '#general',
        'status': '1',
        'lastRunDate': '',
        'viewId': ''
    })
    db.insert('notification', data={
        'type': 'costprediction',
        'email': email,
        'target': 100,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': '07.00',
        'channel': '#general',
        'status': '1',
        'lastRunDate': '',
        'viewId': ''
    })
    db.insert('notification', data={
        'type': 'performancegoaltracking',
        'email': email,
        'metric': 'ga:ROAS',
        'target': 100,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': '07.00',
        'channel': '#general',
        'status': '1',
        'lastRunDate': '',
        'viewId': ''
    })

