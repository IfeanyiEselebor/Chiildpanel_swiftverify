import binascii
import datetime
import os
import uuid
from functools import wraps

from flask import session, request, make_response, redirect, url_for, jsonify

from db_conn import db_start, User, Admin


def rememberme_token():
    db, cur = db_start()
    while True:
        remember_me_token = binascii.hexlify(os.urandom(64)).decode('utf-8')
        # Check if the number already exists in the database
        cur.execute("SELECT COUNT(*) FROM user_tokens WHERE token = %s", (remember_me_token,))
        count = cur.fetchone()['COUNT(*)']
        # If the number doesn't exist, return it
        if count == 0:
            return remember_me_token.strip()


def set_user_session(user_id):
    session['logged_in'] = True
    session['session_id'] = str(uuid.uuid4())
    session['user_id'] = user_id

    db, cur = db_start()
    try:
        # Define the query
        query = "SELECT * FROM users WHERE user_id = %s"

        # Execute the query with the user_uid parameter
        cur.execute(query, (user_id,))

        # Fetch the result
        result = cur.fetchone()
        user = User(**result)
        session['username'] = user.username
        session['email'] = user.email
        session['apikey'] = user.api_key
        cur.execute("DELETE FROM active_sessions WHERE user_id = %s", (user_id,))
        cur.execute("INSERT INTO active_sessions (user_id, session_id) VALUES (%s, %s)",
                    (user_id, session['session_id']))
        db.commit()
    finally:
        cur.close()
        db.close()


def set_admin_session(admin_id):
    session['admin_logged_in'] = True
    session['session_id'] = str(uuid.uuid4())
    session['admin_id'] = admin_id

    db, cur = db_start()
    try:
        # Define the query
        query = "SELECT * FROM admin WHERE id = %s"

        # Execute the query with the user_uid parameter
        cur.execute(query, (admin_id,))

        # Fetch the result
        result = cur.fetchone()
        admin = Admin(**result)
        session['username'] = admin.username
        session['email'] = admin.email
        session['admin_type'] = admin.admin_type
        cur.execute("DELETE FROM active_sessions WHERE user_id = %s", (admin_id,))
        cur.execute("INSERT INTO active_sessions (user_id, session_id) VALUES (%s, %s)",
                    (admin_id, session['session_id']))
        db.commit()
    finally:
        cur.close()
        db.close()


def login_required(f):
    """
        Decorator function to check if a user is logged in before accessing a route.
        If the user is not logged in, they will be redirected to the login page.
        If the user has a remember me cookie, their session will be extended.

        Parameters:
        f (function): The function to be decorated.

        Returns:
        function: The decorated function.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in', False):
            remember_me_cookie = request.cookies.get('rememberme', None)
            if remember_me_cookie is not None:
                db, cur = db_start()
                try:
                    cur.execute("SELECT * FROM user_tokens WHERE token = %s", (remember_me_cookie,))
                    user_token_query = cur.fetchone()
                    if user_token_query:
                        user_token_expire = user_token_query['expiry']
                        if not user_token_expire < datetime.datetime.now():
                            set_user_session(user_token_query['user_id'])
                            rememberme_cookie = rememberme_token()
                            expires = datetime.datetime.now() + datetime.timedelta(days=30)
                            cur.execute("DELETE FROM user_tokens WHERE user_id = %s", (user_token_query['user_id'],))
                            cur.execute("INSERT INTO user_tokens (user_id, token, expiry) VALUES (%s, %s, %s)",
                                        (user_token_query['user_id'], rememberme_cookie, expires))
                            db.commit()
                            response = make_response(f(*args, **kwargs))
                            response.set_cookie('rememberme', rememberme_cookie, expires=expires)
                            response.headers.add('X-LocalStorage-Item', f'apikey={session["apikey"]}')
                            return response
                        else:
                            response = make_response(redirect(url_for('home.login')))
                            response.set_cookie('rememberme', '', expires=0)
                            response.headers.add('X-LocalStorage-Item', f'apikey={session["apikey"]}')
                            return response
                finally:
                    cur.close()
                    db.close()
            return redirect(url_for('home.login'))
        # Check if the current session is active
        db, cur = db_start()
        try:
            cur.execute("SELECT * FROM active_sessions WHERE user_id = %s AND session_id = %s",
                        (session.get('user_id'), session.get('session_id')))
            active_session = cur.fetchone()
            if not active_session:
                # If the session is not active, log out the user
                db, cur = db_start()
                try:
                    # Delete active sessions
                    query = "DELETE FROM active_sessions WHERE user_id = %s"
                    cur.execute(query, (session.get('user_id'),))

                    # Delete "remember me" tokens
                    query = "DELETE FROM user_tokens WHERE user_id = %s"
                    cur.execute(query, (session.get('user_id'),))

                    # Commit the changes
                    db.commit()
                finally:
                    cur.close()
                    db.close()

                session.clear()  # Clear all session variables
                return redirect(url_for('home.login'))
        finally:
            cur.close()
            db.close()
        return f(*args, **kwargs)

    return decorated_function


def login_required_query(f):
    """
        Decorator function to check if a user is logged in before accessing a route.
        If the user is not logged in, they will receive a 401 status code and the message "Login Required".
        If the user has a remember me cookie, their session will be extended.

        Parameters:
        f (function): The function to be decorated. This function should handle HTTP requests and return a response.

        Returns:
        function: The decorated function. This function will check if the user is logged in and handle the response accordingly.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in', False):
            remember_me_cookie = request.cookies.get('rememberme', None)
            if remember_me_cookie is not None:
                db, cur = db_start()
                try:
                    cur.execute("SELECT * FROM user_tokens WHERE token = %s", (remember_me_cookie,))
                    user_token_query = cur.fetchone()
                    if user_token_query:
                        user_token_expire = user_token_query['expiry']
                        if not user_token_expire < datetime.datetime.now():
                            set_user_session(user_token_query['user_id'])
                            rememberme_cookie = rememberme_token()
                            expires = datetime.datetime.now() + datetime.timedelta(days=30)
                            cur.execute("DELETE FROM user_tokens WHERE user_id = %s", (user_token_query['user_id'],))
                            cur.execute("INSERT INTO user_tokens (user_id, token, expiry) VALUES (%s, %s, %s)",
                                        (user_token_query['user_id'], rememberme_cookie, expires))
                            db.commit()
                            # Set a cookie in the response
                            resp = make_response(f(*args, **kwargs))
                            resp.set_cookie('rememberme', rememberme_cookie, expires=expires)
                            resp.headers.add('X-LocalStorage-Item', f'apikey={session["apikey"]}')
                            return resp
                        else:
                            return jsonify({'error': 'Login Required'}), 401
                finally:
                    cur.close()
                    db.close()
            return jsonify({'error': 'Login Required'}), 401
        # Check if the current session is active
        db, cur = db_start()
        try:
            cur.execute("SELECT * FROM active_sessions WHERE user_id = %s AND session_id = %s",
                        (session.get('user_id'), session.get('session_id')))
            active_session = cur.fetchone()
            if not active_session:
                db, cur = db_start()
                try:
                    # Delete active sessions
                    query = "DELETE FROM active_sessions WHERE user_id = %s"
                    cur.execute(query, (session.get('user_id'),))

                    # Delete "remember me" tokens
                    query = "DELETE FROM user_tokens WHERE user_id = %s"
                    cur.execute(query, (session.get('user_id'),))

                    # Commit the changes
                    db.commit()
                finally:
                    cur.close()
                    db.close()

                session.clear()  # Clear all session variables
                return redirect(url_for('home.login'))
        finally:
            cur.close()
            db.close()
        return f(*args, **kwargs)

    return decorated_function


def admin_login_required(f):
    """
        Decorator function to check if an admin user is logged in before accessing a route.
        If the admin user is not logged in, they will be redirected to the login page.
        If the admin user has a remember me cookie, their session will be extended.

        Parameters:
        f (function): The function to be decorated.

        Returns:
        function: The decorated function.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in', False):
            remember_me_cookie = request.cookies.get('rememberme', None)
            if remember_me_cookie is not None:
                db, cur = db_start()
                try:
                    cur.execute("SELECT * FROM admin_tokens WHERE token = %s", (remember_me_cookie,))
                    admin_token_query = cur.fetchone()
                    if admin_token_query:
                        user_token_expire = admin_token_query[2]
                        if not user_token_expire < datetime.datetime.now():
                            set_admin_session(admin_token_query['admin_id'])
                            rememberme_cookie = rememberme_token()
                            expires = datetime.datetime.now() + datetime.timedelta(days=30)
                            cur.execute("DELETE FROM admin_tokens WHERE admin_id = %s", (admin_token_query[3],))
                            cur.execute("INSERT INTO admin_tokens (admin_id, token, expiry) VALUES (%s, %s, %s)",
                                        (admin_token_query[3], rememberme_cookie, expires))
                            db.commit()
                            response = make_response(f(*args, **kwargs))
                            response.set_cookie('rememberme', rememberme_cookie, expires=expires)
                            return response
                        else:
                            response = make_response(redirect(url_for('auth.admin_login')))
                            response.set_cookie('rememberme', '', expires=0)
                            return response
                finally:
                    cur.close()
                    db.close()
            return redirect(url_for('auth.admin_login'))
        if not session.get('admin_type', False):
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_login_required_query(f):
    """
       Decorator function to check if an admin user is logged in before accessing a route.
       If the admin user is not logged in, they will be redirected to the login page.
       If the admin user has a remember me cookie, their session will be extended.

       Parameters:
       f (function): The function to be decorated.

       Returns:
       function: The decorated function. If the admin user is logged in and has the required permissions,
                 the original function will be executed. Otherwise, appropriate responses will be returned.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in', False):
            remember_me_cookie = request.cookies.get('rememberme', None)
            if remember_me_cookie is not None:
                db, cur = db_start()
                try:
                    cur.execute("SELECT * FROM admin_tokens WHERE token = %s", (remember_me_cookie,))
                    admin_token_query = cur.fetchone()
                    if admin_token_query:
                        admin_token_expire = admin_token_query[2]
                        if not admin_token_expire < datetime.datetime.now():
                            set_admin_session(admin_token_query['admin_id'])
                            rememberme_cookie = rememberme_token()
                            expires = datetime.datetime.now() + datetime.timedelta(days=30)
                            cur.execute("DELETE FROM admin_tokens WHERE admin_id = %s", (admin_token_query[3],))
                            cur.execute("INSERT INTO admin_tokens (admin_id, token, expiry) VALUES (%s, %s, %s)",
                                        (admin_token_query[3], rememberme_cookie, expires))
                            db.commit()
                            # Set a cookie in the response
                            resp = make_response(f(*args, **kwargs))
                            resp.set_cookie('rememberme', rememberme_cookie, expires=expires)
                            return resp
                        else:
                            return "Login Required", 401
                finally:
                    cur.close()
                    db.close()
            return "Login Required", 401
        if not session.get('admin_type', False):
            return "Login Required", 403
        return f(*args, **kwargs)

    return decorated_function
