import sqlite3
import os
from datetime import datetime
import hashlib
import secrets


# Import Generative AI module: prefer new `google.genai`, fall back to `google.generativeai`.






# ================= SECURITY =================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split("$")
        check = hashlib.sha256((salt + password).encode()).hexdigest()
        return check == hashed
    except ValueError:
        return False


# ================= PATH =================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "quizy.db")

os.makedirs(DATA_DIR, exist_ok=True)


# ================= CONNECTION =================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ================= INIT DATABASE =================

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # ADMINS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # QUESTIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        subject TEXT,
        difficulty TEXT,
        source TEXT DEFAULT 'manual',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # QUIZZES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # QUIZ - QUESTION RELATION
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER,
        question_id INTEGER,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )
    """)

    # QUIZ ATTEMPTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        attempted_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()


# ================= USER AUTH =================

def create_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def validate_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password FROM users WHERE username=?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    if row and verify_password(password, row[1]):
        return row[0]
    return None


# ================= ADMIN AUTH =================


# if you are deleting the database of app i.e .db file where the data of user and admin is store then you want to run the app and run the admin_pass.py 
# file once to insert the admin_password_password and adminname 
def validate_admin(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password FROM admins WHERE username=?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    if row and verify_password(password, row[1]):
        return row[0]
    return None


# ================= QUIZ DATA =================

def save_quiz_attempt(user_id, quiz_id, score, total):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO quiz_attempts (user_id, quiz_id, score, total, attempted_at)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, quiz_id, score, total, datetime.now().isoformat()))

    conn.commit()
    conn.close()



def get_user_attempts(user_id):
    conn = get_connection()
    cur = conn.cursor()
    # Join with quizzes to get the actual Title for the results list
    cur.execute("""
        SELECT q.title, a.score, a.total, a.attempted_at
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.user_id=?
        ORDER BY a.attempted_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_subject_mastery(user_id):
    conn = get_connection()
    cur = conn.cursor()
    # Gets Subject, Total Quizzes Taken, and Avg Score
    cur.execute("""
        SELECT q.subject, COUNT(a.id), AVG(a.score * 100.0 / a.total)
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.user_id=?
        GROUP BY q.subject
    """, (user_id,))
    data = cur.fetchall()
    conn.close()
    return data # Returns [(Subject, Count, AvgScore), ...]

def get_all_attempts():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT u.username, q.quiz_id, q.score, q.total, q.attempted_at
    FROM quiz_attempts q
    JOIN users u ON q.user_id = u.id
    ORDER BY q.attempted_at DESC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows




def get_admin_kpis():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM quiz_attempts
        WHERE date(attempted_at) >= date('now','-7 day')
    """)
    active_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT quiz_id) FROM quiz_attempts")
    total_quizzes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM quiz_attempts")
    total_attempts = cur.fetchone()[0]

    conn.close()
    return total_users, active_users, total_quizzes, total_attempts


def get_daily_attempts(days=7):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT date(attempted_at), COUNT(*)
        FROM quiz_attempts
        WHERE date(attempted_at) >= date('now','-{days} day')
        GROUP BY date(attempted_at)
        ORDER BY date(attempted_at)
    """)

    data = cur.fetchall()
    conn.close()
    return data

def get_user_dashboard_snapshot(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # quizzes today
    cur.execute("""
        SELECT COUNT(*)
        FROM quiz_attempts
        WHERE user_id=?
        AND date(attempted_at) = date('now')
    """, (user_id,))
    quizzes_today = cur.fetchone()[0]

    # avg score
    cur.execute("""
        SELECT ROUND(AVG(score * 100.0 / total), 2)
        FROM quiz_attempts
        WHERE user_id=?
    """, (user_id,))
    avg_score = cur.fetchone()[0] or 0

    # time spent (rough estimation: 5 min per quiz)
    time_spent = quizzes_today * 5

    conn.close()

    return {
        "quizzes": quizzes_today,
        "avg_score": avg_score,
        "time_spent": time_spent
    }


def get_user_weekly_activity(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT date(attempted_at), COUNT(*)
        FROM quiz_attempts
        WHERE user_id=?
        AND date(attempted_at) >= date('now','-6 day')
        GROUP BY date(attempted_at)
        ORDER BY date(attempted_at)
    """, (user_id,))

    data = cur.fetchall()
    conn.close()

    counts = {d: c for d, c in data}

    result = []
    for i in range(6, -1, -1):
        day = datetime.now().date().fromordinal(
            datetime.now().date().toordinal() - i
        ).isoformat()
        result.append(counts.get(day, 0))

    return result




def get_next_action(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT q.title, AVG(a.score * 100.0 / a.total)
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.user_id=?
        GROUP BY q.id
        ORDER BY AVG(a.score) ASC
        LIMIT 1
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if row:
        return f"Revise: {row[0]}"
    return "Attempt a new quiz 🚀"


def get_user_streak(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT date(attempted_at)
        FROM quiz_attempts
        WHERE user_id=?
        ORDER BY date(attempted_at) DESC
    """, (user_id,))

    dates = [row[0] for row in cur.fetchall()]
    conn.close()

    streak = 0
    today = datetime.now().date()

    for i, d in enumerate(dates):
        if today.fromisoformat(d) == today:
            streak += 1
            today = today.replace(day=today.day - 1)
        else:
            break

    return streak

def get_attempts_per_quiz():
    conn = get_connection()
    cur = conn.cursor()
    # Join with quizzes to get the title instead of ID
    cur.execute("""
        SELECT q.title, COUNT(a.id)
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        GROUP BY q.title
    """)
    data = cur.fetchall()
    conn.close()
    return data

def get_avg_score_per_quiz():
    conn = get_connection()
    cur = conn.cursor()
    # Join with quizzes to get the title instead of ID
    cur.execute("""
        SELECT q.title, AVG(a.score)
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        GROUP BY q.title
    """)
    data = cur.fetchall()
    conn.close()
    return data


def get_all_users_admin():
    conn = get_connection()
    cur = conn.cursor()

    # Enhanced query using a window function to calculate Rank based on average score
    cur.execute("""
        SELECT 
            u.id,
            u.username,
            u.created_at,
            COUNT(a.id) AS attempts,
            MAX(a.attempted_at) AS last_active,
            RANK() OVER (ORDER BY AVG(a.score * 100.0 / a.total) DESC) as current_rank
        FROM users u
        LEFT JOIN quiz_attempts a ON u.id = a.user_id
        GROUP BY u.id
        ORDER BY current_rank ASC
    """)

    users = cur.fetchall()
    conn.close()
    return users


def get_user_profile(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Get User Info
    cur.execute("SELECT username, created_at FROM users WHERE id=?", (user_id,))
    u = cur.fetchone()
    
    if not u:
        conn.close()
        return None  # Or handle the error gracefully

    # Get Aggregated Stats
    cur.execute("""
        SELECT 
            COUNT(*),
            AVG(CAST(score AS FLOAT) / total * 100),
            MAX(attempted_at)
        FROM quiz_attempts
        WHERE user_id=?
    """, (user_id,))
    stats = cur.fetchone()

    conn.close()

    return {
        "username": u[0],
        "joined": u[1],
        "attempts": stats[0] or 0,
        "avg_score": round(stats[1] or 0, 2),
        "last_active": stats[2] or "Never"
    }

# ================= USER ANALYTICS =================

def get_user_analytics_overview(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # total quizzes
    cur.execute(
        "SELECT COUNT(*) FROM quiz_attempts WHERE user_id=?",
        (user_id,)
    )
    total_quizzes = cur.fetchone()[0]

    # avg score %
    cur.execute(
        "SELECT AVG(score * 100.0 / total) FROM quiz_attempts WHERE user_id=?",
        (user_id,)
    )
    avg_score = round(cur.fetchone()[0] or 0, 2)

    # accuracy %
    cur.execute(
        "SELECT SUM(score), SUM(total) FROM quiz_attempts WHERE user_id=?",
        (user_id,)
    )
    s, t = cur.fetchone()
    accuracy = round((s / t) * 100, 2) if t else 0

    # total time spent (estimated 2 min per question)
    cur.execute(
        "SELECT SUM(total) FROM quiz_attempts WHERE user_id=?",
        (user_id,)
    )
    total_questions = cur.fetchone()[0] or 0
    time_spent = total_questions * 2  # minutes

    conn.close()

    return {
        "total_quizzes": total_quizzes,
        "avg_score": avg_score,
        "accuracy": accuracy,
        "time_spent": time_spent
    }


def get_user_score_trend(user_id, limit=7):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT score * 100.0 / total
        FROM quiz_attempts
        WHERE user_id=?
        ORDER BY attempted_at DESC
        LIMIT ?
    """, (user_id, limit))

    data = [int(row[0]) for row in cur.fetchall()]
    conn.close()
    return list(reversed(data))  # oldest → latest


def get_user_subject_performance(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Join quiz_attempts with quizzes to get the subject name
    cur.execute("""
        SELECT q.subject, AVG(a.score * 100.0 / a.total)
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.user_id=?
        GROUP BY q.subject
    """, (user_id,))

    data = {row[0]: int(row[1]) for row in cur.fetchall()}
    conn.close()
    return data


def add_question(quiz_id, q, a, b, c, d, correct, subject, difficulty=None, source="manual"):
    conn = get_connection()
    cur = conn.cursor()

    # 1️⃣ Insert into questions table
    cur.execute("""
        INSERT INTO questions
        (question, option_a, option_b, option_c, option_d,
         correct_option, subject, difficulty, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (q, a, b, c, d, correct, subject, difficulty, source))

    question_id = cur.lastrowid  # get new question id

    # 2️⃣ Link to quiz
    cur.execute("""
        INSERT INTO quiz_questions (quiz_id, question_id)
        VALUES (?, ?)
    """, (quiz_id, question_id))

    conn.commit()
    conn.close()



def get_all_questions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()
    return data


def delete_question(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()


def get_random_questions(limit=10, subject=None):
    conn = get_connection()
    cur = conn.cursor()

    if subject:
        cur.execute("""
            SELECT * FROM questions
            WHERE subject=?
            ORDER BY RANDOM()
            LIMIT ?
        """, (subject, limit))
    else:
        cur.execute("""
            SELECT * FROM questions
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return rows


# ================= QUIZ MANAGEMENT =================

def create_quiz(title, subject, created_by=1):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO quizzes (title, subject, created_by)
        VALUES (?, ?, ?)
    """, (title, subject, created_by))

    quiz_id = cur.lastrowid
    conn.commit()
    conn.close()
    return quiz_id


def add_question_to_quiz(quiz_id, question_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO quiz_questions (quiz_id, question_id)
        VALUES (?, ?)
    """, (quiz_id, question_id))

    conn.commit()
    conn.close()


def get_questions_by_quiz(quiz_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT q.*
        FROM questions q
        JOIN quiz_questions qq ON q.id = qq.question_id
        WHERE qq.quiz_id=?
    """, (quiz_id,))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_quizzes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM quizzes ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_quiz(quiz_id, new_title, new_subject):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE quizzes
        SET title=?, subject=?
        WHERE id=?
    """, (new_title, new_subject, quiz_id))

    conn.commit()
    conn.close()

def delete_quiz(quiz_id):
    conn = get_connection() 
    cur = conn.cursor()

    # remove relations first
    cur.execute("DELETE FROM quiz_questions WHERE quiz_id=?", (quiz_id,))
    
    # remove quiz
    cur.execute("DELETE FROM quizzes WHERE id=?", (quiz_id,))

    conn.commit()
    conn.close()

def remove_question_from_quiz(quiz_id, question_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM quiz_questions
        WHERE quiz_id=? AND question_id=?
    """, (quiz_id, question_id))

    conn.commit()
    conn.close()

def get_quiz_by_id(quiz_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,))
    quiz = cur.fetchone()

    conn.close()
    return quiz



######################## a.i

def get_subject_accuracy_trends(user_id):
    """
    Fetches the percentage score for every attempt, grouped by subject.
    Returns: {'Math': [70, 75, 80], 'Science': [60, 58, 65]}
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # We join quiz_attempts with quizzes to get the subject name 
    # and sort by date so the line goes from oldest to newest
    cur.execute("""
        SELECT q.subject, (CAST(a.score AS FLOAT) / a.total * 100)
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.user_id = ?
        ORDER BY a.attempted_at ASC
    """, (user_id,))
    
    raw_data = cur.fetchall()
    conn.close()
    
    trends = {}
    for subject, accuracy in raw_data:
        if subject not in trends:
            trends[subject] = []
        trends[subject].append(int(accuracy))
    return trends


def get_user_rank_trend(user_id, limit=10):
    """
    Calculates the historical rank for the user over their last 'limit' attempts.
    Returns a list of ranks (e.g., [15, 12, 10, 8]) where lower is better.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Get the timestamps of the user's last X attempts
    cur.execute("""
        SELECT attempted_at 
        FROM quiz_attempts 
        WHERE user_id = ? 
        ORDER BY attempted_at ASC 
        LIMIT ?
    """, (user_id, limit))
    timestamps = [row[0] for row in cur.fetchall()]
    
    rank_trend = []
    
    for ts in timestamps:
        # Calculate what the user's rank was at that specific point in time
        # based on the average of all scores recorded UP TO that timestamp
        cur.execute("""
            WITH HistoricalAvgs AS (
                SELECT user_id, AVG(score * 100.0 / total) as avg_score
                FROM quiz_attempts
                WHERE attempted_at <= ?
                GROUP BY user_id
            )
            SELECT COUNT(*) + 1 FROM HistoricalAvgs
            WHERE avg_score > (SELECT avg_score FROM HistoricalAvgs WHERE user_id = ?)
        """, (ts, user_id))
        
        rank = cur.fetchone()[0]
        rank_trend.append(rank)

    conn.close()
    return rank_trend


def get_unique_users_per_quiz():
    conn = get_connection()
    cur = conn.cursor()

    # COUNT(DISTINCT user_id) ensures we only count each user once per quiz
    cur.execute("""
        SELECT q.title, COUNT(DISTINCT qa.user_id) as unique_user_count
        FROM quizzes q
        LEFT JOIN quiz_attempts qa ON q.id = qa.quiz_id
        GROUP BY q.id
        ORDER BY unique_user_count DESC
    """)
    data = cur.fetchall()
    conn.close()

    # Truncate titles for clean labels
    titles = [(r[0][:12] + '..') if len(r[0]) > 12 else r[0] for r in data]
    user_counts = [r[1] for r in data]
    
    return titles, user_counts