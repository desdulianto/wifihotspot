from flask import g, url_for
from app import app


@app.before_request
def before_request():
    if getattr(g, 'menus', None) is None:
        g.menus = []
    g.menus.append( dict(title='Vouchers', url=url_for('vouchers.index')))
