from flask import Blueprint, redirect, url_for
from flask_login import login_required


messages = Blueprint("messages", __name__)


@messages.route("/")
@login_required
def index():
    return redirect(url_for("chat.chat_page"))
