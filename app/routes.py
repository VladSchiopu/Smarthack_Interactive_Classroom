import os
import uuid
import json
import requests
import sys
import io
from flask import Blueprint, flash, render_template_string, request, redirect, url_for, render_template, jsonify
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime  # AM ADAUGAT

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from . import db
### MODIFICAT ###
# Am importat TOATE modelele
from .models import (
    Absence, User, Student, Professor, Parent, Subject, StudentSubject,
    Assignment, Submission, Feedback, AIReport
)

# ... (Restul functiilor ajutatoare raman la fel) ...
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


# ... (Rutele index, register, login, logout raman la fel) ...
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
        flash("Cont creat cu succes! Te poti loga.", "success")
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
        flash("Email sau parola incorecta.", "error")
        return redirect(url_for("main.login"))
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


# ---- Pagina principala (Home) ----
@bp.route("/home", methods=["GET", "POST"])
@login_required
def home():
    role = current_user.role

    # ... (Logica de upload pentru Profesor ramane la fel) ...
    if role == "Profesor":
        user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
        os.makedirs(user_folder, exist_ok=True)
        if request.method == "POST":
            if "file" not in request.files:
                flash("Nu s-a selectat niciun fisier.")
                return redirect(request.url)
            file = request.files["file"]
            title = request.form.get("title", "")
            if file.filename == "":
                flash("Nume de fisier invalid.")
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
                flash(f"Fisierul '{title or filename}' a fost incarcat cu succes!")
                return redirect(url_for("main.home"))
            else:
                flash("Tip de fisier nepermis.")
                return redirect(request.url)

    # --- Logica de AFISARE pe rol ---

    if role == "Profesor":
        user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id))
        files = get_files_from_folder(user_folder, current_user.id)

        subjects = Subject.query.all()
        subjects_data = []
        for s in subjects:
            subjects_data.append({
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'color': getattr(s, 'color', 'bg-blue-500')  # poti adauga camp color in model daca vrei
            })

        return render_template("test.html", user=current_user, files=files, subjects=subjects_data)

    elif role == "Elev":
        student_profile = Student.query.filter_by(user_id=current_user.id).first()
        assignments_data = []

        if student_profile:
            # --- LOGICA MODIFICATA ---
            # Preluam direct temele (submissions) asignate elevului
            my_submissions = Submission.query.filter_by(
                student_id=student_profile.id
            ).join(Assignment).order_by(Assignment.due_date.asc()).all()

            for sub in my_submissions:
                assignments_data.append({
                    "id": sub.assignment.id,  # ID-ul temei
                    "title": sub.assignment.title,
                    "due_date": sub.assignment.due_date.strftime("%Y-%m-%d") if sub.assignment.due_date else "N/A",
                    "status": sub.status  # "Nefacut", "Trimis" sau "Corectat"
                })

        return render_template("elev.html", user=current_user, assignments=assignments_data)


    elif role == "Parinte":
        # ... (Logica pentru Parinte ramane neschimbata) ...
        parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
        child_info_data = {}
        if parent_profile:
            child_student = None
            if parent_profile.students:
                child_student = parent_profile.students[0]
            if child_student:
                grades_list = []
                student_subjects = StudentSubject.query.filter_by(student_id=child_student.id).all()
                submissions = Submission.query.join(Assignment).join(Subject).filter(
                    Submission.student_id == child_student.id
                ).all()

                grades_by_subject = {}
                for sub in submissions:
                    subject_name = sub.assignment.subject.name
                    grade = sub.feedback.grade if sub.feedback else "N/A"
                    grades_by_subject.setdefault(subject_name, []).append({
                        "assignment_title": sub.assignment.title,
                        "grade": grade
                    })

                # Calculam media pe fiecare materie
                subject_averages = {}
                for subject, grades_list in grades_by_subject.items():
                    total = 0
                    count = 0
                    for g in grades_list:
                        try:
                            total += float(g['grade'])
                            count += 1
                        except (ValueError, TypeError):
                            continue  # ignoram grade non-numerice
                    if count > 0:
                        subject_averages[subject] = total / count
                    else:
                        subject_averages[subject] = 0

                # Calculam media generala
                if subject_averages:
                    general_avg = sum(subject_averages.values()) / len(subject_averages)
                else:
                    general_avg = 0
                general_avg = round(general_avg, 2)

                # Total materii
                total_subjects = len(grades_by_subject)

                # Total note
                total_grades = sum(len(grades) for grades in grades_by_subject.values())

                # Media pe fiecare materie
                subject_averages = {}
                for subject, grades_list in grades_by_subject.items():
                    total = 0
                    count = 0
                    for g in grades_list:
                        try:
                            total += float(g['grade'])
                            count += 1
                        except (ValueError, TypeError):
                            continue
                    if count > 0:
                        subject_averages[subject] = total / count
                    else:
                        subject_averages[subject] = 0

                # Cea mai mare medie
                if subject_averages:
                    max_subject = max(subject_averages, key=subject_averages.get)
                    max_avg = subject_averages[max_subject]
                else:
                    max_subject = None
                    max_avg = 0

                child_info_data = {
                    "name": child_student.user.name,
                    "grades_by_subject": grades_by_subject or {},
                    "general_avg": general_avg or 0,
                    "total_subjects": total_subjects or 0,
                    "total_grades": total_grades or 0,
                    "max_subject": max_subject or 0,
                    "max_avg": max_avg or 0,
                }
                return render_template("situatie.html", user=current_user, child=child_info_data)
            # Parent doesn't have a child
            copii_disponibili = Student.query.all()

            return render_template("preluareCopil.html", user=current_user, copii=copii_disponibili)
    else:
        logout_user()
        return redirect(url_for("main.login"))


@bp.route('/delete_subject/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'error': 'Subject not found'}), 404

    db.session.delete(subject)
    db.session.commit()

    return jsonify({'success': True})


@bp.route('/get_subjects')
def get_subjects():
    subjects = Subject.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'color': getattr(s, 'color', 'bg-blue-500')
    } for s in subjects])


@bp.route('/add_subject', methods=['POST'])
def add_subject():
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    new_subject = Subject(
        name=data['name'],
        description=data.get('description', ''),  # <- asta trebuie
        color=data.get('color', 'bg-blue-500')
    )

    db.session.add(new_subject)
    db.session.commit()

    return jsonify({
        'id': new_subject.id,
        'name': new_subject.name,
        'description': new_subject.description,
        'color': new_subject.color
    })


@bp.route("/asignare_copil", methods=["POST"])
@login_required
def asignare_copil():
    student_id = request.form.get('student_id')
    parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
    student = Student.query.get(student_id)

    if student and parent_profile:
        student.parent_id = parent_profile.id
        db.session.commit()
        flash(f"{student.user.name} a fost asignat parintele curent.", "success")
    else:
        flash("Eroare la asignarea copilului.", "danger")

    return redirect(url_for('main.pdashboard'))


@bp.route("/note_elev", methods=["GET", "POST"])
@login_required
def note_elev():
    role = current_user.role

    if role == "Elev":
        student_profile = Student.query.filter_by(user_id=current_user.id).first()
        child_info_data = {}

        if student_profile:
            # Preluam toate subiectele si notele
            submissions = Submission.query.join(Assignment).join(Subject).filter(
                Submission.student_id == student_profile.id
            ).all()

            grades_by_subject = {}
            for sub in submissions:
                subject_name = sub.assignment.subject.name
                grade = sub.feedback.grade if sub.feedback else "N/A"
                grades_by_subject.setdefault(subject_name, []).append({
                    "assignment_title": sub.assignment.title,
                    "grade": grade
                })

                # Calculam media pe fiecare materie
                subject_averages = {}
                for subject, grades_list in grades_by_subject.items():
                    total = 0
                    count = 0
                    for g in grades_list:
                        try:
                            total += float(g['grade'])
                            count += 1
                        except (ValueError, TypeError):
                            continue  # ignoram grade non-numerice
                    if count > 0:
                        subject_averages[subject] = total / count
                    else:
                        subject_averages[subject] = 0

                # Calculam media generala
                if subject_averages:
                    general_avg = sum(subject_averages.values()) / len(subject_averages)
                else:
                    general_avg = 0
                general_avg = round(general_avg, 2)

                # Total materii
                total_subjects = len(grades_by_subject)

                # Total note
                total_grades = sum(len(grades) for grades in grades_by_subject.values())

                # Media pe fiecare materie
                subject_averages = {}
                for subject, grades_list in grades_by_subject.items():
                    total = 0
                    count = 0
                    for g in grades_list:
                        try:
                            total += float(g['grade'])
                            count += 1
                        except (ValueError, TypeError):
                            continue
                    if count > 0:
                        subject_averages[subject] = total / count
                    else:
                        subject_averages[subject] = 0

                # Cea mai mare medie
                if subject_averages:
                    max_subject = max(subject_averages, key=subject_averages.get)
                    max_avg = subject_averages[max_subject]
                else:
                    max_subject = None
                    max_avg = 0

                child_info_data = {
                    "name": current_user.name,
                    "grades_by_subject": grades_by_subject or {},
                    "general_avg": general_avg or 0,
                    "total_subjects": total_subjects or 0,
                    "total_grades": total_grades or 0,
                    "max_subject": max_subject or 0,
                    "max_avg": max_avg or 0,
                }
            return render_template("note_elev.html", user=current_user, child=child_info_data)
    return "H4CK3R!!"


@bp.route("/absenta", methods=["GET", "POST"])
@login_required
def absenta():
    role = current_user.role

    if role == "Parinte":
        parent_profile = Parent.query.filter_by(user_id=current_user.id).first()

        if not parent_profile or not parent_profile.students:
            return render_template("absenta.html", user=current_user, child=None, absences_by_day={})

        # Luam primul copil al parintelui (presupunem 1 copil)
        child_student = parent_profile.students[0]
        child_info_data = {"name": child_student.user.name}

        # Luam toate absentele copilului + materia
        absences = (
            db.session.query(Absence)
            .join(Subject)
            .filter(Absence.student_id == child_student.id)
            .order_by(Absence.date.desc())
            .all()
        )

        # Grupam absentele dupa data
        absences_by_day = {}
        for a in absences:
            date_str = a.date.strftime("%d/%m/%Y")
            absences_by_day.setdefault(date_str, []).append(a.subject.name)

        return render_template(
            "absenta.html",
            user=current_user,
            child=child_info_data,
            absences_by_day=absences_by_day
        )

    return render_template("absenta.html", user=current_user, child=None, absences_by_day={})


# ... (Rutele link_child, dashboard, teme_profesor, orar raman la fel) ...
@bp.route("/link_child", methods=["GET", "POST"])
@login_required
def link_child():
    if current_user.role != "Parinte":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))
    parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
    if not parent_profile:
        flash("Profil de parinte negasit.", "error")
        return redirect(url_for("main.home"))
    if request.method == "POST":
        student_id = request.form.get("student_id")
        student_to_link = Student.query.get(student_id)
        if student_to_link:
            if student_to_link.parent_id is not None:
                flash("Acest elev are deja un parinte asociat.", "error")
            else:
                student_to_link.parent_id = parent_profile.id
                db.session.commit()
                flash(f"Elevul {student_to_link.user.name} a fost asociat contului tau!", "success")
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


@bp.route("/pdashboard")
@login_required
def pdashboard():
    parent_profile = Parent.query.filter_by(user_id=current_user.id).first()
    child_info_data = {}
    if parent_profile:
        child_student = None
        if parent_profile.students:
            child_student = parent_profile.students[0]
        if child_student:
            grades_list = []
            student_subjects = StudentSubject.query.filter_by(student_id=child_student.id).all()
            submissions = Submission.query.join(Assignment).join(Subject).filter(
                Submission.student_id == child_student.id
            ).all()

            grades_by_subject = {}
            for sub in submissions:
                subject_name = sub.assignment.subject.name
                grade = sub.feedback.grade if sub.feedback else "N/A"
                grades_by_subject.setdefault(subject_name, []).append({
                    "assignment_title": sub.assignment.title,
                    "grade": grade
                })

            # Calculam media pe fiecare materie
            subject_averages = {}
            for subject, grades_list in grades_by_subject.items():
                total = 0
                count = 0
                for g in grades_list:
                    try:
                        total += float(g['grade'])
                        count += 1
                    except (ValueError, TypeError):
                        continue  # ignoram grade non-numerice
                if count > 0:
                    subject_averages[subject] = total / count
                else:
                    subject_averages[subject] = 0

            # Calculam media generala
            if subject_averages:
                general_avg = sum(subject_averages.values()) / len(subject_averages)
            else:
                general_avg = 0
            general_avg = round(general_avg, 2)
            general_avg_percent = round((general_avg / 10) * 100, 1)

        # --- 4. Calculam absentele ---
        absences_count = 100 - Absence.query.filter_by(student_id=child_student.id).count()

        # --- 5. Penalizam procentajul: -1% pentru fiecare absenta ---
        adjusted_percent = general_avg_percent - absences_count
        if adjusted_percent < 0:
            adjusted_percent = 0  # nu mergem sub 0%

        child_info_data = {
            "child": child_student.user.name,
            "percentile": general_avg_percent or 0,
            "absences": absences_count,
        }

        return render_template("pdashboard.html", user=current_user, child_info=child_info_data)


@bp.route("/get_absences/<int:student_id>")
def get_absences(student_id):
    student = Student.query.get_or_404(student_id)
    absences = Absence.query.filter_by(student_id=student.id).join(Subject).all()
    absences_data = [
        {"subject_name": a.subject.name, "date": a.date.strftime("%d-%m-%Y")}
        for a in absences
    ]
    return {"absences": absences_data}


@bp.route("/add_absence", methods=["POST"])
def add_absence():
    data = request.get_json()

    student_id = data.get("student_id")
    subject_id = data.get("subject_id")
    professor_id = data.get("professor_id")
    date_str = data.get("date")  # aici luam data din frontend

    if not student_id or not subject_id or not professor_id or not date_str:
        return jsonify({"error": "Date incomplete"}), 400

    # convertim string-ul din formatul 'YYYY-MM-DD' intr-un obiect date
    try:
        absence_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Data invalida"}), 400

    # Cream obiectul Absence cu data corecta
    new_absence = Absence(
        student_id=student_id,
        subject_id=subject_id,
        date=absence_date
    )

    db.session.add(new_absence)
    db.session.commit()

    return jsonify({"message": "Absenta a fost adaugata cu succes!"})


@bp.route('/students')
def students_dashboard():
    students = Student.query.all()
    profesori = db.session.query(Professor, User).join(User).all()
    materii = Subject.query.all()

    return render_template('listaElevi.html', students=students, user=current_user, profesori=profesori,
                           materii=materii)


@bp.route("/test")
def test():
    return render_template("test.html", user=current_user)


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
                Submission.status != 'Nefacut'  # Numaram doar cele trimise
            ).count()
            total_students = Submission.query.filter_by(assignment_id=assign.id).count()  # Totalul celor asignati
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
        "08:00 - 08:50": ["Matematica", "Romana", "Biologie", "Istorie", "Engleza"],
        "09:00 - 09:50": ["Fizica", "Chimie", "Sport", "Romana", "Matematica"],
    }
    return render_template("orar.html", user=current_user, schedule=schedule_data)


# ===================================================================
# --- RUTA MODIFICATA: Creare Tema (Profesor) ---
# ===================================================================
@bp.route("/creare-tema", methods=["GET", "POST"])
@login_required
def creare_tema():
    if current_user.role != "Profesor":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))

    prof_profile = Professor.query.filter_by(user_id=current_user.id).first()

    # Preluam materiile
    subjects = Subject.query.all()
    # Preluam TOTI elevii
    students = Student.query.join(User).all()  # Join User ca sa avem acces la nume

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date_str = request.form.get("due_date")
        subject_id = request.form.get("subject_id")

        # --- MODIFICARE ---
        # Preluam lista de ID-uri de elevi
        student_ids = request.form.getlist("student_ids")  # .getlist() e cheia

        if not title or not description or not due_date_str or not subject_id:
            flash("Titlul, descrierea, data limita si materia sunt obligatorii.", "error")
            return redirect(url_for("main.creare_tema"))

        if not student_ids:
            flash("Trebuie sa selectezi cel putn un elev.", "error")
            return redirect(url_for("main.creare_tema"))

        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d')

            # 1. Cream Tema (Assignment)
            new_assignment = Assignment(
                teacher_id=prof_profile.id,
                subject_id=int(subject_id),
                title=title,
                description=description,
                due_date=due_date
            )

            db.session.add(new_assignment)
            # Facem un "pre-commit" ca sa obtinem ID-ul temei (new_assignment.id)
            db.session.flush()

            # 2. Cream "fisele" (Submissions) goale pentru fiecare elev
            for student_id in student_ids:
                new_submission = Submission(assignment_id=new_assignment.id,
                    student_id=int(student_id),
                    status="Nefacut"
                    # content este null implicit
                    # submitted_at este null implicit
                )
                db.session.add(new_submission)

            # 3. Salvam totul
            db.session.commit()

            flash(f"Tema creata si asignata la {len(student_ids)} elevi!", "success")
            return redirect(url_for("main.teme_profesor"))

        except Exception as e:
            db.session.rollback()
            flash(f"Eroare la crearea temei: {e}", "error")

    # GET: trimitem materiile SI elevii la template
    return render_template("creare_tema.html", user=current_user, subjects=subjects, students=students)


# ===================================================================
# --- RUTA MODIFICATA: Detaliu si Trimitere Tema (Elev) ---
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
    # Gasim "fisa" (Submission) specifica acestui elev pentru aceasta tema
    submission = Submission.query.filter_by(
        assignment_id=id_tema,
        student_id=student_profile.id
    ).first()

    # Daca nu existe o "fisa", inseamna ca tema nu i-a fost asignata
    if not submission:
        flash("Aceasta tema nu ti-a fost asignata.", "error")
        return redirect(url_for('main.home'))

    if request.method == "POST":
        # Elevul trimite tema

        # --- MODIFICARE ---
        # Verificam statusul "fisei"
        if submission.status != 'Nefacut':
            flash("Ai trimis deja o rezolvare pentru aceasta tema.", "warning")
            return redirect(url_for('main.detaliu_tema', id_tema=id_tema))

        content = request.form.get("content")
        if not content:
            flash("Rezolvarea nu poate fi goala.", "error")
            return redirect(url_for('main.detaliu_tema', id_tema=id_tema))

        # --- MODIFICARE ---
        # Actualizam "fisa" existenta, nu cream una noua
        submission.content = content
        submission.status = "Trimis"
        submission.submitted_at = datetime.utcnow()

        db.session.commit()

        flash("Tema a fost trimisa cu succes!", "success")
        return redirect(url_for('main.detaliu_tema', id_tema=id_tema))

    # Metoda GET: Afisam detaliile
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


# ... (Restul rutelor: detaliu_tema_profesor, corectare_tema, si toata zona de API / AI raman la fel) ...
@bp.route("/tema-profesor/<int:id_tema>")
@login_required
def detaliu_tema_profesor(id_tema):
    if current_user.role != "Profesor":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))

    assignment = Assignment.query.get_or_404(id_tema)

    # Obtine toate submissions pentru aceasta tema
    submissions = Submission.query.filter_by(assignment_id=id_tema).all()

    # ADAUGAT: Sortare - trimise mai intai, apoi dupa nume elev
    submissions_sorted = sorted(submissions, key=lambda s: (
        s.status == 'Nefacut',  # False (Trimis/Corectat) inainte de True (Nefacut)
        s.student.user.name if s.student and s.student.user else ""
    ))

    return render_template(
        "detaliu_tema_profesor.html",
        user=current_user,
        assignment=assignment,
        submissions=submissions_sorted  # Foloseste lista sortata
    )


@bp.route("/corectare/<int:id_submission>", methods=["GET", "POST"])
@login_required
def corectare_tema(id_submission):
    if current_user.role != "Profesor":
        flash("Acces nepermis.", "error")
        return redirect(url_for("main.home"))

    submission = Submission.query.get_or_404(id_submission)

    # VERIFICARE: Are submission raspuns?
    if not submission.content or submission.content.strip() == "":
        flash("Atentie: Elevul nu a furnizat un raspuns text pentru aceasta tema.", "warning")

    if request.method == "POST":
        grade = request.form.get("grade")
        feedback_text = request.form.get("feedback_text")

        if not grade or not feedback_text:
            flash("Nota si feedback-ul sunt obligatorii.", "error")
            return redirect(url_for('main.corectare_tema', id_submission=id_submission))

        try:
            grade = float(grade)
            if grade < 0 or grade > 10:
                flash("Nota trebuie sa fie intre 0 si 10.", "error")
                return redirect(url_for('main.corectare_tema', id_submission=id_submission))
        except ValueError:
            flash("Nota trebuie sa fie un numar valid.", "error")
            return redirect(url_for('main.corectare_tema', id_submission=id_submission))

        # Verifica daca exista deja feedback
        existing_feedback = Feedback.query.filter_by(submission_id=id_submission).first()

        try:
            if existing_feedback:
                print(f"[LOG] Actualizare feedback existent ID: {existing_feedback.id}")
                existing_feedback.grade = grade
                existing_feedback.feedback_text = feedback_text
                feedback_obj = existing_feedback
            else:
                print(f"[LOG] Creare feedback NOU pentru submission {id_submission}")
                new_feedback = Feedback(
                    submission_id=id_submission,
                    grade=grade,
                    feedback_text=feedback_text
                )
                db.session.add(new_feedback)
                db.session.flush()  # Obtine ID-ul inainte de commit
                feedback_obj = new_feedback
                print(f"[LOG] Feedback creat cu ID: {feedback_obj.id}")

            # Update status submission
            submission.status = "Corectat"
            db.session.commit()

            print(f"\n[LOG] Incep generare raport AI...")
            print(f"  - Feedback ID: {feedback_obj.id}")
            print(f"  - Submission ID: {feedback_obj.submission_id}")
            print(f"  - Student ID: {submission.student_id}")

            # Genereaza raport AI
            try:
                generate_ai_report_for_feedback(feedback_obj)
                flash("Feedback salvat si raport AI generat cu succes!", "success")
            except Exception as e:
                print(f"[ERROR] Eroare la generarea raportului AI: {e}")
                import traceback
                traceback.print_exc()
                flash("Feedback salvat, dar a esuat generarea raportului AI.", "warning")

            return redirect(url_for('main.detaliu_tema_profesor', id_tema=submission.assignment_id))

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Eroare la salvare: {e}")
            import traceback
            traceback.print_exc()
            flash(f"Eroare la salvarea feedback-ului: {e}", "error")

    # GET: afiseaza formular
    return render_template("corectare_tema.html", user=current_user, submission=submission)


OPENROUTER_API_KEY = "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"
LOG_FILENAME = "params_log.json"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", LOG_FILENAME)
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def call_model(messages):
    """Trimite request la OpenRouter API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openrouter/polaris-alpha",
        "messages": messages,
        "temperature": 0.7,  # Adaugat pentru consistenta
        "max_tokens": 2000  # Adaugat pentru raspunsuri mai detaliate
    }

    print(f"\n[LOG] REQUEST LA OPENROUTER:")
    print(f"  Model: {payload['model']}")
    print(f"  Messages count: {len(messages)}")
    print(f"  System prompt length: {len(messages[0]['content']) if messages else 0}")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content")

        if not content:
            print(f"[WARNING] Raspuns gol de la API!")
            print(f"Full response: {data}")

        return content

    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP Error: {e}")
        print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        return None
    except Exception as e:
        print(f"[ERROR] call_model error: {e}")
        import traceback
        traceback.print_exc()
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
    print("\n" + "=" * 70)
    print(f"[LOG] GENERARE RAPORT AI - Feedback ID: {feedback_obj.id}")
    print("=" * 70)

    # Obtine date
    submission = feedback_obj.submission
    student = submission.student
    assignment = submission.assignment

    # DEBUG: Afiseaza ce date avem
    print(f"\n[LOG] DATE PRELUATE DIN DB:")
    print(f"  - Student: {student.user.name} (ID: {student.id})")
    print(f"  - Assignment: {assignment.title}")
    print(f"  - Descriere tema: {assignment.description[:100]}...")
    print(f"  - Raspuns elev: {submission.content[:100] if submission.content else 'N/A'}...")
    print(f"  - Feedback profesor: {feedback_obj.feedback_text[:100]}...")
    print(f"  - Nota: {feedback_obj.grade}/10")

    # Obtine istoric feedback-uri
    lista_feedbackuri = []
    student_submissions = Submission.query.filter_by(student_id=student.id).all()

    for sub in student_submissions:
        if sub.feedback:
            lista_feedbackuri.append({
                "assignment": sub.assignment.title if sub.assignment else "N/A",
                "nota": sub.feedback.grade,
                "feedback": sub.feedback.feedback_text
            })

    print(f"\n[LOG] ISTORIC FEEDBACK ({len(lista_feedbackuri)} intrari):")
    for i, fb in enumerate(lista_feedbackuri, 1):
        print(f"  {i}. {fb['assignment']}: {fb['nota']}/10")

    # Construieste prompt EXPLICIT si STRUCTURAT
    system_prompt = """Esti un asistent AI educational pentru scoala primara.

IMPORTANT: Analizeaza DOAR datele pe care le primesti mai jos. NU inventa sau presupune informatii care nu sunt furnizate.

Genereaza un raport structurat in format JSON cu urmatoarele chei:
- "summary": Rezumat scurt (2-3 propozitii) despre performanta elevului la ACEASTA tema specifica
- "strengths": Lista cu 2-3 puncte forte concrete observate in raspunsul elevului
- "weaknesses": Lista cu 2-3 puncte slabe sau greseli specifice
- "suggestions": Lista cu 2-3 sugestii concrete pentru imbunatatire
- "parent_summary": Paragraf pentru parinte (limbaj simplu, fara termeni tehnici)

Raspunde DOAR cu JSON valid, fara text aditional."""

    user_prompt = f"""Analizeaza performanta elevului {student.user.name}:

**TEMA ACTUALA:**
Titlu: {assignment.title}
Cerinta: {assignment.description}

**RASPUNSUL ELEVULUI:**
{submission.content if submission.content else "Elevul nu a furnizat un raspuns text (posibil fisier incarcat)."}

**FEEDBACK PROFESOR (CEL MAI RECENT):**
Nota: {feedback_obj.grade}/10
Comentarii: {feedback_obj.feedback_text}

**CONTEXT ISTORIC (performante anterioare):**
{json.dumps(lista_feedbackuri, ensure_ascii=False, indent=2) if lista_feedbackuri else "Prima tema evaluata"}

Genereaza raportul JSON bazat STRICT pe datele de mai sus."""

    print(f"\n[LOG] PROMPT TRIMIS LA AI:")
    print(f"System: {system_prompt[:150]}...")
    print(f"User: {user_prompt[:300]}...")

    prompt_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Apel AI
    print(f"\n[LOG] Trimit request la OpenRouter...")
    ai_response_str = call_model(prompt_messages)

    if not ai_response_str:
        print("[ERROR] EROARE: Raspuns gol de la API!")
        return

    print(f"\n[LOG] RASPUNS PRIMIT DE LA AI:")
    #print(f"{ai_response_str[:500]}...")

    try:
        # Curata raspuns
        if ai_response_str.startswith("```json"):
            ai_response_str = ai_response_str[7:]
        if ai_response_str.startswith("```"):
            ai_response_str = ai_response_str[3:]
        if ai_response_str.endswith("```"):
            ai_response_str = ai_response_str[:-3]

        ai_response_str = ai_response_str.strip()

        # Parse JSON
        ai_data = json.loads(ai_response_str)

        print(f"\n[LOG] JSON PARSAT CU SUCCES")
        print(f"  - Summary: {ai_data.get('summary', 'N/A')[:100]}...")
        print(f"  - Strengths: {len(ai_data.get('strengths', []))} puncte")
        print(f"  - Weaknesses: {len(ai_data.get('weaknesses', []))} puncte")

        # Verifica daca exista deja raport
        ai_report = AIReport.query.filter_by(feedback_id=feedback_obj.id).first()

        if not ai_report:
            ai_report = AIReport(
                feedback_id=feedback_obj.id,
                student_id=student.id
            )
            db.session.add(ai_report)
            print(f"\n[LOG] Creat raport NOU")
        else:
            print(f"\n[LOG] Actualizat raport EXISTENT (ID: {ai_report.id})")

        # Salveaza datele
        ai_report.report_content = json.dumps(ai_data, ensure_ascii=False)
        ai_report.summary = ai_data.get('summary', 'N/A')

        # Converteste liste in JSON strings
        ai_report.strengths = json.dumps(ai_data.get('strengths', []), ensure_ascii=False)
        ai_report.weaknesses = json.dumps(ai_data.get('weaknesses', []), ensure_ascii=False)
        ai_report.suggestions = json.dumps(ai_data.get('suggestions', []), ensure_ascii=False)
        ai_report.parent_summary = ai_data.get('parent_summary', 'N/A')

        db.session.commit()

        print(f"\n[LOG] RAPORT SALVAT CU SUCCES in DB!")
        print(f"  - AIReport ID: {ai_report.id}")
        print(f"  - Feedback ID: {ai_report.feedback_id}")
        print(f"  - Student ID: {ai_report.student_id}")
        print("=" * 70 + "\n")

    except json.JSONDecodeError as e:
        print(f"\n[ERROR] EROARE PARSARE JSON: {e}")
        print(f"Raspuns problematic: {ai_response_str[:500]}")

    except Exception as e:
        db.session.rollback()
        print(f"\n[ERROR] EROARE la salvare in DB: {e}")
        import traceback
        traceback.print_exc()


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

    # 1. PRELUAM ID-UL FEEDBACK-ULUI DORIT DIN CERERE
    # Frontend-ul va trebui sa trimita acest ID
    feedback_id = data.get("feedback_id", None)

    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        return jsonify({"response": "Eroare: Nu am gasit profilul tau de student."})

    # 2. CAUTAM RAPORTUL SPECIFIC (SAU CEL MAI RECENT DACA NU AVEM ID)
    target_report = None
    if feedback_id:
        # Cautam raportul AI asociat cu feedback_id-ul specificat
        target_report = AIReport.query.filter_by(
            student_id=student.id,
            feedback_id=feedback_id
        ).first()
    else:
        # Comportamentul vechi: luam cel mai recent raport daca nu e specificat unul
        target_report = AIReport.query.filter_by(student_id=student.id).order_by(AIReport.id.desc()).first()

    context_str = "Context intern:\n"

    # 3. CONSTRUIM CONTEXTUL PE BAZA RAPORTULUI GASIT ('target_report')
    if target_report:
        feedback = target_report.feedback
        assignment = feedback.submission.assignment
        context_str += f"Materie={assignment.subject.name}\n"
        context_str += f"Cerinta={assignment.description}\n"
        context_str += f"Feedback_profesor={feedback.feedback_text}\n"
        context_str += f"Puncte_slabe_identificate={target_report.weaknesses}\n"
        context_str += f"Sugestii_AI={target_report.suggestions}\n"
    else:
        if feedback_id:
            # Nu am gasit un raport pentru acel ID
            context_str += f"Nu am gasit un raport AI pentru feedback-ul specificat (ID: {feedback_id})."
        else:
            # Nu exista niciun raport generat pentru acest elev
            context_str += "Niciun raport AI generat inca. Raspunde la intrebarea elevului cat de bine poti."

    responder_prompt = [
        {
            "role": "system",
            "content": (
                "Esti un chatbot tutore, prietenos si incurajator, pentru elevi. "
                "Scopul tau este sa ajuti elevul sa inteleaga feedback-ul primit si sa isi imbunatateasca munca. "
                "Foloseste contextul intern (punctele slabe si sugestiile) pentru a oferi explicatii suplimentare. "
                "Nu preda materia de la zero, ci ghideaza elevul pe baza feedback-ului."
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
        final_answer = "Nu am reusit sa procesez raspunsul. Te rog, mai incearca."

    # Returnam si ID-ul folosit, pentru ca frontend-ul sa stie contextul
    return jsonify({
        "response": final_answer,
        "context_feedback_id": target_report.feedback_id if target_report else None
    })