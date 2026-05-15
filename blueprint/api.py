import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from flask import Blueprint, request, session, jsonify

import swiftverify_client as sv
from blueprint.helper import get_user_balance, create_response
from db_conn import db_start, User, History

api = Blueprint('api', __name__)

# Must match the parent's ROTATION_WEBHOOK_TIMESTAMP_DRIFT.
ROTATION_TIMESTAMP_DRIFT = 300


@api.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin',
                         '*')  # Allow all origins (change '*' to a specific domain if needed)
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Api-Key")
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
    return response


def authenticate_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        db, cur = db_start()
        try:
            # Mirror the parent's contract: header takes precedence, then
            # falls back to ?api_key= (querystring) or form-body api_key.
            api_key = request.headers.get('X-Api-Key') or request.values.get('api_key')
            if not api_key:
                return "BAD_KEY", 401

            query = "SELECT * FROM users WHERE api_key = %s"
            cur.execute(query, (api_key,))
            result = cur.fetchone()

            if not result:
                return "BAD_KEY", 401

            user = User(**result)
            if user.user_status == '0':
                return "BAD_KEY", 401
            session['user_id'] = result['user_id']
            # If authentication is successful, call the original function
            return func(*args, **kwargs)
        finally:
            cur.close()
            db.close()

    return wrapper


@api.route('/api/getNumber', methods=['GET'])
@authenticate_api_key
def get_number():
    """
    Retrieves a random phone number for a given country and service with authentication.

    Returns:
        - JSON response with the phone number details or an error message.
    """
    cost = None
    db, cur = db_start()
    try:
        # Get parameters
        service = request.args.get('service')
        country = request.args.get('country')
        pool = request.args.get('pool')
        max_price = request.args.get('max_price')
        areas = request.args.get('areas')
        carriers = request.args.get('carriers')
        number = request.args.get('number')
        # Validate required parameters
        if not service:
            return "BAD_SERVICE", 400
        if not country:
            return "BAD_COUNTRY", 400
        if not pool:
            return "NO_POOL", 400

        # Retrieve site settings
        cur.execute("SELECT * FROM site_settings WHERE id = %s", (1,))
        site_setting = cur.fetchone()
        if not site_setting:
            return "SITE_SETTINGS_ERROR", 500
        current_profit = int(site_setting['current_profit'])
        api_key = site_setting['api_key']

        # Resolve pool: accept either the canonical codename (Alpha/Bravo/…)
        # OR the operator's display_name. The parent only understands the
        # codename, so we always send that. Also enforce pool_labels.enabled.
        cur.execute(
            "SELECT codename, enabled FROM pool_labels "
            "WHERE codename = %s OR display_name = %s",
            (pool, pool)
        )
        label_row = cur.fetchone()
        if label_row:
            if not label_row.get('enabled'):
                return "BAD_POOL", 400
            pool = label_row['codename']
        # else: unknown — pass through; parent will reject with INVALID_POOL.

        # Validate wallet balance
        wallet_balance = Decimal(get_user_balance())
        if max_price:
            amount = Decimal(max_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cost = Decimal((float(amount) - current_profit)).quantize(Decimal('0.01'),
                                                                      rounding=ROUND_HALF_UP)
            if wallet_balance < amount:
                return "NO_MONEY", 403

        # Process order based on source
        try:
            result = sv.get_number(
                api_key, service, country, pool,
                max_price=cost if max_price else None,
                areas=areas, carriers=carriers, number=number,
            )
            if not result.ok:
                # Parent returns 'NO_MONEY' when our reseller wallet on the
                # parent side is short — surface as NO_NUMBERS to our user.
                if result.error == 'NO_MONEY':
                    return "NO_NUMBERS", 404
                return result.error or "NO_NUMBERS", 404
            response_data = result.data
            wallet_balance = Decimal(get_user_balance()) - Decimal(
                float(response_data["price"]) + int(site_setting['current_profit']))
            if wallet_balance < 0:
                # Refund on parent — user couldn't afford after markup.
                sv.set_status(api_key, response_data['id'], 8)
                return "NO_MONEY", 403

            created_at = datetime.strptime(response_data["created_at"], "%Y-%m-%d %H:%M:%S")
            expires_at = datetime.strptime(response_data["expires"], "%Y-%m-%d %H:%M:%S")
            sql = """
            INSERT INTO history
            (date, service, country, price, Number, code, status, user_id, activation_id, expiration_time,
            duration, source, check_status, repeatable)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                response_data["product"], response_data["country"],
                str(float(response_data["price"]) + int(site_setting['current_profit'])),
                response_data["phone"], None, response_data["status"], session['user_id'],
                response_data["id"], expires_at,
                response_data["duration"], response_data["pool"], response_data["check_status"],
                response_data["repeatable"]
            )
            cur.execute(sql, values)
            db.commit()
            cur.execute("SELECT * FROM history WHERE activation_id = %s", (str(response_data["id"]),))
            history = cur.fetchone()
            return create_response(History(**history)), 200
        except Exception as e:
            print(e)
            return "NO_NUMBERS", 404

    except Exception as e:
        return "NO_NUMBERS", 404
    finally:
        cur.close()
        db.close()


@api.route('/api/getStatus', methods=['GET'])
@authenticate_api_key
def get_status():
    id = request.args.get('id')
    db, cur = db_start()
    try:
        # Retrieve site settings
        cur.execute("SELECT * FROM site_settings WHERE id = %s", (1,))
        site_setting = cur.fetchone()
        if not site_setting:
            return "SITE_SETTINGS_ERROR", 500
        api_key = site_setting['api_key']

        # Execute a SELECT query to get order information
        query = "SELECT * FROM history WHERE id = %s and user_id = %s"
        cur.execute(query, (id, session['user_id']))
        history_obj = cur.fetchone()
        if history_obj:
            history = History(**history_obj)
            result = sv.get_status(api_key, history.activation_id)
            if not result.ok:
                return result.error or 'NO_ACTIVATION'
            response_data = result.data or {}
            parent_status = response_data.get('status')
            parent_id     = response_data.get('id')
            if not parent_status or parent_id is None:
                # Parent returned 200 with an unexpected body — surface as-is
                # to the dashboard so we don't silently corrupt the local row.
                return create_response(history), 200
            sms_list = response_data.get('sms') or []
            if parent_status == "Received" and sms_list:
                code_list_filtered = json.dumps([c for c in sms_list if c and c.strip()])
                cur.execute(
                    "UPDATE history SET code = %s WHERE activation_id = %s",
                    (code_list_filtered, parent_id)
                )
                db.commit()
            elif parent_status == "Timeout":
                cur.execute("UPDATE history SET status='Timeout' WHERE activation_id=%s", (parent_id,))
                db.commit()
            elif parent_status == "Canceled":
                cur.execute("UPDATE history SET status='Canceled' WHERE activation_id=%s", (parent_id,))
                db.commit()
            elif parent_status == "Finished":
                code_list_filtered = json.dumps([c for c in sms_list if c and c.strip()])
                cur.execute(
                    "UPDATE history SET status = %s, code = %s WHERE activation_id = %s",
                    ("Finished", code_list_filtered, parent_id)
                )
                db.commit()
            # Re-fetch so the response reflects the row we just wrote.
            cur.execute("SELECT * FROM history WHERE activation_id = %s", (str(parent_id),))
            history = cur.fetchone()

            return create_response(History(**history)), 200
        else:
            return 'NO_ACTIVATION'
    finally:
        cur.close()
        db.close()


@api.route('/api/setStatus', methods=['GET'])
@authenticate_api_key
def set_status():
    id = (request.values.get('id') or '').strip()
    raw_status = (request.values.get('status') or '').strip()
    if not id or not raw_status:
        return 'BAD_STATUS', 400
    try:
        status = int(raw_status)
    except ValueError:
        return 'BAD_STATUS', 400
    if status not in (3, 6, 8):
        return 'BAD_STATUS', 400
    db, cur = db_start()
    try:
        # Retrieve site settings
        cur.execute("SELECT * FROM site_settings WHERE id = %s", (1,))
        site_setting = cur.fetchone()
        if not site_setting:
            return "SITE_SETTINGS_ERROR", 500
        api_key = site_setting['api_key']

        query = "SELECT * FROM history WHERE id = %s and user_id = %s"
        cur.execute(query, (id, session['user_id']))
        history_obj = cur.fetchone()
        if not history_obj:
            return 'NO_ACTIVATION'
        history = History(**history_obj)
        if status == 8:
            result = sv.set_status(api_key, history.activation_id, 8)
            if result.ok and isinstance(result.data, dict) and 'sms' in result.data:
                # Cancel succeeded with codes (rare — parent had codes when cancelled)
                code_list_filtered = json.dumps([c for c in result.data['sms'] if c and c.strip()])
                cur.execute("UPDATE history SET code = %s WHERE id = %s", (code_list_filtered, id))
                db.commit()
                cur.execute("SELECT * FROM history WHERE id = %s", (id,))
                return create_response(History(**cur.fetchone()))
            # All other shapes are plain text: BAD_STATUS / EARLY_CANCEL_DENIED /
            # ACCESS_CANCEL — surface verbatim. ACCESS_CANCEL can now also arrive
            # as a JSON envelope {"status":"ACCESS_CANCEL","balance":…}.
            if result.ok and isinstance(result.data, dict) and result.data.get('status') == 'ACCESS_CANCEL':
                return 'ACCESS_CANCEL'
            return result.error or 'BAD_STATUS'
        if status == 3:
            result = sv.set_status(api_key, history.activation_id, 3)
            if result.error == 'ACCESS_RETRY_GET':
                return 'ACCESS_RETRY_GET'
            if result.error == 'BAD_STATUS':
                return 'BAD_STATUS'
            return result.error or 'BAD_STATUS'
        if status == 6:
            result = sv.set_status(api_key, history.activation_id, 6)
            if result.error == 'BAD_STATUS':
                return 'BAD_STATUS'
            if result.error == 'Number Activation Finished' or (
                    result.ok and isinstance(result.data, dict)):
                # Parent emits plain text 'Number Activation Finished' on success.
                # We only need to mark Finished locally — the parent already has
                # the SMS code(s) on its history row.
                cur.execute("UPDATE history SET status = 'Finished' WHERE id = %s", (id,))
                db.commit()
                cur.execute("SELECT * FROM history WHERE id = %s", (id,))
                return create_response(History(**cur.fetchone())), 200
            return result.error or 'BAD_STATUS'
    finally:
        cur.close()
        db.close()


@api.route('/api/get_countries', methods=['GET'])
@authenticate_api_key
def get_countries():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, 'api_country.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@api.route('/api/get_services', methods=['GET'])
@authenticate_api_key
def get_services():
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, 'api_service.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@api.route('/api/getPrices', methods=['GET'])
@authenticate_api_key
def getPrices():
    # Get parameters
    service = request.args.get('service')
    country = request.args.get('country')
    db, cur = db_start()
    try:
        # Retrieve site settings
        cur.execute("SELECT * FROM site_settings WHERE id = %s", (1,))
        site_setting = cur.fetchone()
        if not site_setting:
            return "SITE_SETTINGS_ERROR", 500
        api_key = site_setting['api_key']
        current_profit = int(site_setting['current_profit'])

        result = sv.get_prices(api_key, service, country)
        if not result.ok:
            return result.error or 'NO_NUMBERS'
        data = result.data

        # Pool labels: { 'Alpha': ('Premium US', 1, sort_order), … }
        # disabled pools are dropped from the response entirely.
        cur.execute(
            "SELECT codename, display_name, enabled, sort_order "
            "FROM pool_labels"
        )
        label_rows = cur.fetchall() or []
        labels = {r['codename']: r for r in label_rows}

        for country, services in data.items():
            for service, details in services.items():
                filtered = []
                for item in details:
                    # Markup first.
                    item['order_amount'] = float(
                        (Decimal(str(item['order_amount'])) + Decimal(str(current_profit)))
                        .quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )

                    # Apply pool labels.
                    pool_code = item.get('pool') or item.get('provider')
                    label = labels.get(pool_code)
                    if label is not None:
                        if not label.get('enabled'):
                            continue  # admin hid this pool — drop entirely
                        item['pool'] = label['display_name']
                        item['pool_codename'] = pool_code   # keep canonical for the order call
                        item['sort_order'] = int(label['sort_order'] or 0)
                    else:
                        # Codename not in our table — keep as-is so we don't
                        # accidentally hide a pool the parent newly added.
                        item['pool_codename'] = pool_code
                        item['sort_order'] = 999

                    filtered.append(item)

                filtered.sort(key=lambda x: x.get('sort_order', 999))
                services[service] = filtered

        return jsonify(data)

    finally:
        cur.close()
        db.close()


@api.route('/webhook/rotate-api-key', methods=['POST'])
def rotate_api_key_webhook():
    """Receive a new API key from the parent (swiftverifyng).

    Auth: HMAC-SHA256 over the raw request body, keyed by the *current*
    site_settings.api_key (i.e. the key the parent has on file for us).
    The header `X-Signature` carries the hex digest.

    Idempotent on `rotation_id` — a duplicate is a no-op 200 so the parent
    can safely retry on a lost response. See README of the parent repo →
    "Key-rotation webhook" for the wire format.
    """
    raw = request.get_data() or b''
    provided_sig = (request.headers.get('X-Signature') or '').strip().lower()
    ts_header    = (request.headers.get('X-Rotation-Timestamp') or '').strip()

    if not provided_sig or not ts_header:
        return jsonify(ok=False, error='missing_signature'), 400

    try:
        ts = int(ts_header)
    except ValueError:
        return jsonify(ok=False, error='bad_timestamp'), 400
    if abs(int(time.time()) - ts) > ROTATION_TIMESTAMP_DRIFT:
        return jsonify(ok=False, error='stale_timestamp'), 400

    try:
        payload = json.loads(raw.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return jsonify(ok=False, error='bad_body'), 400

    rotation_id = (payload.get('rotation_id') or '').strip()
    new_api_key = (payload.get('new_api_key') or '').strip()
    if not rotation_id or not new_api_key or len(new_api_key) > 100:
        return jsonify(ok=False, error='bad_payload'), 400

    db, cur = db_start()
    try:
        cur.execute("SELECT api_key FROM site_settings WHERE id = 1")
        row = cur.fetchone() or {}
        current_key = (row.get('api_key') or '').strip()
        if not current_key:
            return jsonify(ok=False, error='no_current_key'), 409

        expected = hmac.new(
            current_key.encode('utf-8'), raw, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, provided_sig):
            return jsonify(ok=False, error='bad_signature'), 401

        # Atomic claim — duplicate rotation_id silently no-ops the rest.
        cur.execute(
            "INSERT IGNORE INTO api_key_rotations (rotation_id, new_key_hint) VALUES (%s, %s)",
            (rotation_id, new_api_key[:8])
        )
        if cur.rowcount == 0:
            # Already applied (replay/retry). Don't touch site_settings.
            db.commit()
            return jsonify(ok=True, rotation_id=rotation_id, status='already_applied'), 200

        cur.execute(
            "UPDATE site_settings SET api_key = %s, api_key_rotated_at = NOW() WHERE id = 1",
            (new_api_key,)
        )
        db.commit()
        return jsonify(ok=True, rotation_id=rotation_id, status='applied'), 200
    finally:
        cur.close()
        db.close()


# ── Order-event webhook ────────────────────────────────────────────────
# Receives state changes pushed by the parent so the child doesn't have
# to poll. Auth: HMAC-SHA256 over the raw body, keyed by the *current*
# site_settings.api_key. Idempotent on event_id.

ORDER_EVENT_TIMESTAMP_DRIFT = 300


@api.route('/webhook/order-event', methods=['POST'])
def order_event_webhook():
    raw = request.get_data() or b''
    provided_sig = (request.headers.get('X-Signature') or '').strip().lower()
    ts_header    = (request.headers.get('X-Event-Timestamp') or '').strip()

    if not provided_sig or not ts_header:
        return jsonify(ok=False, error='missing_signature'), 400
    try:
        ts = int(ts_header)
    except ValueError:
        return jsonify(ok=False, error='bad_timestamp'), 400
    if abs(int(time.time()) - ts) > ORDER_EVENT_TIMESTAMP_DRIFT:
        return jsonify(ok=False, error='stale_timestamp'), 400

    try:
        payload = json.loads(raw.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return jsonify(ok=False, error='bad_body'), 400

    event_id      = (payload.get('event_id') or '').strip()
    activation_id = payload.get('activation_id')
    event_type    = (payload.get('event_type') or '').strip()
    new_status    = (payload.get('status') or '').strip()
    sms_list      = payload.get('sms_list')

    if (not event_id or activation_id is None or event_type not in
            ('received', 'finished', 'timeout', 'canceled')):
        return jsonify(ok=False, error='bad_payload'), 400
    if new_status not in ('Received', 'Finished', 'Timeout', 'Canceled'):
        return jsonify(ok=False, error='bad_status'), 400

    db, cur = db_start()
    try:
        # Signature check against current api_key.
        cur.execute("SELECT api_key FROM site_settings WHERE id = 1")
        row = cur.fetchone() or {}
        current_key = (row.get('api_key') or '').strip()
        if not current_key:
            return jsonify(ok=False, error='no_current_key'), 409

        expected = hmac.new(current_key.encode('utf-8'), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, provided_sig):
            return jsonify(ok=False, error='bad_signature'), 401

        # Idempotency: claim the event_id atomically.
        cur.execute(
            "INSERT IGNORE INTO webhook_order_events (event_id, event_type) VALUES (%s, %s)",
            (event_id, event_type)
        )
        if cur.rowcount == 0:
            db.commit()
            return jsonify(ok=True, event_id=event_id, status='already_applied'), 200

        # Apply to local history row keyed on activation_id (parent's history.id).
        if event_type in ('timeout', 'canceled'):
            # No code update — wallet auto-refunds via the balance query
            # since orders with status IN ('Finished','Received') count
            # against balance and Timeout/Canceled don't.
            cur.execute(
                "UPDATE history SET status = %s WHERE activation_id = %s",
                (new_status, str(activation_id))
            )
        else:
            code_json = json.dumps([c for c in (sms_list or []) if c and str(c).strip()])
            cur.execute(
                "UPDATE history SET status = %s, code = %s, check_status = 0 "
                "WHERE activation_id = %s",
                (new_status, code_json, str(activation_id))
            )
        db.commit()
        return jsonify(ok=True, event_id=event_id, status='applied'), 200
    finally:
        cur.close()
        db.close()
