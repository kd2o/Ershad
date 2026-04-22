from datetime import datetime

from bson import ObjectId
from flask import Blueprint, current_app, render_template, request
from flask_login import current_user, login_required
from flask_socketio import emit, join_room

from backend import db, socketio
from backend.roles import get_role_label

news = Blueprint("news", __name__)

NEWS_ROOM = "news_room"
NEWS_HISTORY_LIMIT = 120


def _format_timestamp(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


def _serialize_news_message(document):
    timestamp = document.get("timestamp")
    return {
        "id": str(document.get("_id", "")),
        "author_id": str(document.get("author_id", "")),
        "author_name": document.get("author_name", ""),
        "author_role": document.get("author_role", ""),
        "author_role_label": document.get("author_role_label", ""),
        "message": document.get("message", ""),
        "timestamp": _format_timestamp(timestamp),
        "timestamp_iso": timestamp.isoformat() if timestamp else "",
    }


def _load_news_messages(limit=NEWS_HISTORY_LIMIT):
    documents = list(
        db.db.news_messages.find().sort("timestamp", -1).limit(limit)
    )
    documents.reverse()
    return [_serialize_news_message(document) for document in documents]


@news.route("/news")
@login_required
def index():
    return render_template(
        "news.html",
        news_messages=_load_news_messages(),
        max_news_message_length=current_app.config["MAX_NEWS_MESSAGE_LENGTH"],
    )


@socketio.on("join_news")
def handle_join_news():
    if not current_user.is_authenticated:
        return False

    join_room(NEWS_ROOM)
    emit("news_history", {"messages": _load_news_messages()}, to=request.sid)


@socketio.on("send_news_message")
def handle_send_news_message(data):
    if not current_user.is_authenticated:
        return

    if not current_user.can_post_news():
        emit("news_error", {"message": "يمكن للطاقم فقط نشر الأخبار."}, to=request.sid)
        return

    message_text = str((data or {}).get("message", "")).strip()
    if not message_text:
        return

    if len(message_text) > current_app.config["MAX_NEWS_MESSAGE_LENGTH"]:
        emit("news_error", {"message": "الخبر طويل جدا. يرجى تقصيره."}, to=request.sid)
        return

    now = datetime.utcnow()
    document = {
        "author_id": ObjectId(current_user.get_id()),
        "author_name": current_user.student_name,
        "author_role": current_user.role,
        "author_role_label": get_role_label(current_user.role),
        "message": message_text,
        "timestamp": now,
    }

    inserted = db.db.news_messages.insert_one(document)
    payload = _serialize_news_message({**document, "_id": inserted.inserted_id})
    emit("news_message", payload, room=NEWS_ROOM)


@socketio.on("delete_news_message")
def handle_delete_news_message(data):
    if not current_user.is_authenticated:
        return

    if not current_user.can_post_news():
        emit("news_error", {"message": "يمكن للطاقم فقط حذف الأخبار."}, to=request.sid)
        return

    message_id = str((data or {}).get("id", "")).strip()
    if not message_id:
        return

    try:
        db.db.news_messages.delete_one({"_id": ObjectId(message_id)})
        emit("news_message_deleted", {"id": message_id}, room=NEWS_ROOM)
    except Exception as e:
        emit("news_error", {"message": "حدث خطأ أثناء حذف الخبر."}, to=request.sid)
