import json
import os
import random
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import mysql.connector

import requests
from flask import current_app as app, Blueprint, request, session, jsonify
from werkzeug.utils import secure_filename
from config import get_config_value

from LoginManager.login_manager import login_required_query
from blueprint.user import get_user_balance
from db_conn import db_start
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
import time


fund = Blueprint('fund', __name__)


def get_merchant_credentials():
    """Fetch merchant email and password from the site_settings table."""
    db, cur = db_start()
    if db is None or cur is None:
        return None, None  # Return None if connection fails

    try:
        # Assuming there's only one row or you want the first row
        cur.execute("SELECT vpay_merchant_email, vpay_merchant_password FROM site_settings WHERE id = 1")
        result = cur.fetchone()
        if result:
            email = result['vpay_merchant_email']
            password = result['vpay_merchant_password']
            return email, password
        else:
            print("No merchant credentials found in the database.")
            return None, None

    except mysql.connector.Error as e:
        print(f"Error fetching credentials: {e}")
        return None, None

    finally:
        cur.close()
        db.close()


def generate_access_token():
    """Generate access token using merchant credentials from the database."""
    # Get credentials from the database
    email, password = get_merchant_credentials()
    if not email or not password:
        print("Cannot generate token: Missing merchant credentials.")
        return None

    url = "https://saturn.vpay.africa/service/demo/v1/query/user/login"
    payload = {
        'app': 'merchant',
        'email': email,
        'password': password
    }

    # Convert the request body to JSON
    json_data = json.dumps(payload)

    headers = {
        'Content-Type': 'application/json',
        'publicKey': 'SXZhbkFsZXJnYXBJc05vdE9ubHlBV2l0dHlPbmVIYW5uYWhCYW5la3VJc1RoZVNlY29uZCNOdW4='
    }

    try:
        response = requests.post(url, headers=headers, data=json_data)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()['token']
    except requests.RequestException as e:
        print(f"Error generating access token: {e}")
        return None


def generate_unique_tx_number():
    db, cur = db_start()
    try:
        while True:
            random_number = random.randint(10000000, 99999999)
            transaction_id = f"verif_{str(random_number)}"
            cur.execute("SELECT 1 FROM transactions WHERE transaction_id = %s", (transaction_id,))
            if cur.fetchone() is None:
                return transaction_id
    finally:
        cur.close()
        db.close()


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_email(subject, recipients, body, is_html=True):
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

    # Attach the body string directly
    msg.attach(MIMEText(body, "html" if is_html else "plain"))

    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Establish SMTP connection
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
            
            # Login to the server
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            
            # Send email
            server.sendmail(SMTP_USERNAME, recipients, msg.as_string())
            
            # Close connection
            server.quit()
            print(f"Email sent successfully to {recipients}")
            return jsonify({"message": "Email sent successfully.", "success": True}), 200
            
        except (smtplib.SMTPServerDisconnected, socket.timeout, smtplib.SMTPException) as e:
            retry_count += 1
            if retry_count == max_retries:
                print(f"Failed to send email after {max_retries} attempts. Error: {e}")
                return jsonify({"message": "Failed to send email. Please try again later.", "success": False}), 500
            time.sleep(2 ** retry_count)  # Exponential backoff
            print(f"Retry {retry_count}/{max_retries}: Failed to send email. Error: {e}")

def send_manual_payment_notification(email, transaction_id, amount):
    """
    Send notification to admin about manual payment request using a string body
    """
    # Define admin email
    ADMIN_EMAIL = get_config_value("ADMIN_EMAIL")
    
    subject = "Manual Payment Request Notification"
    
    # Create HTML string body
    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Manual Payment Request</title>
    </head>
    <body>
        <h2>Manual Payment Request Notification</h2>
        <p>A user has submitted a manual payment request with the following details:</p>
        
        <table>
            <tr>
                <td><strong>User Email:</strong></td>
                <td>{email}</td>
            </tr>
            <tr>
                <td><strong>Transaction ID:</strong></td>
                <td>{transaction_id}</td>
            </tr>
            <tr>
                <td><strong>Amount:</strong></td>
                <td>₦{amount}</td>
            </tr>
            <tr>
                <td><strong>Timestamp:</strong></td>
                <td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
            </tr>
        </table>
        
        <p>Please review this request in the admin panel and take appropriate action.</p>
        
        <p>Regards,<br>{get_config_value('SITE_NAME')} System</p>
    </body>
    </html>
    """
    
    return send_email(
        subject=subject,
        recipients=[ADMIN_EMAIL],
        body=body,
        is_html=True
    )


@fund.route('/load-wallet', methods=['POST'])
@login_required_query
def load_wallet():
    data = request.get_json()
    transaction_id = generate_unique_tx_number()
    db, cur = db_start()
    try:
        query = ("INSERT INTO transactions (transaction_id, date, amount, user_id, status, type, processor) "
                 "VALUES (%s, %s, %s, %s, %s, %s, %s)")
        cur.execute(query, (
            transaction_id,
            datetime.now(),
            Decimal(data['amount']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            session['user_id'],
            "Pending",
            data['payment_type'],
            data['processor']
        ))
        db.commit()
    finally:
        cur.close()
        db.close()

    return jsonify({
        'transaction_id': transaction_id,
        'amount': Decimal(data['amount']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'email': session['email'],
        'username': session['username'],
        'payment_type': data['payment_type']
    })


@fund.route('/manual_funding', methods=['POST'])
@login_required_query
def manual_funding():
    db, cur = db_start()
    try:
        with app.app_context():
            # check if the post request has the file part
            if 'files[]' not in request.files:
                resp = jsonify({'message': 'No file part in the request'})
                resp.status_code = 400
                return resp

            sender_name = request.form['sender_name']
            amount = request.form['amount']
            transaction_id = generate_unique_tx_number()

            files = request.files.getlist('files[]')

            if files[0] and allowed_file(files[0].filename):
                original_filename = secure_filename(files[0].filename)
                # generate a unique filename with the original extension
                new_filename = "{}{}".format(uuid.uuid4(), os.path.splitext(original_filename)[1])
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                files[0].save(os.path.join(upload_folder, new_filename))

                cursor = db.cursor()
                # Update the transaction object using a direct SQL query
                query = ("INSERT INTO transactions (transaction_id, date, amount, user_id, status, type, sender_name, "
                         "image)"
                         "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
                cursor.execute(query, (
                    transaction_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    amount,
                    session['user_id'],
                    "Pending",
                    'manual',
                    sender_name,
                    new_filename
                ))
                db.commit()

                # Send notification
                send_manual_payment_notification(
                    email=session['email'],
                    transaction_id=transaction_id,
                    amount=amount
                )

                return jsonify({
                    'message': 'File successfully uploaded'
                }), 206
            else:
                return jsonify({
                    'message': 'File type is not allowed'
                }), 400
    finally:
        cur.close()
        db.close()


@fund.route('/add-funds', methods=['POST'])
@login_required_query
def add_funds():
    db, cur = db_start()
    try:
        data = request.get_json()
        transaction_id = data['transaction_id']

        # Fetch the transaction object
        cur.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
        transaction_obj = cur.fetchone()
        if transaction_obj['type'] == "instant" and transaction_obj['processor'] == "vpay":
            # Fetch the site settings
            cur.execute("SELECT vpay_access_token FROM site_settings WHERE id = 1")
            site_setting = cur.fetchone()
            access_token = site_setting['access_token']

            url = "https://saturn.vpay.africa/api/v1/webintegration/query-transaction"

            payload = {
                'transactionRef': transaction_id
            }

            headers = {
                'Content-Type': 'application/json',
                'publicKey': 'SXZhbkFsZXJnYXBJc05vdE9ubHlBV2l0dHlPbmVIYW5uYWhCYW5la3VJc1RoZVNlY29uZCNOdW4=',
                'b-access-token': access_token
            }
            response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
            if response.json().get('message') == 'Failed to authenticate token.':
                access_token = generate_access_token()
                cur.execute(
                    "INSERT INTO site_settings (id, vpay_access_token) VALUES (1, %s) ON DUPLICATE KEY UPDATE vpay_access_token "
                    "= %s",
                    (access_token, access_token)
                )
                db.commit()
                headers['b-access-token'] = access_token
                response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
            if response.json().get('message') == 'Session has expired.':
                access_token = generate_access_token()
                cur.execute(
                    "INSERT INTO site_settings (id, vpay_access_token) VALUES (1, %s) ON DUPLICATE KEY UPDATE vpay_access_token = %s",
                    (access_token, access_token)
                )
                db.commit()
                headers['b-access-token'] = access_token
                response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
            if response.json().get('message') == 'Transaction with such reference does not exist.':
                cur.execute("UPDATE transactions SET status = 'Failed' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Failed'}

            payment_status = response.json().get('data')['paymentstatus']
            amount = transaction_obj['amount']
            if payment_status == 'paid':
                if transaction_obj['status'] == "Pending":
                    cur.execute("UPDATE transactions SET status = 'Finished' WHERE transaction_id = %s",
                                (transaction_id,))
                    db.commit()
                    send_deposit_notification(
                        f"{session['email']} | Just deposited ₦{amount} | IP ====> {data['ip_address']}")
                    return {'status': 'Payment Successful', 'amount': str(get_user_balance())}
            elif payment_status == 'failed':
                cur.execute("UPDATE transactions SET status = 'Failed' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Failed'}
            elif payment_status == 'pending':
                cur.execute("UPDATE transactions SET status = 'Pending' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Pending'}
        if transaction_obj['type'] == "instant" and transaction_obj['processor'] == "korapay":
            amount = transaction_obj['amount']
            # Fetch the site settings
            cur.execute("SELECT korapay_secret_key FROM site_settings WHERE id = 1")
            site_setting = cur.fetchone()
            korapay_secret_key = site_setting['korapay_secret_key']

            url = f"https://api.korapay.com/merchant/api/v1/charges/{transaction_id}"

            payload = {}
            headers = {
                'Authorization': f'Bearer {korapay_secret_key}'
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            if response.json().get('message') == 'Charge not found':
                cur.execute("UPDATE transactions SET status = 'Failed' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Failed'}
            if response.json().get('error') == 'service_unavailable':
                cur.execute("UPDATE transactions SET status = 'Pending' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Pending'}
            if response.json().get('data')['status'] == 'processing':
                cur.execute("UPDATE transactions SET status = 'Pending' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Pending'}
            if response.json().get('data')['status'] == 'expired' or response.json().get('data')['status'] == 'failed':
                cur.execute("UPDATE transactions SET status = 'Failed' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                return {'status': 'Payment Failed'}
            if response.json().get('data')['status'] == 'success':
                cur.execute("UPDATE transactions SET status = 'Finished' WHERE transaction_id = %s",
                            (transaction_id,))
                db.commit()
                send_deposit_notification(
                    f"{session['email']} | Just deposited ₦{amount} | IP ====> {data['ip_address']}")
                return {'status': 'Payment Successful', 'amount': str(get_user_balance())}
        if transaction_obj['type'] == "manual" and transaction_obj['sender_name'] is None:
            cur.execute(
                "UPDATE transactions SET status = 'Failed', reason = 'Senders Name not added' WHERE transaction_id = "
                "%s",
                (transaction_id,))
            db.commit()
            return {'status': 'Payment Failed'}
        if transaction_obj['type'] == "manual" and transaction_obj['image'] is None:
            cur.execute(
                "UPDATE transactions SET status = 'Failed', reason = 'No debit receipt uploaded' WHERE transaction_id "
                "= %s",
                (transaction_id,))
            db.commit()
            return {'status': 'Payment Failed'}
        if transaction_obj['type'] == "manual" and transaction_obj['image'] != "":
            send_manual_notification("{} just requested for funding {}".format(session['email'], transaction_id))
            return {'status': 'Payment Pending'}
    finally:
        cur.close()
        db.close()
