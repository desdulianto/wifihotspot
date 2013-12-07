from flask.ext.wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import DataRequired


class LoginForm(Form):
    name = TextField('Nama User', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
