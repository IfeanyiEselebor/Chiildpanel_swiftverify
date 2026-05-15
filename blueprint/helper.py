import json
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from flask import Response, session

from db_conn import db_start, User


def get_user_balance():
    db, cur = db_start()
    try:
        query = "SELECT * FROM users WHERE user_id = %s"
        cur.execute(query, (session['user_id'],))
        result = cur.fetchone()

        if result:
            user_query = User(**result)
            if user_query.wallet_balance != User.get_wallet_balance(user_query):
                wallet_balance = Decimal(User.get_wallet_balance(user_query))
                wallet_balance = wallet_balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                update_query = "UPDATE users SET wallet_balance = %s WHERE user_id = %s"
                cur.execute(update_query, (wallet_balance, user_query.user_id))
                db.commit()
                return wallet_balance
            return user_query.wallet_balance
    finally:
        cur.close()
        db.close()


def create_response(history):
    response_data = OrderedDict([
        ("id", history.id),
        ("phone", history.Number),
        ("pool", history.source),
        ("product", history.service),
        ("price", history.price),
        ("status", history.status),
        ("expires", history.expiration_time),
        ("sms", history.code),
        ("created_at", history.date),
        ("country", history.country),
        ("balance", float(get_user_balance()))
    ])
    return Response(json.dumps(response_data), mimetype='application/json')


def calculate_profit(base_price, current_profit):
    if isinstance(current_profit, str) and current_profit.endswith("%"):
        return (float(current_profit.strip("%")) / 100) * base_price
    return float(current_profit)