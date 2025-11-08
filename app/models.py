from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func
from datetime import datetime  # Am adăugat datetime


# --- Modelul User (așa cum l-ai oferit, cu relațiile adăugate) ---
# ... (Nicio modificare aici) ...
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Am mărit la 256 pentru siguranță
    role = db.Column(db.String(20), nullable=False)  # 'student', 'professor', 'parent'

    # Relații unu-la-unu către rolurile specifice
    student = db.relationship('Student', back_populates='user', uselist=False)
    professor = db.relationship('Professor', back_populates='user', uselist=False)
    parent = db.relationship('Parent', back_populates='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)


# --- Rolurile Utilizatorilor ---
# ... (Nicio modificare la Student, Professor, Parent) ...
class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=True)  # Poate fi nullable

    # Relații
    user = db.relationship('User', back_populates='student')
    parent = db.relationship('Parent', back_populates='students')

    # Relații unu-la-mulți (Un student are mai multe...)
    student_subjects = db.relationship('StudentSubject', back_populates='student')
    submissions = db.relationship('Submission', back_populates='student')
    chat_sessions = db.relationship('ChatSession', back_populates='student')
    ai_reports = db.relationship('AIReport', back_populates='student')


class Professor(db.Model):
    __tablename__ = 'professor'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    # Relații
    user = db.relationship('User', back_populates='professor')
    assignments = db.relationship('Assignment', back_populates='teacher')


class Parent(db.Model):
    __tablename__ = 'parent'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

    # Relații
    user = db.relationship('User', back_populates='parent')
    students = db.relationship('Student', back_populates='parent')  # Un părinte poate avea mai mulți studenți


# --- Structura Academică ---
# ... (Nicio modificare la Subject, StudentSubject) ...
class Subject(db.Model):  # Fosta tabelă "Materie" (top-dreapta)
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    # Câmpul 'numw' din diagramă părea o greșeală, am păstrat 'name'

    # Relații
    assignments = db.relationship('Assignment', back_populates='subject')
    student_subjects = db.relationship('StudentSubject', back_populates='subject')


class StudentSubject(db.Model):  # Fosta tabelă "Materie" (centru-stânga)
    __tablename__ = 'student_subject'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)  # 'id_materie FK'
    performance_history = db.Column(db.Text, nullable=True)

    # Relații
    student = db.relationship('Student', back_populates='student_subjects')
    subject = db.relationship('Subject', back_populates='student_subjects')


class Assignment(db.Model):
    # ... (Nicio modificare la Assignment) ...
    __tablename__ = 'assignment'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('professor.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)  # 'id_materie FK'
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # --- CÂMPURI NOI ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)  # Data limită

    # Relații
    teacher = db.relationship('Professor', back_populates='assignments')
    subject = db.relationship('Subject', back_populates='assignments')
    submissions = db.relationship('Submission', back_populates='assignment')


class Submission(db.Model):
    __tablename__ = 'submission'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

    # --- MODIFICARE ---
    content = db.Column(db.Text, nullable=True)  # Rezolvarea elevului (poate fi goală inițial)

    # --- MODIFICARE ---
    status = db.Column(db.String(50), nullable=False, default='Nefăcut')  # ex: Nefăcut, Trimis, Corectat

    # --- MODIFICARE ---
    submitted_at = db.Column(db.DateTime, nullable=True)  # Se setează doar la trimitere

    # Relații
    assignment = db.relationship('Assignment', back_populates='submissions')
    student = db.relationship('Student', back_populates='submissions')
    feedback = db.relationship('Feedback', back_populates='submission', uselist=False,
                               cascade="all, delete-orphan")  # Relație unu-la-unu


class Feedback(db.Model):
    # ... (Nicio modificare la Feedback) ...
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), unique=True, nullable=False)

    # --- CÂMP MODIFICAT ---
    grade = db.Column(db.String(10), nullable=True)  # Nota (ex: 10, 7.5, "A+")

    feedback_text = db.Column(db.Text, nullable=True)  # Feedback-ul profesorului

    # --- CÂMP NOU ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relații
    submission = db.relationship('Submission', back_populates='feedback')
    ai_reports = db.relationship('AIReport', back_populates='feedback', cascade="all, delete-orphan")


# --- Secțiunea AI și Chat ---
# ... (Nicio modificare la AIReport, ChatSession, ChatMessage) ...
class AIReport(db.Model):
    __tablename__ = 'ai_report'
    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

    report_content = db.Column(db.Text, nullable=True)  # Răspunsul JSON brut de la AI
    summary = db.Column(db.Text, nullable=True)
    strengths = db.Column(db.Text, nullable=True)
    weaknesses = db.Column(db.Text, nullable=True)
    suggestions = db.Column(db.Text, nullable=True)
    parent_summary = db.Column(db.Text, nullable=True)

    # Relații
    feedback = db.relationship('Feedback', back_populates='ai_reports')
    student = db.relationship('Student', back_populates='ai_reports')
    chat_sessions = db.relationship('ChatSession', back_populates='report')


class ChatSession(db.Model):
    __tablename__ = 'chat_session'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('ai_report.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

    # Relații
    report = db.relationship('AIReport', back_populates='chat_sessions')
    student = db.relationship('Student', back_populates='chat_sessions')
    messages = db.relationship('ChatMessage', back_populates='session',
                               cascade='all, delete-orphan')  # Șterge mesajele odată cu sesiunea


class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    sender_role = db.Column(db.String(20), nullable=False)  # 'student' sau 'ai'
    content = db.Column(db.Text, nullable=False)
    # created_at = db.Column(db.DateTime(timezone=True), server_default=func.now()) # Exemplu de timestamp

    # Relații
    session = db.relationship('ChatSession', back_populates='messages')