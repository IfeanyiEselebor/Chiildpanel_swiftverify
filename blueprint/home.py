from flask import Blueprint, render_template, session

from config import get_config_value

home = Blueprint('home', __name__)


@home.route('/', methods=['GET'])
@home.route('/home', methods=['GET'])
def homepage():
    if get_config_value("CURRENT_THEME") == "THEME_1":
        return render_template("theme_1/index.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               reviews=get_config_value("reviews"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                               )
    if get_config_value("CURRENT_THEME") == "THEME_2":
        return render_template("theme_2/index.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               reviews=get_config_value("reviews"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                               )


@home.route('/privacy-policy', methods=['GET'])
def privacy_policy():
    if get_config_value("CURRENT_THEME") == "THEME_1":
        return render_template("theme_1/privacy-policy.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON")
                               )
    if get_config_value("CURRENT_THEME") == "THEME_2":
        return render_template("theme_2/policy.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON")
                               )


@home.route('/login', methods=['GET'])
def login():
    if get_config_value("CURRENT_THEME") == "THEME_1":
        return render_template("theme_1/login.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON")
                               )
    elif get_config_value("CURRENT_THEME") == "THEME_2":
        return render_template("theme_2/login.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               reviews=get_config_value("reviews"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                               )
    else:
        return render_template("user/login.html",
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
                               )


@home.route('/register', methods=['GET'])
def register():
    if get_config_value("CURRENT_THEME") == "THEME_1":
        return render_template("theme_1/register.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON")
                               )
    elif get_config_value("CURRENT_THEME") == "THEME_2":
        return render_template("theme_2/register.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               reviews=get_config_value("reviews"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                               )
    else:
        return render_template("user/register.html",
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
                               )


@home.route('/tos', methods=['GET'])
def tos():
    if get_config_value("CURRENT_THEME") == "THEME_1":
        return render_template("theme_1/tos.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON")
                               )
    if get_config_value("CURRENT_THEME") == "THEME_2":
        return render_template("theme_2/terms.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                               )


@home.route('/about', methods=['GET'])
def about():
    if get_config_value("CURRENT_THEME") == "THEME_2":
        return render_template("theme_2/about.html",
                               SITE_NAME=get_config_value("SITE_NAME"),
                               SITE_LOGO=get_config_value("SITE_LOGO"),
                               SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                               SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                               SITE_FAVICON=get_config_value("SITE_FAVICON"),
                               reviews=get_config_value("reviews"),
                               SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                               )


@home.route('/reset_password', methods=['GET'])
def reset_password():
    if get_config_value("CURRENT_THEME") == "THEME_1":
        if not session.get('logged_in', False):
            return render_template("theme_1/reset_password.html",
                                   SITE_NAME=get_config_value("SITE_NAME"),
                                   SITE_LOGO=get_config_value("SITE_LOGO"),
                                   SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                                   SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                                   SITE_FAVICON=get_config_value("SITE_FAVICON"),
                                   reviews=get_config_value("reviews"),
                                   SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                                   )
    elif get_config_value("CURRENT_THEME") == "THEME_2":
        if not session.get('logged_in', False):
            return render_template("theme_2/reset_password.html",
                                   SITE_NAME=get_config_value("SITE_NAME"),
                                   SITE_LOGO=get_config_value("SITE_LOGO"),
                                   SITE_SUPPORT_EMAIL=get_config_value("SITE_SUPPORT_EMAIL"),
                                   SITE_DOMAIN=get_config_value("SITE_DOMAIN"),
                                   SITE_FAVICON=get_config_value("SITE_FAVICON"),
                                   reviews=get_config_value("reviews"),
                                   SITE_TELEGRAM_SUPPORT=get_config_value("SITE_TELEGRAM_SUPPORT")
                                   )
    else:
        return render_template("user/reset_password.html",
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
                               )
