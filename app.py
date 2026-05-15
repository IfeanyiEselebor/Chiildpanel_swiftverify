import os

from dotenv import load_dotenv

load_dotenv()

from extension import bcrypt
from flask import Flask


def create_app(debug=None):
    inner_app = Flask(__name__)  # Flask constructor

    # App Config
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY env var is required (see .env)")
    inner_app.secret_key = secret_key
    inner_app.debug = (os.environ.get("DEBUG", "False").lower() == "true") if debug is None else debug

    # Mail App Config
    inner_app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER', 'mail.diberrysms.com')
    inner_app.config['MAIL_PORT']     = int(os.environ.get('MAIL_PORT', 465))
    inner_app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'support@diberrysms.com')
    inner_app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    inner_app.config['MAIL_USE_TLS']  = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    inner_app.config['MAIL_USE_SSL']  = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'

    # Import Blueprints
    from blueprint.home import home as home_blueprint
    from blueprint.auth import auth as auth_blueprint
    from blueprint.user import user as user_blueprint
    from blueprint.order import order as order_blueprint
    from blueprint.fund import fund as fund_blueprint
    from blueprint.admin import admin as admin_blueprint
    from blueprint.api import api as api_blueprint

    # Register Blueprints
    inner_app.register_blueprint(home_blueprint)
    inner_app.register_blueprint(auth_blueprint)
    inner_app.register_blueprint(user_blueprint)
    inner_app.register_blueprint(order_blueprint)
    inner_app.register_blueprint(fund_blueprint)
    inner_app.register_blueprint(admin_blueprint)
    inner_app.register_blueprint(api_blueprint)

    # Initialize Extensions
    bcrypt.init_app(inner_app)

    return inner_app


app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)  # Standard Flask app run
