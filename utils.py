from flask import session, redirect, url_for
from functools import wraps

def login_required(fn):
    """
    Wrapper function for checking user is logged in.
    Redirects to login page if user is not in session.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'customer_username' in session:
            customer_username = session['customer_username']
            customer_id = session['customer_id']
            return fn(customer_username, customer_id, *args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrapper


def check_user_login(fn):
    """
    Wrapper function for checking user is logged in.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'customer_username' in session:
            customer_username = session['customer_username']
            customer_id = session['customer_id']
            return fn(customer_username, customer_id, *args, **kwargs)
        else:
            return fn(customer_username=None, customer_id=None, *args, **kwargs)

    return wrapper