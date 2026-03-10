from bson import ObjectId
from flask import Flask
from flask_login import LoginManager
from flask_pymongo import PyMongo

from backend.config import Config
from backend.models import User

from backend.auth import auth as auth_bp
from backend.messages import messages as messages_bp
from backend.requests import requests as requests_bp
from backend.routes import main as main_bp


db = PyMongo()
login = LoginManager()
login.login_view = "auth.login"
login.login_message = "Please sign in to continue."
login.login_message_category = "warning"


@login.user_loader
def load_user(user_id):
    try:
        document = db.db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    return User.from_document(document)


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    db.init_app(app)
    login.init_app(app)



    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(messages_bp, url_prefix="/messages")
    app.register_blueprint(requests_bp, url_prefix="/requests")

    return app
