from flask import Blueprint
from flask import request, url_for, redirect, render_template, g, flash
from flask.ext.login import login_user, logout_user, login_required
from flask.ext.paginate import Pagination

from werkzeug.exceptions import Forbidden

from app import app, login_manager, db

import forms
import models


blueprint = Blueprint('users', __name__)

@login_manager.user_loader
def load_user(userid):
    return models.User.query.get(userid)


# register login page to app (not in users blueprint)
@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    form = forms.LoginForm(formdata=request.form)
    if form.validate_on_submit():
        user = models.User.query.filter_by(name=form.name.data).first()
        if (user is None) or not user.password_check(form.password.data):
            form.errors['login'] = 'Nama User/Password salah'
        elif not user.is_active():
            form.errors['login'] = 'User tidak aktif'
        else:
            login_user(user)

            next_page = request.args.get('next', url_for('index'))

            return redirect(next_page)
    return render_template('login.html', form=form)


@app.route('/logout', methods=['GET'], endpoint='logout')
def logout():
    logout_user()

    return redirect(url_for('login'))


@blueprint.route('/', methods=['GET'], endpoint='index')
@login_required
def index():
    per_page = 20
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    users = models.User.query.order_by(models.User.name)

    pagination = Pagination(page=page, per_page=per_page, bs_version=3,
            total=users.count(), record_name='users', search=False)
    return render_template('list.html',
            items=users.limit(per_page).offset((page-1)*per_page).all(),
            columns=[dict(title='Nama User', field='name'),
                     dict(title='Active', field='active')],
            title='Daftar User',
            create_url='.new',
            edit_url='.edit',
            void_url='.delete')


@blueprint.route('/account', methods=['GET', 'POST'], endpoint='account')
@login_required
def user_account():
    user = g.user
    form = forms.ChangePasswordForm()
    if form.validate_on_submit():
        user.password_change(form.password.data)
        db.session.add(user)
        db.session.commit()

        next_page = getattr(request, 'referrer', url_for('index'))

        flash('Password telah diupdate!', 'success')
        return redirect(next_page)
    return render_template('form_complex.html', 
            title='Ubah Password {name}'.format(name=user.name),
            fields=['password', 'password_verify'], form=form)


@blueprint.route('/<int:id>', methods=['GET', 'POST'], endpoint='edit')
@login_required
def edit_user(id):
    if g.user.name != 'admin':
        raise Forbidden('Hanya admin yang dapat mengubah password')
    user = models.User.query.get_or_404(id)

    form = forms.ChangePasswordForm()
    if form.validate_on_submit():
        user.password_change(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Password {name} telah diupdate!'.format(name=user.name),
                'success')
        return redirect(url_for('.index'))
    return render_template('form_complex.html', 
            title='Ubah Password {name}'.format(name=user.name),
            fields=['password', 'password_verify'], form=form)


@blueprint.route('/new', methods=['GET', 'POST'], endpoint='new')
@login_required
def new_user():
    form = forms.UserForm(formdata=request.form)
    if form.validate_on_submit():
        user = models.User(name=form.name.data.strip(),
                password=models.User.password_hash(form.password.data))

        db.session.add(user)
        db.session.commit()
        flash('User {name} telah ditambahkan!'.format(name=user.name),
            'success')
        return redirect(url_for('.index'))
    return render_template('form_complex.html', form=form, 
            title='User Baru',
            fields=['name', 'password', 'password_verify'])


@blueprint.route('/delete/<int:id>', methods=['GET', 'POST'],
        endpoint='delete')
@login_required
def delete_user(id):
    user = models.User.query.get_or_404(id)

    if user.name == 'admin':
        flash('User admin tidak bisa dihapus!', 'warning')
    else:
        flash('User {name} telah dihapus!'.format(name=user.name), 'success')
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('.index'))
