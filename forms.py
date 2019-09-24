from wtforms import Form, StringField, PasswordField, validators, SelectField
from wtforms.fields.html5 import DateField


# Notification Formu

class DataSourceForm(Form):
    invalidvalues = dsforminvalidvalues = ['-- Select an Option --', 'User does not have Google Analytics Account', '']
    account = SelectField("account", choices=[('', '-- Select an Option --')],
                          validators=[validators.NoneOf(invalidvalues, message=u"Invalid value")])
    property = SelectField("property", choices=[('', '-- Select an Option --')],
                          validators=[validators.NoneOf(invalidvalues, message=u"Invalid value")])
    view = SelectField("view", choices=[('', '-- Select an Option --')],
                          validators=[validators.NoneOf(invalidvalues, message=u"Invalid value")])
#    metric = SelectField('metric', choices=[('ga:users', 'users')])
#    dimension = SelectField('dimension', choices=[('ga:userType', 'user type')])
#    start_date = DateField('start_date', format="%Y-%m-%d")
#    end_date = DateField('end_date', format="%Y-%m-%d")
    channel = SelectField('channel', choices=[('', '-- Select a Channel --')],
                          validators=[validators.NoneOf(invalidvalues, message=u"Invalid value")])


# Time Formu

#class TimeForm(Form):
#    frequency = SelectField('frequency', choices=[('0', '0'), ('1', '1')])
#    scheduleType = SelectField('scheduletype', choices=[('daily', 'Daily'), ('weekly', 'weekly')])
#    timeofDay = SelectField('timeofDay', choices=[('07.00', '07.00'), ('09.00', '09.00')])
#    channel = SelectField('channel', choices=[('', '-- Select an Channel --')])


# Kullanıcı giriş formu

class LoginForm(Form):
    email = StringField("Email", validators=[validators.Length(min=7, max=50),
                                             validators.DataRequired(message="Lütfen Bu Alanı Doldurun")])
    password = PasswordField("Parola", validators=[validators.DataRequired(message="Lütfen Bu Alanı Doldurun")])


# Kullanıcı kayıt formu

class RegisterForm(Form):
    name = StringField("Ad", validators=[validators.Length(min=3, max=25),
                                         validators.DataRequired(message="Lütfen Bu Alanı Doldurun")])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=3, max=25),
                                                        validators.DataRequired(message="Lütfen Bu Alanı Doldurun")])
    email = StringField("Email", validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Girin")])
    password = PasswordField("Parola", validators=[
        validators.DataRequired(message="Lütfen Bu Alanı Doldurun"),
        validators.EqualTo(fieldname="confirm", message="Parolalarınız Uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula", validators=[validators.DataRequired(message="Lütfen Bu Alanı Doldurun")])
