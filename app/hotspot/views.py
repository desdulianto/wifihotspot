from flask import render_template, redirect, url_for
from flask import Blueprint

from werkzeug.exceptions import NotFound
from rosapi import RosAPIError

from app import app
from app import db
from app.vouchers import models as vouchers_models

blueprint = Blueprint('hotspot', __name__)

resource = '/ip/hotspot/active'

def getContact(voucher):
    radcheck = (vouchers_models.RadCheck.query.
            filter(vouchers_models.RadCheck.username==voucher['user']).first())
    if radcheck is not None:
        name = (radcheck.contact.name if radcheck.contact is not None else
                '')
        phone = (radcheck.contact.phone if radcheck.contact is not None else '')
    else:
        name, phone = '', ''

    return (name, phone)


@blueprint.route('/', endpoint='index')
def index():

    active_users = app.mikrotik.get_resource(resource).get()
    for user in active_users:
        user['contact-name'], user['contact-phone'] = getContact(user)
    return render_template('list.html', title='Hotspot User',
            items=active_users,
            columns=[
                dict(title='Name', field=lambda x: x['contact-name']),
                dict(title='Phone', field=lambda x: x['contact-phone']),
                dict(title='Voucher', field=lambda x: x['user']),
                dict(title='Address', field=lambda x: x['address']),
                dict(title='Hotspot', field=lambda x: x['server']),
                dict(title='Uptime', field=lambda x: x['uptime']),
                ], void_url='.disconnect_by_id',
                edit_url='.detail_by_id')


@blueprint.route('/<id>', endpoint='detail_by_id')
def detail_by_id(id):
    try:
        user = app.mikrotik.get_resource(resource).get(id=id)[0]
    except IndexError:
        raise NotFound()
    user['contact-name'], user['contact-phone'] = getContact(user)
    return render_template('hotspot_user_detail.html', user=user)


@blueprint.route('/disconnect/<id>', endpoint='disconnect_by_id')
def disconnect_by_id(id):
    app.mikrotik.get_resource(resource).remove(id=id)
    return redirect(url_for('.index'))


@blueprint.route('/disconnect-remove/<id>', endpoint='disconnect_remove_by_id')
def disconnect_remove_by_id(id):
    try:
        user = app.mikrotik.get_resource(resource).get(id=id)[0]
        radcheck = (vouchers_models.RadCheck.query.
                filter_by(username=user['user']).first())
    except IndexError:
        raise NotFound()

    app.mikrotik.get_resource(resource).remove(id=id)
    if radcheck is not None:
        db.session.delete(radcheck)
        db.session.commit()

    return redirect(url_for('.index'))


@blueprint.route('/disconnect/voucher/<id>', endpoint='disconnect_by_voucher')
def disconnect_by_voucher(id):
    try:
        user = app.mikrotik.get_resource(resource).get(user=id)[0]
    except IndexError:
        raise NotFound()

    app.mikrotik.get_resource(resource).remove(id=user['id'])
    return redirect(url_for('.index'))
