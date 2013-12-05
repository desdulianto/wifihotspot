from flask import render_template, url_for, redirect
from app import app

@app.route('/setup', endpoint='setup')
def setup():
    if not app.config['SETUP']:
        return redirect(url_for('index'))
    return render_template('setup.html') 
