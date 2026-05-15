import os
import time

import requests
from requests.exceptions import RequestException  # Correct way to import exception handling

from flask_bcrypt import Bcrypt

from config import get_config_value
from db_conn import db_start

bcrypt = Bcrypt()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def _telegram_send(token: str, chat_id, message: str, timeout: int = 10) -> bool:
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=timeout)
        return True
    except RequestException:
        return False


def send_deposit_notification(message):
    bot_deposit_api = get_config_value("BOT_DEPOSIT_API")
    chat_id = int(get_config_value("CHAT_ID"))
    url = f"https://api.telegram.org/{bot_deposit_api}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, json=data)


def send_balance_notification(message):
    _telegram_send(
        os.environ.get("BALANCE_TELEGRAM_BOT_TOKEN", ""),
        os.environ.get("BALANCE_TELEGRAM_CHAT_ID", ""),
        message,
    )


def send_site_notification(message, max_retries=3, retry_delay=5, timeout=10):
    token   = os.environ.get("SITE_TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("SITE_TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return  # Notifications disabled — env not configured

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            return
        except RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)


def send_manual_notification(message):
    bot_api = get_config_value("BOT_MANUAL_API")
    chat_id = int(get_config_value("CHAT_ID"))
    url = F"https://api.telegram.org/{bot_api}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, json=data)


def generate_activation_id():
    db, cur = db_start()
    try:
        cur.execute("SELECT id FROM history ORDER BY id DESC LIMIT 1")
        last_row = cur.fetchone()
        if last_row:
            return last_row[0] + 1
        else:
            return 1
    finally:
        cur.close()
        db.close()
