from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime

# ==========================================
# SMART QUIZ APPLICATION CONFIGURATION
# ==========================================

app = Flask(__name__)
app.secret_key = "smart_quiz_secret_key_2026"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "smartquiz.db")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_db():
    conn = get_db_connection()

    # USERS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # SUBJECTS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📚'
        )
    """)

    # QUESTIONS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Medium',
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    """)

    # QUIZ RESULTS TABLE
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            percentage REAL DEFAULT 0,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    """)

    # INSERT DEFAULT SUBJECTS
    subjects = [
        ("Python Programming", "Test your Python programming knowledge", "🐍"),
        ("Data Structures", "Arrays, stacks, queues and algorithms", "🧠"),
        ("Artificial Intelligence", "Learn concepts of Artificial Intelligence", "🤖"),
        ("Database Management", "SQL and database concepts", "🗄️"),
        ("Computer Networks", "Networking fundamentals and protocols", "🌐"),
        ("General Knowledge", "Test your general knowledge", "🌍")
    ]

    for subject in subjects:
        conn.execute("""
            INSERT OR IGNORE INTO subjects (name, description, icon)
            VALUES (?, ?, ?)
        """, subject)

    conn.commit()
    conn.close()


# ==========================================
# LOGIN REQUIRED DECORATOR
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# ADMIN REQUIRED DECORATOR
# ==========================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Admin access required!", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function
# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def index():
    conn = get_db_connection()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()

    total_questions = conn.execute(
        "SELECT COUNT(*) FROM questions"
    ).fetchone()[0]

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'student'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        subjects=subjects,
        total_questions=total_questions,
        total_users=total_users
    )


# ==========================================
# USER REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields!", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters!", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()

        existing_user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered! Please login.", "warning")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (name, email, hashed_password, "student"))

        conn.commit()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================================
# USER LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            flash(f"Welcome back, {user['name']}!", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        flash("Invalid email or password!", "danger")

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully!", "success")
    return redirect(url_for("index"))


# ==========================================
# USER DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db_connection()

    subjects = conn.execute("""
        SELECT s.*,
               COUNT(q.id) AS question_count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id
        ORDER BY s.name
    """).fetchall()

    recent_results = conn.execute("""
        SELECT r.*, s.name AS subject_name, s.icon
        FROM results r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.user_id = ?
        ORDER BY r.completed_at DESC
        LIMIT 5
    """, (session["user_id"],)).fetchall()

    stats = conn.execute("""
        SELECT
            COUNT(*) AS quizzes_taken,
            COALESCE(MAX(percentage), 0) AS best_score,
            COALESCE(AVG(percentage), 0) AS average_score
        FROM results
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        subjects=subjects,
        recent_results=recent_results,
        stats=stats
    )
# ==========================================
# QUIZ PAGE
# ==========================================

@app.route("/quiz/<int:subject_id>")
@login_required
def quiz(subject_id):

    conn = get_db_connection()

    subject = conn.execute(
        "SELECT * FROM subjects WHERE id = ?",
        (subject_id,)
    ).fetchone()

    if not subject:
        conn.close()
        flash("Subject not found!", "danger")
        return redirect(url_for("dashboard"))

    questions = conn.execute("""
        SELECT * FROM questions
        WHERE subject_id = ?
        ORDER BY RANDOM()
        LIMIT 10
    """, (subject_id,)).fetchall()

    conn.close()

    if not questions:
        flash(
            "No questions available for this subject yet!",
            "warning"
        )
        return redirect(url_for("dashboard"))

    return render_template(
        "quiz.html",
        subject=subject,
        questions=questions
    )


# ==========================================
# SUBMIT QUIZ
# ==========================================

@app.route("/submit_quiz/<int:subject_id>", methods=["POST"])
@login_required
def submit_quiz(subject_id):

    conn = get_db_connection()

    subject = conn.execute(
        "SELECT * FROM subjects WHERE id = ?",
        (subject_id,)
    ).fetchone()

    if not subject:
        conn.close()
        flash("Subject not found!", "danger")
        return redirect(url_for("dashboard"))

    questions = conn.execute("""
        SELECT * FROM questions
        WHERE subject_id = ?
    """, (subject_id,)).fetchall()

    score = 0
    total_questions = len(questions)

    # Check answers
    for question in questions:

        selected_answer = request.form.get(
            f"question_{question['id']}"
        )

        if selected_answer == question["correct_answer"]:
            score += 1

    percentage = 0

    if total_questions > 0:
        percentage = round(
            (score / total_questions) * 100,
            2
        )

    # Save result
    cursor = conn.execute("""
        INSERT INTO results
        (user_id, subject_id, score, total_questions, percentage)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        subject_id,
        score,
        total_questions,
        percentage
    ))

    result_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return redirect(
        url_for("result", result_id=result_id)
    )


# ==========================================
# RESULT PAGE
# ==========================================

@app.route("/result/<int:result_id>")
@login_required
def result(result_id):

    conn = get_db_connection()

    quiz_result = conn.execute("""
        SELECT r.*,
               s.name AS subject_name,
               s.icon
        FROM results r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.id = ? AND r.user_id = ?
    """, (
        result_id,
        session["user_id"]
    )).fetchone()

    conn.close()

    if not quiz_result:
        flash("Result not found!", "danger")
        return redirect(url_for("dashboard"))

    return render_template(
        "result.html",
        result=quiz_result
    )


# ==========================================
# QUIZ HISTORY
# ==========================================

@app.route("/history")
@login_required
def history():

    conn = get_db_connection()

    results = conn.execute("""
        SELECT r.*,
               s.name AS subject_name,
               s.icon
        FROM results r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.user_id = ?
        ORDER BY r.completed_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "history.html",
        results=results
    )


# ==========================================
# USER PROFILE
# ==========================================

@app.route("/profile")
@login_required
def profile():

    conn = get_db_connection()

    user = conn.execute("""
        SELECT id, name, email, role, created_at
        FROM users
        WHERE id = ?
    """, (session["user_id"],)).fetchone()

    stats = conn.execute("""
        SELECT
            COUNT(*) AS total_quizzes,
            COALESCE(MAX(percentage), 0) AS highest_score,
            COALESCE(AVG(percentage), 0) AS average_score
        FROM results
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        stats=stats
    )
# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = get_db_connection()

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'student'"
    ).fetchone()[0]

    total_subjects = conn.execute(
        "SELECT COUNT(*) FROM subjects"
    ).fetchone()[0]

    total_questions = conn.execute(
        "SELECT COUNT(*) FROM questions"
    ).fetchone()[0]

    total_quizzes = conn.execute(
        "SELECT COUNT(*) FROM results"
    ).fetchone()[0]

    subjects = conn.execute("""
        SELECT s.*, COUNT(q.id) AS question_count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id
        ORDER BY s.name
    """).fetchall()

    recent_users = conn.execute("""
        SELECT id, name, email, created_at
        FROM users
        WHERE role = 'student'
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_subjects=total_subjects,
        total_questions=total_questions,
        total_quizzes=total_quizzes,
        subjects=subjects,
        recent_users=recent_users
    )


# ==========================================
# ADMIN - QUESTIONS PAGE
# ==========================================

@app.route("/admin/questions")
@admin_required
def admin_questions():

    conn = get_db_connection()

    questions = conn.execute("""
        SELECT q.*, s.name AS subject_name
        FROM questions q
        JOIN subjects s ON q.subject_id = s.id
        ORDER BY q.id DESC
    """).fetchall()

    subjects = conn.execute(
        "SELECT * FROM subjects ORDER BY name"
    ).fetchall()

    conn.close()

    return render_template(
        "admin_questions.html",
        questions=questions,
        subjects=subjects
    )


# ==========================================
# ADMIN - ADD QUESTION
# ==========================================

@app.route("/admin/add_question", methods=["POST"])
@admin_required
def add_question():

    subject_id = request.form.get("subject_id")
    question = request.form.get("question", "").strip()
    option_a = request.form.get("option_a", "").strip()
    option_b = request.form.get("option_b", "").strip()
    option_c = request.form.get("option_c", "").strip()
    option_d = request.form.get("option_d", "").strip()
    correct_answer = request.form.get("correct_answer")
    difficulty = request.form.get("difficulty", "Medium")

    if not all([
        subject_id,
        question,
        option_a,
        option_b,
        option_c,
        option_d,
        correct_answer
    ]):
        flash("Please fill all question fields!", "danger")
        return redirect(url_for("admin_questions"))

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO questions (
            subject_id,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            difficulty
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        subject_id,
        question,
        option_a,
        option_b,
        option_c,
        option_d,
        correct_answer,
        difficulty
    ))

    conn.commit()
    conn.close()

    flash("Question added successfully!", "success")
    return redirect(url_for("admin_questions"))


# ==========================================
# ADMIN - DELETE QUESTION
# ==========================================

@app.route("/admin/delete_question/<int:question_id>")
@admin_required
def delete_question(question_id):

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM questions WHERE id = ?",
        (question_id,)
    )

    conn.commit()
    conn.close()

    flash("Question deleted successfully!", "success")

    return redirect(url_for("admin_questions"))


# ==========================================
# ADMIN - ADD SUBJECT
# ==========================================

@app.route("/admin/add_subject", methods=["POST"])
@admin_required
def add_subject():

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    icon = request.form.get("icon", "📚").strip()

    if not name:
        flash("Subject name is required!", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()

    try:
        conn.execute("""
            INSERT INTO subjects (name, description, icon)
            VALUES (?, ?, ?)
        """, (name, description, icon))

        conn.commit()
        flash("Subject added successfully!", "success")

    except sqlite3.IntegrityError:
        flash("This subject already exists!", "warning")

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))
# ==========================================
# INSERT SAMPLE QUESTIONS
# ==========================================

def insert_sample_questions():

    conn = get_db_connection()

    question_count = conn.execute(
        "SELECT COUNT(*) FROM questions"
    ).fetchone()[0]

    # Don't insert again if questions already exist
    if question_count > 0:
        conn.close()
        return

    subjects = conn.execute(
        "SELECT * FROM subjects"
    ).fetchall()

    subject_map = {
        subject["name"]: subject["id"]
        for subject in subjects
    }

    sample_questions = [

        # PYTHON
        (
            subject_map.get("Python Programming"),
            "Which keyword is used to define a function in Python?",
            "function",
            "def",
            "fun",
            "define",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Python Programming"),
            "Which data type is immutable in Python?",
            "List",
            "Dictionary",
            "Set",
            "Tuple",
            "D",
            "Medium"
        ),
        (
            subject_map.get("Python Programming"),
            "What is the output type of range() in Python 3?",
            "List",
            "Tuple",
            "Range object",
            "Integer",
            "C",
            "Medium"
        ),
        (
            subject_map.get("Python Programming"),
            "Which symbol is used for comments in Python?",
            "//",
            "#",
            "/*",
            "--",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Python Programming"),
            "Which function is used to get user input?",
            "get()",
            "input()",
            "scan()",
            "read()",
            "B",
            "Easy"
        ),

        # DATA STRUCTURES
        (
            subject_map.get("Data Structures"),
            "Which data structure follows FIFO?",
            "Stack",
            "Queue",
            "Tree",
            "Graph",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Data Structures"),
            "Which data structure follows LIFO?",
            "Queue",
            "Array",
            "Stack",
            "Linked List",
            "C",
            "Easy"
        ),
        (
            subject_map.get("Data Structures"),
            "What is the time complexity of binary search?",
            "O(n)",
            "O(log n)",
            "O(n²)",
            "O(1)",
            "B",
            "Medium"
        ),
        (
            subject_map.get("Data Structures"),
            "Which structure uses nodes and pointers?",
            "Array",
            "Linked List",
            "Queue",
            "Stack",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Data Structures"),
            "Which traversal visits Root, Left, Right?",
            "Inorder",
            "Postorder",
            "Preorder",
            "Level order",
            "C",
            "Medium"
        ),

        # AI
        (
            subject_map.get("Artificial Intelligence"),
            "What does AI stand for?",
            "Automatic Intelligence",
            "Artificial Intelligence",
            "Advanced Internet",
            "Artificial Integration",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Artificial Intelligence"),
            "Which is a branch of AI?",
            "Machine Learning",
            "HTML",
            "CSS",
            "Networking Cable",
            "A",
            "Easy"
        ),
        (
            subject_map.get("Artificial Intelligence"),
            "Which learning uses labeled data?",
            "Unsupervised Learning",
            "Supervised Learning",
            "Reinforcement only",
            "Random Learning",
            "B",
            "Medium"
        ),
        (
            subject_map.get("Artificial Intelligence"),
            "Neural networks are inspired by?",
            "Human Brain",
            "Computer Keyboard",
            "Database",
            "Internet Cable",
            "A",
            "Easy"
        ),
        (
            subject_map.get("Artificial Intelligence"),
            "Which is used for finding patterns in unlabeled data?",
            "Supervised Learning",
            "Unsupervised Learning",
            "Compilation",
            "Debugging",
            "B",
            "Medium"
        ),

        # DBMS
        (
            subject_map.get("Database Management"),
            "What does DBMS stand for?",
            "Database Management System",
            "Data Backup Management System",
            "Digital Base Management System",
            "Database Machine System",
            "A",
            "Easy"
        ),
        (
            subject_map.get("Database Management"),
            "Which language is used to query databases?",
            "HTML",
            "Python",
            "SQL",
            "CSS",
            "C",
            "Easy"
        ),
        (
            subject_map.get("Database Management"),
            "Which key uniquely identifies a record?",
            "Foreign Key",
            "Primary Key",
            "Duplicate Key",
            "Secondary Key",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Database Management"),
            "Which SQL command retrieves data?",
            "GET",
            "SELECT",
            "FETCHALL",
            "SHOW",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Database Management"),
            "Which SQL command removes a table?",
            "REMOVE",
            "DELETE",
            "DROP",
            "CLEAR",
            "C",
            "Medium"
        ),

        # NETWORKS
        (
            subject_map.get("Computer Networks"),
            "What does IP stand for?",
            "Internet Protocol",
            "Internal Program",
            "Internet Process",
            "Input Protocol",
            "A",
            "Easy"
        ),
        (
            subject_map.get("Computer Networks"),
            "Which device connects different networks?",
            "Switch",
            "Router",
            "Hub",
            "Repeater",
            "B",
            "Easy"
        ),
        (
            subject_map.get("Computer Networks"),
            "Which protocol is used for secure web browsing?",
            "HTTP",
            "FTP",
            "HTTPS",
            "SMTP",
            "C",
            "Easy"
        ),
        (
            subject_map.get("Computer Networks"),
            "How many layers are in the OSI model?",
            "5",
            "6",
            "7",
            "8",
            "C",
            "Medium"
        ),
        (
            subject_map.get("Computer Networks"),
            "Which protocol assigns IP addresses automatically?",
            "DNS",
            "DHCP",
            "HTTP",
            "FTP",
            "B",
            "Medium"
        ),

        # GENERAL KNOWLEDGE
        (
            subject_map.get("General Knowledge"),
            "What is the capital of India?",
            "Mumbai",
            "Chennai",
            "New Delhi",
            "Kolkata",
            "C",
            "Easy"
        ),
        (
            subject_map.get("General Knowledge"),
            "Which planet is known as the Red Planet?",
            "Earth",
            "Mars",
            "Venus",
            "Jupiter",
            "B",
            "Easy"
        ),
        (
            subject_map.get("General Knowledge"),
            "How many continents are there?",
            "5",
            "6",
            "7",
            "8",
            "C",
            "Easy"
        ),
        (
            subject_map.get("General Knowledge"),
            "Who wrote the Indian National Anthem?",
            "Mahatma Gandhi",
            "Rabindranath Tagore",
            "Jawaharlal Nehru",
            "Subhash Chandra Bose",
            "B",
            "Medium"
        ),
        (
            subject_map.get("General Knowledge"),
            "Which is the largest ocean?",
            "Atlantic Ocean",
            "Indian Ocean",
            "Arctic Ocean",
            "Pacific Ocean",
            "D",
            "Easy"
        )
    ]

    for question in sample_questions:

        if question[0] is not None:

            conn.execute("""
                INSERT INTO questions (
                    subject_id,
                    question,
                    option_a,
                    option_b,
                    option_c,
                    option_d,
                    correct_answer,
                    difficulty
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, question)

    conn.commit()
    conn.close()


# ==========================================
# CREATE DEFAULT ADMIN ACCOUNT
# ==========================================

def create_admin():

    conn = get_db_connection()

    admin = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        ("admin@smartquiz.com",)
    ).fetchone()

    if not admin:

        password = generate_password_hash("admin123")

        conn.execute("""
            INSERT INTO users (
                name,
                email,
                password,
                role
            )
            VALUES (?, ?, ?, ?)
        """, (
            "SmartQuiz Admin",
            "admin@smartquiz.com",
            password,
            "admin"
        ))

        conn.commit()

    conn.close()


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()
    insert_sample_questions()
    create_admin()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
    