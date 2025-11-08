from flask import Blueprint, render_template_string, request, redirect, url_for, render_template, jsonify
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .users_db import users, add_user, get_user
import requests
import json
import os


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

    return render_template("register.html")


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

    return render_template("login.html")


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


OPENROUTER_API_KEY = "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"

LOG_FILENAME = "params_log.json"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", LOG_FILENAME)

# Asigurăm logul
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
def chat_page():
    return render_template("chat.html")


# ---- Endpoint API pentru chat ----
@bp.route("/api/query", methods=["POST"])
def query_model():
    user_msg = request.json.get("message", "")

    extractor_prompt = [
        {
            "role": "system",
            "content":
                "Primești text de la utilizator. Extrage DOAR parametrii:\n"
                "- Fericire (Nervos, Fericit, Trist, Plictisit, Normal, Chef_de_bataie)\n"
                "- Varsta (0–100)\n"
                'Răspunde STRICT în JSON valid: { "fericire": "<valoare>", "varsta": numar }'
        },
        {"role": "user", "content": user_msg}
    ]

    extractor_output = call_model(extractor_prompt)
    default_params = {"fericire": "Normal", "varsta": 25}

    try:
        extracted = json.loads(extractor_output) if extractor_output else default_params
        allowed = ["Nervos", "Fericit", "Trist", "Plictisit", "Normal", "Chef_de_bataie"]
        fer = extracted.get("fericire", "Normal").strip().capitalize()
        fer_norm = fer if fer in allowed else "Normal"
        try:
            var_int = max(0, min(100, int(extracted.get("varsta", 25))))
        except:
            var_int = 25
        extracted = {"fericire": fer_norm, "varsta": var_int}
    except:
        extracted = default_params

    append_to_log(extracted)
    current_log = read_log()

    responder_prompt = [
        {
            "role": "system",
            "content": (
                "Ești o IA care răspunde întrebărilor utilizatorului. "
                "Adaptează tonul în funcție de parametrii:\n"
                "- Nervos → răspunde iritat\n"
                "- Fericit → vesel și prietenos\n"
                "- Trist → melancolic\n"
                "- Plictisit → apatic\n"
                "- Normal → neutru\n"
                "- Chef_de_bataie → provocator și furios"
            )
        },
        {"role": "system",
         "content": f"Context intern: Fericire={extracted['fericire']}, Varsta={extracted['varsta']}."},
        {"role": "user", "content": user_msg}
    ]

    final_answer = call_model(responder_prompt)
    if not final_answer:
        final_answer = "Eroare: modelul nu a returnat răspuns."

    return jsonify({
        "response": final_answer,
        "params": extracted,
        "log": current_log
    })