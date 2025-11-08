import os
import uuid
import json
import requests
from flask import Blueprint, flash, render_template_string, request, redirect, url_for, render_template, jsonify
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from . import db
### MODIFICAT ###
# Am importat toate modelele necesare
from .models import User, Student, Professor, Parent, Subject, StudentSubject, Assignment, Submission, Feedback

# Upload files (partea aceasta rămâne neschimbată)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "mp4", "docx", "pptx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


bp = Blueprint("main", __name__)


# ---- Rutele tale originale (neschimbate) ----
@bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return redirect(url_for("main.login"))


# ---- Înregistrare (neschimbat) ----
@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        role = request.form.get("role")  # ex: "Elev", "Profesor", "Parinte"

        if User.query.filter_by(email=email).first():
            flash("Email deja folosit.", "error")
            return redirect(url_for("main.register"))

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # --- Creare profil specific pe rol ---
        # După ce user-ul de bază e creat, creăm și profilul asociat
        try:
            if role == "Elev":
                student_profile = Student(user_id=user.id)
                db.session.add(student_profile)
            elif role == "Profesor":
                prof_profile = Professor(user_id=user.id)
                db.session.add(prof_profile)
            elif role == "Parinte":
                parent_profile = Parent(user_id=user.id)
                db.session.add(parent_profile)

            db.session.commit()
        except Exception as e:
            # În caz de eroare (de ex. user_id duplicat), anulăm crearea user-ului
            db.session.rollback()
            User.query.filter_by(id=user.id).delete()
            db.session.commit()
            flash(f"Eroare la crearea profilului: {e}", "error")
            return redirect(url_for("main.register"))

        flash("Cont creat cu succes! Te poți loga.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# ---- Login (neschimbat) ----
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
            return redirect(url_for("main.home"))

        flash("Email sau parolă incorectă.", "error")
        return redirect(url_for("main.login"))

    return render_template("login.html")


# ---- Logout (neschimbat) ----
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

    # Logica de upload (neschimbată)
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
            unique_id = str(uuid.uuid4())

            if title:
                safe_title = secure_filename(title)
                filename = f"{safe_title}_{unique_id}.{original_ext}"
            else:
                filename = f"{unique_id}.{original_ext}"

            save_path = os.path.join(user_folder, filename)
            file.save(save_path)

            flash(f"Fișierul '{title or filename}' a fost încărcat cu succes!")
            return redirect(url_for("main.home"))
        else:
            flash("Tip de fișier nepermis.")
            return redirect(request.url)

    # --- Logica de afișare pe rol ---

    if role == "Profesor":
        ### MODIFICAT ###
        # Nota: Lista 'files' este încă hardcodată.
        # Pentru a o popula dinamic, ar trebui să avem un model `File` în `models.py`
        # care să stocheze calea fișierului, titlul și user_id-ul.
        files = [
            {"title": "Chapter 1 Reading.pdf", "type": "PDF Document", "img": "images/example.jpg"},
            {"title": "Photosynthesis Slides.pptx", "type": "Presentation", "img": "images/celldivision.jpeg"},
        ]
        return render_template("profesor.html", user=current_user, files=files)

    elif role == "Elev":
        ### MODIFICAT ###
        # Preluăm profilul de student al utilizatorului logat
        student_profile = Student.query.filter_by(user_id=current_user.id).first()

        assignments_data = []
        if student_profile:
            # Preluăm TOATE temele din baza de date (conform cerinței)
            all_assignments = Assignment.query.all()

            for assign in all_assignments:
                # Verificăm dacă studentul curent a trimis ceva pentru această temă
                submission = Submission.query.filter_by(
                    assignment_id=assign.id,
                    student_id=student_profile.id
                ).first()

                status = "Nefăcut"
                if submission:
                    status = submission.status  # ex: "Trimis", "Gradat"

                assignments_data.append({
                    "title": assign.title,
                    "due_date": "N/A",  # Modelul 'Assignment' nu are 'due_date'
                    "status": status
                })

        return render_template("elev.html", user=current_user, assignments=assignments_data)


    elif role == "Parinte":

        ### MODIFICAT ȘI CORECTAT ###

        parent_profile = Parent.query.filter_by(user_id=current_user.id).first()

        child_info_data = {}  # Inițializăm un dicționar gol

        if parent_profile:

            # Preluăm PRIMUL copil al acestui părinte

            # --- AICI ESTE CORECȚIA ---

            # Verificăm dacă lista parent_profile.students nu este goală

            child_student = None

            if parent_profile.students:
                child_student = parent_profile.students[0]  # Accesăm primul element

            if child_student:

                # Părintele ARE un copil asociat, afișăm datele

                grades_list = []

                student_subjects = StudentSubject.query.filter_by(student_id=child_student.id).all()

                for ss in student_subjects:
                    grades_list.append({

                        "subject": ss.subject.name,

                        "grade": ss.performance_history or "N/A"

                    })

                child_info_data = {

                    "name": child_student.user.name,

                    "grades": grades_list

                }

            else:

                # Părintele NU are un copil asociat

                # Adăugăm un flag pentru a-i afișa un link în template

                child_info_data = {

                    "name": "Niciun copil asociat.",

                    "grades": [],

                    "show_link_button": True

                }

        return render_template("parinte.html", user=current_user, child=child_info_data)

    else:
        # Un rol neașteptat
        logout_user()
        return redirect(url_for("main.login"))


@bp.route("/link_child", methods=["GET", "POST"])
@login_required
def link_child():
    # Asigură-te că doar părinții accesează
    if current_user.role != "Parinte":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))

    parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
    if not parent_profile:
        flash("Profil de părinte negăsit.", "error")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        student_id = request.form.get("student_id")
        student_to_link = Student.query.get(student_id)  # Căutăm studentul după ID

        if student_to_link:
            # Verificăm dacă studentul nu are deja un părinte
            if student_to_link.parent_id is not None:
                flash("Acest elev are deja un părinte asociat.", "error")
            else:
                # Facem legătura
                student_to_link.parent_id = parent_profile.id
                # Alternativ, poți folosi relația:
                # parent_profile.students.append(student_to_link)
                db.session.commit()
                flash(f"Elevul {student_to_link.user.name} a fost asociat contului tău!", "success")
                return redirect(url_for("main.home"))
        else:
            flash("Elevul selectat nu este valid.", "error")

        return redirect(url_for("main.link_child"))

    # Metoda GET: Afișăm toți studenții care NU au un părinte
    available_students = Student.query.filter(Student.parent_id == None).all()

    # Trimitem o listă cu id-ul și numele studentului către template
    students_list = []
    for s in available_students:
        students_list.append({"id": s.id, "name": s.user.name})

    return render_template("link_child.html", user=current_user, students=students_list)

@bp.route("/dashboard")
def dashboard():
    ### MODIFICAT ###
    # Aceeași notă ca la /home pentru Profesor:
    # Lista 'files' este încă hardcodată.
    files = [
        {"title": "Chapter 1 Reading.pdf", "type": "PDF Document", "img": "images/example.jpg"},
        {"title": "Sales.pptx", "type": "Presentation", "img": "images/salesPpx.png"},
    ]
    return render_template("dashboard.html", files=files, user=current_user)


@bp.route("/teme_profesor")
@login_required
def teme_profesor():
    if current_user.role != "Profesor":
        return redirect(url_for("main.home"))

    ### MODIFICAT ###
    # Preluăm profilul de profesor
    prof_profile = Professor.query.filter_by(user_id=current_user.id).first()

    assignments_data = []
    if prof_profile:
        # Preluăm temele create de ACEST profesor (folosind relația)
        professor_assignments = prof_profile.assignments

        for assign in professor_assignments:
            # Numărăm câte trimiteri a primit tema
            submissions_count = Submission.query.filter_by(assignment_id=assign.id).count()

            assignments_data.append({
                "title": assign.title,
                "due_date": "N/A",  # Modelul 'Assignment' nu are 'due_date'
                "class": assign.subject.name,  # Folosim numele materiei
                "submitted": submissions_count,
                "total": "?"  # Nu avem numărul total de elevi
            })

    return render_template("teme_profesor.html", user=current_user, assignments=assignments_data)


@bp.route("/orar")
@login_required
def orar():
    ### MODIFICAT ###
    # Datele pentru orar sunt încă hardcodate.
    # Pentru a le prelua dinamic, ar fi necesar un model 'Schedule' sau 'Timetable'
    # în 'models.py', care să lege zile, ore, materii și profesori.
    schedule_data = {
        "08:00 - 08:50": ["Matematică", "Română", "Biologie", "Istorie", "Engleză"],
        "09:00 - 09:50": ["Fizică", "Chimie", "Sport", "Română", "Matematică"],
    }
    return render_template("orar.html", user=current_user, schedule=schedule_data)


# ---- API-ul OpenRouter (neschimbat) ----
OPENROUTER_API_KEY = "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"
LOG_FILENAME = "params_log.json"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", LOG_FILENAME)
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def call_model(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
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


# ---- Pagina de chat (neschimbată) ----
@bp.route("/chat", methods=["GET"])
@login_required
def chat_page():
    return render_template("chat.html")


# ---- Rutele API pentru Chat (MODIFICATE) ----

@bp.route("/api/generate_report", methods=["POST"])
@login_required
def generate_report():
    ### MODIFICAT ###
    # Preluăm date din DB în loc de date hardcodate
    # Vom folosi datele PRIMULUI student și PRIMEI teme (conform cerinței)

    student = Student.query.first()
    assignment = Assignment.query.first()

    if not student or not assignment:
        return jsonify({"status": "error", "message": "Nu există studenți sau teme în baza de date."})

    materie = assignment.subject.name
    cerinta = assignment.description

    # Preluăm toate feedback-urile pentru acest student
    lista_feedbackuri = []
    student_submissions = Submission.query.filter_by(student_id=student.id).all()

    for sub in student_submissions:
        if sub.feedback:  # Doar dacă există feedback
            lista_feedbackuri.append({
                "nota": sub.feedback.grade,
                "feedback": sub.feedback.feedback_text
            })

    # 🔹 Promptul (rămâne la fel)
    raport_prompt = [
        {"role": "system", "content": "Ești un asistent..."},  # Am scurtat promptul aici
        {"role": "user", "content": f"Materie: {materie}\nCerinta: {cerinta}\nFeedbackuri: {lista_feedbackuri}"}
    ]

    raport_text = call_model(raport_prompt)
    if not raport_text:
        raport_text = "Eroare: nu s-a putut genera raportul."

    with open("reports.txt", "a", encoding="utf-8") as f:
        f.write(f"\n=== RAPORT pentru {materie} ===\n{raport_text}\n\n")

    return jsonify({"status": "ok"})


@bp.route("/api/query", methods=["POST"])
@login_required
def query_model():
    data = request.json
    user_msg = data.get("message", "")

    ### MODIFICAT ###
    # Preluăm date din DB. De data aceasta, vom folosi studentul CURENT (logat)

    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"response": "Eroare: Nu am găsit profilul tău de student."})

    # Preluăm prima temă ca și context (conform cerinței)
    assignment = Assignment.query.first()
    if not assignment:
        return jsonify({"response": "Eroare: Nu există nicio temă în sistem."})

    materie = assignment.subject.name
    cerinta = assignment.description

    # Preluăm feedback-urile studentului CURENT
    lista_feedbackuri = []
    student_submissions = Submission.query.filter_by(student_id=student.id).all()

    for sub in student_submissions:
        if sub.feedback:
            lista_feedbackuri.append({
                "nota": sub.feedback.grade,
                "feedback": sub.feedback.feedback_text
            })

    # 🔹 Promptul (rămâne la fel, dar cu date dinamice)
    responder_prompt = [
        {
            "role": "system",
            "content": (
                "Ești un chatbot pentru elevi din școala primară... "
                "Ține cont și de feedbackurile anterioare..."
            )  # Am scurtat promptul
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