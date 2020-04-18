from flask import session, redirect, url_for
from functools import wraps

def login_required(fn):
    """
    Wrapper function for checking user is logged in.
    Redirects to login page if user is not in session.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user' in session:
            username = session['user']
            user_id = session['user_id']
            return fn(username, user_id, *args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrapper


def check_user_login(fn):
    """
    Wrapper function for checking user is logged in.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user' in session:
            username = session['user']
            user_id = session['user_id']
            return fn(username, user_id, *args, **kwargs)
        else:
            return fn(username=None, user_id=None, *args, **kwargs)

    return wrapper