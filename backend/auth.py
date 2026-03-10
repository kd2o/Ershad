import os
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from backend import db
from backend.models import User
from bson import ObjectId

auth = Blueprint("auth", __name__)

def _normalize_student_name(student_name):
    return " ".join(student_name.strip().lower().split())

def _normalize_student_number(student_number):
    return student_number.strip()

def _find_user(student_name, student_number):
    return db.db.users.find_one({
        "student_name_key": _normalize_student_name(student_name),
        "student_number": _normalize_student_number(student_number),
    })


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
    if getattr(current_user, 'role', None) != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('main.home'))

    if request.method == "POST":
        student_name = request.form.get("student_name").strip()
        student_number = request.form.get("student_number").strip()
        role = request.form.get("role")
        
        student_name_key = _normalize_student_name(student_name)

        if db.db.users.find_one({"student_number": student_number}):
            flash("User with this ID already exists!", "warning")
        else:
            db.db.users.insert_one({
                "student_name": student_name,
                "student_name_key": student_name_key,
                "student_number": student_number,
                "role": role
            })
            flash(f"User {student_name} added successfully!", "success")
        return redirect(url_for('auth.add_user'))

    users = list(db.db.users.find())
    return render_template("add_user.html", users=users)

@auth.route("/delete_user/<user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if getattr(current_user, 'role', None) != 'admin':
        return "Unauthorized", 403

    if str(current_user._id) == user_id:
        flash("You cannot delete yourself!", "danger")
        return redirect(url_for('auth.add_user'))

    db.db.users.delete_one({"_id": ObjectId(user_id)})
    flash("User removed.", "info")
    return redirect(url_for('auth.add_user'))

