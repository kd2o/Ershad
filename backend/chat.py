from datetime import datetime

from bson import ObjectId
from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required
from flask_socketio import emit, join_room

from . import db, socketio
from .roles import (
    CHAT_SERVICE_OPTIONS,
    ROLE_ADMIN,
    can_handle_chat_service,
    get_chat_service_description,
    get_chat_service_label,
    get_role_label,
    is_valid_chat_service,
    normalize_chat_service,
)

chat = Blueprint("chat", __name__)

STAFF_NOTIFICATION_ROOM = "staff_notifications_all"

STATUS_LABELS = {
    "pending": "بانتظار الموافقة",
    "active": "محادثة نشطة",
    "closed": "محادثة مغلقة",
}


def _to_object_id(value):
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _user_room(user_id):
    return f"user_{user_id}"


def _service_notification_room(service_type):
    return f"staff_notifications_{normalize_chat_service(service_type)}"


def _conversation_room(user_a_id, user_b_id):
    first_id, second_id = sorted([str(user_a_id), str(user_b_id)])
    return f"conversation_{first_id}_{second_id}"


def _format_timestamp(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


def _get_request_service_type(document):
    return normalize_chat_service((document or {}).get("service_type"))


def _get_request_staff_id(document):
    return (document or {}).get("staff_id") or (document or {}).get("admin_id")


def _get_request_staff_name(document):
    return (document or {}).get("staff_name") or (document or {}).get("admin_name", "")


def _get_request_staff_role(document):
    role = (document or {}).get("staff_role")
    if role:
        return role
    return ROLE_ADMIN if (document or {}).get("admin_id") else ""


def _serialize_request(document):
    if not document:
        return None

    student_id = str(document["student_id"])
    service_type = _get_request_service_type(document)
    staff_id = _get_request_staff_id(document)
    staff_role = _get_request_staff_role(document)
    updated_at = (
        document.get("updated_at")
        or document.get("timestamp")
        or document.get("accepted_at")
        or document.get("created_at")
    )

    serialized = {
        "student_id": student_id,
        "student_name": document.get("student_name", ""),
        "service_type": service_type,
        "service_label": get_chat_service_label(service_type),
        "service_description": get_chat_service_description(service_type),
        "staff_id": str(staff_id) if staff_id else "",
        "staff_name": _get_request_staff_name(document),
        "staff_role": staff_role,
        "staff_role_label": get_role_label(staff_role) if staff_role else "",
        "status": document.get("status", "pending"),
        "status_label": STATUS_LABELS.get(document.get("status", "pending"), "pending"),
        "created_at": _format_timestamp(document.get("created_at")),
        "updated_at": _format_timestamp(updated_at),
        "updated_at_iso": updated_at.isoformat() if updated_at else "",
        "accepted_at": _format_timestamp(document.get("accepted_at")),
        "room_id": _conversation_room(student_id, staff_id) if staff_id else "",
    }

    return serialized


def _serialize_message(document):
    timestamp = document.get("timestamp")
    return {
        "id": str(document.get("_id", "")),
        "room_id": document.get("room_id", ""),
        "sender_id": str(document.get("sender_id", "")),
        "sender_name": document.get("sender_name", ""),
        "recipient_id": str(document.get("recipient_id", "")),
        "message": document.get("message", ""),
        "timestamp": _format_timestamp(timestamp),
        "timestamp_iso": timestamp.isoformat() if timestamp else "",
    }


def _get_request_for_student(student_id):
    student_object_id = _to_object_id(student_id)
    if not student_object_id:
        return None
    return db.db.chat_requests.find_one({"student_id": student_object_id})


def _load_messages_for_room(room_id, limit=100):
    documents = list(
        db.db.chat_messages.find({"room_id": room_id}).sort("timestamp", -1).limit(limit)
    )
    documents.reverse()
    return [_serialize_message(document) for document in documents]


def _build_staff_requests():
    staff_object_id = _to_object_id(current_user.get_id())
    if not staff_object_id:
        return []

    if current_user.is_admin():
        query = {
            "$or": [
                {"status": "pending"},
                {"status": "active", "staff_id": staff_object_id},
                {"status": "active", "admin_id": staff_object_id},
            ]
        }
    else:
        query = {
            "$or": [
                {"status": "pending", "service_type": current_user.role},
                {"status": "active", "staff_id": staff_object_id},
                {"status": "active", "admin_id": staff_object_id},
            ]
        }

    documents = list(db.db.chat_requests.find(query).sort("updated_at", -1))
    return [_serialize_request(document) for document in documents]


def _build_student_context():
    request_document = _get_request_for_student(current_user.get_id())
    serialized_request = _serialize_request(request_document)
    initial_messages = []

    if serialized_request and serialized_request["room_id"]:
        initial_messages = _load_messages_for_room(serialized_request["room_id"])

    return serialized_request, initial_messages


def _request_notification_rooms(service_type):
    return [STAFF_NOTIFICATION_ROOM, _service_notification_room(service_type)]


def _emit_request_to_staff(event_name, request_document):
    serialized_request = _serialize_request(request_document)
    if not serialized_request:
        return

    for room_name in dict.fromkeys(_request_notification_rooms(serialized_request["service_type"])):
        emit(event_name, {"request": serialized_request}, room=room_name)


def _emit_request_deleted(student_id, service_type):
    payload = {"student_id": student_id, "service_type": normalize_chat_service(service_type)}
    for room_name in dict.fromkeys(_request_notification_rooms(service_type)):
        emit("request_deleted", payload, room=room_name)


def _authorize_room(recipient_id):
    recipient_object_id = _to_object_id(recipient_id)
    if not recipient_object_id:
        return None, None, "المستخدم المطلوب غير صالح."

    if current_user.is_staff():
        request_document = _get_request_for_student(recipient_id)
        if not request_document:
            return None, None, "لا يوجد طلب محادثة لهذا الطالب."

        assigned_staff = _get_request_staff_id(request_document)
        if request_document.get("status") != "active" or not assigned_staff:
            return None, None, "يجب قبول الطلب أولا قبل بدء المحادثة."

        if str(assigned_staff) != current_user.get_id():
            return None, None, "هذه المحادثة مرتبطة بعضو آخر من الطاقم."

        return _conversation_room(current_user.get_id(), recipient_id), request_document, ""

    request_document = _get_request_for_student(current_user.get_id())
    if not request_document or request_document.get("status") != "active":
        return None, None, "بانتظار قبول الطلب لبدء المحادثة."

    assigned_staff = _get_request_staff_id(request_document)
    if not assigned_staff or str(assigned_staff) != recipient_id:
        return None, None, "لا يمكنك الانضمام إلى هذه المحادثة."

    return _conversation_room(current_user.get_id(), recipient_id), request_document, ""


@chat.route("/chat")
@login_required
def chat_page():
    if current_user.is_staff():
        return render_template(
            "chat_admin.html",
            chat_requests=_build_staff_requests(),
            selected_student_id="",
            max_chat_message_length=current_app.config["MAX_CHAT_MESSAGE_LENGTH"],
        )

    chat_request, initial_messages = _build_student_context()
    return render_template(
        "chat_student.html",
        chat_request=chat_request,
        initial_messages=initial_messages,
        service_options=CHAT_SERVICE_OPTIONS,
        max_chat_message_length=current_app.config["MAX_CHAT_MESSAGE_LENGTH"],
    )


@chat.route("/chat/private/<student_id>")
@login_required
def admin_private_chat(student_id):
    if not current_user.is_staff():
        abort(403)

    request_document = _get_request_for_student(student_id)
    if not request_document:
        abort(404)

    assigned_staff = _get_request_staff_id(request_document)
    if assigned_staff and str(assigned_staff) != current_user.get_id():
        abort(403)

    return render_template(
        "chat_admin.html",
        chat_requests=_build_staff_requests(),
        selected_student_id=str(student_id),
        max_chat_message_length=current_app.config["MAX_CHAT_MESSAGE_LENGTH"],
    )


@socketio.on("connect")
def handle_connect():
    if not current_user.is_authenticated:
        return False

    join_room(_user_room(current_user.get_id()))

    if not current_user.is_staff():
        return

    if current_user.is_admin():
        join_room(STAFF_NOTIFICATION_ROOM)
        return

    join_room(_service_notification_room(current_user.role))


@socketio.on("request_staff_chat")
def handle_request_staff_chat(data):
    if not current_user.is_authenticated or current_user.is_staff():
        emit("chat_error", {"message": "هذه الخدمة مخصصة للطلاب."}, to=request.sid)
        return

    student_id = current_user.get_id()
    student_object_id = _to_object_id(student_id)
    if not student_object_id:
        emit("chat_error", {"message": "تعذر إنشاء الطلب."}, to=request.sid)
        return

    requested_service_type = str((data or {}).get("service_type", "")).strip().lower()
    if not is_valid_chat_service(requested_service_type):
        emit("chat_error", {"message": "نوع الجهة المطلوبة غير صالح."}, to=request.sid)
        return

    service_type = normalize_chat_service(requested_service_type)
    now = datetime.utcnow()
    existing_request = _get_request_for_student(student_id)

    if existing_request and existing_request.get("status") == "active" and _get_request_staff_id(existing_request):
        emit(
            "chat_request_status",
            {"request": _serialize_request(existing_request)},
            to=request.sid,
        )
        return

    db.db.chat_requests.update_one(
        {"student_id": student_object_id},
        {
            "$set": {
                "student_name": current_user.student_name,
                "service_type": service_type,
                "status": "pending",
                "updated_at": now,
            },
            "$setOnInsert": {
                "student_id": student_object_id,
                "created_at": now,
            },
            "$unset": {
                "staff_id": "",
                "staff_name": "",
                "staff_role": "",
                "admin_id": "",
                "admin_name": "",
                "accepted_at": "",
            },
        },
        upsert=True,
    )

    request_document = _get_request_for_student(student_id)
    emit("chat_request_status", {"request": _serialize_request(request_document)}, to=request.sid)
    _emit_request_to_staff("notify_admin", request_document)


@socketio.on("accept_chat_request")
def handle_accept_chat_request(data):
    if not current_user.is_authenticated or not current_user.is_staff():
        emit("chat_error", {"message": "هذه العملية متاحة فقط لطاقم الإرشاد."}, to=request.sid)
        return

    student_id = str((data or {}).get("student_id", "")).strip()
    student_object_id = _to_object_id(student_id)
    if not student_object_id:
        emit("chat_error", {"message": "تعذر فتح المحادثة المطلوبة."}, to=request.sid)
        return

    request_document = _get_request_for_student(student_id)
    if not request_document:
        emit("chat_error", {"message": "طلب المحادثة غير موجود."}, to=request.sid)
        return

    service_type = _get_request_service_type(request_document)
    if not current_user.can_handle_chat_service(service_type):
        emit("chat_error", {"message": "لا يمكنك استلام هذا النوع من الطلبات."}, to=request.sid)
        return

    assigned_staff = _get_request_staff_id(request_document)
    if assigned_staff and str(assigned_staff) != current_user.get_id():
        emit("chat_error", {"message": "تم استلام هذا الطلب من عضو آخر."}, to=request.sid)
        return

    now = datetime.utcnow()
    staff_object_id = _to_object_id(current_user.get_id())

    db.db.chat_requests.update_one(
        {"student_id": student_object_id},
        {
            "$set": {
                "student_name": request_document.get("student_name", ""),
                "service_type": service_type,
                "status": "active",
                "staff_id": staff_object_id,
                "staff_name": current_user.student_name,
                "staff_role": current_user.role,
                "accepted_at": now,
                "updated_at": now,
            },
            "$setOnInsert": {
                "student_id": student_object_id,
                "created_at": now,
            },
            "$unset": {
                "admin_id": "",
                "admin_name": "",
            },
        },
        upsert=True,
    )

    updated_request = _get_request_for_student(student_id)
    serialized_request = _serialize_request(updated_request)
    room_id = _conversation_room(current_user.get_id(), student_id)

    join_room(room_id)
    emit("chat_ready", {"request": serialized_request, "room_id": room_id}, to=request.sid)
    emit(
        "chat_request_accepted",
        {"request": serialized_request, "room_id": room_id},
        room=_user_room(student_id),
    )
    _emit_request_to_staff("request_updated", updated_request)


@socketio.on("close_chat")
def handle_close_chat(data):
    if not current_user.is_authenticated or not current_user.is_staff():
        emit("chat_error", {"message": "هذه العملية متاحة فقط لطاقم الإرشاد."}, to=request.sid)
        return

    student_id = str((data or {}).get("student_id", "")).strip()
    request_document = _get_request_for_student(student_id)
    if not request_document:
        emit("chat_error", {"message": "لا توجد محادثة نشطة لهذا الطالب."}, to=request.sid)
        return

    assigned_staff = _get_request_staff_id(request_document)
    if request_document.get("status") != "active" or not assigned_staff:
        emit("chat_error", {"message": "لا توجد محادثة نشطة قابلة للإنهاء."}, to=request.sid)
        return

    if str(assigned_staff) != current_user.get_id():
        emit("chat_error", {"message": "لا يمكنك إنهاء محادثة مرتبطة بعضو آخر."}, to=request.sid)
        return

    room_id = _conversation_room(current_user.get_id(), student_id)
    service_type = _get_request_service_type(request_document)

    db.db.chat_messages.delete_many({"room_id": room_id})
    db.db.chat_requests.delete_one({"student_id": request_document["student_id"]})

    payload = {
        "student_id": student_id,
        "room_id": room_id,
        "message": "تم إنهاء المحادثة من قبل طاقم الإرشاد وحذف جميع بياناتها.",
    }

    emit("chat_closed", payload, to=request.sid)
    emit("chat_closed", payload, room=_user_room(student_id))
    _emit_request_deleted(student_id, service_type)


@socketio.on("join_chat")
def handle_join_chat(data):
    if not current_user.is_authenticated:
        return

    recipient_id = str((data or {}).get("recipient_id", "")).strip()
    room_id, request_document, error_message = _authorize_room(recipient_id)
    if not room_id:
        emit("chat_error", {"message": error_message}, to=request.sid)
        return

    join_room(room_id)
    emit(
        "conversation_history",
        {
            "room_id": room_id,
            "request": _serialize_request(request_document),
            "messages": _load_messages_for_room(room_id),
        },
        to=request.sid,
    )


@socketio.on("private_message")
def handle_private_message(data):
    if not current_user.is_authenticated:
        return

    recipient_id = str((data or {}).get("recipient_id", "")).strip()
    message_text = str((data or {}).get("message", "")).strip()

    if not message_text:
        emit("chat_error", {"message": "لا يمكن إرسال رسالة فارغة."}, to=request.sid)
        return

    if len(message_text) > current_app.config["MAX_CHAT_MESSAGE_LENGTH"]:
        emit(
            "chat_error",
            {"message": "الرسالة طويلة جدا. يرجى تقصيرها وإعادة المحاولة."},
            to=request.sid,
        )
        return

    room_id, request_document, error_message = _authorize_room(recipient_id)
    if not room_id:
        emit("chat_error", {"message": error_message}, to=request.sid)
        return

    now = datetime.utcnow()
    message_document = {
        "room_id": room_id,
        "sender_id": _to_object_id(current_user.get_id()),
        "sender_name": current_user.student_name,
        "recipient_id": _to_object_id(recipient_id),
        "message": message_text,
        "timestamp": now,
    }

    insert_result = db.db.chat_messages.insert_one(message_document)
    db.db.chat_requests.update_one(
        {"student_id": request_document["student_id"]},
        {"$set": {"updated_at": now}},
    )

    payload = _serialize_message({**message_document, "_id": insert_result.inserted_id})
    emit("new_message", payload, room=room_id)

    refreshed_request = _get_request_for_student(str(request_document["student_id"]))
    _emit_request_to_staff("request_updated", refreshed_request)
