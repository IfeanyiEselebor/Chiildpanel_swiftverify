import datetime

import mysql.connector
import random
import secrets
import smtplib
import socket
import string
import time
from config import get_config_value
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import Blueprint, request, jsonify, session, make_response, redirect, url_for, render_template

from LoginManager.login_manager import set_user_session, set_admin_session, rememberme_token
from db_conn import db_start, User, Admin
from extension import bcrypt

auth = Blueprint('auth', __name__)


@auth.route('/admin/login', methods=['GET'])
def admin_login():
    if not session.get('admin_logged_in', False) and not session.get('admin_type', False):
        return render_template("admin/admin_login.html", SITE_NAME=get_config_value("SITE_NAME"))
    else:
        return redirect(url_for('user.user_dashboard'))


@auth.route('/login_admin', methods=['POST'])
def login_admin():
    data = request.get_json()
    admin_uid = data['username']
    password = data['password']
    remember_me = data['remember_me']
    db, cur = db_start()
    if db is None:
        return jsonify({'status': "Database connection failed"}), 500
    try:
        # Define the query
        query = "SELECT * FROM admin WHERE username = %s OR email = %s"

        # Execute the query with the user_uid parameter
        cur.execute(query, (admin_uid, admin_uid))

        # Fetch the result
        result = cur.fetchone()

        if result is None:
            return jsonify({
                'status': "Username or password not correct"
            }), 200
        else:
            admin = Admin(**result)
            if bcrypt.check_password_hash(admin.password.encode('utf-8'), password.encode('utf-8')):
                set_admin_session(admin.id)
                if remember_me is True:
                    rememberme_cookie = rememberme_token()
                    expires = datetime.datetime.now() + datetime.timedelta(days=30)
                    cur.execute("DELETE FROM admin_tokens WHERE admin_id = %s", (session['admin_id'],))
                    cur.execute("INSERT INTO admin_tokens (admin_id, token, expiry) VALUES (%s, %s, %s)",
                                (session['admin_id'], rememberme_cookie, expires))
                    db.commit()
                    return jsonify({
                        'status': "Login Successful",
                        'rememberme': rememberme_cookie
                    }), 200
                else:
                    return jsonify({
                        'status': "Login Successful",
                        'rememberme': ""
                    }), 200
            else:
                return jsonify({
                    'status': "Username or password not correct"
                }), 200
    finally:
        cur.close()
        db.close()


@auth.route('/login-user', methods=['POST'])
def login_user():
    data = request.get_json()
    user_uid = data['username']
    password = data['password']
    db, cur = db_start()
    try:
        # Define the query
        query = "SELECT * FROM users WHERE username = %s OR email = %s"

        # Execute the query with the user_uid parameter
        cur.execute(query, (user_uid, user_uid))

        # Fetch the result
        result = cur.fetchone()
        if result is None:
            return jsonify({
                'status': "User not Found"
            }), 200
        user = User(**result)
        if user.user_status == '0':
            return jsonify({
                'status': "User has been ban",
                'data': user.reason
            }), 200
        else:
            if bcrypt.check_password_hash(user.password.encode('utf-8'), password.encode('utf-8')):
                set_user_session(user.user_id)
                if not session['apikey']:
                    while True:
                        api_key = secrets.token_urlsafe(30)
                        cur.execute("SELECT 1 FROM users WHERE api_key = %s", (api_key,))
                        if cur.fetchone() is None:
                            break
                    session['apikey'] = api_key
                    cur.execute("UPDATE users SET api_key = %s WHERE user_id = %s",
                                (session['apikey'], session['user_id']))
                    db.commit()
                return jsonify({
                    'status': "Login Successful",
                    "temp_password": f"{True if user.temp_password_status == 1 else False if user.temp_password_status == 0 else False}",
                    'rememberme': "",
                    'apiKey': session['apikey'],
                    'url': '/dashboard'
                }), 200
            else:
                return jsonify({
                    'status': "Username or password not correct"
                }), 200
    finally:
        cur.close()
        db.close()


@auth.route('/logout', methods=['GET'])
def logout():
    db, cur = db_start()
    try:
        if not session.get('logged_in', False):
            session.clear()  # Clear all session variables

            response = make_response(redirect(url_for('auth.admin_login')))
            response.set_cookie('rememberme', '', expires=0)
            return response
        if not session.get('admin_type', False):
            # Delete active sessions
            query = "DELETE FROM active_sessions WHERE user_id = %s"
            cur.execute(query, (session['user_id'],))

            # Delete "remember me" tokens
            query = "DELETE FROM user_tokens WHERE user_id = %s"
            cur.execute(query, (session['user_id'],))

            # Commit the changes
            db.commit()
            session.clear()  # Clear all session variables

            response = make_response(redirect(url_for('home.login')))
            response.set_cookie('rememberme', '', expires=0)
            return response
        else:
            # Delete active sessions
            query = "DELETE FROM active_sessions WHERE user_id = %s"
            cur.execute(query, (session['admin_id'],))

            # Delete "remember me" tokens
            query = "DELETE FROM admin_tokens WHERE admin_id = %s"
            cur.execute(query, (session['admin_id'],))

            # Commit the changes
            db.commit()

            session.clear()  # Clear all session variables

            response = make_response(redirect(url_for('auth.admin_login')))
            response.set_cookie('rememberme', '', expires=0)
            return response
    finally:
        cur.close()
        db.close()


@auth.route('/register-user', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data['username']
    email = data['email']
    password = data['password']
    if username == 'admin':
        return jsonify({'success': False, 'message': 'Username already exists'}), 200
    db, cur = db_start()
    try:
        # Check if username exists
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Username already exists'}), 200

        # Check if email exists
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Email already exists'}), 200

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Generate Apikey for user
        while True:
            api_key = secrets.token_urlsafe(30)
            cur.execute("SELECT 1 FROM users WHERE api_key = %s", (api_key,))
            if cur.fetchone() is None:
                break
        apikey = api_key

        # Insert new user
        insert_query = """
                INSERT INTO users (username, password, email, wallet_balance, api_key)
                VALUES (%s, %s, %s, %s, %s)
                """
        user_data = (username, hashed_password, email, '0.00', apikey)

        cur.execute(insert_query, user_data)
        db.commit()
        return jsonify({'success': True, 'message': 'User Registration Successfully'}), 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()


def send_email(subject, recipients, template, **kwargs):
    # SMTP Configuration
    SMTP_SERVER = get_config_value("SMTP_SERVER")
    SMTP_PORT = get_config_value("SMTP_PORT")  # Typically 587 for TLS or 465 for SSL
    SMTP_USERNAME = get_config_value("SMTP_USERNAME")
    SMTP_PASSWORD = get_config_value("SMTP_PASSWORD")

    """Send an email using smtplib with retry logic."""
    msg = MIMEMultipart()
    msg["From"] = f"{get_config_value('SITE_NAME')} Support <{SMTP_USERNAME}>"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # Render the HTML template
    body = render_template(template, **kwargs)
    msg.attach(MIMEText(body, "html"))

    retry_count = 0
    while retry_count < 3:
        try:
            # Establish SMTP connection
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)  # Use SSL directly

            # Login to the server
            server.login(SMTP_USERNAME, SMTP_PASSWORD)

            # Sending email
            server.sendmail(SMTP_USERNAME, recipients, msg.as_string())

            # Closing server connection
            server.quit()
            return jsonify({"message": "Email sent successfully.", "success": True}), 200
        except (smtplib.SMTPServerDisconnected, socket.timeout, smtplib.SMTPException) as e:
            retry_count += 1
            time.sleep(2 ** retry_count)  # Exponential backoff
            print(f"Retry {retry_count}: Failed to send email. Error: {e}")

    return jsonify({"message": "Failed to send email. Please try again later.", "success": False}), 500


# Password Reset Route
@auth.route("/reset-password", methods=["POST"])
def reset_password():
    email = request.form.get("email")

    if not email:
        return jsonify({"message": "Email is required", "success": False})

    db, cur = db_start()
    # Check if email exists
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if not user:
        return jsonify({"message": "Email not found", "success": False})

    # Generate Temporary Password
    chars = string.ascii_letters + string.digits
    temp_password = "".join(random.choice(chars) for _ in range(10))
    # Hash the password
    hashed_password = bcrypt.generate_password_hash(temp_password).decode('utf-8')
    # Update the database
    cur.execute("UPDATE users SET password = %s AND temp_password_status = 1 WHERE email = %s",
                (hashed_password, email))
    db.commit()
    cur.close()
    db.close()

    """Send a temporary password to the user's email."""
    return send_email(
        "Your Temporary Password",
        [email],
        "emails/password_reset.html",
        temp_password=temp_password,
        SITE_NAME=get_config_value("SITE_NAME")
    )


@auth.route('/change_password', methods=['POST'])
def change_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    user_id = session['user_id']

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new passwords are required'}), 400

    db, cur = db_start()
    if not db or not cur:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        # Fetch current password hash
        cur.execute("SELECT password FROM users WHERE user_id = %s AND temp_password_status = 1", (user_id,))
        user = cur.fetchone()
        if not user or not bcrypt.check_password_hash(user['password'].encode('utf-8'),
                                                      current_password.encode('utf-8')):
            return jsonify({'error': 'Invalid current password'}), 400

        # Update with new hashed password
        hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cur.execute("""
            UPDATE users 
            SET password = %s, temp_password_status = 0 
            WHERE user_id = %s AND temp_password_status = 1
        """, (hashed_new_password, user_id))

        if cur.rowcount == 0:
            return jsonify({'error': 'Update failed'}), 400

        return jsonify({'success': True, 'message': 'Password updated successfully'})
    except mysql.connector.Error as e:
        print(f"Query Error: {e}")
        return jsonify({'error': 'Failed to update password'}), 500
    finally:
        cur.close()
        db.close()
