from flask import render_template, url_for, redirect, g
from flask.ext.login import current_user, login_required
from app import app


@app.before_request
def before_request():
    g.user = current_user


@app.route('/', endpoint='index')
@login_required
def index():
    return render_template('index.html')
