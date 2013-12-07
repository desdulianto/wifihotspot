from flask import Blueprint
from flask import request, url_for, redirect, render_template
from flask.ext.login import login_user, logout_user

from app import app, login_manager

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
