import customtkinter as ctk
from db.database import (
    get_all_quizzes,
    get_connection,
    get_questions_by_quiz,
    get_questions_by_quiz,
    get_quiz_by_id,
    get_subject_mastery,
    get_user_rank_trend,
    get_user_dashboard_snapshot,
    get_user_streak,
    get_user_weekly_activity,
    get_next_action,get_attempts_per_quiz,
)
from db.database import (
    get_user_analytics_overview,
    get_user_score_trend,
    get_user_subject_performance,get_avg_score_per_quiz
)
from ai_gpt_engine import predict_user_readiness, get_smart_feedback


from db.database import get_user_attempts,save_quiz_attempt
import time         #




def user_dashboard(root, user_id):

    from typing import Optional
    timer_label: dict[str, Optional[ctk.CTkLabel]] = {"widget": None}       #
    # aboves meaning
    # {"widget": None}   or
    # {"widget": ctk.CTkLabel(...)}


    ctk.set_appearance_mode("dark")

    app = ctk.CTkToplevel(root)
    app.title("Quizy - User Dashboard")

    # Full screen
    app.state("zoomed")

    # ================= STATE =================
    active_quiz = {"id": ""}
    quiz_in_progress = {"active": False}

    current_q = 0
    selected_answers = {}
    attempt_data = {}
    
    # ADD THIS LINE:
    quiz_violations = {"count": 0}


    timer_seconds = {"value": 0}
    timer_running = {"active": False}
    timer_after_id: dict[str, Optional[str]] = {"id": None}
    

    # ================= LOGOUT =================
    def logout():
        if quiz_in_progress["active"]:
            return
        app.destroy()
        root.deiconify()

    # ================= SIDEBAR =================
    sidebar = ctk.CTkFrame(app, width=220, corner_radius=0, fg_color="#111111")
    sidebar.pack(side="left", fill="y")

    ctk.CTkLabel(sidebar, text="Quizy", font=("Segoe UI", 22, "bold")).pack(pady=(30, 5))
    ctk.CTkLabel(sidebar, text="User Panel", text_color="gray").pack(pady=(0, 30))

    # ================= CONTENT =================
    content = ctk.CTkScrollableFrame(app)
    content.pack(side="left", fill="both", expand=True)

    def clear_content():
        for w in content.winfo_children():  #
            w.destroy()

    # ================= SIDEBAR LOCK =================
    def set_sidebar_state(lock: bool):
        for widget in sidebar.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") != "Logout":  # if the widget is button and txt on that button is not logout
                widget.configure(state="disabled" if lock else "normal")

    # ================= TIMER =================
    def start_timer(minutes):
        # cancel any existing after callback
        widget = timer_label.get("widget")
        tid = timer_after_id.get("id")
        if tid is not None and widget is not None and widget.winfo_exists():
            widget.after_cancel(tid)
            timer_after_id["id"] = None

        timer_seconds["value"] = minutes * 60
        timer_running["active"] = True
        update_timer()


    def update_timer():
        widget = timer_label.get("widget")
        if widget is None or not widget.winfo_exists():
            return

        mins, secs = divmod(timer_seconds["value"], 60)
        widget.configure(text=f"⏱ {mins:02d}:{secs:02d}")

        if timer_seconds["value"] <= 0:  
            # Auto submit the quiz when the time over
            submit_quiz()
            return

        timer_seconds["value"] -= 1
        timer_after_id["id"] = widget.after(1000, update_timer)




    # ================= PAGES =================
    from tkinter import Canvas
    from datetime import datetime

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


# ---------- DASHBOARD ----------
    def show_dashboard():
        clear_content()

        main = ctk.CTkFrame(content, fg_color="#0b0f1a")
        main.pack(fill="both", expand=True)

        # ===== HEADER =====
        header = ctk.CTkFrame(main, height=80, fg_color="#0f172a")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="👋 Welcome back",
            font=("Segoe UI", 24, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=30, pady=20)

        # ===== TOP CARDS =====
        cards = ctk.CTkFrame(main, fg_color="#0b0f1a")
        cards.pack(fill="x", padx=20)

        snapshot = get_user_dashboard_snapshot(user_id)
        streak = get_user_streak(user_id)

        def stat_card(title, value, sub):
            card = ctk.CTkFrame(cards, fg_color="#020617", corner_radius=18, width=220, height=120)
            card.pack(side="left", padx=10, pady=10)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=title, text_color="#94a3b8").pack(anchor="w", padx=20, pady=(15, 0))
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=20)
            ctk.CTkLabel(card, text=sub, text_color="#22c55e").pack(anchor="w", padx=20)

        stat_card("Today's Quizzes", snapshot["quizzes"], "Active")
        stat_card("Avg Score", f"{snapshot['avg_score']}%", "Performance")
        stat_card("Time Spent", f"{snapshot['time_spent']} min", "Focused")
        stat_card("Streak", f"{streak} days 🔥", "Consistency")

        # ===== MAIN GRID =====
        grid = ctk.CTkFrame(main, fg_color="#0b0f1a")
        grid.pack(fill="both", expand=True, padx=20, pady=10)

        # ----- NEXT ACTION -----
        next_action = ctk.CTkFrame(grid, fg_color="#020617", corner_radius=18)
        next_action.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            next_action,
            text="🎯 Next Best Action",
            font=("Segoe UI", 18, "bold"),
            text_color="#a78bfa"
        ).pack(anchor="w", padx=20, pady=(18, 8))

        ctk.CTkLabel(
            next_action,
            text=get_next_action(user_id),
            font=("Segoe UI", 20),
            text_color="#e5e7eb"
        ).pack(anchor="w", padx=20)

        ctk.CTkButton(
            next_action,
            text="Start Now",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=12,
            command = show_quizzes
        ).pack(anchor="w", padx=20, pady=20)

        # ----- WEEKLY ACTIVITY GRAPH (FIXED) -----
        activity = ctk.CTkFrame(grid, fg_color="#020617", corner_radius=18)
        activity.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            activity,
            text="📊 Weekly Activity",
            font=("Segoe UI", 18, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=20, pady=(18, 8))

        canvas = Canvas(activity, bg="#020617", highlightthickness=0, height=240)
        canvas.pack(fill="both", expand=True, padx=20)

        # ===== DATA FIX =====
        weekly = get_user_weekly_activity(user_id)

        # FORCE 7 DAYS
        if len(weekly) < 7:
            weekly += [0] * (7 - len(weekly))
        weekly = weekly[:7]

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        max_val = max(weekly) if max(weekly) > 0 else 1

        bar_width = 30
        gap = 25
        x_start = 40
        base_y = 200
        graph_height = 160

        # ---- Y GRID ----
        for p in range(0, max_val + 1, max(1, max_val // 4)):
            y = base_y - int((p / max_val) * graph_height)
            canvas.create_line(
                x_start - 20, y,
                x_start + 7 * (bar_width + gap), y,
                fill="#1e293b", dash=(2, 4)
            )
            canvas.create_text(
                x_start - 25, y,
                text=str(p),
                fill="#64748b",
                anchor="e",
                font=("Segoe UI", 9)
            )

        # ---- BARS + DAY LABELS ----
        for i, val in enumerate(weekly):
            x = x_start + i * (bar_width + gap)
            h = int((val / max_val) * graph_height)

            fill = "#3b82f6" if val > 0 else "#1e293b"

            canvas.create_rectangle(
                x, base_y - h,
                x + bar_width, base_y,
                fill=fill,
                outline=""
            )

            canvas.create_text(
                x + bar_width / 2,
                base_y - h - 10,
                text=str(val),
                fill="#e5e7eb",
                font=("Segoe UI", 9)
            )

            canvas.create_text(
                x + bar_width / 2,
                base_y + 12,
                text=days[i],
                fill="#94a3b8",
                font=("Segoe UI", 9)
            )


        # =====================================================
        # 4️⃣ ML Prediction + AI Feedback (UPDATED)
        # =====================================================

        prediction_frame = ctk.CTkFrame(main, fg_color="#020617", corner_radius=18)
        prediction_frame.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            prediction_frame,
            text="📈 AI Insights & Prediction",
            font=("Segoe UI", 16, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # ===== UPDATED ML Prediction =====
        # Pass get_user_streak to factor in user momentum
        pred_val = predict_user_readiness(user_id, get_user_attempts, get_user_streak)

        # Color logic
        if "Not enough data" in pred_val or "Insufficient" in pred_val:
            pred_color = "#f59e0b"  # orange
        else:
            pred_color = "#22c55e"  # green

        ctk.CTkLabel(
            prediction_frame,
            text=pred_val,
            font=("Segoe UI", 22, "bold"),
            text_color=pred_color
        ).pack(anchor="w", padx=20, pady=(0, 10))


        # ===== UPDATED Smart Feedback =====
        # Pass advanced analytics helpers to generate specific revision tips
        feedback = get_smart_feedback(
            user_id, 
            get_connection, 
            get_user_analytics_overview, 
            get_next_action
        )

        ctk.CTkLabel(
            prediction_frame,
            text="🧠 Smart Recommendation",
            font=("Segoe UI", 13, "bold"),
            text_color="#a78bfa"
        ).pack(anchor="w", padx=20, pady=(10, 5))

        ctk.CTkLabel(
            prediction_frame,
            text=feedback,
            font=("Segoe UI", 11),
            text_color="#94a3b8",
            wraplength=350,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # ===== FOOTER =====
        footer = ctk.CTkFrame(main, height=60, fg_color="#0f172a")
        footer.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            footer,
            text="📈 Progress updated from real activity",
            text_color="#22c55e",
            font=("Segoe UI", 14)
        ).pack(side="left", padx=30, pady=15)

        ctk.CTkLabel(
            footer,
            text=f"Last Login: {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            text_color="#94a3b8"
        ).pack(side="right", padx=30)


    def show_quizzes():
        clear_content()
        ctk.CTkLabel(content, text="Available Quizzes",
                    font=("Segoe UI", 22, "bold")).pack(pady=20)

        quizzes = get_all_quizzes()

        if not quizzes:
            ctk.CTkLabel(content,
                        text="No quizzes available yet.",
                        text_color="gray").pack(pady=20)
            return

        for quiz in quizzes:

            quiz_id = quiz[0]
            title = quiz[1]
            subject = quiz[2]

            card = ctk.CTkFrame(content, corner_radius=15)
            card.pack(padx=80, pady=10, fill="x")

            ctk.CTkLabel(card,
                        text=title,
                        font=("Segoe UI", 16, "bold")
                        ).pack(anchor="w", padx=20, pady=(10, 0))

            ctk.CTkLabel(card,
                        text=f"Subject: {subject}",
                        text_color="gray"
                        ).pack(anchor="w", padx=20)

            def start(q=quiz_id):
                start_quiz(q)

            ctk.CTkButton(card,
                        text="Start Quiz",
                        command=start).pack(anchor="e",padx=20,pady=10)

    # ================= For Tab disabling =================
    # give 3 warning and then autosubmit quiz
    def on_focus_lost(event):
        # Only trigger if a quiz is actually active
        if quiz_in_progress["active"]:
            quiz_violations["count"] += 1
            max_limit = 3
            
            if quiz_violations["count"] >= max_limit:
                # from tkinter import messagebox
                # messagebox.showerror("Security Violation", "Multiple tab switches detected. Quiz auto-submitted.")
                submit_quiz() # Existing function in your code
                show_quizzes()            
            else:
                from tkinter import messagebox
                messagebox.showwarning("Anti-Cheating Warning", 
                    f"Warning: Do not leave the app window!\nViolation {quiz_violations['count']}/{max_limit}")
                # Force the window back to focus
                app.after(100, lambda: app.focus_force())


    # ================= QUIZ FLOW =================

        
        # ... rest of your existing start_quiz code ...
    def start_quiz(qid):

        nonlocal current_q

        quiz_violations["count"] = 0            #
        app.bind("<FocusOut>", on_focus_lost)   #   "<FocusOut>"  for tab exchange

        active_quiz["id"] = qid
        quiz_in_progress["active"] = True
        set_sidebar_state(True)

        current_q = 0
        selected_answers.clear()

        quiz = get_quiz_by_id(qid)
        questions = get_questions_by_quiz(qid)

        if not questions:
            quiz_in_progress["active"] = False
            set_sidebar_state(False)
            return

        attempt_data.clear()
        attempt_data["quiz_info"] = quiz
        attempt_data["questions"] = questions

        start_timer(60)  # keeping your existing fixed time logic
        ################################################
        show_quiz_attempt()

    def show_quiz_attempt():
        clear_content()

        quiz = attempt_data["quiz_info"]
        questions = attempt_data["questions"]

        q = questions[current_q]

        if timer_label["widget"] is None or not timer_label["widget"].winfo_exists():
            timer_label["widget"] = ctk.CTkLabel(
                content,
                font=("Segoe UI", 14, "bold")
            )
            timer_label["widget"].pack(anchor="ne", padx=20, pady=10)

        ctk.CTkLabel(
            content,
            text=f'{quiz[1]}  ({current_q + 1}/{len(questions)})',
            font=("Segoe UI", 22, "bold")
        ).pack(pady=15)

        ctk.CTkLabel(
            content,
            text=q[1],
            wraplength=700
        ).pack(pady=20)

        selected = ctk.StringVar(value=selected_answers.get(current_q, ""))

        options = [q[2], q[3], q[4], q[5]]

        for opt in options:
            ctk.CTkRadioButton(
                content,
                text=opt,
                variable=selected,
                value=opt
            ).pack(anchor="w", padx=200, pady=5)

        def save_answer():
            selected_answers[current_q] = selected.get()

        nav_frame = ctk.CTkFrame(content)
        nav_frame.pack(pady=30)

        def next_q():
            nonlocal current_q
            save_answer()
            if current_q < len(questions) - 1:
                current_q += 1
                show_quiz_attempt()

        def prev_q():
            nonlocal current_q
            save_answer()
            if current_q > 0:
                current_q -= 1
                show_quiz_attempt()
        
        ctk.CTkButton(nav_frame, text="Previous",
                    command=prev_q).pack(side="left", padx=10)
        

        ##########
        if current_q == len(questions) - 1:
            ctk.CTkButton(nav_frame, text="Save",command=save_answer).pack(side="left", padx=10)
        else:
            ctk.CTkButton(nav_frame, text="Next",command=next_q).pack(side="left", padx=10)
            


        if current_q == len(questions) - 1:
            ctk.CTkButton(
                nav_frame,
                text="Submit Quiz",
                fg_color="#2e7d32",
                command=submit_quiz
            ).pack(side="left", padx=10)

        update_timer()



    # ================= SUBMIT & RESULT =================
    def submit_quiz():
                
        tid = timer_after_id.get("id")
        widget = timer_label.get("widget")
        if tid and widget and widget.winfo_exists():
            widget.after_cancel(tid)
            timer_after_id["id"] = None

        quiz_in_progress["active"] = False
        set_sidebar_state(False)

        quiz = attempt_data["quiz_info"]
        questions = attempt_data["questions"]

        score = 0
        details = []

        for i, q in enumerate(questions):

            correct_letter = q[6]  # 'a', 'b', 'c', 'd'

            # Map letter → actual option text
            options_map = {
                "a": q[2],
                "b": q[3],
                "c": q[4],
                "d": q[5]
            }

            correct_answer = options_map.get(correct_letter.lower(), "")    # correct answer

            chosen = selected_answers.get(i, "")    # chosen

            is_correct = chosen == correct_answer
            # print(correct_answer,chosen)

            if is_correct:
                score += 1

            details.append({
                "question": q[1],
                "selected": chosen,
                "correct": correct_answer,
                "is_correct": is_correct
            })

        attempt_data.clear()
        attempt_data.update({
            "quiz_id": quiz[0],
            "score": score,
            "total": len(questions),
            "details": details
        })

        save_quiz_attempt(
            user_id=user_id,
            quiz_id=quiz[0],
            score=score,
            total=len(questions)
        )

        
         # UNBIND THE EVENT HERE
        app.unbind("<FocusOut>")



        show_results()
#quiz_id, score, total, attempted_at  contain by dictionry ATTEMPT  from database , i.e row in database

    def show_results():
        clear_content()
        ctk.CTkLabel(
            content,
            text="My Results",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=20)

        attempts = get_user_attempts(user_id)

        if not attempts:
            ctk.CTkLabel(
                content,
                text="No quiz attempts yet.",
                text_color="gray"
            ).pack(pady=20)
            return

    # ... (clear_content and header code)
        attempts = get_user_attempts(user_id)

# Inside show_results() in ui_user_dashboard.py
        for quiz_title, score, total, attempted_at in attempts: # Adjusted to match database.py return values
            card = ctk.CTkFrame(content, corner_radius=15)
            card.pack(padx=80, pady=10, fill="x")

            ctk.CTkLabel(
                card,
                text=f"Quiz: {quiz_title}", # Corrected to display the title string
                font=("Segoe UI", 16, "bold")
            ).pack(anchor="w", padx=20, pady=(10, 0))

            ctk.CTkLabel(
                card,
                text=f"Score: {score} / {total}",
            ).pack(anchor="w", padx=20)

            ctk.CTkLabel(
                card,
                text=f"Attempted on: {attempted_at}",
                text_color="gray"
            ).pack(anchor="w", padx=20, pady=(0, 10))


    def analytics():
        clear_content()

        main = ctk.CTkFrame(content, fg_color="#0b0f1a")
        main.pack(fill="both", expand=True)

        # ===== HEADER =====
        header = ctk.CTkFrame(main, height=70, fg_color="#0f172a")
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="📊 User Analytics",
            font=("Segoe UI", 24, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=30, pady=18)

        # ===== STATS SECTION (UNCHANGED) =====
        overview = get_user_analytics_overview(user_id)

        stats = ctk.CTkFrame(main, fg_color="#0b0f1a")
        stats.pack(fill="x", padx=20)

        def stat(title, value):
            card = ctk.CTkFrame(stats, fg_color="#020617",
                                corner_radius=16, width=200, height=100)
            card.pack(side="left", padx=10, pady=10)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=title,
                        text_color="#94a3b8").pack(anchor="w", padx=15, pady=(15, 0))

            ctk.CTkLabel(card, text=value,
                        font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=15)

        stat("Total Quizzes", overview["total_quizzes"])
        stat("Avg Score", f"{overview['avg_score']}%")
        stat("Accuracy", f"{overview['accuracy']}%")
        stat("Time Spent", f"{overview['time_spent']} min")

        # ================= GRID =================
        graphs = ctk.CTkFrame(main, fg_color="#0b0f1a")
        graphs.pack(fill="both", expand=True, padx=20, pady=10)

        # allow two rows for the analytics grid (score trend/pie on top,
        # bar performance + subject-trend side-by-side below)
        for i in range(2):
            graphs.grid_columnconfigure(i, weight=1)
            graphs.grid_rowconfigure(i, weight=1)

        # =====================================================
        # 1️⃣ LINE GRAPH (Score Trend)
        # =====================================================
        line_frame = ctk.CTkFrame(graphs, fg_color="#020617", corner_radius=18)
        line_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(line_frame, text="📈 Score Trend",
                    font=("Segoe UI", 16, "bold"),
                    text_color="#a78bfa").pack(anchor="w", padx=20, pady=10)

        canvas1 = Canvas(line_frame, bg="#020617", highlightthickness=0, height=220)
        canvas1.pack(fill="both", expand=True, padx=20, pady=10)

        trend = get_user_score_trend(user_id)

        if trend:
            max_val = 100
            base_y = 170
            gap = 45
            left = 40
            prev = None

            for i, val in enumerate(trend):
                x = left + i * gap
                y = base_y - int((val / max_val) * 130)

                canvas1.create_oval(x-4, y-4, x+4, y+4, fill="#38bdf8", outline="")
                canvas1.create_text(x, y-12,
                                    text=f"{val}%",
                                    fill="#e2e8f0",
                                    font=("Segoe UI", 8))

                if prev:
                    canvas1.create_line(prev[0], prev[1], x, y,
                                        fill="#38bdf8", width=2)

                prev = (x, y)

        # =====================================================
        # 2️⃣ PIE CHART (Accuracy)
        # =====================================================
        pie_frame = ctk.CTkFrame(graphs, fg_color="#020617", corner_radius=18)
        pie_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(pie_frame, text="🥧 Accuracy",
                    font=("Segoe UI", 16, "bold"),
                    text_color="#22c55e").pack(anchor="w", padx=20, pady=10)

        canvas2 = Canvas(pie_frame, bg="#020617", highlightthickness=0, height=220)
        canvas2.pack(fill="both", expand=True, padx=20, pady=10)

        correct = overview["accuracy"]
        incorrect = 100 - correct

        canvas2.create_arc(60, 30, 240, 210,
                        start=0,
                        extent=correct * 3.6,
                        fill="#22c55e")

        canvas2.create_arc(60, 30, 240, 210,
                        start=correct * 3.6,
                        extent=incorrect * 3.6,
                        fill="#ef4444")

        # Center text inside pie
        canvas2.create_text(150, 120,
                            text=f"{correct}%",
                            fill="white",
                            font=("Segoe UI", 16, "bold"))

        canvas2.create_text(150, 235,
                            text="Correct vs Incorrect",
                            fill="#94a3b8",
                            font=("Segoe UI", 9))

        # =====================================================
        # 3️⃣ BAR GRAPH (Subject Performance)
        # =====================================================
        bar_frame = ctk.CTkFrame(graphs, fg_color="#020617", corner_radius=18)
        bar_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(bar_frame, text="📊 Subject Performance",
                    font=("Segoe UI", 16, "bold"),
                    text_color="#facc15").pack(anchor="w", padx=20, pady=10)

        canvas3 = Canvas(bar_frame, bg="#020617", highlightthickness=0, height=220)
        canvas3.pack(fill="both", expand=True, padx=20, pady=10)


        subjects = get_user_subject_performance(user_id)

        if subjects:
            max_val = 100
            base_y = 170
            gap = 80 # Increased gap slightly for longer subject names
            left = 40

            for i, (subject_name, val) in enumerate(subjects.items()):
                x = left + i * gap
                height = int((val / max_val) * 130)

                # Draw the bar
                canvas3.create_rectangle(
                    x, base_y - height,
                    x + 40, base_y,
                    fill="#facc15",
                    outline=""
                )

                # Percentage Text
                canvas3.create_text(x + 20, base_y - height - 12,
                                    text=f"{val}%",
                                    fill="#e2e8f0",
                                    font=("Segoe UI", 9, "bold"))

                # Subject Name Text (Truncated if too long)
                display_name = (subject_name[:8] + '..') if len(str(subject_name)) > 10 else subject_name
                canvas3.create_text(x + 20, base_y + 15,
                                    text=display_name,
                                    fill="#94a3b8",
                                    font=("Segoe UI", 8))
            
# =====================================================
        # 4️⃣ RANK PROGRESSION (CodeChef Style)
        # =====================================================
        rank_frame = ctk.CTkFrame(graphs, fg_color="#020617", corner_radius=18)
        rank_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(rank_frame, text="📈 Global Rank Progression",
                    font=("Segoe UI", 16, "bold"),
                    text_color="#38bdf8").pack(anchor="w", padx=20, pady=10)

        canvas4 = Canvas(rank_frame, bg="#020617", highlightthickness=0, height=220)
        canvas4.pack(fill="both", expand=True, padx=20, pady=10)

        rank_history = get_user_rank_trend(user_id) # New function from database.py

        if rank_history and len(rank_history) > 1:
            # CodeChef graphs use an inverted Y-axis (Rank 1 is at the top)
            max_rank = max(rank_history) + 5
            min_rank = 1
            base_y = 180
            top_y = 40
            gap = 220 / (len(rank_history) - 1)
            left = 40
            
            prev_point = None

            for i, rank in enumerate(rank_history):
                x = left + i * gap
                # Invert logic: (rank/max_rank) determines distance from top
                y = top_y + ((rank - min_rank) / (max_rank - min_rank)) * (base_y - top_y)

                # Draw point
                canvas4.create_oval(x-3, y-3, x+3, y+3, fill="#38bdf8", outline="")
                
                # Draw Rank Label
                canvas4.create_text(x, y-15, text=f"#{rank}", fill="white", font=("Segoe UI", 8))

                # Draw Line
                if prev_point:
                    canvas4.create_line(prev_point[0], prev_point[1], x, y, 
                                        fill="#38bdf8", width=2, smooth=True)
                
                prev_point = (x, y)
                
            canvas4.create_text(150, 205, text="Rank over last 10 quizzes", 
                                fill="#94a3b8", font=("Segoe UI", 9))
        else:
            canvas4.create_text(150, 110, text="Take more quizzes to see rank trend", fill="gray")




    def show_feedback():
        clear_content()
        ctk.CTkLabel(content, text="Feedback", font=("Segoe UI", 22, "bold")).pack(pady=20)

        for d in attempt_data.get("details", []):
            frame = ctk.CTkFrame(content, corner_radius=15)
            frame.pack(padx=60, pady=10, fill="x")

            ctk.CTkLabel(frame, text=d["question"], wraplength=700).pack(anchor="w", padx=20, pady=5)
            ctk.CTkLabel(frame, text=f"Your answer: {d['selected']}", text_color="gray").pack(anchor="w", padx=20)
            ctk.CTkLabel(frame, text=f"Correct answer: {d['correct']}", text_color="#4caf50").pack(anchor="w", padx=20)

    # ================= NAV =================
    def nav(text, cmd):
        def guarded():
            # Prevent navigation during quiz
            if quiz_in_progress["active"] and text != "Logout":
                return
            cmd()
        if(text == "Logout"):
            ctk.CTkButton(
            sidebar,
            text=f"{text}",
            width=180,
            height=42,
            corner_radius=12,
            fg_color="#1f1f1f",
            hover_color="#d30303",
            anchor="w",
            command=guarded
            ).pack(pady=8)
        else:
            ctk.CTkButton(
            sidebar,
            text=text,
            width=180,
            height=42,
            corner_radius=12,
            fg_color="#1f1f1f",
            hover_color="#2a2a2a",
            anchor="w",
            command=guarded
            ).pack(pady=8)
    nav("Dashboard", show_dashboard)
    nav("Available Quizzes", show_quizzes)
    nav("My Results", show_results)
    nav("Analytics", analytics)

    nav("Feedback", show_feedback)
    nav("Logout", logout)

    show_dashboard()
