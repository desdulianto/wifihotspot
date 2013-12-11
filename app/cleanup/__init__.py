import ConfigParser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.vouchers import models
from datetime import datetime, timedelta

from app import app, db

def cleanup():
    session_time = (models.RadGroupReply.query.
            filter_by(attribute='Session-Time').first())
    if session_time is None:
        session_time = 86400
    else:
        try:
            session_time = int(session_time.value)
        except:
            session_time = 86400
    # query 
    delta = timedelta(seconds=session_time)
    vouchers = (models.RadCheck.query.
            filter(models.RadCheck.time<=datetime.today()-delta).all())
    for voucher in vouchers:
        db.session.delete(voucher)
    db.session.commit()
