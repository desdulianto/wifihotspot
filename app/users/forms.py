from flask.ext.wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import DataRequired, ValidationError

import models


class LoginForm(Form):
    name = TextField('Nama User', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class ChangePasswordForm(Form):
    password = PasswordField('Password')
    password_verify = PasswordField('Verifikasi Password')

    def validate_password(form, field):
        password = form.password.data

        if len(password) < 8:
            raise ValidationError('Password min. 8 karakter!')

    def validate_password_verify(form, field):
        password = form.password.data
        password_verify = field.data

        if password != password_verify:
            raise ValidationError('Password tidak sama!')


class UserForm(Form):
    name = TextField('Nama User')
    password = PasswordField('Password')
    password_verify = PasswordField('Verifikasi Password')

    def validate_name(form, field):
        name = field.data.strip()

        if models.User.query.filter_by(name=name).first() != None:
            raise ValidationError('User sudah terdaftar!')

    def validate_password(form, field):
        password = form.password.data

        if len(password) < 8:
            raise ValidationError('Password min. 8 karakter!')

    def validate_password_verify(form, field):
        password = form.password.data
        password_verify = field.data

        if password != password_verify:
            raise ValidationError('Password tidak sama!')
