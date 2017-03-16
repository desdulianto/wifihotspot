from flask.ext.wtf import Form
from wtforms import TextField, IntegerField, RadioField, BooleanField, \
    SelectField, FileField
from wtforms.validators import ValidationError, IPAddress, DataRequired


def MACAddress(message=None):
    import re

    def inner(form, field):
        address = field.data
        address_type = form.address_type.data
        mac = re.compile('^([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2}$')
        if mac.match(address) is None:
            raise ValidationError(message)
    return inner


class GroupAttributeForm(Form):
    mikrotikRateLimit = TextField('Rate Limit (rx/tx)')
    mikrotikRecvLimit = IntegerField('Upload Quota (bytes)', default=0)
    mikrotikXmitLimit = IntegerField('Download Quota (bytes)', default=0)
    sessionTimeout    = IntegerField('Session Time (seconds)', default=0)
    idleTimeout       = IntegerField('Idle Timeout (seconds)', default=0)
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
    phone = TextField('Phone/Email')
    user = TextField('Voucher')
    address = TextField('IP Address')
    server = TextField('Hotspot')


class IpBindingForm(Form):
    address = TextField('Address')
    address_type = RadioField('Address Type', choices=[('mac', 'MAC Address'),
                                                        ('ip' , 'IP Address')],
                                                        default='mac')
    server  = SelectField('Server')
    type    = RadioField('Action', choices=[('bypassed', 'Bypass'),
                                          ('blocked', 'Block')],
                                          default='bypassed')
    comment = TextField('Comment')
    enabled = BooleanField('Enabled')

    def validate_address(form, field):
        address_type = form.address_type.data

        if address_type == 'ip':
            IPAddress('Invalid IP address')(form, field)
        else:
            MACAddress('Invalid MAC address')(form, field)


class BannerForm(Form):
    image = FileField('Image File')

    def validate_image(form, field):
        mimetype = field.data.mimetype

        if 'image/' not in mimetype:
            raise ValidationError('Must be image file')
