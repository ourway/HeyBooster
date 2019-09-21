from flask import Flask, render_template, flash, redirect, request, session, url_for, make_response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# from forms import LoginForm, RegisterForm, NotificationForm, TimeForm
from forms import LoginForm, RegisterForm, DataSourceForm
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
import requests
import time
from modules import performancegoaltracking, costprediction
OAuth2ConsumerBlueprint.authorized = authorized
URL = "https://slack.com/api/{}"


# Kullanıcı Giriş Decorator'ı

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session or 'auth_token' in session:
            return f(*args, **kwargs)
        else:
            flash('Bu sayfayı görüntülemek için lütfen giriş yapın.', category='danger')
            return redirect(url_for('login'))

    return decorated_function


app = Flask(__name__)
db.init()

app.config['SECRET_KEY'] = 'linuxdegilgnulinux'

app.config["SLACK_OAUTH_CLIENT_ID"] = os.environ.get('SLACK_CLIENT_ID')
app.config["SLACK_OAUTH_CLIENT_SECRET"] = os.environ.get('SLACK_CLIENT_SECRET')

slack_bp = make_slack_blueprint(
    scope=["identify,bot,commands,channels:read,chat:write:bot,links:read,users:read,groups:read"])
slack_bp.authorized = authorized
app.register_blueprint(slack_bp, url_prefix="/login")
app.register_blueprint(google_auth.app)
app.register_blueprint(google_analytics.app)


@app.route('/', methods=['GET', 'POST'])
def home():
    # slack_message()
    return render_template('index.html')


@app.route('/change', methods=['POST'])
def change():
    message_action = request.form
    # Open a slack client
    user = db.find_one('user', {'sl_userid': message_action['sl_userid']})
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
            if user['password'] != "":
                if check_password_hash(user['password'], form.password.data):
                    flash("Başarıyla Giriş Yaptınız", category="success")

                    session['logged_in'] = True
                    session['email'] = user['email']

                    return redirect(url_for('home'))
                else:
                    flash("Kullanıcı Adı veya Parola Yanlış", category="danger")
                    return redirect(url_for('login'))

    return render_template('auths/login.html', form=form)


@app.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        user = db.find_one('user', {'email': form.email.data})
        if (user):
            flash('Bu kullanıcı zaten Google hesabı ile kayıtlı! Lütfen "Sign in with Google" butonuna basınız',
                  category="danger")
            return redirect(url_for('login'))
        else:
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


@app.route('/privacypolicy')
def privacy():
    return render_template('privacy.html')


@app.route("/connect")
@login_required
def connect():
    #    if not slack.authorized:
    #        return redirect(url_for("slack.login"))
    #    return redirect('/')
    return redirect(url_for("slack.login"))


def get_channels():
    #    data = [('token', slack.token['access_token'])]
    if not 'sl_accesstoken' in session.keys():
        session['sl_accesstoken'] = db.find_one('user', query={'email': session['email']})['sl_accesstoken']
    data = [('token', session['sl_accesstoken']),
             ('types', 'public_channel, private_channel'),
             ('limit', 200)]
    channels = []
    conversationslist = requests.post(URL.format('conversations.list'), data).json()['channels']
    for conv in conversationslist:
        if(conv['is_channel'] or conv['is_group']):
            conv['name'] = '#' + conv['name']
            channels += [conv]
            
    userslist = requests.post(URL.format('users.list'), data).json()['members']
    for user in userslist:
        if(not user['is_bot']):
            channels += [user]
    return channels

@app.route("/datasources", methods=['GET', 'POST'])
@login_required
def datasources():
    nForm = DataSourceForm(request.form)
    datasources = db.find('datasource', query={'email': session['email']})
    unsortedargs = []
    for datasource in datasources:
        unsortedargs.append(datasource)
    #    args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
    #    tForm = TimeForm(request.form)
    if request.method == 'POST':
        #        data = [('token', session['sl_accesstoken'])]
        #        uID = requests.post(URL.format('users.identity'), data).json()['user']['id']
        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
        ts = time.time()
        
        data = {
            'email': session['email'],
            'sl_userid': uID,
            'sourceType': "Google Analytics",
            'accountID': nForm.account.data.split('\u0007')[0],
            'accountName': nForm.account.data.split('\u0007')[1],
            'propertyID': nForm.property.data.split('\u0007')[0],
            'propertyName': nForm.property.data.split('\u0007')[1],
            'viewID': nForm.view.data.split('\u0007')[0],
            'currency': nForm.view.data.split('\u0007')[1],
            'viewName': nForm.view.data.split('\u0007')[2],
            'channelType': "Slack",
            'channelID': nForm.channel.data.split('\u0007')[0],
            'channelName': nForm.channel.data.split('\u0007')[1],
            'createdTS': ts
        }
        _id = db.insert_one("datasource", data=data).inserted_id
        data['_id'] = _id
        unsortedargs.append(data)
        insertdefaultnotifications(session['email'], userID=uID,
                                   dataSourceID=_id,
                                   channelID=nForm.channel.data.split('\u0007')[0])
    #        args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
    #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
    else:
        #        user_info = google_auth.get_user_info()
        nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                  google_analytics.get_accounts(session['email'])['accounts']]
        channels = get_channels()
        nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
                                  in channels]
        # incoming_webhook = slack.token['incoming_webhook']
    #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
    return render_template('datasources.html', nForm=nForm, args=args)

@app.route("/datasourcesinfo", methods=['GET', 'POST'])
@login_required
def datasourcesinfo():
    nForm = DataSourceForm(request.form)
    datasources = db.find('datasource', query={'email': session['email']})
    unsortedargs = []
    for datasource in datasources:
        unsortedargs.append(datasource)
    #    args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
    #    tForm = TimeForm(request.form)
    if request.method == 'POST':
        #        data = [('token', session['sl_accesstoken'])]
        #        uID = requests.post(URL.format('users.identity'), data).json()['user']['id']
        uID = db.find_one("user", query={"email": session["email"]})['sl_userid']
        ts = time.time()
        data = {
            'email': session['email'],
            'sl_userid': uID,
            'sourceType': "Google Analytics",
            'accountID': nForm.account.data.split('\u0007')[0],
            'accountName': nForm.account.data.split('\u0007')[1],
            'propertyID': nForm.property.data.split('\u0007')[0],
            'propertyName': nForm.property.data.split('\u0007')[1],
            'viewID': nForm.view.data.split('\u0007')[0],
            'viewName': nForm.view.data.split('\u0007')[1],
            'channelType': "Slack",
            'channelID': nForm.channel.data.split('\u0007')[0],
            'channelName': nForm.channel.data.split('\u0007')[1],
            'createdTS': ts
        }
        _id = db.insert_one("datasource", data=data).inserted_id
        data['_id'] = _id
        unsortedargs.append(data)
        insertdefaultnotifications(session['email'], userID=uID,
                                   dataSourceID=_id,
                                   channelID=nForm.channel.data.split('\u0007')[0])
    #        args = sorted(unsortedargs, key = lambda i: i['createdTS'], reverse=False)
    #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
    else:
        #        user_info = google_auth.get_user_info()
        nForm.account.choices += [(acc['id'] + '\u0007' + acc['name'], acc['name']) for acc in
                                  google_analytics.get_accounts(session['email'])['accounts']]
        channels = get_channels()
        nForm.channel.choices += [(channel['id'] + '\u0007' + channel['name'], channel['name']) for channel
                                  in channels]
        # incoming_webhook = slack.token['incoming_webhook']
    #        return render_template('datasourcesinfo.html', nForm = nForm, args = args)
    args = sorted(unsortedargs, key=lambda i: i['createdTS'], reverse=False)
    return render_template('datasourcesinfo.html', nForm=nForm, args=args)

@app.route("/gatest/<email>")
def gatest(email):
    service = google_analytics.build_management_api_v3_woutSession(email)
    accs = service.management().accounts().list().execute()
    accounts = []
    if accs.get('items'):
        for acc in accs.get('items'):
            accounts.append({'id': acc.get('id'), 'name': acc.get('name')})
    return {'accounts': accounts}


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    # Parse the request payload
    message_action = json.loads(request.form["payload"])
    # Open a slack client
    sl_userid = message_action['user']['id']
    channel = message_action['channel']['id']
    user = db.find_one('user', {'sl_userid': sl_userid})
    slack_token = user['sl_accesstoken']
    email = user['email']
    slack_client = WebClient(token=slack_token)
    if message_action["type"] == "interactive_message":
        if (message_action['actions'][-1]['value'] == 'track'):
            houroptions = []
            for i in range(0, 24):
                houroptions.append({'label': str(i), 'value': i})
            minuteoptions = []
            for i in range(0, 60):
                minuteoptions.append({'label': str(i), 'value': i})
            text = message_action['original_message']['attachments'][0]['pretext']
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
                            #                            {
                            #                                "label": "Schedule Type",
                            #                                "type": "select",
                            #                                "name": "schedule_types",
                            #                                "placeholder": "Select a schedule type",
                            #                                "options": [
                            #                                    {
                            #                                        "label": "Daily",
                            #                                        "value": "daily"
                            #                                    },
                            #                                    {
                            #                                        "label": "Weekly",
                            #                                        "value": "weekly"
                            #                                    }
                            #                                ]
                            #                            },
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
                            },
                            #                            {
                            #                                "label": "Threshold (%)",
                            #                                "name": "threshold",
                            #                                "type": "text",
                            #                                "subtype": "number",
                            #                                "placeholder": "Enter a number"
                            #                            }
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
                            #                            {
                            #                                "label": "Schedule Type",
                            #                                "type": "select",
                            #                                "name": "schedule_types",
                            #                                "placeholder": "Select a schedule type",
                            #                                "options": [
                            #                                    {
                            #                                        "label": "Daily",
                            #                                        "value": "daily"
                            #                                    },
                            #                                    {
                            #                                        "label": "Weekly",
                            #                                        "value": "weekly"
                            #                                    }
                            #                                ]
                            #                            },
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
                            },
                            #                            {
                            #                                "label": "Threshold (%)",
                            #                                "name": "threshold",
                            #                                "type": "text",
                            #                                "subtype": "number",
                            #                                "placeholder": "Enter a number"
                            #                            }
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
                            #                            {
                            #                                "label": "Schedule Type",
                            #                                "type": "select",
                            #                                "name": "schedule_types",
                            #                                "placeholder": "Select a schedule type",
                            #                                "options": [
                            #                                    {
                            #                                        "label": "Daily",
                            #                                        "value": "daily"
                            #                                    },
                            #                                    {
                            #                                        "label": "Weekly",
                            #                                        "value": "weekly"
                            #                                    }
                            #                                ]
                            #                            },
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
                            },
                            #                            {
                            #                                "label": "Monthly Adwords Budget",
                            #                                "name": "target",
                            #                                "type": "text",
                            #                                "subtype": "number",
                            #                                "placeholder": "Enter a number"
                            #                            }
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
                            #                            {
                            #                                "label": "Schedule Type",
                            #                                "type": "select",
                            #                                "name": "schedule_types",
                            #                                "placeholder": "Select a schedule type",
                            #                                "options": [
                            #                                    {
                            #                                        "label": "Daily",
                            #                                        "value": "daily"
                            #                                    },
                            #                                    {
                            #                                        "label": "Weekly",
                            #                                        "value": "weekly"
                            #                                    }
                            #                                ]
                            #                            },
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
                            },
                            #                            {
                            #                                "label": "Metric Type",
                            #                                "type": "select",
                            #                                "name": "metric",
                            #                                "placeholder": "Select a metric type",
                            #                                "options": [
                            #                                    {
                            #                                        "label": "ROAS",
                            #                                        "value": "ga:ROAS"
                            #                                    },
                            #                                    {
                            #                                        "label": "CPC",
                            #                                        "value": "ga:CPC"
                            #                                    },
                            #                                    {
                            #                                        "label": "Revenue",
                            #                                        "value": "ga:transactionRevenue"
                            #                                    }
                            #                                ]
                            #                            },
                            #                            {
                            #                                "label": "Goal",
                            #                                "name": "target",
                            #                                "type": "text",
                            #                                "subtype": "number",
                            #                                "placeholder": "Enter a number"
                            #                            }
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
        elif (message_action['actions'][-1]['value'] == 'ignore'):
            text = message_action['original_message']['attachments'][0]['pretext']
            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid, 'channelID': channel})['_id']
            if (("performance" in text.lower()) and ("change" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'performancechangetracking'},
                                   status='0')
            elif (("funnel" in text.lower()) and ("change" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'shoppingfunnelchangetracking'},
                                   status='0')
            elif (("cost" in text.lower()) and ("prediction" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'costprediction'},
                                   status='0')
            elif (("performance" in text.lower()) and ("goal" in text.lower())):
                db.find_and_modify('notification', query={'datasourceID': datasourceID,
                                                          'type': 'performancegoaltracking'},
                                   status='0')
        elif (message_action['actions'][-1]['value'] == 'change'):
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

        elif (message_action['actions'][-1]['value'] == 'setmygoal'):
            text = message_action['original_message']['text']
            if (True):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Set My Goal",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Metric",
                                "type": "select",
                                "name": "metric",
                                "placeholder": "Select a metric",
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
                                        "label": "Session",
                                        "value": "ga:sessions",
                                    },
                                    {
                                        "label": "Cost Per Transaction",
                                        "value": "ga:costPerTransaction",
                                    },
                                    {
                                        "label": "Revenue",
                                        "value": "ga:transactionRevenue"
                                    }
                                ]
                            },
                            {
                                "label": "Dimension",
                                "type": "select",
                                "name": "dimension",
                                "placeholder": "Select a dimension",
                                "optional": True,
                                "options": [
                                    {
                                        "label": "Campaign",
                                        "value": "ga:campaign"
                                    },
                                    {
                                        "label": "Source / Medium",
                                        "value": "ga:sourceMedium"
                                    },
                                    {
                                        "label": "Device Category",
                                        "value": "ga:deviceCategory",
                                    },
                                ]
                            },
                            {
                                "label": "Operator",
                                "type": "select",
                                "name": "operator",
                                "placeholder": "Select an operator",
                                "optional": True,
                                "options": [
                                    {
                                        "label": "Exact Match",
                                        "value": "=="
                                    },
                                    {
                                        "label": "Does Not Match",
                                        "value": "!="
                                    },
                                    {
                                        "label": "Contains",
                                        "value": "=@"
                                    },
                                    {
                                        "label": "Does Not Contain",
                                        "value": "!@",
                                    },
                                ]
                            },
                            {
                                "label": "Expression",
                                "type": "text",
                                "name": "expression",
                                "placeholder": "Enter an expression",
                                "optional": True
                            },
                            {
                                "label": "Target",
                                "type": "text",
                                "name": "target",
                                "subtype": "number",
                                "placeholder": "Enter a target"
                            }
                        ]
                    }
                )

        elif (message_action['actions'][-1]['value'] == 'setmybudget'):
            text = message_action['original_message']['text']
            if (True):
                slack_client.dialog_open(
                    trigger_id=message_action["trigger_id"],
                    dialog={
                        "title": "Set My Budget",
                        "submit_label": "Submit",
                        "callback_id": "notification_form",
                        "elements": [
                            {
                                "label": "Monthly Adwords Budget",
                                "name": "budget",
                                "type": "text",
                                "subtype": "number",
                                "placeholder": "Enter a number"
                            }
                        ]
                    }
                )
        elif ('ignoreone' in message_action['actions'][-1]['value']):
            metric = message_action['actions'][-1]['value'].split(' ')[-1]
            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid,
                                                            'channelID': channel})['_id']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'performancegoaltracking'})
            module_id = module['_id']
            metricindex = module['metric'].index(metric)
            db.DATABASE['notification'].update({"_id":module["_id"]}, {"$unset" : {"metric."+ str(metricindex): 1, 
                                                                                   "target."+ str(metricindex): 1,
                                                                                   "filterExpression."+ str(metricindex): 1 }}) 
            db.DATABASE['notification'].update({"_id":module["_id"]}, {"$pull" : {"metric" : None,
                                                                                  "target" : None,
                                                                                  "filterExpression" : None }})

    elif message_action["type"] == "dialog_submission":
        submission = message_action['submission']
        datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid,
                                                        'channelID': channel})['_id']
        if ('module_types' in submission.keys()):
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
            moduleType = submission['module_types']
            if (moduleType == 'performancechangetracking'):
                #                scheduleType = submission['schedule_types']
                #                threshold = float(submission['threshold'])
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType
                                                                     },
                                   #                                                               scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # threshold=threshold,
                                   # status='1'
                                   )
            elif (moduleType == 'shoppingfunnelchangetracking'):
                #                scheduleType = submission['schedule_types']
                #                threshold = float(submission['threshold'])
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType
                                                                     },
                                   #                                                               scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # threshold=threshold,
                                   # status='1'
                                   )
            elif (moduleType == 'costprediction'):
                #                scheduleType = submission['schedule_types']
                #                target = float(submission['target'])
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType
                                                                     },
                                   #                                                                   scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # target=target,
                                   # status='1'
                                   )
            elif (moduleType == 'performancegoaltracking'):
                #                scheduleType = submission['schedule_types']
                #                target = float(submission['target'])
                #                metric = submission['metric']
                db.find_and_modify(collection='notification', query={'datasourceID': datasourceID,
                                                                     'type': moduleType},
                                   #                                                                       scheduleType=scheduleType,
                                   timeofDay="%s.%s" % (writtenhour, selectedminute),
                                   # target=target,
                                   # metric=metric,
                                   # status='1'
                                   )
        elif ('hour' in submission.keys() and 'minute' in submission.keys()):
            datasourceID = db.find_one("datasource", query={'sl_userid': sl_userid,
                                                            'channelID': channel})['_id']
            modules = db.find("notification", query={'datasourceID': datasourceID})
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
        elif ('metric' in submission.keys() and 'target' in submission.keys() and len(submission.keys()) == 5):
            dataSource = db.find_one("datasource", query={'sl_userid': sl_userid,
                                                            'channelID': channel})
            datasourceID = dataSource['_id']
            viewId = dataSource['viewID']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'performancegoaltracking'})
            module_id = module['_id']
            if( submission['dimension'] != None and submission['operator'] != None and submission['expression'] != None ):
                filterExpression = submission['dimension']+submission['operator']+submission['expression']
            else:
                filterExpression = ''
            try:
                metricindex = module['metric'].index(submission['metric'])
                db.DATABASE['notification'].update(
                    {'_id': module_id},
                    {'$set': {
                        "target." + str(metricindex): submission['target'], "filterExpression." + str(metricindex): filterExpression}}
                )
                module['metric'] = [module['metric'][metricindex]]
                module['target'] = [module['target'][metricindex]]
                module['filter'] = [module['filter'][metricindex]]
                performancegoaltracking(slack_token, module, dataSource)
            except:
                db.DATABASE['notification'].update(
                    {'_id': module_id},
                    {'$push': {'metric': submission['metric']}}
                )
                db.DATABASE['notification'].update(
                    {'_id': module_id},
                    {'$push': {'target': submission['target']}}
                )
                db.DATABASE['notification'].update(
                    {'_id': module_id},
                    {'$push': {'filterExpression': filterExpression}}
                )
                module['metric'] = [submission['metric']]
                module['target'] = [submission['target']]
                module['filter'] = [filterExpression]
                performancegoaltracking(slack_token, module, dataSource)
            db.find_and_modify("notification", query={'_id': module['_id']},
                               status='1')
        elif ('budget' in submission.keys() and len(submission.keys()) == 1):
            dataSource = db.find_one("datasource", query={'sl_userid': sl_userid,
                                                          'channelID': channel})
            datasourceID = dataSource['_id']
            viewId = dataSource['viewID']
            module = db.find_one("notification", query={'datasourceID': datasourceID,
                                                        'type': 'costprediction'})
            module_id = module['_id']
            target = float(submission['budget'])
            db.find_and_modify(collection='notification', query={'_id': module['_id']},
                                                           target=target,
                                                           status='1'
                                                           )
            module['viewId'] = viewId
            module['channel'] = channel
            module['target'] = target
            costprediction(slack_token, module, dataSource)

    return make_response("", 200)


def insertdefaultnotifications(email, userID, dataSourceID, channelID):
    # Default Notifications will be inserted here
    #    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['sl_accesstoken']}
    #    requests.post(URL.format('chat.postMessage'), data=json.dumps(data), headers=headers)
    lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
    #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
    data = [('token', session['sl_accesstoken']),
            ('user', userID)]
    usr_tz_offset = requests.post(URL.format('users.info'), data).json()['user']['tz_offset'] // 3600
    if (7 >= (usr_tz_offset - lc_tz_offset)):
        default_time = str(7 - (usr_tz_offset - lc_tz_offset)).zfill(2)
    else:
        default_time = str(24 + (7 - (usr_tz_offset - lc_tz_offset))).zfill(2)
    db.insert('notification', data={
        'type': 'performancechangetracking',
        'email': email,
        'period': 1,
        'threshold': 10,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': "%s.00" % (default_time),
        'status': '1',
        'lastRunDate': '',
        'datasourceID': dataSourceID
    })
    db.insert('notification', data={
        'type': 'shoppingfunnelchangetracking',
        'email': email,
        'period': 1,
        'threshold': 10,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': "%s.00" % (default_time),
        'status': '1',
        'lastRunDate': '',
        'datasourceID': dataSourceID
    })
    db.insert('notification', data={
        'type': 'costprediction',
        'email': email,
        'target': 100,
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': "%s.00" % (default_time),
        'status': '0',
        'lastRunDate': '',
        'datasourceID': dataSourceID
    })
    db.insert('notification', data={
        'type': 'performancegoaltracking',
        'email': email,
        'metric': [],
        'target': [],
        'filterExpression': [],
        'scheduleType': 'daily',
        'frequency': 0,
        'timeofDay': "%s.00" % (default_time),
        'status': '0',
        'lastRunDate': '',
        'datasourceID': dataSourceID
    })
    # When the slack connection is completed send notification user to set time
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + session['sl_accesstoken']}
    data = {
        "channel": channelID,
        "attachments": [{
            # "title": "Blog Yazıları",
            # "title_link": "https://blog.boostroas.com/tr/"
        },
            {
                "text": "Welcome to Heybooster, I am your digital buddy to support " +
                        "you to boost your website by analyzing your data with marketing perspective." +
                        "You will get first insights tomorrow at 7 am",
                "callback_id": "notification_form",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "change",
                        "text": "Reschedule",
                        "type": "button",
                        "value": "change"
                    },
                    {
                        "name": "setmygoal",
                        "text": "Set My Goal",
                        "type": "button",
                        "value": "setmygoal"
                    },
                    {
                        "name": "setmybudget",
                        "text": "Set My Budget",
                        "type": "button",
                        "value": "setmybudget"
                    }
                ]
            }]}
    requests.post(URL.format('chat.postMessage'), data=json.dumps(data), headers=headers)
