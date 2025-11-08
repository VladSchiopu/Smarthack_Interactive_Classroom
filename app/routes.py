from flask import Blueprint, render_template_string, request, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .users_db import users, add_user, get_user

bp = Blueprint("main", __name__)

# Model simplu pentru utilizatori
class User(UserMixin):
    def __init__(self, email, name):
        self.id = email
        self.name = name

# ---- Rutele tale originale ----
@bp.route("/", methods=["GET"])
def hello():
    return "Hello, World!"


# ---- Înregistrare ----
@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        name = request.form["name"]
        password = request.form["password"]

        if get_user(email):
            return "Email deja folosit!"
        add_user(email, name, password)
        return redirect(url_for("main.login"))

    return render_template_string("""
        <h2>Înregistrare</h2>
        <form method="post">
            Nume: <input type="text" name="name"><br>
            Email: <input type="email" name="email"><br>
            Parola: <input type="password" name="password"><br>
            <button type="submit">Înregistrează</button>
        </form>
        <a href="/login">Ai deja cont?</a>
    """)


# ---- Login ----
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = get_user(email)

        if user and check_password_hash(user["password"], password):
            login_user(User(email, user["name"]))
            return redirect(url_for("main.hello"))
        return "Date de autentificare incorecte!"

    return render_template_string("""
        <h2>Login</h2>
        <form method="post">
            Email: <input type="email" name="email"><br>
            Parola: <input type="password" name="password"><br>
            <button type="submit">Autentificare</button>
        </form>
        <a href="/register">Nu ai cont?</a>
    """)


# ---- Logout ----
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
def dashboard():
    # Dummy data — later we’ll pull from DB
    files = [
        {"title": "Chapter 1 Reading.pdf", "type": "PDF Document", "img": "images/doc.png"},
        {"title": "Photosynthesis Slides.pptx", "type": "Presentation", "img": "images/presentation.png"},
        {"title": "Introduction Video.mp4", "type": "Video", "img": "images/video.png"},
        {"title": "Syllabus_Fall_2024.docx", "type": "Word Document", "img": "images/doc.png"},
        {"title": "Lab Safety Rules.pdf", "type": "PDF Document", "img": "images/doc.png"},
        {"title": "Cell Division Animation.mp4", "type": "Video", "img": "images/video.png"},
        {"title": "Genetics Worksheet.pdf", "type": "PDF Document", "img": "images/doc.png"},
        {"title": "Final Project Rubric.docx", "type": "Word Document", "img": "images/doc.png"},
    ]
    return render_template("dashboard.html", files=files, user=current_user)
