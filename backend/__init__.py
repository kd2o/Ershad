import certifi

from bson import ObjectId
from flask import Flask, flash, redirect, request, url_for
from flask_login import LoginManager
from flask_pymongo import PyMongo
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFError, CSRFProtect

from backend.config import Config

db = PyMongo()
login = LoginManager()
csrf = CSRFProtect()
socketio = SocketIO(async_mode="threading")


def _mongo_client_options(app):
    options = {
        "serverSelectionTimeoutMS": app.config.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", 2000),
    }
    mongo_uri = app.config.get("MONGO_URI", "")
    if mongo_uri.startswith("mongodb+srv://") or "tls=true" in mongo_uri.lower():
        options["tlsCAFile"] = certifi.where()
    return options


def _ensure_indexes():
    index_builders = (
        lambda: db.db.users.create_index("student_number", unique=True),
        lambda: db.db.chat_requests.create_index("student_id", unique=True),
        lambda: db.db.chat_messages.create_index([("room_id", 1), ("timestamp", 1)]),
        lambda: db.db.schedule_entries.create_index([("day_order", 1), ("start_time", 1)]),
        lambda: db.db.news_messages.create_index([("timestamp", -1)]),
    )

    for build_index in index_builders:
        try:
            build_index()
        except Exception as exc:
            print(f"[MongoDB] Index warning: {exc}")


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    db.init_app(app, **_mongo_client_options(app))

    with app.app_context():
        try:
            db.cx.admin.command("ping")
            if db.db is None:
                raise RuntimeError(
                    "MongoDB connected, but no default database was selected. "
                    "Check that MONGO_URI includes '/Ershad'."
                )
            _ensure_indexes()
            print(f"[MongoDB] Connected to database: {db.db.name}")
        except Exception as exc:
            print(f"[MongoDB] Connection check failed: {exc}")

    login.init_app(app)
    csrf.init_app(app)
    socketio.init_app(
        app,
        async_mode="threading",
        cors_allowed_origins=app.config.get("SOCKETIO_CORS_ALLOWED_ORIGINS"),
    )

    login.login_view = "auth.login"
    login.login_message = "يرجى تسجيل الدخول للمتابعة."
    login.login_message_category = "warning"

    from .chat import chat
    from backend.auth import auth as auth_bp
    from backend.messages import messages as messages_bp
    from backend.news import news as news_bp
    from backend.requests import requests as requests_bp
    from backend.routes import main as main_bp
    from backend.schedule import schedule as schedule_bp

    app.register_blueprint(chat)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(messages_bp, url_prefix="/messages")
    app.register_blueprint(news_bp)
    app.register_blueprint(requests_bp, url_prefix="/requests")
    app.register_blueprint(schedule_bp)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("انتهت صلاحية النموذج أو أن طلب الإرسال غير موثوق.", "danger")
        return redirect(request.referrer or url_for("main.home"))

    return app


@login.user_loader
def load_user(user_id):
    from backend.models import User

    try:
        if db.db is None:
            return None
        document = db.db.users.find_one({"_id": ObjectId(user_id)})
        return User.from_document(document) if document else None
    except Exception:
        return None
