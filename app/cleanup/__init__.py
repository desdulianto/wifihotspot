import ConfigParser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.vouchers import models
from datetime import datetime, timedelta

from app import app, db

# read config
config = ConfigParser.ConfigParser()
config.read('config.ini')
CONFIG = dict()

def databaseStartup():
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    session = sessionmaker(bind=engine)
    return session()


def cleanup():
    session = databaseStartup()

    # query 
    days = timedelta(minutes=1)
    vouchers = (models.RadCheck.query.
            filter(models.RadCheck.time<=datetime.today()-days).all())
    for voucher in vouchers:
        db.session.delete(voucher)
    db.session.commit()
