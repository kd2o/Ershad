import os
import secrets
from urllib.parse import quote_plus, urlsplit, urlunsplit
from dotenv import load_dotenv 

load_dotenv()

DEFAULT_MONGO_DB_NAME = "Ershad"
INSECURE_SECRET_KEYS = {"", "dev-secret-key", "change-me"}


def _ensure_database_name(uri, database_name=DEFAULT_MONGO_DB_NAME):
    if not uri:
        return uri

    parsed_uri = urlsplit(uri)
    if parsed_uri.path not in ("", "/"):
        return uri

    return urlunsplit(
        (
            parsed_uri.scheme,
            parsed_uri.netloc,
            f"/{database_name}",
            parsed_uri.query,
            parsed_uri.fragment,
        )
    )


def _build_default_mongo_uri():
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if mongo_uri:
        return _ensure_database_name(mongo_uri)

    mongo_username = os.getenv("MONGO_USERNAME", "").strip()
    mongo_password = os.getenv("MONGO_PASSWORD", "").strip()
    mongo_cluster = os.getenv("MONGO_CLUSTER", "").strip()

    if not (mongo_username and mongo_password and mongo_cluster):
        return f"mongodb://localhost:27017/{DEFAULT_MONGO_DB_NAME}"

    mongo_user = quote_plus(mongo_username)
    mongo_password = quote_plus(mongo_password)

    return _ensure_database_name(
        f"mongodb+srv://kdo3l:kdo3liloverayan@ershad.rwxfiop.mongodb.net/?appName=Ershad"
    )


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name):
    raw_value = os.getenv(name, "")
    values = [value.strip() for value in raw_value.split(",") if value.strip()]
    return values or None


def _load_secret_key():
    configured_secret = os.getenv("SECRET_KEY", "").strip()
    if configured_secret and configured_secret not in INSECURE_SECRET_KEYS:
        return configured_secret
    return secrets.token_hex(32)

class Config:
    SECRET_KEY = _load_secret_key()
    DEBUG = _env_flag("FLASK_DEBUG", default=False)
    MONGO_URI = _build_default_mongo_uri()
    MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "2000"))
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", default=False)
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    WTF_CSRF_TIME_LIMIT = 3600
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SOCKETIO_CORS_ALLOWED_ORIGINS = _env_list("SOCKETIO_CORS_ALLOWED_ORIGINS")
    MAX_STUDENT_NAME_LENGTH = 120
    MAX_STUDENT_NUMBER_LENGTH = 32
    MAX_CHAT_MESSAGE_LENGTH = 1200
    MAX_NEWS_MESSAGE_LENGTH = 1600
    MAX_SCHEDULE_TITLE_LENGTH = 120
    MAX_SCHEDULE_LOCATION_LENGTH = 120
    MAX_SCHEDULE_NOTES_LENGTH = 400
