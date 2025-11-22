from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, abort

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Not logged in ⇒ send to login page
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # Logged in but not admin ⇒ forbidden
        if not current_user.is_admin:
            return abort(403)  # 403 Forbidden

        # Logged in AND admin ⇒ continue
        return f(*args, **kwargs)

    return decorated_function
