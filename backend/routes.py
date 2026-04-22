from flask import Blueprint, render_template
from flask_login import current_user, login_required


main = Blueprint("main", __name__)


@main.route("/")
@login_required
def home():
    return render_template("home.html", current_user=current_user)


@main.route('/about')
@login_required
def about():
    return render_template('about.html')