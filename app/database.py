import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Calea către fișierul bazei de date
DB_PATH = "education_platform.db"


def init_database():
    """
    Creează baza de date și toate tabelele.
    Rulează această funcție o singură dată la început!
    """
    # Citește schema SQL
    schema_path = Path("schema.sql")

    # Conectare la baza de date (o creează dacă nu există)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Dacă ai schema într-un fișier separat:
    # with open(schema_path, 'r', encoding='utf-8') as f:
    #     schema = f.read()
    #     cursor.executescript(schema)

    # SAU poți pune direct schema aici:
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT CHECK(role IN ('teacher', 'student', 'parent')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        parent_id INTEGER,
        grade_level TEXT,
        interests TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (parent_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT CHECK(status IN ('submitted', 'graded')) DEFAULT 'submitted',
        FOREIGN KEY (assignment_id) REFERENCES assignments(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS teacher_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER UNIQUE NOT NULL,
        grade REAL,
        feedback_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (submission_id) REFERENCES submissions(id)
    );

    CREATE TABLE IF NOT EXISTS ai_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        report_content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (submission_id) REFERENCES submissions(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        report_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (report_id) REFERENCES ai_reports(id)
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role TEXT CHECK(role IN ('student', 'ai')) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
    );

    CREATE TABLE IF NOT EXISTS parent_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        parent_id INTEGER NOT NULL,
        report_content TEXT NOT NULL,
        period_start DATE,
        period_end DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (parent_id) REFERENCES users(id)
    );

    CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id);
    CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
    CREATE INDEX IF NOT EXISTS idx_ai_reports_student ON ai_reports(student_id);
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_student ON chat_sessions(student_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
    """

    cursor.executescript(schema)
    conn.commit()
    conn.close()

    print(f"✅ Baza de date creată cu succes: {DB_PATH}")


def get_connection():
    """Obține o conexiune la baza de date"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Pentru a accesa rezultatele ca dicționare
    return conn


# ========== FUNCȚII PENTRU USERS ==========

def create_user(email, password_hash, name, role):
    """Creează un utilizator nou"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (email, password_hash, name, role)
        VALUES (?, ?, ?, ?)
    """, (email, password_hash, name, role))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return user_id


def get_user_by_email(email):
    """Găsește un user după email"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    conn.close()
    return dict(user) if user else None


# ========== FUNCȚII PENTRU SUBMISSIONS ==========

def create_submission(assignment_id, student_id, content):
    """Creează o submission nouă"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO submissions (assignment_id, student_id, content)
        VALUES (?, ?, ?)
    """, (assignment_id, student_id, content))

    submission_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return submission_id


def get_submission(submission_id):
    """Obține o submission după ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    submission = cursor.fetchone()

    conn.close()
    return dict(submission) if submission else None


# ========== FUNCȚII PENTRU TEACHER FEEDBACK ==========

def create_teacher_feedback(submission_id, grade, feedback_text):
    """Creează feedback de la profesor"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO teacher_feedback (submission_id, grade, feedback_text)
        VALUES (?, ?, ?)
    """, (submission_id, grade, feedback_text))

    feedback_id = cursor.lastrowid

    # Actualizează status-ul submission-ului
    cursor.execute("""
        UPDATE submissions SET status = 'graded' WHERE id = ?
    """, (submission_id,))

    conn.commit()
    conn.close()

    return feedback_id


def get_teacher_feedback(submission_id):
    """Obține feedback-ul profesorului pentru o submission"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM teacher_feedback WHERE submission_id = ?
    """, (submission_id,))

    feedback = cursor.fetchone()
    conn.close()

    return dict(feedback) if feedback else None


# ========== FUNCȚII PENTRU AI REPORTS ==========

def create_ai_report(submission_id, student_id, strengths, weaknesses, suggestions):
    """Creează un raport AI"""
    conn = get_connection()
    cursor = conn.cursor()

    # Convertim la JSON
    report_content = json.dumps({
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions
    }, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO ai_reports (submission_id, student_id, report_content)
        VALUES (?, ?, ?)
    """, (submission_id, student_id, report_content))

    report_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return report_id


def get_ai_report(report_id):
    """Obține un raport AI"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM ai_reports WHERE id = ?", (report_id,))
    report = cursor.fetchone()

    conn.close()

    if report:
        report_dict = dict(report)
        # Parse JSON content
        report_dict['report_content'] = json.loads(report_dict['report_content'])
        return report_dict

    return None


def get_student_reports(student_id):
    """Obține toate rapoartele unui elev"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM ai_reports WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,))

    reports = cursor.fetchall()
    conn.close()

    result = []
    for report in reports:
        report_dict = dict(report)
        report_dict['report_content'] = json.loads(report_dict['report_content'])
        result.append(report_dict)

    return result


# ========== FUNCȚII PENTRU CHAT ==========

def create_chat_session(student_id, report_id):
    """Creează o sesiune de chat nouă"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_sessions (student_id, report_id)
        VALUES (?, ?)
    """, (student_id, report_id))

    session_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return session_id


def add_chat_message(session_id, role, content):
    """Adaugă un mesaj într-o sesiune de chat"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (?, ?, ?)
    """, (session_id, role, content))

    message_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return message_id


def get_chat_messages(session_id):
    """Obține toate mesajele dintr-o sesiune"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM chat_messages 
        WHERE session_id = ?
        ORDER BY created_at ASC
    """, (session_id,))

    messages = cursor.fetchall()
    conn.close()

    return [dict(msg) for msg in messages]


# ========== FUNCȚIE PENTRU DATE DE TEST ==========

def insert_test_data():
    """Inserează date de test pentru dezvoltare"""
    # Creează un profesor
    teacher_id = create_user(
        email="profesor@test.ro",
        password_hash="hashed_password_123",
        name="Prof. Ion Popescu",
        role="teacher"
    )

    # Creează un elev
    student_id = create_user(
        email="elev@test.ro",
        password_hash="hashed_password_456",
        name="Maria Ionescu",
        role="student"
    )

    # Creează un părinte
    parent_id = create_user(
        email="parinte@test.ro",
        password_hash="hashed_password_789",
        name="Ana Ionescu",
        role="parent"
    )

    print(f"✅ Date de test create:")
    print(f"  - Profesor ID: {teacher_id}")
    print(f"  - Elev ID: {student_id}")
    print(f"  - Părinte ID: {parent_id}")

    return teacher_id, student_id, parent_id


# ========== RULARE ==========

if __name__ == "__main__":
    # Creează baza de date
    init_database()

    # Inserează date de test (opțional)
    insert_test_data()