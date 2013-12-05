from flask import render_template, url_for, redirect
from flask import Blueprint

from app import app
import forms


blueprint = Blueprint('setup', __name__)

@blueprint.route('/', methods=['GET', 'POST'], endpoint='index')
def setup():
    form = forms.SetupForm()
    if form.validate_on_submit():
        pass
    return render_template('form_setup.html', form=form, title='Setup')
