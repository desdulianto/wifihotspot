from flask import render_template, jsonify
from flask import Blueprint

import random
import string

from app import app, db, redis
import models
import json


blueprint = Blueprint('vouchers', __name__)

@blueprint.route('/', endpoint='index')
def index():
    return render_template('index.html')


@blueprint.route('/<name>/<phone>', methods=['POST'], endpoint='add_voucher_by_phone')
def add_voucher_by_phone(name, phone):
    symbols = app.config.get('VOUCHER_SYMBOLS', string.ascii_letters +
            string.digits)
    length = app.config.get('VOUCHER_LENGTH', 8)

    voucher = ''.join([symbols[random.randint(0, len(symbols)-1)] for x in
        xrange(length)])

    # save to radius db
    radcheck = models.RadCheck(username=voucher, attribute='Cleartext-Password',
            op=':=', value=voucher)
    db.session.add(radcheck)
    db.session.commit()

    # send to sms queue
    redis.rpush(app.config['SMS_KEY'], json.dumps(dict(Number=phone, 
        Text='Nomor voucher Wifi HotSpot: %s' % voucher)))
    return jsonify(status='OK', phone=phone, voucher=voucher)
