"""
    wifihotspot.app.vouchers.views
    ------------------------------

    Vouchers views

    :copyright: (c) 2013 by Des Dulianto
"""

from flask import render_template, jsonify, flash, redirect, url_for, request
from flask import Blueprint

from flask.ext.paginate import Pagination

from jinja2 import Markup
from sqlalchemy.sql import func

import random
import string
import json

from app import app, db, redis
import models
import forms


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
    name = name.strip().title()
    phone = phone.strip()
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


@blueprint.route('/<name>/<phone>', methods=['POST'],
        endpoint='voucher_service_new')
def voucher_service_new(name, phone):
    voucher = generateVoucher()

    # save to radius db
    addToRadius(voucher, name, phone, 'hotspot')

    # send to sms queue
    #sendSMS(phone, text='Nomor voucher Wifi HotSpot: %s' % voucher)
    return jsonify(status='OK', phone=phone, voucher=voucher)


@blueprint.route('/list', methods=['GET'], endpoint='voucher_list')
def voucher_list():
    per_page=20
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    vouchers = (models.RadCheck.query.order_by(models.RadCheck.name).
            order_by(models.RadCheck.phone))

    pagination = Pagination(page=page, total=vouchers.count(), search=False,
            record_name='vouchers', per_page=per_page, bs_version=3)
    return render_template('list.html',
            items=vouchers.limit(per_page).offset((page-1)*per_page).all(),
            columns=[dict(title='Nama', field=lambda x: x.contact.name),
                     dict(title='Telepon', field=lambda x: x.contact.phone),
                     dict(title='No. Voucher', field='username'),
                     dict(title='Waktu Generate', field='time')],
            title='Daftar Voucher',
            void_url='.voucher_delete', 
            create_url='.voucher_new',
            confirm_void=\
            'Yakin hapus (user yang sedang online akan di-disconnect)?',
            pagination=pagination)


@blueprint.route('/new', methods=['GET', 'POST'], endpoint='voucher_new')
def voucher_new():
    form = forms.VoucherForm()
    if form.validate_on_submit():
        voucher = generateVoucher()
        addToRadius(voucher, form.name.data, form.phone.data, 'hotspot') 
        flash(Markup(
        '<h1>Voucher untuk <strong>{name} ({phone}): {voucher}</strong></h1>'.
                format(name=form.name.data.title(), phone=form.phone.data,
                    voucher=voucher)), 'success')
        return redirect(url_for('.voucher_list'))
    return render_template('form_complex.html', form=form,
            fields=['name', 'phone'], title='Voucher Baru')


@blueprint.route('/delete/<int:id>', methods=['GET', 'POST'], endpoint='voucher_delete')
def voucher_delete(id):
    voucher = models.RadCheck.query.get_or_404(id)
    db.session.delete(voucher)
    db.session.commit()
    flash(Markup(
        '<h1>Voucher {voucher} telah dihapus!</h1>'.
        format(voucher=voucher.username)), 'success')
    return redirect(url_for('.voucher_list'))
