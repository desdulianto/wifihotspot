from app import db

class RadCheck(db.Model):
    __tablename__ = 'radcheck'
    __bind_key__ = 'radius'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), nullable=False, default='', index=True)
    attribute = db.Column(db.String(64), nullable=False, default='', index=True)
    op = db.Column(db.String(2), nullable=False, default='==')
    value = db.Column(db.String(253), nullable=False, default='')
