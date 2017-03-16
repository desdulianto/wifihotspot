"""
    wifihotspot.app.vouchers.forms
    ------------------------------

    Vouchers forms

    :copyright: (c) 2013 by Des Dulianto
"""

from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField
from wtforms.validators import DataRequired, ValidationError


class VoucherForm(Form):
    name = TextField('Nama', validators=[DataRequired()])
    phone = TextField('No. Telepon/email', validators=[DataRequired()])


class VoucherMessageForm(Form):
    message = TextAreaField('Pesan', validators=[DataRequired()])

    def validate_message(form, field):
        message = field.data.strip()

        if len(message) > 160:
            raise ValidationError('Pesan maksimum 160 karakter')

        field.data = message
