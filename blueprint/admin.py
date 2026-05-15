import os
import random
import smtplib
import socket
import time
from datetime import datetime
import mysql.connector
from decimal import Decimal, ROUND_HALF_UP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from json import JSONDecodeError

import requests
from flask import current_app as app, Blueprint, render_template, jsonify, json, request, current_app, session, \
    redirect, url_for
from werkzeug.utils import secure_filename

from LoginManager.login_manager import admin_login_required, admin_login_required_query
from config import get_config_value, load_config, update_config_value
from db_conn import db_start, User, Transaction, Admin
from extension import send_deposit_notification, bcrypt, ALLOWED_EXTENSIONS

admin = Blueprint('admin', __name__)


def send_email(subject, recipients, template, **kwargs):
    """Send an email using smtplib with retry logic."""
    SMTP_SERVER = get_config_value("SMTP_SERVER")
    SMTP_PORT = get_config_value("SMTP_PORT")
    SMTP_USERNAME = get_config_value("SMTP_USERNAME")
    SMTP_PASSWORD = get_config_value("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = f"{get_config_value('SITE_NAME')} Support <{SMTP_USERNAME}>"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # Render the HTML template
    with app.app_context():  # Ensure template rendering works outside request context
        body = render_template(template, **kwargs)
    msg.attach(MIMEText(body, "html"))

    retry_count = 0
    while retry_count < 3:
        try:
            # Establish SMTP connection with SSL
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipients, msg.as_string())
            server.quit()
            return {"message": "Email sent successfully.", "success": True}, 200
        except (smtplib.SMTPServerDisconnected, socket.timeout, smtplib.SMTPException) as e:
            retry_count += 1
            time.sleep(2 ** retry_count)  # Exponential backoff
            print(f"Retry {retry_count}: Failed to send email. Error: {e}")
            if retry_count == 3:
                return {"message": f"Failed to send email after retries: {e}", "success": False}, 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_code_from_db(value):
    # Return an empty list if the value is falsy
    if not value:
        return []
    try:
        # Convert the value to a string before parsing
        parsed_value = json.loads(str(value))
        # If parsing results in a number, we treat it as a string
        if isinstance(parsed_value, (int, float)):
            return [str(value)]
        return parsed_value
    except (JSONDecodeError, TypeError):
        return [str(value)]  # Convert the value to a string and wrap it in a list


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




@admin.route("/admin/site", methods=["GET", "POST"])
def settings():
    config = load_config()
    if request.method == "POST":
        # Handle file uploads
        logo_file = request.files.get('site_logo')
        favicon_file = request.files.get('site_favicon')

        # Validate and save logo file only if a new one is uploaded
        upload_folder = os.path.join(app.root_path, 'static', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        if logo_file and logo_file.filename:  # Check if a new logo file is provided
            if not allowed_file(logo_file.filename):
                return render_template("admin/admin_site.html", **config,
                                       error="Invalid logo file format. Allowed: png, jpg, jpeg, gif, ico", active_menu="site"), 400
            logo_filename = secure_filename(logo_file.filename)
            logo_path = os.path.join(upload_folder, logo_filename)
            logo_file.save(logo_path)
            relative_logo_path = os.path.join('static', 'uploads', logo_filename).replace(os.sep, '/')
            update_config_value("SITE_LOGO", relative_logo_path)
        # Otherwise, SITE_LOGO remains unchanged

        # Validate and save favicon file only if a new one is uploaded
        if favicon_file and favicon_file.filename:  # Check if a new favicon file is provided
            if not allowed_file(favicon_file.filename):
                return render_template("admin/admin_site.html", **config,
                                       error="Invalid favicon file format. Allowed: png, jpg, jpeg, gif, ico", active_menu="site"), 400
            favicon_filename = secure_filename(favicon_file.filename)
            favicon_path = os.path.join(upload_folder, favicon_filename)
            favicon_file.save(favicon_path)
            relative_favicon_path = os.path.join('static', 'uploads', favicon_filename).replace(os.sep, '/')
            update_config_value("SITE_FAVICON", relative_favicon_path)
        # Otherwise, SITE_FAVICON remains unchanged

        # Update site config
        update_config_value("SITE_NAME", request.form.get("site_name"))
        update_config_value("SITE_SUPPORT_EMAIL", request.form.get("site_support_email"))
        update_config_value("SITE_TELEGRAM_SUPPORT", request.form.get("site_telegram_support"))

        # Update SMTP config
        update_config_value("SMTP_SERVER", request.form.get("smtp_server"))
        update_config_value("SMTP_USERNAME", request.form.get("smtp_username"))
        update_config_value("SMTP_PASSWORD", request.form.get("smtp_password"))
        update_config_value("SMTP_PORT", int(request.form.get("smtp_port")))

        # Update theme config
        update_config_value("THEME_MODE", request.form.get("theme_mode"))
        update_config_value("THEME_CONTRAST", request.form.get("theme_contrast"))
        update_config_value("THEME_COLOUR", request.form.get("custom_theme"))
        update_config_value("THEME_LAYOUT", request.form.get("theme_layout"))
        update_config_value("THEME_LAYOUT_WIDTH", "boxed" if request.form.get("layout_width") == "true" else "")
        update_config_value("THEME_LAYOUT_DIRECTION", "rtl" if request.form.get("direction") == "true" else "ltr")
        update_config_value("THEME_SIDEBAR_CAPTION", request.form.get("sidebar_caption"))

        # Update bot config
        update_config_value("BOT_DEPOSIT_API", request.form.get("bot_deposit_api"))
        update_config_value("BOT_MANUAL_API", request.form.get("bot_manual_api"))
        update_config_value("CHAT_ID", request.form.get("chat_id"))

        return render_template("admin/admin_site.html", **config, error="Settings updated successfully", active_menu="site")
    return render_template("admin/admin_site.html", **config, active_menu="site")


@admin.route('/install', methods=['GET', 'POST'])
def install():
    # Check if site is installed
    if get_config_value("SITE_INSTALLED") == "1":
        return redirect(url_for('home.homepage'))  # Redirect to home or dashboard if installed

    if request.method == 'POST':
        # Collect form data
        form_data = {
            "site_name": request.form.get('site_name'),
            "site_logo": request.form.get('site_logo'),
            "site_favicon": request.form.get('site_favicon'),
            "site_telegram_support": request.form.get('site_telegram_support', ''),
            "username": request.form.get('username'),
            "password": request.form.get('password'),
            "theme_mode": request.form.get('theme_mode'),
            "theme_contrast": request.form.get('theme_contrast'),
            "custom_theme": request.form.get('custom_theme'),
            "theme_layout": request.form.get('theme_layout'),
            "sidebar_caption": request.form.get('sidebar_caption'),
            "direction": request.form.get('direction'),
            "layout_width": request.form.get('layout_width'),
            "current_profit": request.form.get('current_profit'),
            "parent_api_key": (request.form.get('parent_api_key') or '').strip(),
        }

        # Validate required fields
        required_fields = {k: v for k, v in form_data.items() if k not in ['site_telegram_support', 'site_logo',
                                                                           'site_favicon']}
        missing = [key.replace('_', ' ').title() for key, value in required_fields.items() if not value]
        if missing:
            return render_template('install.html', error=f"Missing fields: {', '.join(missing)}",
                                   domain=request.host), 400

        # Handle file uploads
        logo_file = request.files.get('site_logo')
        favicon_file = request.files.get('site_favicon')

        if not logo_file or not favicon_file:
            return render_template('install.html', error="Site Logo and Favicon are required",
                                   domain=request.host), 400

        if not (allowed_file(logo_file.filename) and allowed_file(favicon_file.filename)):
            return render_template('install.html', error="Invalid file format. Allowed: png, jpg, jpeg, gif, ico",
                                   domain=request.host), 400
        with app.app_context():
            # Save files
            upload_folder = os.path.join(app.root_path, 'static', 'uploads')
            logo_filename = secure_filename(logo_file.filename)
            favicon_filename = secure_filename(favicon_file.filename)
            logo_path = os.path.join(upload_folder, logo_filename)
            favicon_path = os.path.join(upload_folder, favicon_filename)
            logo_file.save(logo_path)
            favicon_file.save(favicon_path)

        # Relative paths for config
        relative_logo_path = os.path.join('static', 'uploads', logo_filename).replace(os.sep, '/')
        relative_favicon_path = os.path.join('static', 'uploads', favicon_filename).replace(os.sep, '/')

        # Save files to disk
        logo_file.save(logo_path)
        favicon_file.save(favicon_path)
        # Initialize database connection
        db, cur = db_start()
        if not db or not cur:
            return jsonify({'error': 'Database connection failed'}), 500

        try:
            # Create admin table
            cur.execute("""
                            CREATE TABLE IF NOT EXISTS admin (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                username VARCHAR(50) NOT NULL,
                                email VARCHAR(50) NOT NULL,
                                password VARCHAR(255) NOT NULL,
                                admin_type VARCHAR(255) NOT NULL
                            )
                        """)

            # Generate email as username@site_domain and insert admin
            admin_email = f"{form_data['username']}@{request.host}"
            hashed_password = bcrypt.generate_password_hash(form_data['password']).decode('utf-8')
            cur.execute("""
                            INSERT INTO admin (username, email, password, admin_type)
                            VALUES (%s, %s, %s, %s)
                        """, (form_data['username'], admin_email, hashed_password, 'admin'))

            # Insert or update site_settings for id = 1 with profit + parent api_key.
            # ON DUPLICATE KEY UPDATE covers re-installs over an existing seeded row.
            cur.execute("""
                            INSERT INTO site_settings (id, current_profit, api_key)
                            VALUES (1, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                current_profit = VALUES(current_profit),
                                api_key        = VALUES(api_key)
                        """, (form_data['current_profit'], form_data['parent_api_key']))

            # Update config incrementally using update_config_value
            update_config_value("SITE_INSTALLED", "1")
            update_config_value("SITE_NAME", form_data["site_name"])
            update_config_value("SITE_LOGO", relative_logo_path)
            update_config_value("SITE_FAVICON", relative_favicon_path)
            update_config_value("SITE_DOMAIN", request.host)
            update_config_value("SITE_TELEGRAM_SUPPORT", form_data["site_telegram_support"])
            update_config_value("THEME_MODE", form_data["theme_mode"])
            update_config_value("THEME_CONTRAST", form_data["theme_contrast"])
            update_config_value("THEME_COLOUR", form_data["custom_theme"])
            update_config_value("THEME_LAYOUT", form_data["theme_layout"])
            update_config_value("THEME_SIDEBAR_CAPTION", form_data["sidebar_caption"])
            update_config_value("THEME_LAYOUT_DIRECTION", "rtl" if form_data["direction"] == "true" else "ltr")
            update_config_value("THEME_LAYOUT_WIDTH", "boxed" if form_data["layout_width"] == "true" else "")

            # Show the post-install page with the webhook URLs the operator
            # must paste back into the PARENT's settings page.
            scheme = 'https' if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https' else 'http'
            return render_template(
                'install_complete.html',
                rotate_url=f"{scheme}://{request.host}/webhook/rotate-api-key",
                event_url=f"{scheme}://{request.host}/webhook/order-event",
                parent_settings_url="https://swiftverifyng.com/settings#api_key",
            )

        except mysql.connector.Error as e:
            print(f"Database Error: {e}")
            return render_template('install.html', error="Failed to create admin account"), 500
        finally:
            cur.close()
            db.close()

    # GET request: Show installation form
    return render_template('install.html', domain=request.host)


@admin.route('/admin/dashboard', methods=['GET'])
@admin_login_required
def dashboard():
    db, cur = db_start()
    try:
        # Fetch the Total Sales
        total_sales_query = """
            SELECT COUNT(*) as count
            FROM history
            WHERE code IS NOT NULL
              AND code != ''
              AND code != '[]'
        """
        cur.execute(total_sales_query)
        total_sales = cur.fetchone()
        total_sales = total_sales['count'] if total_sales and 'count' in total_sales else 0

        # Fetch the Total Users
        total_users_query = "SELECT COUNT(*) as count FROM users"
        cur.execute(total_users_query)
        total_users = cur.fetchone()
        total_users = total_users['count'] if total_users and 'count' in total_users else 0

        # Fetch the Amount Spent
        amount_spent_query = """
            SELECT COALESCE(SUM(CAST(price AS DECIMAL(10,2))), 0) as sum
            FROM history
            WHERE code IS NOT NULL
              AND code != ''
              AND code != '[]'
              AND TRIM(code) != ''
        """
        cur.execute(amount_spent_query)
        amount_spent = cur.fetchone()
        # Ensure proper formatting even if None
        amount_spent = "{:,.2f}".format(float(amount_spent['sum'])) if amount_spent and 'sum' in amount_spent and amount_spent['sum'] is not None else "0.00"

        # Fetch the Total Deposit
        total_deposit_query = """
            SELECT COALESCE(SUM(CAST(amount AS DECIMAL(10,2))), 0) as sum 
            FROM transactions 
            WHERE status = 'Finished'
        """
        cur.execute(total_deposit_query)
        total_deposit = cur.fetchone()
        # Ensure proper formatting even if None
        total_deposit = "{:,.2f}".format(float(total_deposit['sum'])) if total_deposit and 'sum' in total_deposit and total_deposit['sum'] is not None else "0.00"

        # Get the count of pending manual transactions
        count_query = """
            SELECT COUNT(*) as pending_count 
            FROM transactions 
            WHERE type = 'manual' 
            AND status = 'Pending'
        """
        cur.execute(count_query)
        result = cur.fetchone()
        pending_count = result['pending_count'] if result and 'pending_count' in result else 0

    finally:
        if db.is_connected():
            cur.close()
            db.close()

    return render_template("admin/admin_dashboard.html",
                          total_sales=total_sales,
                          total_users=int(total_users) - 1,
                          amount_spent=amount_spent,
                          total_deposit=total_deposit,
                          active_menu='dashboard',
                          pending_transaction=pending_count,
                          SITE_NAME=get_config_value("SITE_NAME"),
                          SITE_LOGO=get_config_value("SITE_LOGO"),
                          SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                          SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                          SITE_FAVICON=get_config_value("SITE_FAVICON"))


@admin.route('/admin/orders', methods=['GET'])
@admin_login_required
def admin_orders():
    db, cur = db_start()
    try:
        # Get the count of pending manual transactions
        count_query = "SELECT COUNT(*) FROM transactions WHERE type='manual' AND status='Pending'"
        cur.execute(count_query)
        # Fetch the count, set to 0 if None
        result = cur.fetchone()
        pending_count = result['COUNT(*)'] if result else 0
    finally:
        if db.is_connected():
            cur.close()
            db.close()
    return render_template("admin/admin_orders.html", active_menu='orders',
                           pending_transaction=pending_count,
                           SITE_NAME=get_config_value("SITE_NAME"),
                           SITE_LOGO=get_config_value("SITE_LOGO"),
                           SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                           SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                           SITE_FAVICON=get_config_value("SITE_FAVICON"),
                           )


@admin.route('/admin/users', methods=['GET'])
@admin_login_required
def admin_users():
    db, cur = db_start()
    try:
        # Get the count of pending manual transactions
        count_query = "SELECT COUNT(*) FROM transactions WHERE type='manual' AND status='Pending'"
        cur.execute(count_query)
        # Fetch the count, set to 0 if None
        result = cur.fetchone()
        pending_count = result['COUNT(*)'] if result else 0
    finally:
        if db.is_connected():
            cur.close()
            db.close()
    return render_template("admin/admin_users.html",
                           active_menu='users', pending_transaction=pending_count,
                           SITE_NAME=get_config_value("SITE_NAME"),
                           SITE_LOGO=get_config_value("SITE_LOGO"),
                           SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                           SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                           SITE_FAVICON=get_config_value("SITE_FAVICON"),
                           )


@admin.route('/admin/history/<user_id>', methods=['GET'])
@admin_login_required
def admin_user_history(user_id):
    db, cur = db_start()
    try:
        # Get User_id of user with username (using parameterized query)
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        query = cur.fetchone()
        if not query:
            # Handle case where user is not found
            return "User not found", 404
        user = User(**query)

        # Define the balance query (simplified for MySQL 5.7.44)
        balance_query = """
            SELECT 
                IFNULL(
                    REPLACE(
                        FORMAT(
                            SUM(
                                IF(type IN ('instant', 'manual') AND status = 'Finished', 
                                    amount, 
                                    IF(status IN ('Finished', 'Received'), 
                                        -amount, 
                                        0)
                                    )
                            ), 
                            2
                        ), 
                        ',', 
                        ''
                    ), 
                    '0.00'
                ) AS balance
            FROM (
                SELECT date, type, amount, NULL AS service, NULL AS country, status 
                FROM transactions 
                WHERE user_id = %s
                UNION ALL
                SELECT date, NULL AS type, price AS amount, service, country, status 
                FROM history 
                WHERE user_id = %s
            ) AS combined_result
        """
        cur.execute(balance_query, (user_id, user_id))
        balance = cur.fetchone()
        user_balance = balance['balance'] if balance and 'balance' in balance else "0.00"

        # Fetch the Amount Spent (parameterized)
        amount_spent_query = """
            SELECT COALESCE(SUM(CAST(price AS DECIMAL(10,2))), 0) as sum
            FROM history
            WHERE code IS NOT NULL
                  AND code != ''
                  AND code != '[]'
                  AND user_id = %s
        """
        cur.execute(amount_spent_query, (user_id,))
        amount_spent = cur.fetchone()
        amount_spent = "{:,.2f}".format(float(amount_spent['sum'])) if amount_spent and 'sum' in amount_spent and amount_spent['sum'] is not None else "0.00"

        # Fetch the Total Deposit (parameterized)
        total_deposit_query = """
            SELECT COALESCE(SUM(CAST(amount AS DECIMAL(10,2))), 0) as sum 
            FROM transactions 
            WHERE status = 'Finished' 
            AND user_id = %s
        """
        cur.execute(total_deposit_query, (user_id,))
        total_deposit = cur.fetchone()
        total_deposit = "{:,.2f}".format(float(total_deposit['sum'])) if total_deposit and 'sum' in total_deposit and total_deposit['sum'] is not None else "0.00"

        # Get the count of pending manual transactions (parameterized)
        count_query = """
            SELECT COUNT(*) as pending_count 
            FROM transactions 
            WHERE type = 'manual' 
            AND status = 'Pending' 
            AND user_id = %s
        """
        cur.execute(count_query, (user_id,))
        result = cur.fetchone()
        pending_count = result['pending_count'] if result and 'pending_count' in result else 0

        # User status formatting
        if user.user_status == 1:
            status = "<span class='badge bg-success'>Active</span>"
        elif user.user_status == 0:
            status = "<span class='badge bg-danger'>Inactive</span>"
        else:
            status = "<span class='badge bg-warning'>Unknown</span>"

        return render_template("admin/admin_transactions.html",
                              user_email=user.email,
                              user_balance=user_balance,  # Already formatted in query
                              username=user.username,
                              total_deposit=total_deposit,
                              amount_spent=amount_spent,
                              status=status,
                              active_menu='users',
                              pending_transaction=pending_count,
                              SITE_NAME=get_config_value("SITE_NAME"),
                              SITE_LOGO=get_config_value("SITE_LOGO"),
                              SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                              SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                              SITE_FAVICON=get_config_value("SITE_FAVICON"))

    finally:
        if db.is_connected():
            cur.close()
            db.close()

@admin.route('/admin/payment', methods=['GET'])
@admin_login_required
def admin_payment():
    db, cur = db_start()
    try:
        # Execute the query
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))

        # Fetch the result
        site_setting = cur.fetchone()
        vpay = site_setting['vpay']
        korapay = site_setting['korapay']
        manual_pay = site_setting['manual_payment']
        manual_payment_account = site_setting['manual_payment_account']
        manual_payment_account_name = site_setting['manual_payment_account_name']
        manual_payment_bank = site_setting['manual_payment_bank']
        payment = {
            'method': {
                'vpay': vpay,
                'korapay': korapay,
                'manual_payment': manual_pay
            },
            'manual_payment_account': manual_payment_account,
            'manual_payment_account_name': manual_payment_account_name,
            'manual_payment_bank': manual_payment_bank,
            'api_key': {
                'vpay': site_setting['vpay_access_token'],
                'korapay': site_setting['korapay_secret_key']
            },
            'public_key': {
                'vpay_public_key': site_setting['vpay_public_key'],
                'korapay_public_key': site_setting['korapay_public_key']
            },
            'vpay': {
                'vpay_merchant_email': site_setting['vpay_merchant_email'],
                'vpay_merchant_password': site_setting['vpay_merchant_password'],
            }
        }
        # Get the count of pending manual transactions
        count_query = "SELECT COUNT(*) FROM transactions WHERE type='manual' AND status='Pending'"
        cur.execute(count_query)
        # Fetch the count, set to 0 if None
        result = cur.fetchone()
        pending_count = result['COUNT(*)'] if result else 0
        return render_template("admin/admin_payment.html", payment=payment,
                               active_menu='payment_gateway',
                               pending_transaction=pending_count,
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               )
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin/manual_funding', methods=['GET'])
@admin_login_required
def admin_manual_funding():
    db, cur = db_start()
    try:
        # Get the count of pending manual transactions
        count_query = "SELECT COUNT(*) FROM transactions WHERE type='manual' AND status='Pending'"
        cur.execute(count_query)
        # Fetch the count, set to 0 if None
        result = cur.fetchone()
        pending_count = result['COUNT(*)'] if result else 0
        return render_template("admin/admin_manual.html",
                               active_menu='manual_funding',
                               pending_transaction=pending_count,
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               )
    finally:
        if db.is_connected():
            cur.close()
            db.close()


async def fetch_balance(session, provider, api_key):
    url = ""
    if provider == 'daisysms':
        url = f"https://daisysms.com/stubs/handler_api.php?api_key={api_key}&action=getBalance"
    elif provider == 'grizzlysms':
        url = f"https://api.grizzlysms.com/stubs/handler_api.php?api_key={api_key}&action=getBalance"
    elif provider == 'smsbower':
        url = f"https://smsbower.com/stubs/handler_api.php?api_key={api_key}&action=getBalance"
    elif provider == '5sim':
        url = 'https://5sim.net/v1/user/profile'
        headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'}
        async with session.get(url, headers=headers) as response:
            if response.status == 401:
                return "Bad key"
            api_response = await response.json()
            balance = api_response.get('balance')
            if balance is not None:
                return f"{float(balance) / 88:.2f}"
            else:
                return "Bad key"
    elif provider == 'smspool':
        url = f"https://api.smspool.net/request/balance?key={api_key}"
        async with session.get(url) as response:
            json_response = await response.json()
            balance = json_response.get('balance')
            if balance is not None:
                return f"{float(balance):.2f}"
            else:
                return "Bad key"
    else:
        return "Unknown provider"

    async with session.get(url) as response:
        if provider == 'daisysms':
            api_response = await response.text()
            if "ACCESS_BALANCE:" in api_response:
                balance = api_response.replace("ACCESS_BALANCE:", "")
                return f"{float(balance):.2f}"
            else:
                return "Bad key"
        if provider == 'grizzlysms' or provider == 'smsbower':
            api_response = await response.text()
            if "ACCESS_BALANCE:" in api_response:
                balance = api_response.replace("ACCESS_BALANCE:", "")
                return f"{float(balance) / 88:.2f}"
            else:
                return "Bad key"


@admin.route('/admin/settings', methods=['GET'])
@admin_login_required
def admin_settings():
    db, cur = db_start()
    try:
        # Get the count of pending manual transactions
        count_query = "SELECT COUNT(*) FROM transactions WHERE type='manual' AND status='Pending'"
        cur.execute(count_query)
        # Fetch the count, set to 0 if None
        result = cur.fetchone()
        pending_count = result['COUNT(*)'] if result else 0

        # Execute the query
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))

        # Fetch the result
        site_setting = cur.fetchone()
        current_profit = int(site_setting['current_profit'])

        # Mask the parent api_key for display — show only the last 4 chars.
        # The full key never leaves the server unless the operator pastes a
        # new one explicitly.
        raw_key = (site_setting.get('api_key') or '').strip()
        parent_api_key_masked = ('•' * 8 + raw_key[-4:]) if len(raw_key) >= 4 else ''
        api_key_rotated_at = site_setting.get('api_key_rotated_at') or ''

        return render_template('admin/admin_settings.html',
                               active_menu='settings', pending_transaction=pending_count,
                               profit=current_profit,
                               parent_api_key_masked=parent_api_key_masked,
                               api_key_rotated_at=str(api_key_rotated_at) if api_key_rotated_at else '',
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               )
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin/verification', methods=['GET'])
@admin_login_required
def admin_verification():
    """Pool labels — let the admin rename / hide / reorder the parent's
    pool codenames (Alpha…Foxtrot) for their own users. The underlying
    API call always uses the canonical codename; only the display
    string is customised."""
    db, cur = db_start()
    try:
        cur.execute("SELECT COUNT(*) FROM transactions WHERE type='manual' AND status='Pending'")
        result = cur.fetchone()
        pending_count = result['COUNT(*)'] if result else 0

        cur.execute(
            "SELECT codename, display_name, enabled, sort_order, updated_at "
            "FROM pool_labels ORDER BY sort_order ASC, codename ASC"
        )
        pools = cur.fetchall() or []
        return render_template(
            'admin/admin_verification.html',
            active_menu='verification',
            pending_transaction=pending_count,
            pools=pools,
            SITE_NAME=get_config_value("SITE_NAME"),
            SITE_LOGO=get_config_value("SITE_LOGO"),
            SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
            SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
            SITE_FAVICON=get_config_value("SITE_FAVICON"),
        )
    finally:
        cur.close()
        db.close()


@admin.route('/admin/pools/update', methods=['POST'])
@admin_login_required_query
def update_pool_label():
    """Update one pool's display_name / enabled / sort_order.

    Body (JSON or form):
      codename      str  required, must already exist in pool_labels
      display_name  str  optional, 1-100 chars
      enabled       0/1  optional
      sort_order    int  optional
    """
    data = request.get_json(silent=True) or request.form
    codename = (data.get('codename') or '').strip()
    if not codename:
        return jsonify(status='error', message='codename is required'), 400

    updates, params = [], []
    if 'display_name' in data:
        name = (data.get('display_name') or '').strip()
        if not name or len(name) > 100:
            return jsonify(status='error', message='display_name must be 1-100 chars'), 400
        updates.append('display_name = %s')
        params.append(name)
    if 'enabled' in data:
        try:
            updates.append('enabled = %s')
            params.append(1 if str(data.get('enabled')).lower() in ('1', 'true', 'on') else 0)
        except Exception:
            return jsonify(status='error', message='enabled must be 0/1'), 400
    if 'sort_order' in data:
        try:
            updates.append('sort_order = %s')
            params.append(int(data.get('sort_order')))
        except (ValueError, TypeError):
            return jsonify(status='error', message='sort_order must be int'), 400

    if not updates:
        return jsonify(status='info', message='nothing to update'), 200

    db, cur = db_start()
    try:
        params.append(codename)
        cur.execute(
            f"UPDATE pool_labels SET {', '.join(updates)} WHERE codename = %s",
            tuple(params)
        )
        db.commit()
        if cur.rowcount == 0:
            return jsonify(status='error', message='unknown codename'), 404
        return jsonify(status='success')
    finally:
        cur.close()
        db.close()


@admin.route('/admin/update-parent-api-key', methods=['POST'])
@admin_login_required_query
def update_parent_api_key():
    """Manually update the parent platform API key.

    This is the fallback path when the rotation webhook fails (e.g. operator
    typo'd the initial key during install, or wants to set up a new parent
    account). Normal rotations come in via /webhook/rotate-api-key.
    """
    new_key = (request.form.get('api_key') or request.values.get('api_key') or '').strip()
    if not new_key:
        return jsonify(status='error', message='API key is required'), 400
    if len(new_key) > 100:
        return jsonify(status='error', message='API key too long (max 100 chars)'), 400

    db, cur = db_start()
    try:
        cur.execute(
            "UPDATE site_settings SET api_key = %s, api_key_rotated_at = NOW() WHERE id = 1",
            (new_key,)
        )
        db.commit()
        return jsonify(status='success', last4=new_key[-4:])
    finally:
        cur.close()
        db.close()


@admin.route('/top-sales', methods=['GET'])
@admin_login_required_query
def top_sales():
    db, cur = db_start()
    try:
        query = """
                    SELECT country, service, COUNT(id) as num_sold, SUM(price) as total_price
                    FROM history
                    WHERE code IS NOT NULL
                    AND code != ''
                    AND code != '[]'
                    GROUP BY country, service
                    ORDER BY num_sold DESC
                    LIMIT 10
                    """
        cur.execute(query)
        results = cur.fetchall()

        tbody = ""
        row_id = 1
        if not results:
            tbody += "<tr><td align='center' colspan='5'>No data available</td></tr>"
        else:
            for row in results:
                country = row['country']
                service = row['service']
                num_sold = row['num_sold']
                total_price = row['total_price']
                avg_price = total_price / num_sold if num_sold else 0
                tbody += "<tr>"
                tbody += f"<th scope='row'>{row_id}</th></th>"
                tbody += f"<td>{country} - {service}</td>"
                tbody += f"<td>₦{'{:,.2f}'.format(avg_price)}</td>"
                tbody += f"<td>{num_sold}</td>"
                tbody += f"<td>₦{'{:,.2f}'.format(total_price)}</td>"
                tbody += "</tr>"
                row_id += 1

        return jsonify({'status': 'Table Loaded', 'data': tbody}), 200
    finally:
        cur.close()
        db.close()


@admin.route('/recent-sales', methods=['GET'])
@admin_login_required_query
def recent_sales():
    db, cur = db_start()
    try:
        query = """
                    SELECT h.id, h.user_id, h.service, h.country, h.price, h.status, u.email
                    FROM history h
                    LEFT JOIN users u ON h.user_id = u.user_id
                    ORDER BY h.id DESC
                    LIMIT 5
                    """
        cur.execute(query)
        results = cur.fetchall()

        tbody = ""
        for record in results:
            status = {
                "Received": '<span class="badge bg-warning">Received</span>',
                "Finished": '<span class="badge bg-success">Finished</span>',
                "Canceled": '<span class="badge bg-danger">Canceled</span>',
                "Timeout": '<span class="badge bg-warning">Timeout</span>'
            }.get(record['status'], "")

            # Build the table row
            tbody += "<tr>"
            tbody += f"<th scope='row'>{record['id']}</th></th>"
            tbody += f"<td>{record['email']}</td>"
            tbody += f"<td>{record['service']} {record['country']}</td>"
            tbody += f"<td>₦{'{:,.2f}'.format(float(record['price']))}</td>"
            tbody += f"<td>{status}</td>"
            tbody += "</tr>"

        return jsonify({'status': 'Table Loaded', 'data': tbody}), 200
    finally:
        cur.close()
        db.close()


@admin.route('/admin_orders', methods=['GET'])
@admin_login_required_query
def admin_orders_get():
    db, cur = db_start()
    try:
        # Get parameters from DataTables
        draw = request.args.get('draw', type=int)
        start = request.args.get('start', type=int, default=0)
        length = request.args.get('length', type=int, default=10)
        search_value = request.args.get('search[value]', default='')

        # Base query
        query = "SELECT * FROM history"
        count_query = "SELECT COUNT(*) as count FROM history"

        # Apply search if present
        if search_value:
            search_clause = f" WHERE id LIKE '%{search_value}%' OR service LIKE '%{search_value}%' OR country LIKE '%{search_value}%' OR Number LIKE '%{search_value}%'"
            query += search_clause
            count_query += search_clause

        # Get total count
        cur.execute(count_query)
        total_count = cur.fetchone()['count']

        # Apply sorting (assuming sorting by date in descending order)
        query += " ORDER BY date DESC"

        # Apply pagination
        query += f" LIMIT {length} OFFSET {start}"

        # Execute the final query
        cur.execute(query)
        rows = cur.fetchall()

        result = {'data': []}
        for row in rows:
            if row['status'] == "Received":
                status = (f'<span class="order-btn" tabindex="0"> <i class="fa-solid fa-hourglass-start '
                          f'text-warning order-btn-i"></i><span class="order-btn-span"></span></span>')
            elif row['status'] == "Finished":
                status = (f'<span class="order-btn" tabindex="0" aria-label="Finished"><i '
                          f'class="fa-regular fa-circle-check text-success order-btn-i"></i><span '
                          f'class="order-btn-span"></span></span>')
            elif row['status'] == "Canceled":
                status = (f'<span class="order-btn" tabindex="0" aria-label="Canceled"><i '
                          f'class="fa-regular fa-circle-xmark text-danger order-btn-i"></i><span '
                          f'class="order-btn-span"></span></span>')
            elif row['status'] == "Timeout":
                status = (f'<span class="order-btn" tabindex="0" aria-label="Timeout"><i '
                          f'class="fa-regular fa-clock text-warning order-btn-i"></i><span '
                          f'class="order-btn-span"></span></span>')
            else:
                status = ""

            date = row['date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row['date'], datetime) else row['date']
            price = '{:,.2f}'.format(float(row['price'])) if row['price'] else '0.00'

            db_code = get_code_from_db(row['code'])
            code = ""
            if db_code:
                for codes in db_code:
                    if codes is not None:
                        code += str(codes) + "<br>"

            action = ''
            if row['status'] == "Finished":
                query = "SELECT * FROM transactions WHERE processor = 'Admin adjustment - {}'".format(row['id'])
                cur.execute(query)
                history = cur.fetchone()
                if not history:
                    action = (f'<button type="button" class="btn btn-outline-info btn-block btn-flat cancel-order" '
                              f'data-order_no="{row["id"]}"><i class="fa fa-rotate"></i> Cancel Order</button>')

            result['data'].append({
                'id': row['id'],
                'date': date,
                'service': row['service'],
                'country': row['country'],
                'Number': row['Number'],
                'Code': code,
                'amount': f"₦{price}",
                'status': status,
                'action': action
            })

        # Add DataTables required data
        result['draw'] = draw
        result['recordsTotal'] = total_count
        result['recordsFiltered'] = total_count

        # Convert the result to JSON
        json_result = json.dumps(result, default=str)
        return json_result, 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/view_pending_funds', methods=['GET'])
@admin_login_required_query
def view_pending_funds():
    db, cur = db_start()
    try:
        # Format the result data
        result = {'data': []}

        # Execute the query
        query = "SELECT * FROM transactions WHERE type='manual' AND status='Pending'"
        cur.execute(query)

        # Fetch all the results
        transactions = cur.fetchall()

        for transaction in transactions:
            result['data'].append({
                'id': transaction['transaction_id'],
                'date': transaction['date'],  # Format date as string
                'amount': f"₦{transaction['amount']}",
                'sender_name': transaction['sender_name'],
                'view_receipt': f"<a id='view-btn' data-image_path='{transaction['image']}' data-transaction_id='{transaction['transaction_id']}' "
                                f"class='badge bg-primary'>View Receipt</a>",
                'action': f"<a id='approve-btn' data-transaction_id='{transaction['transaction_id']}' data-sender_name='{transaction['sender_name']}' data"
                          f"-amount='{transaction['amount']}' class='badge bg-success'>Approve</a>    <a id='disapprove-btn' "
                          f"data-transaction_id='{transaction['transaction_id']}'"
                          f"class='badge bg-danger'>Decline</a>"
            })

        # Convert the result to JSON
        json_result = jsonify(result)
        return json_result, 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin/cancel_order', methods=['POST'])
@admin_login_required_query
def admin_cancel():
    db, cur = db_start()
    try:
        data = request.get_json()
        order_no = data['order_no']
        query = "SELECT * FROM history WHERE id = %s"
        cur.execute(query, (order_no,))
        history_obj = cur.fetchone()

        if not history_obj:
            return jsonify({'status': 'Error'}), 400

        query = ("INSERT INTO transactions (transaction_id, date, amount, user_id, status, type, processor) "
                 "VALUES (%s, %s, %s, %s, %s, %s, %s)")
        cur.execute(query, (
            generate_unique_tx_number(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            Decimal(history_obj['price']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            history_obj['user_id'],
            "Finished",
            "instant",
            f"Admin adjustment - {history_obj['id']}"
        ))
        db.commit()
        return jsonify({'status': 'success'}), 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin_users', methods=['GET'])
@admin_login_required_query
def admin_users_get():
    db, cur = db_start()
    try:
        cur.execute("SELECT * FROM users")
        query = cur.fetchall()
        # Format the result data
        result = {'data': []}
        x = 1
        for user in query:
            user = User(**user)
            if user.user_status == "1":
                action = (f"<a data-user_id='{user.user_id}' class='badge bg-danger ban-btn' "
                          f"style='cursor: pointer;'>Ban</a>   <a href='/admin/history/{user.user_id}' "
                          f"class='badge bg-primary' style='cursor: pointer;'>View History</a>")
            else:
                action = (f"<a data-user_id='{user.user_id}' data-reason ='{user.reason}' "
                          f"class='badge bg-success unban-btn' style='cursor: pointer;'>Unban</a>  "
                          f"<a href='/admin/history/{user.user_id}' class='badge bg-primary' style='cursor: pointer;'>"
                          f"View History</a>"),
            result['data'].append({
                'id': x,
                'username': user.username,
                'email': user.email,
                'wallet_balance': f"₦{user.wallet_balance}",
                'action': action
            })
            x = x + 1
        # Convert the result to JSON
        json_result = json.dumps(result)

        return json_result, 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/unban_user', methods=['POST'])
@admin_login_required_query
def unban_user():
    db, cur = db_start()
    try:
        user_id = request.form['user_id']
        cur.execute("""
                        UPDATE users
                        SET user_status = 1, reason = ''
                        WHERE user_id = %s
                    """, (user_id,))
        db.commit()
        return jsonify({'message': 'Unban User successfully'}), 206
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/ban_user', methods=['POST'])
@admin_login_required_query
def ban_user():
    db, cur = db_start()
    try:
        user_id = request.form['user_id']
        reason = request.form['reason']
        cur.execute("""
                        UPDATE users
                        SET user_status = 0, reason = %s
                        WHERE user_id = %s
                    """, (reason, user_id))
        db.commit()
        return jsonify({'message': 'Ban User successfully'}), 206
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin_load_transactions', methods=['GET'])
@admin_login_required_query
def load_admin_transactions():
    db, cur = db_start()
    try:
        user_id = request.args['username']

        query = f"""
                        SELECT 
                            date,
                            type,
                            amount,
                            service,
                            country,
                            status,
                            processor,
                            transaction_id,
                            FORMAT(
                                @running_balance := @running_balance + 
                                IF(type IN ('instant', 'manual') AND status = 'Finished', 
                                   amount, 
                                   IF(status IN ('Finished', 'Received'), 
                                      -amount, 
                                      0)
                                  ),
                                2
                            ) AS balance
                        FROM (
                            SELECT date, type, amount, NULL AS service, NULL AS country, status, processor, transaction_id 
                            FROM transactions 
                            WHERE user_id = {user_id}
                            UNION ALL
                            SELECT date, NULL AS type, price AS amount, service, country, status, NULL AS processor, id AS transaction_id 
                            FROM history 
                            WHERE user_id = {user_id}
                        ) AS combined_result
                        CROSS JOIN (SELECT @running_balance := 0) AS init
                        ORDER BY STR_TO_DATE(date, '%Y-%m-%d %H:%i:%s.%f') ASC;
                    """
        # Execute SQL Statement
        cur.execute(query)
        # Fetch all the results
        transactions = cur.fetchall()

        # Process the results
        table_data = {'data': []}
        x = len(transactions)
        for transaction in transactions:
            transaction = Transaction(**transaction)

            if transaction.status == "Finished":
                status = "<span class='badge bg-success'>Finished</span>"
            elif transaction.status == "Failed":
                status = "<span class='badge bg-danger'>Failed</span>"
            elif transaction.status == "Canceled":
                status = "<span class='badge bg-danger'>Cancelled</span>"
            elif transaction.status == "Received":
                status = "<span class='badge bg-warning'>Received</span>"
            elif transaction.status == "Pending":
                status = f"<button class='bg-warning' id='pending_button' transaction_id='{transaction.transaction_id}'>Query</button>"
            elif transaction.status == "Timeout":
                status = "<span class='badge bg-warning'>Timeout</span>"
            else:
                status = ""
            if transaction.processor is None:
                processor = 'vpay'
            else:
                processor = transaction.processor
            if transaction.type == "instant":
                transaction_type = "Instant Deposit - {}".format(processor)
            elif transaction.type == "manual":
                transaction_type = "Manual Deposit"
            else:
                transaction_type = transaction.type

            if transaction.type in ["instant", "manual"] and transaction.status == 'Finished':
                text_class = 'text-success'
            elif transaction.type not in ["instant", "manual"] and transaction.status == 'Finished':
                text_class = 'text-danger'
            else:
                text_class = ''
            table_data['data'].append({
                'id': x,
                'date': transaction.date,
                'operation': f"{transaction.service} - {transaction.country} - #{transaction.transaction_id}" if transaction.service and transaction.country else f"{transaction_type} - {transaction.transaction_id}",
                'amount': f"<span class='{text_class}'>₦{transaction.amount}</span>",
                'status': status,
                'balance': transaction.balance
            })
            x = x - 1

        # Convert the result to JSON
        json_result = json.dumps(table_data)

        return json_result, 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()


def bool_to_tinyint(value):
    return 1 if value else 0


@admin.route('/admin/payment_update', methods=['POST'])
@admin_login_required_query
def payment_update():
    """
    This function handles the POST request to update payment settings. It fetches the current settings from the database,
    compares them with the incoming data, and updates the necessary fields.

    Parameters:
    - None

    Returns:
    - A JSON response with the following structure:
      {
        'status': 'success' or 'info' or 'error',
        'message': A string describing the outcome of the operation.
      }
    """
    db, cur = db_start()
    try:
        data = request.get_json()

        # Fetch current settings
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))
        site_setting = cur.fetchone()

        updates = []
        params = []

        if data['method'] == 'korapay':
            if data['korapay_status'] != site_setting['korapay']:
                updates.append("korapay = %s")
                params.append(bool_to_tinyint(data['korapay_status']))

            if (data['korapay_secret_key'] is not None and
                    data['korapay_secret_key'] != site_setting['korapay_secret_key']):
                updates.append("korapay_secret_key = %s")
                params.append(data['korapay_secret_key'])

            if (data['korapay_public_key'] is not None and
                    data['korapay_public_key'] != site_setting['korapay_public_key']):
                updates.append("korapay_public_key = %s")
                params.append(data['korapay_public_key'])

        elif data['method'] == 'vpay':
            if data['vpay_status'] != site_setting['vpay']:
                updates.append("vpay = %s")
                params.append(bool_to_tinyint(data['vpay_status']))

            if (data['vpay_access_token'] is not None and
                    data['vpay_access_token'] != site_setting['vpay_access_token']):
                updates.append("vpay_access_token = %s")
                params.append(data['vpay_access_token'])

            if (data['vpay_public_key'] is not None and
                    data['vpay_public_key'] != site_setting['vpay_public_key']):
                updates.append("vpay_public_key = %s")
                params.append(data['vpay_public_key'])

            if (data['vpay_merchant_email'] is not None and
                    data['vpay_merchant_email'] != site_setting['vpay_merchant_email']):
                updates.append("vpay_merchant_email = %s")
                params.append(data['vpay_merchant_email'])

            if (data['vpay_merchant_password'] is not None and
                    data['vpay_merchant_password'] != site_setting['vpay_merchant_password']):
                updates.append("vpay_merchant_password = %s")
                params.append(data['vpay_merchant_password'])

        elif data['method'] == 'manual_funds':
            if data['manual_fund_status'] != site_setting['manual_payment']:
                updates.append("manual_payment = %s")
                params.append(bool_to_tinyint(data['manual_fund_status']))

            if data['manual_payment_bank'] is not None and data['manual_payment_bank'] != site_setting[
                'manual_payment_bank']:
                updates.append("manual_payment_bank = %s")
                params.append(data['manual_payment_bank'])

            if data['manual_payment_account_name'] is not None and data['manual_payment_account_name'] != site_setting[
                'manual_payment_account_name']:
                updates.append("manual_payment_account_name = %s")
                params.append(data['manual_payment_account_name'])

            if data['manual_payment_account'] is not None and data['manual_payment_account'] != site_setting[
                'manual_payment_account']:
                updates.append("manual_payment_account = %s")
                params.append(data['manual_payment_account'])

        if updates:
            update_query = f"UPDATE site_settings SET {', '.join(updates)} WHERE id = %s"
            params.append(1)  # for the WHERE clause
            cur.execute(update_query, tuple(params))
            db.commit()
            return jsonify({'status': 'success', 'message': 'Payment settings updated successfully'})
        else:
            return jsonify({'status': 'info', 'message': 'No changes detected'})
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/manual_fund', methods=['POST'])
@admin_login_required_query
def manual_funds():
    db, cur = db_start()
    try:
        transactionId = request.form['transactionId']

        # Get transaction
        cur.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transactionId,))
        transaction = cur.fetchone()

        if transaction:
            amount = Decimal(transaction['amount'])
            user_id = transaction['user_id']

            # Get user
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()

            if user:
                # Update transaction status
                cur.execute("UPDATE transactions SET status = 'Finished' WHERE transaction_id = %s",
                            (transactionId,))

                # Update user's wallet balance
                # Get User_id of user with username
                cur.execute("SELECT * FROM users WHERE user_id = %s", [user_id])
                query = cur.fetchone()
                user = User(**query)

                # Define the query
                query = f"""
                                SELECT FORMAT(balance, 2) AS balance
                                FROM (
                                  SELECT SUM(IF(type IN ('instant', 'manual') AND status = 'Finished', amount, IF(status IN ('Finished', 'Received'), -amount, 0))) AS balance
                                  FROM (
                                    SELECT date, type, amount, NULL AS service, NULL AS country, status FROM transactions WHERE user_id = {user_id}
                                    UNION ALL
                                    SELECT date, Null AS type, price AS amount, service, country, status FROM history WHERE user_id = {user_id}
                                  ) AS combined_result
                                ) AS subquery;
                            """

                # Execute the query with the user_uid parameter
                cur.execute(query)

                # Fetch the result
                balance = cur.fetchall()
                if balance[0]['balance'] is None:
                    user_balance = "0.00"
                else:
                    user_balance = balance[0]['balance'].replace(',', '')
                cur.execute("UPDATE users SET wallet_balance = %s WHERE user_id = %s", (user_balance, user_id))
                # Parse the input string to a datetime object
                dt = datetime.strptime(transaction['date'], "%Y-%m-%d %H:%M:%S")

                # Format the datetime object to the desired output
                output_date = dt.strftime("%B %d at %I:%M %p")

                db.commit()
                # Fetch user details
                cur.execute("SELECT username, email FROM users WHERE user_id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    return jsonify({'message': 'User not found'}), 404

                # Send email
                email_result, status = send_email(
                    subject="Payment Receipt",
                    recipients=[user['email']],
                    template="payment.html",
                    username=user['username'],
                    amount=amount,
                    transactionId=transactionId,
                    date=output_date
                )

                # Delete uploaded file if it exists (assuming transaction data is available)
                transaction = {'image': f"{transactionId}.jpg"}  # Mock transaction data; adjust as needed
                with app.app_context():
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    file_path = os.path.join(upload_folder, transaction['image'])
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"Deleted file: {file_path}")
                        except Exception as e:
                            print(f"Error deleting file: {e}")

                send_deposit_notification(
                    f"{user.email} | Just deposited ₦{amount} | Manually")
                return jsonify({'message': 'Payment Status Updated'}), 200
            else:
                return jsonify({'message': 'User not found'}), 404
        else:
            return jsonify({'message': 'Transaction not found'}), 404
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/decline_funding', methods=['POST'])
@admin_login_required_query
def decline_funding():
    db, cur = db_start()
    transactionId = request.form['transactionId']
    reason = request.form['reason']
    try:
        # Check if the transaction exists
        cur.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transactionId,))
        transaction = cur.fetchone()

        if transaction:
            # Update the transaction
            update_query = """
                   UPDATE transactions
                   SET status = 'Failed', reason = %s
                   WHERE transaction_id = %s
                   """
            cur.execute(update_query, (reason, transactionId))
            db.commit()
            with app.app_context():
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                file_path = os.path.join(upload_folder, transaction['image'])
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            return jsonify({'message': 'Payment Status Updated'}), 200
        else:
            return jsonify({'message': 'Transaction not found'}), 404
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin/verification_update', methods=['POST'])
@admin_login_required_query
def verification_update():
    """
    This function handles the POST request to update verification settings. It fetches the current settings from the database,
    compares them with the incoming data, and updates the necessary fields.

    Parameters:
    - None

    Returns:
    - A JSON response with the following structure:
      {
        'status': 'success' or 'info' or 'error',
        'message': A string describing the outcome of the operation.
      }
    """
    db, cur = db_start()
    try:
        data = request.get_json()

        # Fetch current settings
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))
        site_setting = cur.fetchone()

        updates = []
        params = []

        if data['method'] == 'daisysms':
            if data['provider_status'] != site_setting['daisy']:
                updates.append("daisy = %s")
                params.append(bool_to_tinyint(data['provider_status']))

            if (data['apikey'] is not None and
                    data['apikey'] != site_setting['daisy_api_key']):
                updates.append("daisy_api_key = %s")
                params.append(data['apikey'])

        elif data['method'] == 'grizzlysms':
            if data['provider_status'] != site_setting['grizzly']:
                updates.append("grizzly = %s")
                params.append(bool_to_tinyint(data['provider_status']))

            if (data['apikey'] is not None and
                    data['apikey'] != site_setting['grizzly_api_key']):
                updates.append("grizzly_api_key = %s")
                params.append(data['apikey'])
        elif data['method'] == 'smsbower':
            if data['provider_status'] != site_setting['smsbower']:
                updates.append("smsbower = %s")
                params.append(bool_to_tinyint(data['provider_status']))

            if (data['apikey'] is not None and
                    data['apikey'] != site_setting['smsbower_api_key']):
                updates.append("smsbower_api_key = %s")
                params.append(data['apikey'])
        elif data['method'] == '5sim':
            if data['provider_status'] != site_setting['5sim']:
                updates.append("5sim = %s")
                params.append(bool_to_tinyint(data['provider_status']))

            if (data['apikey'] is not None and
                    data['apikey'] != site_setting['5sim_api_key']):
                updates.append("5sim_api_key = %s")
                params.append(data['apikey'])
        elif data['method'] == 'smspool':
            if data['provider_status'] != site_setting['smspool']:
                updates.append("smspool = %s")
                params.append(bool_to_tinyint(data['provider_status']))

            if (data['apikey'] is not None and
                    data['apikey'] != site_setting['smspool_api_key']):
                updates.append("smspool_api_key = %s")
                params.append(data['apikey'])

        if updates:
            update_query = f"UPDATE site_settings SET {', '.join(updates)} WHERE id = %s"
            params.append(1)  # for the WHERE clause
            cur.execute(update_query, tuple(params))
            db.commit()
            return jsonify({'status': 'success', 'message': 'Payment settings updated successfully'})
        else:
            return jsonify({'status': 'info', 'message': 'No changes detected'})
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin/site_update', methods=['POST'])
@admin_login_required_query
def admin_site_update():
    db, cur = db_start()
    try:
        data = request.get_json()

        # Fetch current settings
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))
        site_setting = cur.fetchone()

        updates = []
        params = []

        if (data['profit'] is not None and
                data['profit'] != site_setting['current_profit']):
            updates.append("current_profit = %s")
            params.append(data['profit'])

        if updates:
            update_query = f"UPDATE site_settings SET {', '.join(updates)} WHERE id = %s"
            params.append(1)  # for the WHERE clause
            cur.execute(update_query, tuple(params))
            db.commit()
            # Fetch current settings
            query = "SELECT * FROM site_settings WHERE id = %s"
            cur.execute(query, (1,))
            site_setting = cur.fetchone()
            return jsonify({'status': 'success', 'profit': site_setting['current_profit']})
        else:
            return jsonify({'status': 'info', 'message': 'No changes detected'})
    finally:
        if db.is_connected():
            cur.close()
            db.close()


@admin.route('/admin/password_update', methods=['POST'])
@admin_login_required_query
def password_update():
    db, cur = db_start()
    try:
        data = request.get_json()
        currentPassword = data['current_password'].encode('utf-8')
        newPassword = data['password'].encode('utf-8')

        # Get the user from the database
        cur.execute("SELECT * FROM admin WHERE id = %s", (session['admin_id'],))
        result = cur.fetchone()

        if result is None:
            return jsonify({
                'status': "User not Found"
            }), 200

        admin = Admin(**result)
        stored_password = admin.password
        # Ensure stored_password is in bytes
        if isinstance(stored_password, str):
            stored_password = stored_password.encode('utf-8')

        # Ensure currentPassword is in bytes
        if isinstance(currentPassword, str):
            currentPassword = currentPassword.encode('utf-8')

        if bcrypt.check_password_hash(stored_password, currentPassword):
            # Password is correct
            new_hashed_password = bcrypt.generate_password_hash(newPassword).decode('utf-8')

            # Update the password in the database
            cur.execute("UPDATE admin SET password = %s WHERE id = %s",
                        (new_hashed_password, session['admin_id']))
            db.commit()

            return jsonify({
                'status': "success",
            }), 200
        else:
            return jsonify({
                'status': "Incorrect Password",
            }), 200
    finally:
        if db.is_connected():
            cur.close()
            db.close()
