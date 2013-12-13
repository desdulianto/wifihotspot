from flask import render_template, redirect, url_for, request
from flask import Blueprint
from flask.ext.login import login_required

from werkzeug.exceptions import NotFound
from rosapi import RosAPIError
from sqlalchemy import or_

from app import app
from app import db
from app.vouchers import models as vouchers_models

import forms

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
@login_required
def index():
    menus = [dict(title='Daftar User Online', url=url_for('.list')),
             dict(title='Hotspot Parameter',
             url=url_for('.group_attribute_list')),
             dict(title='Hotspot Bypass/Block', url=url_for('.ip_bindings_list'))]
    return render_template('module_index.html', menus=menus)



@blueprint.route('/list', endpoint='list')
@login_required
def list_view():
    form = forms.OnlineUserFilterForm(formdata=request.args)
    kwargs = dict()
    username = None
    phone = None
    for key, value in request.args.iteritems():
        if value == '':
            continue
        elif key == 'username':
            username = value.lower()
        elif key == 'phone':
            phone = value.lower()
        else:
            kwargs[key] = value

    query = vouchers_models.Contact.query
    if username is not None:
        query = query.filter_by(name=username)
    if phone is not None:
        query = query.filter_by(phone=phone)

    active_users = []
    if username is not None or phone is not None:
        for contact in query.all():
            for voucher in contact.vouchers:
                active_users.extend(
                        app.mikrotik.get_resource(resource).get(user=voucher.username))
    else:
        active_users.extend(
                app.mikrotik.get_resource(resource).get(**kwargs))
    for user in active_users:
        user['contact-name'], user['contact-phone'] = getContact(user)
    return render_template('online_user_list.html', title='Hotspot User',
            items=active_users,
            columns=[
                dict(title='Name', field=lambda x: x['contact-name']),
                dict(title='Phone', field=lambda x: x['contact-phone']),
                dict(title='Voucher', field=lambda x: x['user']),
                dict(title='Address', field=lambda x: x['address']),
                dict(title='Hotspot', field=lambda x: x['server']),
                dict(title='Uptime', field=lambda x: x['uptime']),
                ], void_url='.disconnect_by_id',
                edit_url='.detail_by_id', form=form)


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
    attributes_mapping = {'Mikrotik-Rate-Limit': 'Rate Limit (rx/tx)',
                        'Session-Timeout'    : 'Session Time (seconds)',
                        'Port-Limit'         : 'Max Session per-user',
                        'Mikrotik-Xmit-Limit': 'Download Quota (bytes)',
                        'Mikrotik-Recv-Limit': 'Upload Quota (bytes)'}

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
            'value', 1)
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
                            attribute=attrname.strip(),
                            op = ':=', value=data.strip())
                else:
                    attr.value = data
                db.session.add(attr)

        update_attribute('Mikrotik-Rate-Limit',
                lambda x: x == '', form.mikrotikRateLimit.data, attributes)
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


@blueprint.route('/ip-bindings', methods=['GET'], endpoint='ip_bindings_list')
@login_required
def ip_bindings_list():
    bindings = app.mikrotik.get_resource('/ip/hotspot/ip-binding').get()
    return render_template('list.html', title='IP Bindings',
            items=bindings,
            columns=[
                dict(title='Address', field=lambda x: x.get('mac-address',
                    False) or x.get('address')),
                dict(title='Type', field=lambda x: x.get('type', 'regular')),
                dict(title='Server', field=lambda x: x.get('server', 'all')),
                dict(title='Comment', field=lambda x: x.get('comment', '')),
                dict(title='Enabled', field=lambda x: x['disabled'] == 'false')
                ],
                create_url='.ip_bindings_new',
                void_url='.ip_bindings_delete',
                edit_url='.ip_bindings_edit'
            )


@blueprint.route('/ip-bindings/new', methods=['GET', 'POST'],
        endpoint='ip_bindings_new')
@login_required
def ip_bindings_new():
    form = forms.IpBindingForm()
    servers = app.mikrotik.get_resource('/ip/hotspot').get()
    form.server.choices = [('all', 'all')]
    form.server.choices.extend([(x['name'], x['name']) for x in servers])
    if form.validate_on_submit():
        kwargs = dict()
        if form.address_type.data == 'ip':
            kwargs['address'] = form.address.data.strip()
        else:
            kwargs['mac-address'] = form.address.data.strip().replace('-', ':')
        kwargs['type'] = form.type.data.strip()
        if form.server.data.strip() != '':
            kwargs['server'] = form.server.data.strip()

        res = app.mikrotik.get_resource('/ip/hotspot/ip-binding')
        res.add(**kwargs)
        return redirect(url_for('.ip_bindings_list'))
    return render_template('form_complex.html', title='New Host Bypass/Block',
            fields=[('Host Address', ['address_type', 'address']), 'server',
                'type', 'comment'], form=form)


@blueprint.route('/ip-bindings/delete/<id>', methods=['GET'],
        endpoint='ip_bindings_delete')
@login_required
def ip_binding_delete(id):
    res = app.mikrotik.get_resource('/ip/hotspot/ip-binding')
    res.remove(id=id)
    return redirect(url_for('.ip_bindings_list'))


@blueprint.route('/ip-bindings/<id>', methods=['GET', 'POST'],
        endpoint='ip_bindings_edit')
@login_required
def ip_bindings_edit(id):
    res = app.mikrotik.get_resource('/ip/hotspot/ip-binding')
    form = forms.IpBindingForm(request.form)
    servers = app.mikrotik.get_resource('/ip/hotspot').get()
    form.server.choices = [('all', 'all')]
    form.server.choices.extend([(x['name'], x['name']) for x in servers])
    if request.method == 'GET':
        binding = res.get(id=id)
        if len(binding) == 0:
            raise NotFound
        binding = binding[0]
        form.address.data = (binding.get('mac-address', False) or
            binding.get('address'))
        form.type.data = binding.get('type')
        if binding.get('mac-address', False):
            form.address_type.data = 'mac'
        else:
            form.address_type.data = 'ip'
        form.server.data = binding.get('server', '')
        form.comment.data = binding.get('comment', '')
        form.enabled.data = binding.get('disabled', 'false') == 'false'
    if form.validate_on_submit():
        kwargs = dict(id=id)
        if form.address_type.data == 'ip':
            kwargs['mac-address'] = '0:0:0:0:0:0'
            kwargs['address'] = form.address.data.strip()
        else:
            kwargs['address'] = '0.0.0.0'
            kwargs['mac-address'] = form.address.data.strip().replace('-', ':')
        kwargs['type'] = form.type.data.strip()
        if form.server.data.strip() != '':
            kwargs['server'] = form.server.data.strip()
        kwargs['disabled'] = 'false' if form.enabled.data else 'true'
        kwargs['comment'] = form.comment.data

        print kwargs

        res = app.mikrotik.get_resource('/ip/hotspot/ip-binding')
        res.set(**kwargs)
        return redirect(url_for('.ip_bindings_list'))
    return render_template('form_complex.html', title='Edit Host Bypass/Block',
            fields=[('Host Address', ['address_type', 'address']), 'server',
                'type', 'comment', 'enabled'], form=form)
