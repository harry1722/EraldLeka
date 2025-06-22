from functools import wraps
from flask import redirect, url_for, flash, session, request, jsonify

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user') != 'admin':
            if request.is_json or request.method in ['POST', 'DELETE', 'PUT']:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
            flash("Access denied", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def unread_count():
    # Import brenda funksionit për të shmangur circular import
    from app.models import Message
    unread = Message.query.filter_by(is_read=False).count()
    return dict(unread_count=unread)

