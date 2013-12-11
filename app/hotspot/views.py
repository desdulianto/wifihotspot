from flask import render_template, redirect, url_for, request
from flask import Blueprint
from flask.ext.login import login_required

from werkzeug.exceptions import NotFound
from rosapi import RosAPIError

from app import app
from app import db
from app.vouchers import models as vouchers_models

import forms

blueprint = Blueprint('hotspot', __name__)

resource = '/ip/hotspot/active'

attributes_mapping = {'Mikrotik-Rate-Limit': 'Rate Limit (rx/tx)',
                      'Session-Timeout'    : 'Session Time (seconds)',
                      'Port-Limit'         : 'Max Session per-user',
                      'Mikrotik-Xmit-Limit': 'Download Quota (bytes)',
                      'Mikrotik-Recv-Limit': 'Upload Quota (bytes)'}


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
@login_required
def index():
    menus = [dict(title='Daftar User Online', url=url_for('.list')),
             dict(title='Hotspot Parameter',
             url=url_for('.group_attribute_list'))]
    return render_template('module_index.html', menus=menus)



@blueprint.route('/list', endpoint='list')
@login_required
def list_view():

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
@login_required
def detail_by_id(id):
    try:
        user = app.mikrotik.get_resource(resource).get(id=id)[0]
    except IndexError:
        raise NotFound()
    user['contact-name'], user['contact-phone'] = getContact(user)
    return render_template('hotspot_user_detail.html', user=user)


@blueprint.route('/disconnect/<id>', endpoint='disconnect_by_id')
@login_required
def disconnect_by_id(id):
    app.mikrotik.get_resource(resource).remove(id=id)
    return redirect(url_for('.list'))


@blueprint.route('/disconnect-remove/<id>', endpoint='disconnect_remove_by_id')
@login_required
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

    return redirect(url_for('.list'))


@blueprint.route('/disconnect/voucher/<id>', endpoint='disconnect_by_voucher')
@login_required
def disconnect_by_voucher(id):
    try:
        user = app.mikrotik.get_resource(resource).get(user=id)[0]
    except IndexError:
        raise NotFound()

    app.mikrotik.get_resource(resource).remove(id=user['id'])
    return redirect(url_for('.list'))


@blueprint.route('/group-attribute',
    endpoint='group_attribute_list')
@login_required
def group_attribute_list():
    attributes = (vouchers_models.RadGroupReply.query.
            filter_by(groupname=app.config['RADIUS_GROUP']).all())
    return render_template('list.html', title='Group Attribute',
            items=attributes,
            columns=[dict(title='Attribute', field=lambda x:
                attributes_mapping[x.attribute]),
                    dict(title='Value', field='value')],
            create_url='.edit_group_attribute')


def getAttribute(predicate, attributes):
    results = filter(lambda x: x.attribute == predicate, attributes) 
    if len(results) == 1:
        return results[0]
    elif len(results) == 0:
        return None
    else:
        return results


@blueprint.route('/group-attribute/edit', methods=['GET', 'POST'],
        endpoint='edit_group_attribute')
@login_required
def edit_group_attribute():
    form = forms.GroupAttributeForm()
    if request.method == 'GET':
        attributes = (vouchers_models.RadGroupReply.query.
                filter_by(groupname=app.config['RADIUS_GROUP']).all())
        form.mikrotikRateLimit.data = getattr(getAttribute('Mikrotik-Rate-Limit'
            , attributes), 'value', '')
        form.sessionTimeout.data = getattr(getAttribute('Session-Timeout',
            attributes), 'value', 0)
        form.portLimit.data = getattr(getAttribute('Port-Limit', attributes),
            'value', 0)
        form.mikrotikRecvLimit.data = getattr(getAttribute('Mikrotik-Recv-Limit'
            , attributes), 'value', 0)
        form.mikrotikXmitLimit.data = getattr(getAttribute('Mikrotik-Xmit-Limit'
            , attributes), 'value', 0)
    if form.validate_on_submit():
        attributes = (vouchers_models.RadGroupReply.query.
                filter_by(groupname=app.config['RADIUS_GROUP']).all())

        def update_attribute(attrname, predicate, data, attributes):
            attr = getAttribute(attrname, attributes)
            if predicate(data):
                if attr is not None:
                    db.session.delete(attr)
            else:
                if attr is None:
                    attr = vouchers_models.RadGroupReply(
                            groupname=app.config['RADIUS_GROUP'],
                            attribute=attrname,
                            op = ':=', value=data)
                else:
                    attr.value = data
                db.session.add(attr)

        update_attribute('Mikrotik-Rate-Limit',
                lambda x: x == 0, form.mikrotikRateLimit.data, attributes)
        update_attribute('Session-Timeout', lambda x: x == 0,
                form.sessionTimeout.data, attributes)
        update_attribute('Port-Limit', lambda x: x == 1,
                form.portLimit.data, attributes)
        update_attribute('Mikrotik-Recv-Limit', lambda x: x == 0,
                form.mikrotikRecvLimit.data, attributes)
        update_attribute('Mikrotik-Xmit-Limit', lambda x: x == 0,
                form.mikrotikXmitLimit.data, attributes)

        db.session.commit()

        return redirect(url_for('.group_attribute_list'))

    return render_template('form_complex.html', title='Group Attribute',
            fields=['mikrotikRateLimit', 'sessionTimeout', 'portLimit', 
                'mikrotikRecvLimit', 'mikrotikXmitLimit'], form=form)
