from flask import Flask, render_template, flash, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from forms import LoginForm, RegisterForm
from flask_wtf import FlaskForm
from wtforms import SelectField, DateField
from flask_dance.contrib.slack import make_slack_blueprint, slack

from data import data

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


@app.route('/')
def home():
    return render_template('index.html')


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
        flash('Başarılı bir şekilde kayıt oldunuz', 'success')
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
    rdrct = data()
    text = ':exclamation: Bu ay kalan para: {} ₺'.format(rdrct)
    if not slack.authorized:
        return redirect(url_for("slack.login"))
    resp = slack.post("chat.postMessage", data={
        "channel": "#web-app",
        "text": text,
        "icon_emoji": ":male-technologist:",
    })

    assert resp.ok, resp.text

    return resp.text


@app.route("/notifications", methods=['GET', 'POST'])
@login_required
def notifications():
    form = Form(request.form)
    if request.method == 'POST':
        return google_analytics.get_results(form)
    else:
        form.account.choices += [(acc['id'], acc['name']) for acc in google_analytics.get_accounts()['accounts']]
        return render_template('notifications.html', form=form)


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
