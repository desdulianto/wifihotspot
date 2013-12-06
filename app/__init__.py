from flask import Flask, render_template, g, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.principal import Principal, Permission, RoleNeed, \
    PermissionDenied
from flask.ext.login import LoginManager
from werkzeug.exceptions import InternalServerError

import sqlalchemy.exc


app = Flask(__name__)

# load templates custom filters and test
import templates

# check config.py if no config.py then call setup views
try:
    open('config.ini', 'r')
    app.config['SETUP'] = False
except IOError:
    # generate temporary secret key
    import random
    import string
    s = string.ascii_letters + string.digits
    app.config['SECRET_KEY'] = ''.join([s[random.randint(0, len(s)-1)] for x in
        xrange(1024/8)])

    app.config['SETUP'] = True


# read config
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('config.ini')

# flask
app.config['SECRET_KEY'] = config.get('flask', 'SECRET_KEY')

# mikrotik
app.config['MIKROTIK_HOST'] = config.get('mikrotik', 'host')
app.config['MIKROTIK_USER'] = config.get('mikrotik', 'user')
app.config['MIKROTIK_PASSWORD'] = config.get('mikrotik', 'password')

# radius
app.config['RADIUS_DBTYPE'] = config.get('radius', 'dbtype')
app.config['RADIUS_HOST'] = config.get('radius', 'host')
app.config['RADIUS_DBNAME'] = config.get('radius', 'dbname')
app.config['RADIUS_USER'] = config.get('radius', 'user')
app.config['RADIUS_PASSWORD'] = config.get('radius', 'password')

# sms
app.config['SMS_HOST'] = config.get('sms', 'host')
app.config['SMS_USER'] = config.get('sms', 'user')
app.config['SMS_PASSWORD'] = config.get('sms', 'password')


# initialize db
db = SQLAlchemy(app)

# load login extensions
login_manager = LoginManager(app)
principal = Principal(app)

# handle exceptions
@app.errorhandler(PermissionDenied)
def permission_denied_page(error):
    app.logger.warning(error.message)

    return render_template('error.html', message='Permission Denied',
            sub='You don\'t have permission to view this page'), 403


@app.errorhandler(404)
def not_found(error):
    app.logger.warning(error.message)
    return render_template('error.html', message='Not Found', 
            sub='The page you\'re looking for is not found'), 404


@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error(error)
    return render_template('error.html', 
            message='Sorry, something happened on server', 
            sub='The admin is already notified. Please try again in the \
            moment'), 500


@app.errorhandler(sqlalchemy.exc.SQLAlchemyError)
def sqlalchemy_invalid_request_error(error):
    import traceback
    db.session.rollback()
    app.logger.error(traceback.format_exc())
    return render_template('error.html',
            message='Sorry, something happened on server!',
            sub='The admin has already notified. Please try again in a \
            moment'), 500


@app.errorhandler(Exception)
def default_exception(error):
    import traceback
    app.logger.error(traceback.format_exc())
    return render_template('error.html',
            message='Sorry, something happened on server!',
            sub='The admin has already notified. Please try again in a \
            moment'), 500


# init logging
if not app.debug:
    import logging
    from logging import Formatter
    from logging.handlers import SMTPHandler, RotatingFileHandler
    file_handler = RotatingFileHandler(filename='access.log',
        maxBytes=1073741824, backupCount=10)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
            ))
    app.logger.addHandler(file_handler)

# views
import views
from setup.views import blueprint as setup_blueprint

app.register_blueprint(setup_blueprint, url_prefix='/setup')

