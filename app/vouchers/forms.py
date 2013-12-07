"""
    wifihotspot.app.vouchers.forms
    ------------------------------

    Vouchers forms

    :copyright: (c) 2013 by Des Dulianto
"""

from flask.ext.wtf import Form
from wtforms import TextField
from wtforms.validators import DataRequired


class VoucherForm(Form):
    name = TextField('Nama', validators=[DataRequired()])
    phone = TextField('No. Telepon', validators=[DataRequired()])
