import os
import uuid
import json
import requests
from flask import Blueprint, flash, render_template_string, request, redirect, url_for, render_template, jsonify
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime  # AM ADĂUGAT

from . import db
### MODIFICAT ###
# Am importat TOATE modelele
from .models import (
    User, Student, Professor, Parent, Subject, StudentSubject,
    Assignment, Submission, Feedback, AIReport
)

# ... (Restul funcțiilor ajutătoare rămân la fel) ...
APP_FOLDER = os.path.dirname(__file__)
STATIC_FOLDER = os.path.join(APP_FOLDER, "static")
UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, "uploads")
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "mp4", "docx", "pptx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


FILE_TYPES = {
    "txt": {"type": "Text File", "img": "images/example.jpg"},
    "pdf": {"type": "PDF Document", "img": "images/example.jpg"},
    "png": {"type": "Image", "img": "images/celldivision.jpeg"},
    "jpg": {"type": "Image", "img": "images/celldivision.jpeg"},
    "jpeg": {"type": "Image", "img": "images/celldivision.jpeg"},
    "gif": {"type": "Image", "img": "images/celldivision.jpeg"},
    "mp4": {"type": "Video", "img": "images/matematica.jpg"},
    "docx": {"type": "Word Document", "img": "images/missiong.jpg"},
    "pptx": {"type": "Presentation", "img": "images/celldivision.jpeg"},
}


def get_files_from_folder(folder_path, user_id):
    files = []
    if not os.path.exists(folder_path):
        return files
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if os.path.isfile(filepath):
            ext = filename.rsplit(".", 1)[-1].lower()
            file_info = FILE_TYPES.get(ext, {"type": "Unknown", "img": "images/example.jpg"})
            img_path = url_for('main.uploaded_file', user_id=user_id, filename=filename)
            files.append({
                "title": filename,
                "type": file_info["type"],
                "img": img_path
            })
    return files


bp = Blueprint("main", __name__)
from flask import send_from_directory


@bp.route('/uploads/<int:user_id>/<filename>')
@login_required
def uploaded_file(user_id, filename):
    user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))
    return send_from_directory(user_folder, filename)


# ... (Rutele index, register, login, logout rămân la fel) ...
@bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return redirect(url_for("main.login"))


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
            flash("Email deja folosit.", "error")
            return redirect(url_for("main.register"))
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
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
            db.session.rollback()
            User.query.filter_by(id=user.id).delete()
            db.session.commit()
            flash(f"Eroare la crearea profilului: {e}", "error")
            return redirect(url_for("main.register"))
        flash("Cont creat cu succes! Te poți loga.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")


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


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


# ---- Pagină principală (Home) ----
@bp.route("/home", methods=["GET", "POST"])
@login_required
def home():
    role = current_user.role

    # ... (Logica de upload pentru Profesor rămâne la fel) ...
    if role == "Profesor":
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

    # --- Logica de AFIȘARE pe rol ---

    if role == "Profesor":
        user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
        files = get_files_from_folder(user_folder, current_user.id)
        return render_template("profesor.html", user=current_user, files=files)

    elif role == "Elev":
        student_profile = Student.query.filter_by(user_id=current_user.id).first()
        assignments_data = []

        if student_profile:
            # --- LOGICĂ MODIFICATĂ ---
            # Preluăm direct temele (submissions) asignate elevului
            my_submissions = Submission.query.filter_by(
                student_id=student_profile.id
            ).join(Assignment).order_by(Assignment.due_date.asc()).all()

            for sub in my_submissions:
                assignments_data.append({
                    "id": sub.assignment.id,  # ID-ul temei
                    "title": sub.assignment.title,
                    "due_date": sub.assignment.due_date.strftime("%Y-%m-%d") if sub.assignment.due_date else "N/A",
                    "status": sub.status  # "Nefăcut", "Trimis" sau "Corectat"
                })

        return render_template("elev.html", user=current_user, assignments=assignments_data)


    elif role == "Parinte":
        # ... (Logica pentru Părinte rămâne neschimbată) ...
        parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
        child_info_data = {}
        if parent_profile:
            child_student = None
            if parent_profile.students:
                child_student = parent_profile.students[0]
            if child_student:
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
                child_info_data = {
                    "name": "Niciun copil asociat.",
                    "grades": [],
                    "show_link_button": True
                }
        return render_template("parinte.html", user=current_user, child=child_info_data)

    else:
        logout_user()
        return redirect(url_for("main.login"))


# ... (Rutele link_child, dashboard, teme_profesor, orar rămân la fel) ...
@bp.route("/link_child", methods=["GET", "POST"])
@login_required
def link_child():
    if current_user.role != "Parinte":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))
    parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
    if not parent_profile:
        flash("Profil de părinte negăsit.", "error")
        return redirect(url_for("main.home"))
    if request.method == "POST":
        student_id = request.form.get("student_id")
        student_to_link = Student.query.get(student_id)
        if student_to_link:
            if student_to_link.parent_id is not None:
                flash("Acest elev are deja un părinte asociat.", "error")
            else:
                student_to_link.parent_id = parent_profile.id
                db.session.commit()
                flash(f"Elevul {student_to_link.user.name} a fost asociat contului tău!", "success")
                return redirect(url_for("main.home"))
        else:
            flash("Elevul selectat nu este valid.", "error")
        return redirect(url_for("main.link_child"))
    available_students = Student.query.filter(Student.parent_id == None).all()
    students_list = []
    for s in available_students:
        students_list.append({"id": s.id, "name": s.user.name})
    return render_template("link_child.html", user=current_user, students=students_list)


@bp.route("/dashboard")
def dashboard():
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
    prof_profile = Professor.query.filter_by(user_id=current_user.id).first()
    assignments_data = []
    if prof_profile:
        professor_assignments = prof_profile.assignments
        for assign in professor_assignments:
            submissions_count = Submission.query.filter(
                Submission.assignment_id == assign.id,
                Submission.status != 'Nefăcut'  # Numărăm doar cele trimise
            ).count()
            total_students = Submission.query.filter_by(assignment_id=assign.id).count()  # Totalul celor asignați
            graded_count = Submission.query.filter(
                Submission.assignment_id == assign.id,
                Submission.status == 'Corectat'
            ).count()
            assignments_data.append({
                "id": assign.id,
                "title": assign.title,
                "due_date": assign.due_date.strftime("%Y-%m-%d") if assign.due_date else "N/A",
                "class": assign.subject.name,
                "submitted": submissions_count,
                "total": total_students if total_students > 0 else '0',  # Schimbat din '?'
                "graded": graded_count
            })
    return render_template("teme_profesor.html", user=current_user, assignments=assignments_data)


@bp.route("/orar")
@login_required
def orar():
    schedule_data = {
        "08:00 - 08:50": ["Matematică", "Română", "Biologie", "Istorie", "Engleză"],
        "09:00 - 09:50": ["Fizică", "Chimie", "Sport", "Română", "Matematică"],
    }
    return render_template("orar.html", user=current_user, schedule=schedule_data)


# ===================================================================
# --- RUTĂ MODIFICATĂ: Creare Temă (Profesor) ---
# ===================================================================
@bp.route("/creare-tema", methods=["GET", "POST"])
@login_required
def creare_tema():
    if current_user.role != "Profesor":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))

    prof_profile = Professor.query.filter_by(user_id=current_user.id).first()

    # Preluăm materiile
    subjects = Subject.query.all()
    # Preluăm TOȚI elevii
    students = Student.query.join(User).all()  # Join User ca să avem acces la nume

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date_str = request.form.get("due_date")
        subject_id = request.form.get("subject_id")

        # --- MODIFICARE ---
        # Preluăm lista de ID-uri de elevi
        student_ids = request.form.getlist("student_ids")  # .getlist() e cheia

        if not title or not description or not due_date_str or not subject_id:
            flash("Titlul, descrierea, data limită și materia sunt obligatorii.", "error")
            return redirect(url_for("main.creare_tema"))

        if not student_ids:
            flash("Trebuie să selectezi cel puțn un elev.", "error")
            return redirect(url_for("main.creare_tema"))

        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')

            # 1. Creăm Tema (Assignment)
            new_assignment = Assignment(
                teacher_id=prof_profile.id,
                subject_id=int(subject_id),
                title=title,
                description=description,
                due_date=due_date
            )

            db.session.add(new_assignment)
            # Facem un "pre-commit" ca să obținem ID-ul temei (new_assignment.id)
            db.session.flush()

            # 2. Creăm "fișele" (Submissions) goale pentru fiecare elev
            for student_id in student_ids:
                new_submission = Submission(
                    assignment_id=new_assignment.id,
                    student_id=int(student_id),
                    status="Nefăcut"
                    # content este null implicit
                    # submitted_at este null implicit
                )
                db.session.add(new_submission)

            # 3. Salvăm totul
            db.session.commit()

            flash(f"Temă creată și asignată la {len(student_ids)} elevi!", "success")
            return redirect(url_for("main.teme_profesor"))

        except Exception as e:
            db.session.rollback()
            flash(f"Eroare la crearea temei: {e}", "error")

    # GET: trimitem materiile ȘI elevii la template
    return render_template("creare_tema.html", user=current_user, subjects=subjects, students=students)


# ===================================================================
# --- RUTĂ MODIFICATĂ: Detaliu și Trimitere Temă (Elev) ---
# ===================================================================
@bp.route("/tema/<int:id_tema>", methods=["GET", "POST"])
@login_required
def detaliu_tema(id_tema):
    if current_user.role != "Elev":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))

    student_profile = Student.query.filter_by(user_id=current_user.id).first()
    assignment = Assignment.query.get_or_404(id_tema)

    # --- MODIFICARE ---
    # Găsim "fișa" (Submission) specifică acestui elev pentru această temă
    submission = Submission.query.filter_by(
        assignment_id=id_tema,
        student_id=student_profile.id
    ).first()

    # Dacă nu există o "fișă", înseamnă că tema nu i-a fost asignată
    if not submission:
        flash("Această temă nu ți-a fost asignată.", "error")
        return redirect(url_for('main.home'))

    if request.method == "POST":
        # Elevul trimite tema

        # --- MODIFICARE ---
        # Verificăm statusul "fișei"
        if submission.status != 'Nefăcut':
            flash("Ai trimis deja o rezolvare pentru această temă.", "warning")
            return redirect(url_for('main.detaliu_tema', id_tema=id_tema))

        content = request.form.get("content")
        if not content:
            flash("Rezolvarea nu poate fi goală.", "error")
            return redirect(url_for('main.detaliu_tema', id_tema=id_tema))

        # --- MODIFICARE ---
        # Actualizăm "fișa" existentă, nu creăm una nouă
        submission.content = content
        submission.status = "Trimis"
        submission.submitted_at = datetime.utcnow()

        db.session.commit()

        flash("Tema a fost trimisă cu succes!", "success")
        return redirect(url_for('main.detaliu_tema', id_tema=id_tema))

    # Metoda GET: Afișăm detaliile
    feedback = None
    if submission and submission.feedback:
        feedback = submission.feedback

    return render_template(
        "detaliu_tema_elev.html",
        user=current_user,
        assignment=assignment,
        submission=submission,
        feedback=feedback
    )


# ... (Restul rutelor: detaliu_tema_profesor, corectare_tema, și toată zona de API / AI rămân la fel) ...
@bp.route("/tema-profesor/<int:id_tema>")
@login_required
def detaliu_tema_profesor(id_tema):
    if current_user.role != "Profesor":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))
    assignment = Assignment.query.get_or_404(id_tema)
    submissions = Submission.query.filter_by(assignment_id=id_tema).all()
    return render_template(
        "detaliu_tema_profesor.html",
        user=current_user,
        assignment=assignment,
        submissions=submissions
    )


@bp.route("/corectare/<int:id_submission>", methods=["GET", "POST"])
@login_required
def corectare_tema(id_submission):
    if current_user.role != "Profesor":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))
    submission = Submission.query.get_or_404(id_submission)
    if request.method == "POST":
        grade = request.form.get("grade")
        feedback_text = request.form.get("feedback_text")
        if not grade or not feedback_text:
            flash("Nota și feedback-ul sunt obligatorii.", "error")
            return redirect(url_for('main.corectare_tema', id_submission=id_submission))
        existing_feedback = Feedback.query.filter_by(submission_id=id_submission).first()
        feedback_obj = None
        try:
            if existing_feedback:
                existing_feedback.grade = grade
                existing_feedback.feedback_text = feedback_text
                feedback_obj = existing_feedback
            else:
                new_feedback = Feedback(
                    submission_id=id_submission,
                    grade=grade,
                    feedback_text=feedback_text
                )
                db.session.add(new_feedback)
                feedback_obj = new_feedback
            submission.status = "Corectat"
            db.session.commit()
            try:
                generate_ai_report_for_feedback(feedback_obj)
                flash("Feedback salvat și raport AI generat!", "success")
            except Exception as e:
                print(f"Eroare la generarea raportului AI: {e}")
                flash("Feedback salvat, dar a eșuat generarea raportului AI.", "warning")
            return redirect(url_for('main.detaliu_tema_profesor', id_tema=submission.assignment_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Eroare la salvarea feedback-ului: {e}")
    return render_template("corectare_tema.html", user=current_user, submission=submission)


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


@bp.route("/chat", methods=["GET"])
@login_required
def chat_page():
    return render_template("chat.html")


def generate_ai_report_for_feedback(feedback_obj):
    print(f"--- Inițiere generare raport AI pentru Feedback ID: {feedback_obj.id} ---")
    student = feedback_obj.submission.student
    assignment = feedback_obj.submission.assignment
    lista_feedbackuri = []
    student_submissions = Submission.query.filter_by(student_id=student.id).all()
    for sub in student_submissions:
        if sub.feedback:
            lista_feedbackuri.append({
                "nota": sub.feedback.grade,
                "feedback": sub.feedback.feedback_text
            })
    system_prompt = (
        "Ești un asistent AI educațional. Rolul tău este să analizezi feedback-ul unui profesor "
        "și cerința unei teme, și să generezi un raport structurat pentru elev."
        "Raportul trebuie să fie încurajator, să identifice punctele forte, punctele slabe și să ofere sugestii clare."
        "Trebuie să răspunzi OBLIGATORIU într-un format JSON valid, cu următoarele chei: "
        "'summary' (un scurt rezumat al performanței), "
        "'strengths' (ce a făcut bine elevul), "
        "'weaknesses' (ce a greșit sau unde mai are de lucrat), "
        "'suggestions' (sfaturi concrete pentru îmbunătățire), "
        "'parent_summary' (un rezumat scurt, pe înțelesul unui părinte)."
    )
    user_prompt = (
        f"Analizează următoarea situație:\n"
        f"**Cerința Temei:**\n{assignment.description}\n\n"
        f"**Feedback-ul Profesorului (cel mai recent):**\n{feedback_obj.feedback_text}\n"
        f"**Nota:** {feedback_obj.grade}\n\n"
        f"**Istoricul de feedback al elevului (dacă există):**\n{json.dumps(lista_feedbackuri, ensure_ascii=False)}\n\n"
        f"Generează raportul JSON structurat."
    )
    prompt_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    ai_response_str = call_model(prompt_messages)
    if not ai_response_str:
        print("Eroare: Răspuns gol de la modelul AI.")
        return
    try:
        if ai_response_str.startswith("```json"):
            ai_response_str = ai_response_str[7:-3].strip()
        ai_data = json.loads(ai_response_str)
        ai_report = AIReport.query.filter_by(feedback_id=feedback_obj.id).first()
        if not ai_report:
            ai_report = AIReport(
                feedback_id=feedback_obj.id,
                student_id=student.id
            )
            db.session.add(ai_report)
        ai_report.report_content = ai_response_str
        ai_report.summary = ai_data.get('summary', 'N/A')
        ai_report.strengths = ai_data.get('strengths', 'N/A')
        ai_report.weaknesses = ai_data.get('weaknesses', 'N/A')
        ai_report.suggestions = ai_data.get('suggestions', 'N/A')
        ai_report.parent_summary = ai_data.get('parent_summary', 'N/A')
        db.session.commit()
        print(f"--- Raport AI salvat cu succes pentru Feedback ID: {feedback_obj.id} ---")
    except json.JSONDecodeError:
        print(f"Eroare: Răspunsul AI nu a fost un JSON valid: {ai_response_str}")
    except Exception as e:
        db.session.rollback()
        print(f"Eroare la salvarea raportului AI în baza de date: {e}")


@bp.route("/api/generate_report", methods=["POST"])
@login_required
def generate_report():
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"status": "error", "message": "Doar elevii pot genera rapoarte de test."})
    latest_submission = Submission.query.filter_by(student_id=student.id).order_by(
        Submission.submitted_at.desc()).first()
    if not latest_submission or not latest_submission.feedback:
        return jsonify(
            {"status": "error", "message": "Nu ai niciun feedback de la profesor pentru a genera un raport."})
    try:
        generate_ai_report_for_feedback(latest_submission.feedback)
        return jsonify({"status": "ok", "message": "Raport de test generat cu succes!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Eroare la generare: {e}"})


@bp.route("/api/query", methods=["POST"])
@login_required
def query_model():
    data = request.json
    user_msg = data.get("message", "")
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"response": "Eroare: Nu am găsit profilul tău de student."})
    latest_report = AIReport.query.filter_by(student_id=student.id).order_by(AIReport.id.desc()).first()
    context_str = "Context intern:\n"
    if latest_report:
        feedback = latest_report.feedback
        assignment = feedback.submission.assignment
        context_str += f"Materie={assignment.subject.name}\n"
        context_str += f"Cerinta={assignment.description}\n"
        context_str += f"Feedback_profesor={feedback.feedback_text}\n"
        context_str += f"Puncte_slabe_identificate={latest_report.weaknesses}\n"
        context_str += f"Sugestii_AI={latest_report.suggestions}\n"
    else:
        context_str += "Niciun raport AI generat încă. Răspunde la întrebarea elevului cât de bine poți."
    responder_prompt = [
        {
            "role": "system",
            "content": (
                "Ești un chatbot tutore, prietenos și încurajator, pentru elevi. "
                "Scopul tău este să ajuți elevul să înțeleagă feedback-ul primit și să își îmbunătățească munca. "
                "Folosește contextul intern (punctele slabe și sugestiile) pentru a oferi explicații suplimentare. "
                "Nu preda materia de la zero, ci ghidează elevul pe baza feedback-ului."
            )
        },
        {
            "role": "system",
            "content": context_str
        },
        {"role": "user", "content": user_msg}
    ]
    final_answer = call_model(responder_prompt)
    if not final_answer:
        final_answer = "Nu am reușit să procesez răspunsul. Te rog, mai încearcă."
    return jsonify({"response": final_answer})