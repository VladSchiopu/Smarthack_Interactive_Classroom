from flask import Blueprint, flash, render_template_string, request, redirect, url_for, render_template, jsonify
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
import os

from . import db
from .models import User

# Upload files
import uuid
from werkzeug.utils import secure_filename
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "mp4", "docx", "pptx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


bp = Blueprint("main", __name__)


# ---- Rutele tale originale ----
@bp.route("/", methods=["GET"])
def index():
    # Redirecționează către login dacă nu e logat, sau către home dacă este
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return redirect(url_for("main.login"))


# ---- Înregistrare ----
@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        role = request.form.get("role")

        if User.query.filter_by(email=email).first():
            # Ar fi bine să trimiți un mesaj flash aici
            return redirect(url_for("main.register"))

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("main.login"))

    return render_template("register.html")


# ---- Login ----
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            # Redirecționează către 'home' care va gestiona rolul
            return redirect(url_for("main.home"))

            # Ar fi bine să trimiți un mesaj flash aici
        return redirect(url_for("main.login"))

    return render_template("login.html")


# ---- Logout ----
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


# ---- Pagină principală (Home) care redirecționează pe rol ----
@bp.route("/home", methods=["GET", "POST"])
@login_required
def home():
    role = current_user.role

    user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
    os.makedirs(user_folder, exist_ok=True)

    if request.method == "POST":
        if "file" not in request.files:
            flash("Nu s-a selectat niciun fișier.")
            return redirect(request.url)

        file = request.files["file"]
        title = request.form.get("title", "")

        if file.filename == "":
            flash("Nume de fișier invalid.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            original_ext = file.filename.rsplit(".", 1)[1].lower()
            title = request.form.get("title", "").strip()

            # generăm un ID unic
            unique_id = str(uuid.uuid4())

            # construim un nume sigur
            if title:
                safe_title = secure_filename(title)
                filename = f"{safe_title}_{unique_id}.{original_ext}"
            else:
                filename = f"{unique_id}.{original_ext}"

            save_path = os.path.join(user_folder, filename)
            file.save(save_path)

            # poți loga și titlul în DB dacă vrei
            flash(f"Fișierul '{title or filename}' a fost încărcat cu succes!")
            return redirect(url_for("main.home"))
        else:
            flash("Tip de fișier nepermis.")
            return redirect(request.url)


    if role == "Profesor":
        # Date dummy pentru profesor
        files = [
            {"title": "Chapter 1 Reading.pdf", "type": "PDF Document", "img": "images/example.jpg"},
            {"title": "Photosynthesis Slides.pptx", "type": "Presentation", "img": "images/celldivision.jpeg"},
            {"title": "Introduction Video.mp4", "type": "Video", "img": "images/matematica.jpg"},
            {"title": "Syllabus_Fall_2024.docx", "type": "Word Document", "img": "images/missiong.jpg"},
        ]
        return render_template("profesor.html", user=current_user, files=files)

    elif role == "Elev":
        # Date dummy pentru elev
        assignments = [
            {"title": "Eseu Biologie", "due_date": "10 Nov 2025", "status": "În progres"},
            {"title": "Test Matematică", "due_date": "12 Nov 2025", "status": "Nefăcut"},
            {"title": "Proiect Istorie", "due_date": "8 Nov 2025", "status": "Trimis"},
        ]
        return render_template("elev.html", user=current_user, assignments=assignments)

    elif role == "Parinte":
        # Date dummy pentru părinte
        child_info = {
            "name": "Popescu Ionuț (Elev)",
            "grades": [
                {"subject": "Matematică", "grade": "10"},
                {"subject": "Română", "grade": "9"},
                {"subject": "Biologie", "grade": "10"},
            ]
        }
        return render_template("parinte.html", user=current_user, child=child_info)

    else:
        # Un rol neașteptat
        logout_user()
        return redirect(url_for("main.login"))


@bp.route("/dashboard")
def dashboard():
    # Dummy data — later we’ll pull from DB
    files = [
        {"title": "Chapter 1 Reading.pdf", "type": "PDF Document", "img": "images/example.jpg"},
        {"title": "Sales.pptx", "type": "Presentation", "img": "images/salesPpx.png"},
        {"title": "Introduction Video.mp4", "type": "Video", "img": "images/matematica.jpg"},
        {"title": "Missing Latter.docx", "type": "Word Document", "img": "images/missiong.jpg"},
        {"title": "Lab Safety Rules.pdf", "type": "PDF Document", "img": "images/lab.jpg"},
        {"title": "Cell Division Animation.mp4", "type": "Video", "img": "images/celldivision.jpeg"},
    ]
    return render_template("dashboard.html", files=files, user=current_user)


@bp.route("/teme_profesor")
@login_required
def teme_profesor():
    # Asigură-te că doar profesorii văd asta
    if current_user.role != "Profesor":
        return redirect(url_for("main.home"))

    # Date dummy pentru temele create de profesor
    assignments = [
        {"title": "Eseu Biologie", "due_date": "10 Nov 2025", "class": "Clasa a 10-a A", "submitted": 28, "total": 30},
        {"title": "Test Matematică", "due_date": "12 Nov 2025", "class": "Clasa a 9-a B", "submitted": 15, "total": 25},
        {"title": "Proiect Istorie", "due_date": "8 Nov 2025", "class": "Clasa a 10-a A", "submitted": 30, "total": 30},
    ]
    return render_template("teme_profesor.html", user=current_user, assignments=assignments)
@bp.route("/orar")
@login_required
def orar():
    # Date dummy pentru orar
    # Folosim un dicționar pentru a păstra ordinea orelor
    schedule_data = {
        "08:00 - 08:50": ["Matematică", "Română", "Biologie", "Istorie", "Engleză"],
        "09:00 - 09:50": ["Fizică", "Chimie", "Sport", "Română", "Matematică"],
        "10:00 - 10:50": ["Biologie", "Istorie", "Geografie", "Fizică", "Informatică"],
        "11:00 - 11:10": ["Pauză", "Pauză", "Pauză", "Pauză", "Pauză"],
        "11:10 - 12:00": ["Istorie", "Engleză", "Franceză", "Sport", "Română"],
        "12:10 - 13:00": ["Engleză", "Matematică", "Informatică", "Chimie", "Geografie"],
        "13:10 - 14:00": ["Română", "Sport", "Dirigenție", "Muzică", "Franceză"],
    }
    return render_template("orar.html", user=current_user, schedule=schedule_data)

OPENROUTER_API_KEY = "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"

LOG_FILENAME = "params_log.json"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", LOG_FILENAME)

if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def call_model(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": "openrouter/polaris-alpha", "messages": messages}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception as e:
        print("call_model error:", e)
        return None


def read_log():
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def append_to_log(entry):
    log = read_log()
    log.append(entry)
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error writing log file:", e)



# ---- Pagina de chat ----
@bp.route("/chat", methods=["GET"])
@login_required  # E bine să fie protejată
def chat_page():
    return render_template("chat.html")


@bp.route("/api/generate_report", methods=["POST"])
@login_required
def generate_report():
    # 🔹 Date hardcodate pentru test
    materie = "Matematică"
    cerinta = "Rezolvă exercițiile despre fracții, amplificări și simplificări."
    lista_feedbackuri = [
        {"nota": 7.5, "feedback": "Ai făcut corect exercițiile legate de înmulțiri și ecuații, dar nu ai făcut fracțiile."},
        {"nota": 5, "feedback": "Ai făcut corect ecuațiile, dar nu ai făcut exercițiile nici de la amplificări, nici de la simplificări."}
    ]

    # 🔹 Prompt pentru generarea raportului
    raport_prompt = [
        {
            "role": "system",
            "content": (
                "Ești un asistent care analizează evoluția unui elev la o materie. "
                "Primești o listă de feedbackuri sub forma [(nota, feedback)] și trebuie să generezi un raport complet. "
                "Considera ultimul feedback ca cel de la assignmentul curent"
                "Raportul trebuie să detalieze:\n"
                "- care au fost principalele probleme repetate,\n"
                "- ce a îmbunătățit copilul de-a lungul timpului,\n"
                "- dacă performanța s-a îmbunătățit sau s-a înrăutățit (în funcție de note),\n"
                "- ce ar trebui să revizuiască pentru viitoarele assignmenturi."
            )
        },
        {
            "role": "user",
            "content": f"Materie: {materie}\nCerinta: {cerinta}\nFeedbackuri: {lista_feedbackuri}"
        }
    ]

    raport_text = call_model(raport_prompt)
    if not raport_text:
        raport_text = "Eroare: nu s-a putut genera raportul."

    # 🔹 Salvează în reports.txt
    with open("reports.txt", "a", encoding="utf-8") as f:
        f.write(f"\n=== RAPORT pentru {materie} ===\n{raport_text}\n\n")

    return jsonify({"status": "ok"})


@bp.route("/api/query", methods=["POST"])
@login_required
def query_model():
    data = request.json
    user_msg = data.get("message", "")

    # 🔹 Date hardcodate pentru test (până când vor fi primite din UI)
    materie = "Matematică"
    cerinta = "Rezolvă exercițiile despre fracții, amplificări și simplificări."
    lista_feedbackuri = [
        {"nota": 7.5, "feedback": "Ai făcut corect exercițiile legate de înmulțiri și ecuații, dar nu ai făcut fracțiile."},
        {"nota": 5, "feedback": "Ai făcut corect ecuațiile, dar nu ai făcut exercițiile nici de la amplificări, nici de la simplificări."}
    ]


    # 🔹 Prompt pentru chatbot
    responder_prompt = [
        {
            "role": "system",
            "content": (
                "Ești un chatbot pentru elevi din școala primară. "
                "Primești materia, cerința assignmentului, feedbackul profesorului și nota elevului. "
                "Explică elevului într-un mod prietenos cum ar fi trebuit rezolvat assignmentul, "
                "răspunde la întrebări legate de cerință și oferă încurajări. "
                "Ține cont și de feedbackurile anterioare pentru a-l ajuta să înțeleagă ce repetă greșit sau unde s-a îmbunătățit."
                "Considera ultimul feedback ca cel de la assignmentul curent"
            )
        },
        {
            "role": "system",
            "content": (
                f"Context intern:\n"
                f"Materie={materie}\n"
                f"Cerinta={cerinta}\n"
                f"Feedbackuri_anterioare={lista_feedbackuri}"
            )
        },
        {"role": "user", "content": user_msg}
    ]

    final_answer = call_model(responder_prompt)
    if not final_answer:
        final_answer = "Nu am reușit să răspund, te rog mai încearcă."

    return jsonify({"response": final_answer})