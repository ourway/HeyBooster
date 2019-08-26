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
import json
from slackclient import SlackClient
OAuth2ConsumerBlueprint.authorized = authorized


# Kullanıcı Giriş Decorator'ı

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Bu sayfayı görüntülemek için lütfen giriş yapın.', 'danger')
            return redirect(url_for('login'))

    return decorated_function


app = Flask(__name__)
db.init()

app.config['SECRET_KEY'] = 'linuxdegilgnulinux'

app.config["SLACK_OAUTH_CLIENT_ID"] = ''
app.config["SLACK_OAUTH_CLIENT_SECRET"] = ''
slack_bp = make_slack_blueprint(scope=["admin,identify,bot,commands,incoming-webhook,channels:read,chat:write:bot,links:read"])
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
    slack_message()
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate:
        user = db.find_one('user', {'email': form.email.data})
        if user:
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
        new_user = User(name=form.name.data, username=form.username.data, email=form.email.data,
                        password=hashed_password)
        new_user.insert()
        db.insert('notification', data={
            'type': 'performancechangetracking',
            'email': form.email.data,
            'period': 1,
            'threshold': 0.10,
            'scheduleType': 'daily',
            'frequency': 0,
            'timeofDay': '07.00',
            'channel': '#general',
            'status': 'active',
            'lastRunDate': '',
            'viewId': ''
        })
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
        nForm.account.choices += [(acc['id'], acc['name']) for acc in google_analytics.get_accounts()['accounts']]
        incoming_webhook = slack.token['incoming_webhook']
        print(incoming_webhook['channel'])
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


@app.route("/save", methods=['GET', 'POST'])
def save():
    tForm = TimeForm(request.form)

    scheduleType = tForm.scheduleType.data
    frequency = tForm.frequency.data
    timeofDay = tForm.timeofDay.data

    db.find_and_modify(collection='notification',
                       email=session['email'],
                       scheduleType=scheduleType,
                       frequency=frequency,
                       timeofDay=timeofDay)

    return redirect('/')


@app.route('/scheduleType/daily', methods=['POST'])
def scheduleTypeDaily():
    scheduleType = "daily"
    db.find_and_modify(collection='notification',
                       email=session['email'],
                       scheduleType=scheduleType)
    return jsonify(
        response_type='in_channel',
        text='<https://youtu.be/frszEJb0aOo|General Kenobi!>',
    )


@app.route('/scheduleType/weekly', methods=['GET', 'POST'])
def scheduleTypeWeekly():
    scheduleType = "weekly"
    db.find_and_modify(collection='notification',
                       email=session['email'],
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

@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    # Parse the request payload
    message_action = json.loads(request.form["payload"])
    #Open a slack client
    user = db.find_one('user', {'user_id': message_action['user']['id']})
    slack_token = user['sl_accesstoken']
    email = user['email']
#    notification = db.find_one('notification', {'email': email})
#    channel = notification['channel']
#    message_ts = notification['message_ts']
    slack_client = SlackClient(token=slack_token)
    if message_action["type"] == "interactive_message":
        if(message_action['actions'][0]['value']=='track'):
            # Show the ordering dialog to the user
            slack_client.api_call(
                "dialog.open",
                trigger_id=message_action["trigger_id"],
                dialog={
                    "title": "Notification Settings",
                    "submit_label": "Submit",
                    "callback_id": "notification_form",
                    "elements": [
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

    elif message_action["type"] == "dialog_submission":
        submission = message_action['submission']
        scheduleType = submission['schedule_types']
        db.find_and_modify(collection='notification', email=email, scheduleType = scheduleType)
#        # Update the message to show that we're in the process of taking their order
#        slack_client.api_call(
#            "chat.update",
#            channel=channel,
#            ts=message_ts,
#            text=":white_check_mark: Order received!",
#            attachments=[]
#        )
    return make_response("", 200)
