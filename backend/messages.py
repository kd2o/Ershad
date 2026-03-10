from flask import Blueprint, render_template
from flask_login import login_required


messages = Blueprint("messages", __name__)


@messages.route("/")
@login_required
def index():
    return render_template("messages.html")
