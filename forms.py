from wtforms import Form, StringField, PasswordField, validators, SelectField
from wtforms.fields.html5 import DateField


# Notification Formu

class DataSourceForm(Form):
    data_source_name = StringField("Data Source Name",
                                   validators=[validators.DataRequired(message="This field is required")],
                                   render_kw={"class": "form-control text-center form-control-sm",
                                              "placeholder": "Type a name eg. 'My Store’s First Audit'"})
    account = SelectField("account", choices=[('', 'Select your account')],
                          validators=[validators.DataRequired(message="This field is required.")],
                          render_kw={"class": "selection-2"})
    property = SelectField("property", choices=[('', 'Select your property')],
                           validators=[validators.DataRequired(message="This field is required.")],
                           render_kw={"class": "selection-2"})
    view = SelectField("view", choices=[('', 'Select your view')],
                       validators=[validators.DataRequired(message="This field is required.")],
                       render_kw={"class": "selection-2"})
    #    metric = SelectField('metric', choices=[('ga:users', 'users')])
    #    dimension = SelectField('dimension', choices=[('ga:userType', 'user type')])
    #    start_date = DateField('start_date', format="%Y-%m-%d")
    #    end_date = DateField('end_date', format="%Y-%m-%d")
    channel = SelectField('channel', choices=[('', 'Select your channel')],
                          render_kw={"class": "selection-2"})


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
