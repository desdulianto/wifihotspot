from flask.ext.wtf import Form
from wtforms import TextField, SelectField, FormField, PasswordField
from wtforms.validators import DataRequired


class MikrotikSetupForm(Form):
    host = TextField('Host', default='localhost', validators=[DataRequired()])
    user = TextField('User')
    password = PasswordField('Password')


class RadiusDatabaseSetupForm(Form):
    dbtype = SelectField('Type', choices=[('', '-- Select DB type --'),
                                          ('mysql', 'MySQL'),
                                          ('postgres', 'PostgreSQL')],
                         validators=[DataRequired()])
    dbname = TextField('DB Name', default='radius', validators=[DataRequired()])
    host = TextField('Host', default='localhost', validators=[DataRequired()])
    user = TextField('User')
    password = PasswordField('Password')


class SetupForm(Form):
    mikrotik = FormField(MikrotikSetupForm, 'Mikrotik')
    radius = FormField(RadiusDatabaseSetupForm, 'RADIUS')
