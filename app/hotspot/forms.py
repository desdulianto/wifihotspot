from flask.ext.wtf import Form
from wtforms import TextField, IntegerField
from wtforms.validators import ValidationError


class GroupAttributeForm(Form):
    mikrotikRateLimit = TextField('Rate Limit (rx/tx)')
    mikrotikRecvLimit = IntegerField('Upload Quota (bytes)', default=0)
    mikrotikXmitLimit = IntegerField('Download Quota (bytes)', default=0)
    sessionTimeout    = IntegerField('Session Time (seconds)', default=0)
    portLimit         = IntegerField('Sessions per-user', default=1)

    def validate_mikrotikRateLimit(form, field):
        if len(field.data.strip()) == 0:
            return 

        rx, tx = field.data.split('/')

        try:
            rx = int(rx.strip('k').strip('M'))
            tx = int(tx.strip('k').strip('M'))
        except ValueError:
            raise ValidationError('Wrong Value')

        if rx < 0 or tx < 0:
            raise ValidationError('Wrong Value')

    def validate_mikrotikRecvLimit(form, field):
        limit = field.data

        if limit < 0:
            raise ValidationError('Wrong Value')


    def validate_mikrotikXmitLimit(form, field):
        limit = field.data

        if limit < 0:
            raise ValidationError('Wrong Value')

    def validate_sessionTimeout(form, field):
        timeout = field.data

        if timeout < 0:
            raise ValidationError('Wrong Value')


    def validate_portLimit(form, field):
        limit = field.data

        if limit < 1:
            raise ValidationError('Wrong Value')


class OnlineUserFilterForm(Form):
    username = TextField('User Name')
    phone = TextField('Phone')
    user = TextField('Voucher')
    address = TextField('IP Address')
    server = TextField('Hotspot')
