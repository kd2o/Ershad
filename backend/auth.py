from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from backend import db
from backend.models import User
from backend.roles import (
    ROLE_ADMIN,
    ROLE_GUIDANCE_COMMITTEE,
    ROLE_MENTOR,
    ROLE_USER,
    VALID_ROLES,
    can_delete_role,
    get_role_label,
    normalize_role,
)

auth = Blueprint("auth", __name__)

ROLE_OPTIONS = (
    {"value": ROLE_USER, "label": get_role_label(ROLE_USER)},
    {"value": ROLE_MENTOR, "label": get_role_label(ROLE_MENTOR)},
    {"value": ROLE_GUIDANCE_COMMITTEE, "label": get_role_label(ROLE_GUIDANCE_COMMITTEE)},
    {"value": ROLE_ADMIN, "label": get_role_label(ROLE_ADMIN)},
)

def _normalize_student_name(student_name):
    return " ".join(student_name.strip().lower().split())

def _normalize_student_number(student_number):
    return student_number.strip()


def _validate_user_fields(student_name, student_number):
    if len(student_name) > current_app.config["MAX_STUDENT_NAME_LENGTH"]:
        return "Student name is too long."
    if len(student_number) > current_app.config["MAX_STUDENT_NUMBER_LENGTH"]:
        return "Student ID is too long."
    return ""


def _has_users():
    return db.db is not None and db.db.users.find_one({}, {"_id": 1}) is not None


def _find_user(student_name, student_number):
    student_name_key = _normalize_student_name(student_name)
    normalized_student_number = _normalize_student_number(student_number)

    user_documents = db.db.users.find({"student_number": normalized_student_number})
    for user_document in user_documents:
        stored_name_key = user_document.get("student_name_key") or _normalize_student_name(
            user_document.get("student_name", "")
        )
        if stored_name_key == student_name_key:
            return user_document

    return None


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home")) 
    if request.method == "POST":
        student_name = request.form.get("student_name", "")
        student_number = request.form.get("student_number", "")

        if not student_name or not student_number:
            flash("name and ID are required.", "danger")
            return redirect(url_for("auth.login"))

        validation_error = _validate_user_fields(student_name.strip(), student_number.strip())
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("auth.login"))

        if db.db is None:
            flash("Database connection is not available.", "danger")
            return redirect(url_for("auth.login"))

        if not _has_users():
            flash("No user accounts are configured yet. Create an admin account first.", "warning")
            return redirect(url_for("auth.login"))

        user_document = _find_user(student_name, student_number)
        if user_document:
            login_user(User.from_document(user_document))
            flash("Signed in successfully.", "success")
            return redirect(url_for("main.home"))

        flash("The student name or ID is incorrect.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out successfully.", "success")
    return redirect(url_for("auth.login"))


@auth.route("/add_user", methods=["GET", "POST"])
@login_required

def add_user():
    if not current_user.can_access_user_management():
        flash("Access denied.", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        if not current_user.can_add_users():
            flash("You do not have permission to add new users.", "danger")
            return redirect(url_for("auth.add_user"))

        student_name = request.form.get("student_name", "").strip()
        student_number = request.form.get("student_number", "").strip()
        selected_role = str(request.form.get("role", "")).strip()

        if not student_name or not student_number:
            flash("Student name and ID are required.", "danger")
            return redirect(url_for("auth.add_user"))

        validation_error = _validate_user_fields(student_name, student_number)
        if validation_error:
            flash(validation_error, "danger")
            return redirect(url_for("auth.add_user"))

        if selected_role not in VALID_ROLES:
            flash("The selected role is not valid.", "danger")
            return redirect(url_for("auth.add_user"))

        role = normalize_role(selected_role)

        student_name_key = _normalize_student_name(student_name)

        if db.db.users.find_one({"student_number": student_number}):
            flash("User with this ID already exists!", "warning")
        else:
            try:
                db.db.users.insert_one({
                    "student_name": student_name,
                    "student_name_key": student_name_key,
                    "student_number": student_number,
                    "role": role,
                })
                flash(f"User {student_name} added successfully!", "success")
            except DuplicateKeyError:
                flash("User with this ID already exists!", "warning")
        return redirect(url_for("auth.add_user"))

    users = list(db.db.users.find())
    for user in users:
        user["role"] = normalize_role(user.get("role"))
        user["role_label"] = get_role_label(user["role"])
        user["can_be_deleted"] = current_user.can_delete_role(user["role"]) and str(
            user["_id"]
        ) != current_user.get_id()

    return render_template(
        "add_user.html",
        users=users,
        role_options=ROLE_OPTIONS,
        can_add_users=current_user.can_add_users(),
    )

@auth.route("/delete_user/<user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.can_access_user_management():
        return "Unauthorized", 403

    if current_user.get_id() == user_id:
        flash("You cannot delete yourself!", "danger")
        return redirect(url_for("auth.add_user"))

    try:
        target_object_id = ObjectId(user_id)
    except Exception:
        flash("Invalid user id.", "danger")
        return redirect(url_for("auth.add_user"))

    target_user = db.db.users.find_one({"_id": target_object_id})
    if not target_user:
        flash("User not found.", "warning")
        return redirect(url_for("auth.add_user"))

    target_role = normalize_role(target_user.get("role"))
    if not can_delete_role(current_user.role, target_role):
        flash("You do not have permission to delete this account.", "danger")
        return redirect(url_for("auth.add_user"))

    db.db.users.delete_one({"_id": target_object_id})
    flash("User removed.", "info")
    return redirect(url_for("auth.add_user"))

