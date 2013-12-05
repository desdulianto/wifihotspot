from flask import render_template, url_for, redirect
from app import app


@app.route('/', endpoint='index')
def index():
    if app.config['SETUP']:
        return redirect(url_for('setup.index'))
    return render_template('index.html')
