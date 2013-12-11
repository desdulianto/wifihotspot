"""
    wifihotspot.app.vouchers.views
    ------------------------------

    Vouchers views

    :copyright: (c) 2013 by Des Dulianto
"""

from flask import render_template, jsonify, flash, redirect, url_for, request
from flask import Blueprint
from flask.ext.login import login_required

from flask.ext.paginate import Pagination

from jinja2 import Markup
from sqlalchemy import and_, or_
from sqlalchemy.sql import func

import random
import string
import json
from subprocess import check_call
import os

from app import app, db
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
    name = name.strip().lower()
    phone = phone.strip()
    entry = models.Contact.query.filter(and_(models.Contact.name == name,
                models.Contact.phone == phone)).first()
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
    ret = check_call(['gammu-smsd-inject', 'TEXT', phone, 
            '-text', text])


@blueprint.route('/', endpoint='index')
@login_required
def index():
    menus = [dict(title='Daftar Voucher', url=url_for('.voucher_list')),
             dict(title='Template Pesan',
             url=url_for('.edit_message_template'))]
    return render_template('module_index.html', menus=menus)


@blueprint.route('/<name>/<phone>', methods=['GET'],
        endpoint='voucher_service_new')
def voucher_service_new(name, phone):
    voucher = generateVoucher()

    # save to radius db
    addToRadius(voucher, name, phone, app.config['RADIUS_GROUP'])

    # send to sms queue
    sms_text = render_template('voucher_message.txt', name=name, phone=phone,
            voucher=voucher)
    #sendSMS(phone, text=sms_text)
    return jsonify(status='OK', phone=phone, voucher=voucher)


@blueprint.route('/list', methods=['GET'], endpoint='voucher_list')
@login_required
def voucher_list():
    per_page=20
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    q = request.args.get('q', None)

    vouchers = (models.RadCheck.query.outerjoin(models.Contact).
            order_by(models.Contact.name).
            order_by(models.Contact.phone))

    if q is not None:
        vouchers = vouchers.filter(or_( 
            models.RadCheck.username.like('%' + q +'%'),
            models.Contact.name.like('%' + q + '%'),
            models.Contact.phone.like('%' + q + '%') ))

    pagination = Pagination(page=page, total=vouchers.count(), search=False,
            record_name='vouchers', per_page=per_page, bs_version=3)
    return render_template('list.html',
            items=vouchers.limit(per_page).offset((page-1)*per_page).all(),
            columns=[dict(title='Nama', field=lambda x: x.contact.name if
                x.contact is not None else '-'),
                     dict(title='Telepon', field=lambda x: x.contact.phone if
                         x.contact is not None else '-'),
                     dict(title='No. Voucher', field='username'),
                     dict(title='Waktu Generate', field='time')],
            title='Daftar Voucher',
            void_url='.voucher_delete', 
            create_url='.voucher_new',
            confirm_void=\
            'Yakin hapus (user yang sedang online akan di-disconnect)?',
            pagination=pagination,
            search=True)


@blueprint.route('/new', methods=['GET', 'POST'], endpoint='voucher_new')
@login_required
def voucher_new():
    form = forms.VoucherForm()
    if form.validate_on_submit():
        voucher = generateVoucher()
        addToRadius(voucher, form.name.data, form.phone.data,
            app.config['RADIUS_GROUP']) 
        flash(Markup(
        '<h1>Voucher untuk <strong>{name} ({phone}): {voucher}</strong></h1>'.
                format(name=form.name.data.title(), phone=form.phone.data,
                    voucher=voucher)), 'success')
        return redirect(url_for('.voucher_list'))
    return render_template('form_complex.html', form=form,
            fields=['name', 'phone'], title='Voucher Baru')


@blueprint.route('/delete/<int:id>', methods=['GET', 'POST'], endpoint='voucher_delete')
@login_required
def voucher_delete(id):
    voucher = models.RadCheck.query.get_or_404(id)
    try:
        user = app.mikrotik.get_resource('/ip/hotspot/active').get(user=voucher.username)[0]
    except IndexError:
        pass
    else:
        try:
            app.mikrotik.get_resource('/ip/hotspot/active').remove(id=user['id'])
        except:
            pass
    db.session.delete(voucher)
    db.session.commit()
    flash(Markup(
        '<h1>Voucher {voucher} telah dihapus!</h1>'.
        format(voucher=voucher.username)), 'success')
    return redirect(url_for('.voucher_list'))


@blueprint.route('/template', methods=['GET', 'POST'],
        endpoint='edit_message_template')
@login_required
def edit_message_template():
    form = forms.VoucherMessageForm()
    if request.method == 'GET':
        with app.open_resource('templates/voucher_message.txt') as f:
            form.message.data = f.read()
    if form.validate_on_submit():
        with open(os.path.join(app.root_path, 'templates/voucher_message.txt'),
            'w') as f:
            f.write(form.message.data)
        return redirect(url_for('.index'))
    return render_template('form_voucher_message.html', title='Format Pesan Voucher',
            fields=[('message', {'rows': 5})], form=form)
