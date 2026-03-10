from flask import Blueprint, render_template
from flask_login import login_required


requests = Blueprint("requests", __name__)


@requests.route("/")
@login_required
def index():
    return render_template("requests.html")
