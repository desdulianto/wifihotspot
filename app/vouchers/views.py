"""
    wifihotspot.app.vouchers.views
    ------------------------------

    Vouchers views

    :copyright: (c) 2013 by Des Dulianto
"""

from flask import render_template, jsonify, flash, redirect, url_for, \
        request, current_app, render_template_string
from flask import make_response
from flask import Blueprint
from flask.ext.login import login_required

from flask.ext.paginate import Pagination

from werkzeug.exceptions import InternalServerError

from jinja2 import Markup
from sqlalchemy import and_, or_
from sqlalchemy.sql import func

import random
import string
import json
from subprocess import check_call
import os
from functools import wraps
from datetime import datetime, timedelta
import xlwt
from StringIO import StringIO

from app import app, db
import models
import forms


blueprint = Blueprint('vouchers', __name__)

def jsonp(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated_function

def generateVoucher():
    symbols = app.config.get('VOUCHER_SYMBOLS',
            'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ0123456789'
            )
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
    try:
        session_timeout = int((models.RadGroupReply.query.filter_by(
            groupname=app.config['RADIUS_GROUP']).filter_by(
                attribute='Session-Timeout').first()).value)
    except:
        session_timeout = 86400 # default session timeout 24 hours
    expiration = ((datetime.now() + timedelta(seconds=session_timeout)).
            strftime('%d %b %Y %H:%M'))
    expired = models.RadCheck(username=voucher, attribute='Expiration',
            op=':=', value=expiration)
    radgroup = models.RadUserGroup(username=voucher, groupname=groupname,
            priority=1)
    contact = addContact(name=name, phone=phone)
    radcheck.contact = contact
    expired.contact = contact
    db.session.add(radcheck)
    db.session.add(expired)
    db.session.add(radgroup)
    db.session.add(contact)
    db.session.commit()


def sendSMS(phone, text):
    ret = check_call(['gammu-smsd-inject', 'TEXT', phone, 
            '-text', text])


@blueprint.route('/', endpoint='index')
@login_required
def index():
    menus = [dict(title='Daftar Contact', url=url_for('.contact_list')),
             dict(title='Daftar Voucher', url=url_for('.voucher_list')),
             dict(title='Template Pesan',
             url=url_for('.edit_message_template'))]
    return render_template('module_index.html', menus=menus)


@blueprint.route('/<name>/<phone>', methods=['GET'],
        endpoint='voucher_service_new')
@jsonp
def voucher_service_new(name, phone):
    voucher = generateVoucher()

    # save to radius db
    addToRadius(voucher, name, phone, app.config['RADIUS_GROUP'])

    # send to sms queue
    try:
        voucher_message = open(app.config['VOUCHER_TEMPLATE_FILE'], 'r').read()
        sms_text = render_template_string(voucher_message, name=name,
                phone=phone, voucher=voucher)
    except IOError:
        raise InternalServerError(
            description='Cannot read voucher template file')
    sendSMS(phone, text=sms_text)
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

    vouchers = (models.RadCheck.query.filter_by(
        attribute='Cleartext-Password').outerjoin(models.Contact).
            order_by(models.Contact.name).
            order_by(models.Contact.phone))

    if q is not None:
        vouchers = vouchers.filter(or_( 
            models.RadCheck.username.like('%' + q +'%'),
            models.Contact.name.like('%' + q + '%'),
            models.Contact.phone.like('%' + q + '%') ))

    def getExpiration(voucher):
        expiration = (models.RadCheck.query.filter_by(
            username=voucher.username).filter_by(attribute='Expiration').first())
        if expiration is not None:
            expiration = expiration.value
        return expiration

    pagination = Pagination(page=page, total=vouchers.count(), search=False,
            record_name='vouchers', per_page=per_page, bs_version=3)
    return render_template('list.html',
            items=vouchers.limit(per_page).offset((page-1)*per_page).all(),
            columns=[dict(title='Nama', field=lambda x: x.contact.name if
                x.contact is not None else '-'),
                     dict(title='Telepon', field=lambda x: x.contact.phone if
                         x.contact is not None else '-'),
                     dict(title='No. Voucher', field='username'),
                     dict(title='Waktu Generate', field=lambda x:
                         '-' if x.time is None else x.time.strftime(
                             '%d %b %Y %H:%M')),
                     dict(title='Waktu Expired', field=lambda x:
                         getExpiration(x))],
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
    records = models.RadCheck.query.filter_by(username=voucher.username).all()
    for record in records:
        db.session.delete(record)
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
        with open(app.config['VOUCHER_TEMPLATE_FILE'], 'r') as f:
            form.message.data = f.read()
    if form.validate_on_submit():
        with open(app.config['VOUCHER_TEMPLATE_FILE'], 'w') as f:
            f.write(form.message.data)
        return redirect(url_for('.index'))
    return render_template('form_voucher_message.html', title='Format Pesan Voucher',
            fields=[('message', {'rows': 5})], form=form)


@blueprint.route('/contacts', methods=['GET'], endpoint='contact_list',
        defaults={'output': 'html'})
@blueprint.route('/contacts/<string:output>', methods=['GET'], endpoint='contact_list')
@login_required
def contact_list(output='html'):
    per_page=20
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    q = request.args.get('q', None)

    items = (models.Contact.query.order_by(models.Contact.name).
            order_by(models.Contact.phone))

    if q is not None:
        items = items.filter(or_(
            models.Contact.name.like('%' + q + '%'),
            models.Contact.phone.like('%' + q + '%')))

    if output == 'excel':
        return render_excel(items=items.all(), title='Daftar Contact',
                columns=[dict(title='Nama', field='name', width=6000),
                         dict(title='No. Telepon', field='phone', width=4000)])

    pagination = Pagination(page=page, total=items.count(), search=False,
            record_name='contacts', per_page=per_page, bs_version=3)

    return render_template('list.html', items=items.all(), title='Daftar Contact',
            columns=[dict(title='Nama', field='name'),
                     dict(title='No. Telepon', field='phone')],
            pagination=pagination, search=True,
            buttons=[dict(title='Export to Excel', url='.contact_list',
                url_params={'output': 'excel'})])


def render_excel(items, title='', columns=None):
    book = xlwt.Workbook()
    sheet = book.add_sheet(title)

    if columns is None:
        columns = []

    style = xlwt.easyxf('font: bold on, height 280;')
    sheet.row(0).height = 400
    align = xlwt.Alignment()
    align.horz = xlwt.Alignment.HORZ_CENTER
    style.alignment = align
    sheet.write_merge(0, 0, 0, len(columns), title, style)

    sheet.row(2).height = 300
    for i in xrange(len(columns)):
        style = xlwt.easyxf('font: bold on;')
        sheet.write(2, 1+i, columns[i]['title'], style) 
        if columns[i].get('width', False) is not False:
            sheet.col(1+i).width = columns[i]['width']
    sheet.col(0).width = 1500

    for i in xrange(len(items)):
        style = xlwt.easyxf()
        pattern = xlwt.Pattern()
        if (i+1) % 2 == 0:
            pattern.pattern = 0x12
            pattern.pattern_back_colour = 22
        else:
            pattern.pattern = 0x00
        style.pattern = pattern
        sheet.write(3+i, 0, i+1, style)
        for j in xrange(len(columns)):
            value = getattr(items[i], columns[j]['field'])
            sheet.write(3+i, 1+j, value, style)

    output = StringIO()
    book.save(output)

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/ms-excel'
    response.headers['Content-Disposition'] = \
            'attachment; filename=contact.xls'
    output.close()

    return response
