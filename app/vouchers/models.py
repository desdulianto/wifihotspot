from app import db
from datetime import datetime

class RadCheck(db.Model):
    __tablename__ = 'radcheck'
    __bind_key__ = 'radius'
    __table_args__ = (db.ForeignKeyConstraint(
                        ['name', 'phone'],
                        ['contact.name', 'contact.phone']),
                     )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), nullable=False, default='', index=True)
    attribute = db.Column(db.String(64), nullable=False, default='', index=True)
    op = db.Column(db.String(2), nullable=False, default='==')
    value = db.Column(db.String(253), nullable=False, default='')
    time = db.Column(db.DateTime, default=datetime.now)
    group = db.relationship('RadUserGroup', backref='user', cascade='delete',
        primaryjoin='RadCheck.username==RadUserGroup.username')
    name = db.Column(db.String(64)) 
    phone= db.Column(db.String(20))


class RadUserGroup(db.Model):
    __tablename__ = 'radusergroup'
    __bind_key__  = 'radius'
    username = db.Column(db.String(64), db.ForeignKey('radcheck.username'), nullable=False, 
            default='', index=True, primary_key=True, )
    groupname = db.Column(db.String(64), nullable=False, default='', index=True)
    priority = db.Column(db.Integer, nullable=False, default=0)


class Contact(db.Model):
    __tablename__ = 'contact'
    __bind_key__ = 'radius'
    name = db.Column(db.String(64), nullable=False, default='',
            primary_key=True)
    phone = db.Column(db.String(20), primary_key=True)
    vouchers = db.relationship('RadCheck', backref='contact')
