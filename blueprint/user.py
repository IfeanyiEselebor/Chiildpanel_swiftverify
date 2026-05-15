import json
import secrets

import mysql.connector
from flask import Blueprint, render_template, jsonify, session

from LoginManager.login_manager import login_required, login_required_query
from blueprint.helper import get_user_balance
from config import get_config_value
from db_conn import db_start, History, Transaction

user = Blueprint('user', __name__)


@user.route('/dashboard', methods=['GET'])
@login_required
def user_dashboard():
    return render_template("user/dashboard.html",
                           SITE_NAME=get_config_value("SITE_NAME"),
                           SITE_LOGO=get_config_value("SITE_LOGO"),
                           SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                           SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                           SITE_FAVICON=get_config_value("SITE_FAVICON"),
                           reviews=get_config_value("reviews"),
                           SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT"),
                           THEME_MODE=get_config_value("THEME_MODE"),
                           THEME_CONTRAST=get_config_value("THEME_CONTRAST"),
                           THEME_COLOUR=get_config_value("THEME_COLOUR"),
                           THEME_LAYOUT=get_config_value("THEME_LAYOUT"),
                           THEME_LAYOUT_WIDTH=get_config_value("THEME_LAYOUT_WIDTH"),
                           THEME_LAYOUT_DIRECTION=get_config_value("THEME_LAYOUT_DIRECTION"),
                           THEME_SIDEBAR_CAPTION=get_config_value("THEME_SIDEBAR_CAPTION"),
                           wallet_balance=get_user_balance(),
                           user_name=session['username']
                           )


@user.route('/get_history', methods=['GET'])
@login_required_query
def get_history():
    db, cur = db_start()
    if not db or not cur:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        query = """
            SELECT id, date, service, country, price, Number AS phone_number, code, status, 
                   user_id, expiration_time, duration, check_status, repeatable
            FROM history
            WHERE user_id = %s
            ORDER BY date DESC
        """
        cur.execute(query, (session['user_id'],))
        history_records = cur.fetchall()

        # Convert records to History objects and prepare response
        history_list = [History(**record).__dict__ for record in history_records]
        return jsonify({'history': history_list})

    except mysql.connector.Error as e:
        print(f"Query Error: {e}")
        return jsonify({'error': 'Failed to fetch history'}), 500
    finally:
        cur.close()
        db.close()


@user.route('/fund-wallet', methods=['GET'])
@login_required
def fund_wallet():
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
        vpay_public_key = site_setting['vpay_public_key']
        korapay_public_key = site_setting['korapay_public_key']
        payment = {
            'method': {
                'vpay': vpay,
                'korapay': korapay,
                'manual_payment': manual_pay
            },
            'manual_payment_account': manual_payment_account,
            'manual_payment_account_name': manual_payment_account_name,
            'manual_payment_bank': manual_payment_bank
        }
    finally:
        cur.close()
        db.close()
    return render_template('user/fund_wallet.html',
                           wallet_balance=get_user_balance(),
                           payment=payment,
                           vpay_public_key=vpay_public_key,
                           korapay_public_key=korapay_public_key,
                           SITE_NAME=get_config_value("SITE_NAME"),
                           SITE_LOGO=get_config_value("SITE_LOGO"),
                           SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                           SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                           SITE_FAVICON=get_config_value("SITE_FAVICON"),
                           reviews=get_config_value("reviews"),
                           SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT"),
                           THEME_MODE=get_config_value("THEME_MODE"),
                           THEME_CONTRAST=get_config_value("THEME_CONTRAST"),
                           THEME_COLOUR=get_config_value("THEME_COLOUR"),
                           THEME_LAYOUT=get_config_value("THEME_LAYOUT"),
                           THEME_LAYOUT_WIDTH=get_config_value("THEME_LAYOUT_WIDTH"),
                           THEME_LAYOUT_DIRECTION=get_config_value("THEME_LAYOUT_DIRECTION"),
                           THEME_SIDEBAR_CAPTION=get_config_value("THEME_SIDEBAR_CAPTION")
                           )


@user.route('/load-orders', methods=['GET'])
@login_required_query
def load_orders():
    db, cur = db_start()
    try:
        # Fetch Users Deposit History From Database
        # Execute the query
        query = "SELECT * FROM transactions WHERE user_id = %s"
        cur.execute(query, (session['user_id'],))

        # Fetch all the results
        transactions = cur.fetchall()

        result = {'data': []}
        for transaction in transactions:
            transaction = Transaction(**transaction)
            if transaction.status == "Finished":
                status = "<span class='badge bg-success'>Finished</span>"
            elif transaction.status == "Failed":
                status = "<span class='badge bg-danger'>Failed</span>"
            elif transaction.status == "Pending":
                status = f"<a id='query-btn' data-transaction_id='{transaction.transaction_id}' class='badge bg-primary'>Query</a>"
            else:
                status = ""
            if transaction.processor:
                type = f" - {transaction.processor}"
            else:
                if transaction.type == 'instant':
                    type = " - vpay"
                else:
                    type = ""
            # Convert datetime to string before adding to result
            date_str = transaction.date.strftime('%Y-%m-%d %H:%M:%S') if transaction.date else None
            result['data'].append({
                'transaction_id': transaction.transaction_id,
                'amount': f"₦{transaction.amount}",
                'date': date_str,
                'status': status,
                'payment_type': f"{transaction.type}{type}",
                'reason': transaction.reason
            })

        # Convert the result to JSON
        json_result = json.dumps(result)

        return json_result, 200
    finally:
        cur.close()
        db.close()


@user.route('/history', methods=['GET'])
@login_required
def transaction_history():
    db, cur = db_start()
    try:
        # Execute the query
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))

        # Fetch the result
        site_setting = cur.fetchone()
    finally:
        cur.close()
        db.close()
    return render_template('user/transaction_history.html',
                           wallet_balance=get_user_balance(),
                           SITE_NAME=get_config_value("SITE_NAME"),
                           SITE_LOGO=get_config_value("SITE_LOGO"),
                           SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                           SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                           SITE_FAVICON=get_config_value("SITE_FAVICON"),
                           reviews=get_config_value("reviews"),
                           SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT"),
                           THEME_MODE=get_config_value("THEME_MODE"),
                           THEME_CONTRAST=get_config_value("THEME_CONTRAST"),
                           THEME_COLOUR=get_config_value("THEME_COLOUR"),
                           THEME_LAYOUT=get_config_value("THEME_LAYOUT"),
                           THEME_LAYOUT_WIDTH=get_config_value("THEME_LAYOUT_WIDTH"),
                           THEME_LAYOUT_DIRECTION=get_config_value("THEME_LAYOUT_DIRECTION"),
                           THEME_SIDEBAR_CAPTION=get_config_value("THEME_SIDEBAR_CAPTION")
                           )



@user.route('/load-transactions', methods=['GET'])
@login_required_query
def load_transaction():
    db, cur = db_start()
    # Fetch Users Deposit History and Users Orders History From Database
    sql_statement = f"""
               SELECT 
                    date,
                    type,
                    amount,
                    service,
                    country,
                    status,
                    transaction_id,
                    FORMAT(
                        (
                            SELECT SUM(
                                IF(t2.type IN ('instant', 'manual') AND t2.status = 'Finished', 
                                   t2.amount, 
                                   IF(t2.status IN ('Finished', 'Received'), 
                                      -t2.amount, 
                                      0)
                                  )
                            )
                            FROM (
                                SELECT date, type, amount, NULL AS service, NULL AS country, status, transaction_id 
                                FROM transactions 
                                WHERE user_id = {session['user_id']}
                                UNION ALL
                                SELECT date, NULL AS type, price AS amount, service, country, status, id AS transaction_id 
                                FROM history 
                                WHERE user_id = {session['user_id']}
                            ) t2
                            WHERE STR_TO_DATE(t2.date, '%Y-%m-%d %H:%i:%s') <= 
                                  STR_TO_DATE(t1.date, '%Y-%m-%d %H:%i:%s')
                        ), 
                        2
                    ) AS balance
                FROM (
                    SELECT date, type, amount, NULL AS service, NULL AS country, status, transaction_id 
                    FROM transactions 
                    WHERE user_id = {session['user_id']}
                    UNION ALL
                    SELECT date, NULL AS type, price AS amount, service, country, status, id AS transaction_id 
                    FROM history 
                    WHERE user_id = {session['user_id']}
                ) t1
                ORDER BY STR_TO_DATE(date, '%Y-%m-%d %H:%i:%s') ASC;
            """

    # Execute SQL Statement
    cur.execute(sql_statement)
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
            status = f"<span class='badge bg-warning'>Received</span>"
        elif transaction.status == "Pending":
            status = f"<span class='badge bg-warning'>Pending</span>"
        elif transaction.status == "Timeout":
            status = f"<span class='badge bg-warning'>Timeout</span>"
        else:
            status = ""
        if transaction.type == "instant":
            transaction_type = "Instant Deposit"
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
        # Convert datetime to string before adding to result
        date_str = transaction.date.strftime('%Y-%m-%d %H:%M:%S') if transaction.date else None
        table_data['data'].append({
            'id': x,
            'date': date_str,
            'operation': f"{transaction.service} - {transaction.country} - #{transaction.transaction_id}" if transaction.service and transaction.country else f"{transaction_type} - {transaction.transaction_id}",
            'amount': f"<span class='{text_class}'>₦{transaction.amount}</span>",
            'status': status,
            'balance': transaction.balance
        })
        x = x - 1

    # Convert the result to JSON
    json_result = json.dumps(table_data)

    return json_result, 200


@user.route('/settings', methods=['GET'])
@login_required
def settings():
    db, cur = db_start()
    try:
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

        # Execute the query
        query = "SELECT * FROM site_settings WHERE id = %s"
        cur.execute(query, (1,))

        # Fetch the result
        site_setting = cur.fetchone()
        return render_template('user/settings.html',
                               wallet_balance=get_user_balance(),
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               reviews=get_config_value("reviews"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT"),
                               THEME_MODE=get_config_value("THEME_MODE"),
                               THEME_CONTRAST=get_config_value("THEME_CONTRAST"),
                               THEME_COLOUR=get_config_value("THEME_COLOUR"),
                               THEME_LAYOUT=get_config_value("THEME_LAYOUT"),
                               THEME_LAYOUT_WIDTH=get_config_value("THEME_LAYOUT_WIDTH"),
                               THEME_LAYOUT_DIRECTION=get_config_value("THEME_LAYOUT_DIRECTION"),
                               THEME_SIDEBAR_CAPTION=get_config_value("THEME_SIDEBAR_CAPTION")
                               )
    finally:
        cur.close()
        db.close()


@user.route('/api_update', methods=['GET'])
@login_required_query
def api_update():
    db, cur = db_start()
    try:
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
            'status': 'success',
            'apikey': session['apikey']
        })
    finally:
        cur.close()
        db.close()


