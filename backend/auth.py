from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from backend import db
from backend.models import User


auth = Blueprint("auth", __name__)


def _normalize_student_name(student_name):
    return " ".join(student_name.strip().lower().split())


def _normalize_student_number(student_number):
    return student_number.strip()


def _find_user(student_name, student_number):
    return db.db.users.find_one(
        {
            "student_name_key": _normalize_student_name(student_name),
            "student_number": _normalize_student_number(student_number),
        }
    )


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        student_name = request.form.get("student_name", "")
        student_number = request.form.get("student_number", "")

        if not student_name or not student_number:
            flash("Student name and student number are required.", "danger")
            return redirect(url_for("auth.login"))

        user_document = _find_user(student_name, student_number)
        if user_document:
            login_user(User.from_document(user_document))
            flash("Signed in successfully.", "success")
            return redirect(url_for("main.home"))

        flash("The student name or student number is incorrect.", "danger")
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
    if not current_user.is_admin():
        flash("Admin access is required.", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        student_name = request.form.get("student_name", "")
        student_number = request.form.get("student_number", "")
        role = request.form.get("role", "user").strip().lower()

        if not student_name or not student_number:
            flash("Student name and student number are required.", "danger")
            return redirect(url_for("auth.add_user"))

        if role not in {"admin", "user"}:
            flash("Role must be either admin or user.", "danger")
            return redirect(url_for("auth.add_user"))

        normalized_student_name = _normalize_student_name(student_name)
        normalized_student_number = _normalize_student_number(student_number)

        if db.db.users.find_one({"student_number": normalized_student_number}):
            flash("This student number is already in use.", "warning")
            return redirect(url_for("auth.add_user"))

        db.db.users.insert_one(
            {
                "student_name": student_name.strip(),
                "student_name_key": normalized_student_name,
                "student_number": normalized_student_number,
                "role": role,
            }
        )
        flash("User added successfully.", "success")
        return redirect(url_for("main.home"))

    return render_template("add_user.html")
