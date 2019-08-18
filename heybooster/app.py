from flask import Flask, render_template, flash, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from forms import LoginForm, RegisterForm, NotificationForm, TimesForm
from flask_dance.contrib.slack import make_slack_blueprint, slack
from flask_pymongo import PyMongo
from mongoengine import *
import google_auth
import google_analytics

from database import db
from models.user import User
from slack_auth import authorized
from flask_dance.consumer import OAuth2ConsumerBlueprint

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
slack_bp = make_slack_blueprint(scope=["admin,identify,bot,incoming-webhook,channels:read,chat:write:bot,links:read"])
slack_bp.authorized = authorized
app.register_blueprint(slack_bp, url_prefix="/login")
app.register_blueprint(google_auth.app)
app.register_blueprint(google_analytics.app)


@app.route('/', methods=['GET', 'POST'])
def home():
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
                        password=hashed_password, ga_accesstoken='', ga_refreshtoken='', sl_accesstoken='')
        new_user.insert()
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
    form = NotificationForm(request.form)
    if request.method == 'POST':
        message = google_analytics.get_results(form)
        slack_message(message)
        return redirect('/')
    else:
        form.account.choices += [(acc['id'], acc['name']) for acc in google_analytics.get_accounts()['accounts']]
        return render_template('notifications.html', form=form)


@app.route("/gatest/<email>")
def gatest(email):
    service = google_analytics.build_management_api_v3_woutSession(email)
    accs = service.management().accounts().list().execute()
    accounts = []
    if accs.get('items'):
        for acc in accs.get('items'):
            accounts.append({'id': acc.get('id'), 'name': acc.get('name')})
    return {'accounts': accounts}


def slack_message(message):
    if not slack.authorized:
        return redirect(url_for("slack.login"))
    slack.post("chat.postMessage", data={
        "text": message,
        "channel": "#general",
        "icon_emoji": ":male-technologist:",
    })

    return redirect('/')
