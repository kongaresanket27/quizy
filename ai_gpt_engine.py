import requests
import json
import numpy as np
from sklearn.linear_model import LinearRegression
import re


# to close connection of ollama , end the task from task manager
import subprocess
try:
    requests.get("http://127.0.0.1:11434")
    print("Server Started")
except:
    # Start the serve daemon, not the interactive 'run'
    print("Starting the Server .....")
    subprocess.Popen(["ollama", "serve"]) 



def fetch_ai_questions(prompt, quiz_id, subject, add_question_func):
    """
    Generate quiz questions using local Llama3 via Ollama.
    """

    structured_prompt = f"""
    Generate {prompt}.
    Return ONLY valid JSON array.
    Format:
    [
      {{
        "q": "Question text",
        "a": "Option A",
        "b": "Option B",
        "c": "Option C",
        "d": "Option D",
        "correct": "a"
      }}
    ]
    Only return JSON. No explanation.
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": structured_prompt,
                "stream": False
            },
            timeout=3200
        )

        result = response.json()
        text = result["response"]

        # Extract JSON block safely
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            print("AI did not return valid JSON.")
            print(text)
            return False

        questions = json.loads(match.group(0))

        for item in questions:
            add_question_func(
                quiz_id,
                item["q"],
                item["a"],
                item["b"],
                item["c"],
                item["d"],
                item["correct"],
                subject
            )

        print("✅ Local AI questions added successfully.")
        return True

    except Exception as e:
        print("❌ Ollama Error:", e)
        return False

import numpy as np
from sklearn.linear_model import LinearRegression


# ==============================
# 2 .ML SCORE PREDICTION (ENHANCED)
# ==============================

def predict_user_readiness(user_id, get_user_attempts, get_user_streak):
    """
    Predict next score using Linear Regression and adjust based on user streak.
    """
    # Fetch data using your database functions
    attempts = get_user_attempts(user_id)
    streak = get_user_streak(user_id)

    if len(attempts) < 3:
        return "Insufficient Data: Take 3+ quizzes"

    # attempts format from database.py: (title, score, total, attempted_at)
    # We want Chronological order (oldest to newest) for regression
    scores_pct = [(row[1] / row[2]) * 100 for row in reversed(attempts)]
    
    y = np.array(scores_pct)
    x = np.arange(len(y)).reshape(-1, 1)

    # Fit model
    model = LinearRegression()
    model.fit(x, y)

    # Predict the next index
    next_index = np.array([[len(y)]])
    prediction = model.predict(next_index)[0]

    # Logical Cap: Score can't be > 100 or < 0
    prediction = max(0, min(100, prediction))
    
    # Optional: Boost prediction slightly if user is on a hot streak (> 3 days)
    if streak >= 3:
        prediction = min(100, prediction + 2)

    return f"Predicted Next Score: {int(prediction)}%"


# ==============================
# 2️⃣ ENHANCED SMART FEEDBACK
# ==============================

def get_smart_feedback(user_id, get_connection, get_user_analytics_overview, get_next_action):
    """
    Combines SQL analysis and trend data to give high-quality advice.
    """
    # 1. Get General Overview
    stats = get_user_analytics_overview(user_id)
    if stats["total_quizzes"] == 0:
        return "Welcome! Complete your first quiz to see AI insights."

    # 2. Get specific next action (Revise subject with lowest score)
    next_step = get_next_action(user_id)
    
    # 3. Get Weakest Subject via custom query
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT q.subject, AVG(qa.score * 100.0 / qa.total) as avg_pct
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        WHERE qa.user_id = ?
        GROUP BY q.subject ORDER BY avg_pct ASC LIMIT 1
    """, (user_id,))
    
    weak_subject_row = cur.fetchone()
    conn.close()

    # Logic-based advice
    accuracy = stats["accuracy"]
    
    if accuracy < 50:
        base_msg = f"Focus on accuracy over speed. {next_step}."
    elif accuracy < 80:
        base_msg = f"You're doing well! {next_step} to push past 80%."
    else:
        base_msg = "Mastery detected! Challenge yourself with new subjects."

    # Append subject-specific tip
    if weak_subject_row:
        subject, score = weak_subject_row
        return f"{base_msg} \nTip: Your {subject} score ({int(score)}%) is your biggest growth opportunity."
    
    return base_msg






# --- FUNCTION 1: PREDICTION FOR EVERY USER ---
def get_user_performance_predictions(get_all_users_admin, get_user_attempts):
    """
    Predicts the next quiz score probability for every user in the system.
    """
    user_results = []
    users = get_all_users_admin()

    for u in users:
        user_id, username = u[0], u[1]
        attempts = get_user_attempts(user_id)
        
        # Need at least 3 data points for a meaningful trend line
        if attempts and len(attempts) >= 3:
            # Calculate percentages and reverse to get chronological order
            scores = [(row[1] / row[2]) * 100 for row in reversed(attempts)]
            y = np.array(scores)
            x = np.arange(len(y)).reshape(-1, 1)
            
            model = LinearRegression().fit(x, y)
            # Predict the score for the next attempt index
            prediction = model.predict([[len(y)]])[0]
            val = int(max(0, min(100, prediction)))
            
            # Categorize status
            if val >= 75:
                status, msg = "Excellent", "Highly likely to pass next quiz."
            elif val >= 50:
                status, msg = "Average", "Consistent performance expected."
            else:
                status, msg = "At Risk", "Predicted score below passing threshold."
                
            user_results.append({
                "user": username, "pred": val, "status": status, "desc": msg
            })
        else:
            user_results.append({
                "user": username, "pred": "N/A", "status": "New User", "desc": "Need 3+ attempts to forecast."
            })
            
    return user_results


import numpy as np
from datetime import datetime, timedelta

def get_platform_growth_predictions(get_connection, get_daily_attempts):
    """
    Predicts future user joins and total attempt volume for the next 7 days
    using rolling average instead of unstable linear regression.
    """

    stats = {
        "predicted_new_users": 0,
        "predicted_attempts": 0
    }

    try:
        # =========================
        # A. USER GROWTH PREDICTION
        # =========================
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT date(created_at), COUNT(*)
            FROM users
            GROUP BY date(created_at)
            ORDER BY date(created_at) ASC
        """)

        growth_data = cur.fetchall()
        conn.close()

        if growth_data:

            # Convert to dictionary
            growth_dict = {row[0]: row[1] for row in growth_data}

            # Create continuous date range (fills missing days with 0)
            start_date = datetime.fromisoformat(growth_data[0][0]).date()
            end_date = datetime.now().date()

            total_days = (end_date - start_date).days + 1

            daily_counts = []
            for i in range(total_days):
                day = (start_date + timedelta(days=i)).isoformat()
                daily_counts.append(growth_dict.get(day, 0))

            # Use last 7 days average (or less if not enough data)
            recent_data = daily_counts[-7:] if len(daily_counts) >= 7 else daily_counts
            avg_growth = np.mean(recent_data)

            stats["predicted_new_users"] = int(round(avg_growth * 7))

        # =========================
        # B. ATTEMPT VOLUME PREDICTION
        # =========================

        daily_stats = get_daily_attempts(days=30)  # use 30 days for better smoothing

        if daily_stats:

            attempts_dict = {row[0]: row[1] for row in daily_stats}

            start_date = datetime.now().date() - timedelta(days=29)
            daily_attempt_counts = []

            for i in range(30):
                day = (start_date + timedelta(days=i)).isoformat()
                daily_attempt_counts.append(attempts_dict.get(day, 0))

            recent_attempts = daily_attempt_counts[-7:]
            avg_attempts = np.mean(recent_attempts)

            stats["predicted_attempts"] = int(round(avg_attempts * 7))

    except Exception as e:
        print(f"Prediction Error: {e}")

    return stats