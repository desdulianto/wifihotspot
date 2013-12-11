from flask.ext.wtf import Form
from wtforms import TextField, IntegerField
from wtforms.validators import ValidationError


class GroupAttributeForm(Form):
    mikrotikRateLimit = TextField('Rate Limit (rx/tx)')
    mikrotikRecvLimit = IntegerField('Upload Quota (bytes)', default=0)
    mikrotikXmitLimit = IntegerField('Download Quota (bytes)', default=0)
    sessionTimeout    = IntegerField('Session Time (seconds)', default=0)
    portLimit         = IntegerField('Sessions per-user', default=1)

    def mikrotikRateLimit_validate(form, field):
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

    def mikrotikRecvLimit_validate(form, field):
        limit = field.data

        if limit < 0:
            raise ValidationError('Wrong Value')


    def mikrotikXmitLimit_validate(form, field):
        limit = field.data

        if limit < 0:
            raise ValidationError('Wrong Value')

    def sessionTimeout_validate(form, field):
        timeout = field.data

        if timeout < 0:
            raise ValidationError('Wrong Value')


    def portLimit_validate(form, field):
        limit = field.data

        if limit < 1:
            raise ValidationError('Wrong Value')
