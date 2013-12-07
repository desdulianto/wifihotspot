from hashlib import sha1
from flask.ext.login import UserMixin
from app import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    password = db.Column(db.String(40), nullable=False)
    active = db.Column(db.Boolean, default=True)

    @staticmethod
    def password_hash(password):
        return sha1(password).hexdigest()

    def password_check(self, password):
        return self.password == User.password_hash(password)

    def password_change(self, password):
        self.password = User.password_hash(password)

    def is_active(self):
        return self.active

    def __repr__(self):
        return '<User %r>' % self.name
