from flask import render_template, jsonify
from flask import Blueprint

import random
import string

from app import app, db, redis
import models
import json


blueprint = Blueprint('vouchers', __name__)

def generateVoucher():
    symbols = app.config.get('VOUCHER_SYMBOLS', string.ascii_letters +
            string.digits)
    length = app.config.get('VOUCHER_LENGTH', 8)

    while True:
        voucher = ''.join([symbols[random.randint(0, len(symbols)-1)] for x in
            xrange(length)])
        if models.RadCheck.query.filter_by(username=voucher).first() == None:
            break
    return voucher


def addContact(name, phone):
    entry = models.Contact.query.get((name, phone))
    if entry is None:
        entry = models.Contact(name=name, phone=phone)
        db.session.add(entry)
        db.session.commit()
    return entry


def addToRadius(voucher, name, phone, groupname):
    radcheck = models.RadCheck(username=voucher, attribute='Cleartext-Password',
            op=':=', value=voucher)
    radgroup = models.RadUserGroup(username=voucher, groupname=groupname,
            priority=1)
    contact = addContact(name=name, phone=phone)
    radcheck.contact = contact
    db.session.add(radcheck)
    db.session.add(radgroup)
    db.session.add(contact)
    db.session.commit()


def sendSMS(phone, text):
    redis.rpush(app.config['SMS_KEY'], json.dumps(dict(Number=phone, 
        Text=text)))


@blueprint.route('/', endpoint='index')
def index():
    return render_template('index.html')


@blueprint.route('/<name>/<phone>', methods=['POST'], endpoint='add_voucher_by_phone')
def add_voucher_by_phone(name, phone):
    voucher = generateVoucher()

    # save to radius db
    addToRadius(voucher, name, phone, 'hotspot')

    # send to sms queue
    sendSMS(phone, text='Nomor voucher Wifi HotSpot: %s' % voucher)
    return jsonify(status='OK', phone=phone, voucher=voucher)
