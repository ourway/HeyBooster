from flask import Flask, render_template, flash, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from forms import LoginForm, RegisterForm
from flask_wtf import FlaskForm
from wtforms import SelectField, DateField
from flask_dance.contrib.slack import make_slack_blueprint, slack

import google_auth
import google_analytics


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
app.config['SECRET_KEY'] = 'linuxdegilgnulinux'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config["SLACK_OAUTH_CLIENT_ID"] = '711101969589.708601483569'
app.config["SLACK_OAUTH_CLIENT_SECRET"] = 'f319c69ea84ecb3b6b5643e09c31ca97'
slack_bp = make_slack_blueprint(scope=["admin,identify,bot,incoming-webhook,channels:read,chat:write:bot,links:read"])

app.register_blueprint(slack_bp, url_prefix="/login")
app.register_blueprint(google_auth.app)
app.register_blueprint(google_analytics.app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(15), unique=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(25), unique=True)


class Form(FlaskForm):
    account = SelectField("account", choices=[('', '-- Select an Option --')])
    property = SelectField("property", choices=[('', '-- Select an Option --')])
    view = SelectField("view", choices=[('', '-- Select an Option --')])
    metric = SelectField('metric', choices=[('ga:users', 'users')])
    dimension = SelectField('dimension', choices=[('ga:userType', 'user type')])
    start_date = DateField('start_date', format='%Y-%m-%d')
    end_date = DateField('end_date', format='%Y-%m-%d')


class TimesForm(FlaskForm):
    time_range = SelectField("account", choices=[('daily', 'Daily'), ('weekly', 'Weekly')])


@app.route('/', methods=['GET', 'POST'])
def home():
    form = TimesForm(request.form)
    if request.method == 'POST':
        value = form.time_range.data
        file = open('value.txt', 'w')
        file.write(value)
        file.close()
        return redirect('/')
    return render_template('index.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate:
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                flash("Başarıyla Giriş Yaptınız", "success")

                session['logged_in'] = True
                session['email'] = user.email

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
        db.session.add(new_user)
        db.session.commit()
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
    file = open('data.txt', 'r')
    text = file.read()
    file.close()
    # file2 = open('value.txt', 'r')
    # value = file2.read()
    #
    # if value == 'daily':
    #     print('daily')
    # elif value == 'weekly':
    #     print('weekly')

    if not slack.authorized:
        return redirect(url_for("slack.login"))
    slack.post("chat.postMessage", data={
        "text": text,
        "channel": "#general",
        "icon_emoji": ":male-technologist:",
    })

    # assert resp.ok, resp.text

    return redirect('/')


@app.route("/notifications", methods=['GET', 'POST'])
@login_required
def notifications():
    form = Form(request.form)
    if request.method == 'POST':
        value = google_analytics.get_results(form)
        file = open('data.txt', 'w')
        file.write(value)
        file.close()
        return redirect('/')
    else:
        form.account.choices += [(acc['id'], acc['name']) for acc in google_analytics.get_accounts()['accounts']]
        return render_template('notifications.html', form=form)
