from datetime import datetime

from bson import ObjectId
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend import db

schedule = Blueprint("schedule", __name__)

DAY_OPTIONS = (
    {"value": "sunday", "label": "الأحد", "order": 0},
    {"value": "monday", "label": "الاثنين", "order": 1},
    {"value": "tuesday", "label": "الثلاثاء", "order": 2},
    {"value": "wednesday", "label": "الأربعاء", "order": 3},
    {"value": "thursday", "label": "الخميس", "order": 4},
)

DAY_LABELS = {option["value"]: option["label"] for option in DAY_OPTIONS}
DAY_ORDERS = {option["value"]: option["order"] for option in DAY_OPTIONS}


def _serialize_schedule_entry(document):
    return {
        "_id": str(document["_id"]),
        "title": document.get("title", ""),
        "day": document.get("day", ""),
        "day_label": DAY_LABELS.get(document.get("day", ""), document.get("day", "")),
        "start_time": document.get("start_time", ""),
        "end_time": document.get("end_time", ""),
        "location": document.get("location", ""),
        "notes": document.get("notes", ""),
        "created_by_name": document.get("created_by_name", ""),
    }


def _load_schedule_entries():
    documents = list(
        db.db.schedule_entries.find().sort(
            [("day_order", 1), ("start_time", 1), ("title", 1)]
        )
    )
    return [_serialize_schedule_entry(document) for document in documents]


@schedule.route("/schedule", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        if not current_user.can_manage_schedule():
            flash("You do not have permission to manage the schedule.", "danger")
            return redirect(url_for("schedule.index"))

        title = request.form.get("title", "").strip()
        day = request.form.get("day", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        location = request.form.get("location", "").strip()
        notes = request.form.get("notes", "").strip()

        if not title or not day or not start_time or not end_time:
            flash("Course title, day, and time fields are required.", "danger")
            return redirect(url_for("schedule.index"))

        if len(title) > current_app.config["MAX_SCHEDULE_TITLE_LENGTH"]:
            flash("Course title is too long.", "danger")
            return redirect(url_for("schedule.index"))

        if len(location) > current_app.config["MAX_SCHEDULE_LOCATION_LENGTH"]:
            flash("Location is too long.", "danger")
            return redirect(url_for("schedule.index"))

        if len(notes) > current_app.config["MAX_SCHEDULE_NOTES_LENGTH"]:
            flash("Notes are too long.", "danger")
            return redirect(url_for("schedule.index"))

        if day not in DAY_LABELS:
            flash("The selected day is invalid.", "danger")
            return redirect(url_for("schedule.index"))

        if start_time >= end_time:
            flash("End time must be later than start time.", "danger")
            return redirect(url_for("schedule.index"))

        db.db.schedule_entries.insert_one(
            {
                "title": title,
                "day": day,
                "day_order": DAY_ORDERS[day],
                "start_time": start_time,
                "end_time": end_time,
                "location": location,
                "notes": notes,
                "created_by": ObjectId(current_user.get_id()),
                "created_by_name": current_user.student_name,
                "created_at": datetime.utcnow(),
            }
        )
        flash("Schedule entry added successfully.", "success")
        return redirect(url_for("schedule.index"))

    return render_template(
        "schedule.html",
        schedule_entries=_load_schedule_entries(),
        day_options=DAY_OPTIONS,
    )


@schedule.route("/schedule/delete/<entry_id>", methods=["POST"])
@login_required
def delete_entry(entry_id):
    if not current_user.can_manage_schedule():
        return "Unauthorized", 403

    try:
        entry_object_id = ObjectId(entry_id)
    except Exception:
        flash("Invalid schedule entry id.", "danger")
        return redirect(url_for("schedule.index"))

    db.db.schedule_entries.delete_one({"_id": entry_object_id})
    flash("Schedule entry removed.", "info")
    return redirect(url_for("schedule.index"))
