# from ap import open_main
# if i import it here i get the circular error due to importing it here and ap.py also importing this file



##
## there was required change in the question evaluation
##

import customtkinter as ctk
import matplotlib.pyplot as plt
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from db.database import (
    get_admin_kpis,
    get_daily_attempts,
    get_attempts_per_quiz,
    get_avg_score_per_quiz,
    get_unique_users_per_quiz,
    get_all_attempts,
    get_connection,
    get_all_users_admin,
    get_user_profile,
    get_user_attempts,
    create_quiz,
    get_all_quizzes,
    add_question,
    get_questions_by_quiz,
    delete_quiz,
    get_quiz_by_id,
    update_quiz,
    remove_question_from_quiz
)

from ai_gpt_engine import fetch_ai_questions
import requests



from tkinter import messagebox


from datetime import datetime, timedelta


def admin_dashboard(root):
    ctk.set_appearance_mode("dark")

    app = ctk.CTkToplevel(root)
    app.title("Quizy - Admin Dashboard")

    screen_width = app.winfo_screenwidth()
    screen_height = app.winfo_screenheight()
    app.geometry(f"{screen_width}x{screen_height}+0+0")
    app.state("zoomed")
    app.resizable(True, True)

    # ================= SIDEBAR =================
    sidebar = ctk.CTkFrame(app, width=220, corner_radius=0, fg_color="#111111")
    sidebar.pack(side="left", fill="y")

    ctk.CTkLabel(sidebar, text="Quizy", font=("Segoe UI", 22, "bold")).pack(pady=(30, 5))
    ctk.CTkLabel(sidebar, text="Admin Panel", text_color="gray").pack(pady=(0, 30))

    # ================= MAIN CONTENT =================
    content = ctk.CTkFrame(app)
    content.pack(side="left", fill="both", expand=True)

    def clear_content():
        for w in content.winfo_children():
            w.destroy()

    # ===== ADMIN STATS =====
    def get_admin_stats():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM users
            WHERE date(created_at) >= date('now','-7 days')
        """)
        new_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM quiz_attempts")
        total_attempts = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM quiz_attempts
            WHERE date(attempted_at) >= date('now','-7 days')
        """)
        active_users = cur.fetchone()[0]

        conn.close()
        return {
            "total_users": total_users,
            "new_users": new_users,
            "total_attempts": total_attempts,
            "active_users": active_users
        }
    def style_axes(ax):
        ax.set_facecolor("#141414")
        ax.tick_params(colors="#e5e7eb")
        for spine in ax.spines.values():
            spine.set_visible(False)

    # ===== USERS JOINED LAST 7 DAYS =====
    def users_last_7_days():
        conn = get_connection()
        cur = conn.cursor()

        labels, counts = [], []
        for i in range(6, -1, -1):
            day = datetime.now() - timedelta(days=i)
            print(day)
            labels.append(day.strftime("%a"))

            cur.execute(
                "SELECT COUNT(*) FROM users WHERE date(created_at)=date(?)",
                (day.date(),)
            )
            counts.append(cur.fetchone()[0])

        conn.close()
        return labels, counts

    # ===== ATTEMPTS PER QUIZ =====
    def attempts_per_quiz():
        conn = get_connection()
        cur = conn.cursor()

        # JOIN with quizzes table to get titles instead of just IDs
        cur.execute("""
            SELECT q.title, COUNT(qa.id) as attempt_count
            FROM quizzes q
            LEFT JOIN quiz_attempts qa ON q.id = qa.quiz_id
            GROUP BY q.id
            ORDER BY attempt_count DESC
        """)
        data = cur.fetchall()
        conn.close()

        # Returns ([Titles], [Counts])
        # Truncate titles if they are too long for the graph
        titles = [(r[0][:15] + '..') if len(r[0]) > 15 else r[0] for r in data]
        counts = [r[1] for r in data]
        
        return titles, counts

    # ===== ACTIVE VS INACTIVE USERS =====
    def activity_distribution():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM quiz_attempts
            WHERE date(attempted_at) >= date('now','-7 days')
        """)
        active = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        conn.close()
        return ["Active", "Inactive"], [active, total - active]

    # ===== ADMIN DASHBOARD =====
    def show_dashboard():
        clear_content()
        content.configure(fg_color="#0b0b0f")

        ctk.CTkLabel(content,text="Dashboard",font=("Segoe UI", 28, "bold"),text_color="#a78bfa").pack(pady=20)

        stats = get_admin_stats()
        kpi_frame = ctk.CTkFrame(content, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=30)

        def kpi_card(parent, title, value):
            card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=18, width=220, height=120)
            card.pack(side="left", expand=True, padx=12)
            ctk.CTkLabel(card, text=title, text_color="gray").pack(padx =10,pady=(16, 6))
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 24, "bold")).pack(padx = 13,pady =1)

        kpi_card(kpi_frame, "Total Users", stats["total_users"])
        kpi_card(kpi_frame, "New Users (7 Days)", stats["new_users"])
        kpi_card(kpi_frame, "Quiz Attempts", stats["total_attempts"])
        kpi_card(kpi_frame, "Active Users", stats["active_users"])

        grid = ctk.CTkFrame(content, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=30, pady=30)
        grid.columnconfigure((0, 1), weight=1)
        grid.rowconfigure((0, 1), weight=1)

        def graph_card(parent, title):
            card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=18)
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 16, "bold"),
                         text_color="#22d3ee").pack(anchor="w", padx=20, pady=(15, 5))
            return card

        # ===== GRAPH 1 =====
        g1 = graph_card(grid, "Users Joined (Last 7 Days)")
        g1.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        d, u = users_last_7_days()
        fig1 = Figure(figsize=(4, 3), facecolor="#141414")
        ax1 = fig1.add_subplot(111)
        ax1.plot(d, u, marker="o", color="#38bdf8", linewidth=2)
        ax1.set_title("New Users", color="#e5e7eb")
        style_axes(ax1)
        ax1.grid(color="#1f2937", linestyle="--", alpha=0.5)


        FigureCanvasTkAgg(fig1, g1).get_tk_widget().pack(fill="both", expand=True)

        # ===== GRAPH 2 (POPULARITY) =====
        g2 = graph_card(grid, "Quiz Popularity (Total Attempts)")
        g2.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)

        titles, counts = attempts_per_quiz()
        quiz_count = len(titles)

        # Import Figure if not already done: from matplotlib.figure import Figure
        fig2 = Figure(figsize=(max(4, quiz_count * 0.8), 3), facecolor="#141414")
        ax2 = fig2.add_subplot(111)

        # Use the lists directly in ax.bar for simpler code
        ax2.bar(titles, counts, color="#38bdf8", width=0.6)

        # Improve label readability
        ax2.tick_params(axis='x', colors="#e5e7eb", labelsize=9) #rotation = 45 ,if needed for xticks
        ax2.tick_params(axis='y', colors="#e5e7eb")
        ax2.set_ylabel("Attempts", color="#94a3b8", fontfamily="Segoe UI")
        ax2.set_facecolor("#141414")

        # Remove top and right spines for a modern look
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color('#1f2937')
        ax2.spines['bottom'].set_color('#1f2937')

        ax2.grid(axis="y", color="#1f2937", linestyle="--", alpha=0.3)
        fig2.tight_layout()

        canvas2 = FigureCanvasTkAgg(fig2, g2)
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)


        # ===== GRAPH 3 =====
        g3 = graph_card(grid, "User Activity Distribution")
        g3.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        labels, sizes = activity_distribution()
        fig3 = Figure(figsize=(4, 3), facecolor="#141414")
        ax3 = fig3.add_subplot(111)
        ax3.pie(sizes, labels=labels, autopct="%1.1f%%", textprops={"color": "#e5e7eb"})

        FigureCanvasTkAgg(fig3, g3).get_tk_widget().pack(fill="both", expand=True)

        # =====================================================
        # 4️⃣ UNIQUE USER PARTICIPATION (Beautified Line Graph)
        # =====================================================
        g4 = graph_card(grid, "Unique Student Reach")
        g4.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)

        u_titles, u_counts = get_unique_users_per_quiz()
        
        # Create Figure with modern dark theme
        fig4 = Figure(figsize=(5, 3), facecolor="#141414")
        ax4 = fig4.add_subplot(111)

        # Plotting the Line
        ax4.plot(u_titles, u_counts, color="#4654c3", linewidth=3, 
                 marker='o', markersize=8, markerfacecolor="#2E3131", 
                 markeredgewidth=2, markeredgecolor="#585858F4", label="Unique Users")

        # Fill the area under the line for a modern 'Area Chart' look
        ax4.fill_between(u_titles, u_counts, color="#f472b6", alpha=0.1)

        # Beautification & Styling
        ax4.set_facecolor("#141414")
        ax4.tick_params(axis='x', colors="#e5e7eb", labelsize=8)
        ax4.tick_params(axis='y', colors="#e5e7eb")
        
        # Grid and Spines
        ax4.grid(color="#1f2937", linestyle="--", alpha=0.3)
        for spine in ax4.spines.values():
            spine.set_visible(False)
        
        # Adding a subtle bottom border
        ax4.spines['bottom'].set_visible(True)
        ax4.spines['bottom'].set_color('#1f2937')

        fig4.tight_layout()

        # Render to Canvas
        canvas4 = FigureCanvasTkAgg(fig4, g4)
        canvas4.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
    # ================= RESULTS =================
    def open_user_profile(user_id):
        clear_content()
        con = ctk.CTkScrollableFrame(content)
        content.configure(fg_color="#0b0b0f")
        con.pack(side="left", fill="both", expand=True)
        user = get_user_profile(user_id)
        if not user:
            ctk.CTkLabel(
                con,
                text="User not found",
                font=("Segoe UI", 20, "bold"),
                text_color="red"
            ).pack(pady=40)
            return

        attempts = get_user_attempts(user_id)

        # ===== HEADER =====
        ctk.CTkLabel(
            con,
            text=f"👤 {user['username']} – Profile Analytics",
            font=("Segoe UI", 26, "bold"),
            text_color="#a78bfa"
        ).pack(pady=20)

        # ===== SUMMARY CARD =====
        summary = ctk.CTkFrame(
            con,
            fg_color="#141414",
            corner_radius=18
        )
        summary.pack(fill="x", padx=60, pady=10)

        ctk.CTkLabel(
            summary,
            text=f"Joined: {user['joined']}"
        ).pack(anchor="w", padx=20, pady=6)

        ctk.CTkLabel(
            summary,
            text=f"Total Attempts: {user['attempts']}"
        ).pack(anchor="w", padx=20, pady=6)

        ctk.CTkLabel(
            summary,
            text=f"Average Score: {user['avg_score']}"
        ).pack(anchor="w", padx=20, pady=6)

        ctk.CTkLabel(
            summary,
            text=f"Last Active: {user['last_active'] or '—'}"
        ).pack(anchor="w", padx=20, pady=6)

        # ===== ATTEMPTS LIST =====
        ctk.CTkLabel(
            con,
            text="📄 Quiz Attempts",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(30, 10))

        if not attempts:
            ctk.CTkLabel(
                con,
                text="No attempts yet",
                text_color="gray"
            ).pack(pady=20)
            return

        for quiz_id, score, total, attempted_at in attempts:
            row = ctk.CTkFrame(
                con,
                fg_color="#101010",
                corner_radius=12
            )
            row.pack(fill="x", padx=80, pady=6)

            ctk.CTkLabel(
                row,
                text=f"{quiz_id}  |  Score: {score}/{total}  |  {attempted_at}"
            ).pack(anchor="w", padx=20, pady=10)



    def show_users():
        clear_content()
        con = ctk.CTkScrollableFrame(content)
        con.pack(side="left", fill="both", expand=True)
        content.configure(fg_color="#0b0b0f")

        ctk.CTkLabel(
            con,
            text="👥 User Management & Rankings",
            font=("Segoe UI", 26, "bold"),
            text_color="#a78bfa"
        ).pack(pady=20)

        users = get_all_users_admin()

        if not users:
            ctk.CTkLabel(con, text="No users found", text_color="gray").pack(pady=20)
            return

        for u in users:
            # Now unpacking 6 values including the rank
            user_id, username, joined, attempts, last_active, rank = u

            card = ctk.CTkFrame(con, fg_color="#141414", corner_radius=16)
            card.pack(fill="x", padx=60, pady=8)

            # 🏆 Rank Badge (Displayed on the right side of the card)
            rank_label = ctk.CTkLabel(
                card,
                text=f"Rank #{rank}",
                font=("Segoe UI", 18, "bold"),
                text_color="#38bdf8"
            )
            rank_label.pack(side="right", padx=30)

            # 👤 Username + ID
            ctk.CTkLabel(
                card,
                text=f"{username}  (ID: {user_id})",
                font=("Segoe UI", 16, "bold")
            ).pack(anchor="w", padx=20, pady=(10, 0))

            ctk.CTkLabel(
                card,
                text=f"Joined: {joined}",
                text_color="gray",
                font=("Segoe UI", 12)
            ).pack(anchor="w", padx=20)

            ctk.CTkLabel(
                card,
                text=f"Attempts: {attempts} | Last Active: {last_active or '—'}",
                font=("Segoe UI", 13)
            ).pack(anchor="w", padx=20, pady=(0, 10))

            # Re-apply click binding for the new rank label and card
            for widget in card.winfo_children():
                widget.bind("<Button-1>", lambda e, uid=user_id: open_user_profile(uid))
            card.bind("<Button-1>", lambda e, uid=user_id: open_user_profile(uid))
                    
    # ----------- manage question ------------------
    import threading
    def manage():
        clear_content()
        content.configure(fg_color="#0b0b0f")

        ctk.CTkLabel(
            content,
            text="Manage Questions",
            font=("Segoe UI", 26, "bold"),
            text_color="#a78bfa"
        ).pack(pady=30)

        # --- Section Cards ---
        grid = ctk.CTkFrame(content, fg_color="transparent")
        grid.pack()

        def section_card(parent, title, command):
            card = ctk.CTkFrame(parent, fg_color="#141414",
                                corner_radius=20, width=280, height=160)
            card.pack(side="left", padx=20)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=title,
                        font=("Segoe UI", 16, "bold")).pack(pady=25)

            ctk.CTkButton(card, text="Open", command=command).pack()

        section_card(grid, "Create Quiz", show_create_quiz)
        section_card(grid, "Manage Existing", show_manage_existing)

        # --- AI Question Generator ---
        ai_card = ctk.CTkFrame(content, fg_color="#141414", corner_radius=18)
        ai_card.pack(fill="x", padx=80, pady=40)

        ctk.CTkLabel(
            ai_card,
            text="✨ AI Question Generator",
            font=("Segoe UI", 18, "bold"),
            text_color="#22d3ee"
        ).pack(anchor="w", padx=25, pady=(20, 10))

        quizzes = get_all_quizzes()

        if not quizzes:
            ctk.CTkLabel(
                ai_card,
                text="No quizzes available. Create one first.",
                text_color="red"
            ).pack(pady=20)
            return

        # quiz_id is index 0, title is 1, subject is 2
        quiz_map = {q[1]: (q[0], q[2]) for q in quizzes}
        quiz_titles = list(quiz_map.keys())

        input_row = ctk.CTkFrame(ai_card, fg_color="transparent")
        input_row.pack(fill="x", padx=25, pady=15)

        input_row.columnconfigure(0, weight=1)
        input_row.columnconfigure(1, weight=2)
        input_row.columnconfigure(2, weight=0)

        quiz_var = tk.StringVar(value=quiz_titles[0])

        quiz_dropdown = ctk.CTkOptionMenu(
            input_row,
            values=quiz_titles,
            variable=quiz_var,
            width=200
        )
        quiz_dropdown.grid(row=0, column=0, sticky="ew", padx=(0, 15))

        prompt_input = ctk.CTkEntry(
            input_row,
            placeholder_text="Generate 5 medium-level Python questions",
            height=40
        )
        prompt_input.grid(row=0, column=1, sticky="ew", padx=(0, 15))

        def handle_ai():
            prompt_text = prompt_input.get().strip()
            selected_quiz = quiz_var.get()

            if not prompt_text:
                messagebox.showwarning("Input Required", "Please enter a prompt.")
                return

            quiz_id, subject = quiz_map[selected_quiz]
            generate_btn.configure(state="disabled", text="Generating...")

            def run_ai():
                success = fetch_ai_questions(
                    prompt=prompt_text,
                    quiz_id=quiz_id,
                    subject=subject,
                    add_question_func=add_question
                )

                def update_ui():
                    generate_btn.configure(state="normal", text="Generate")
                    if success:
                        messagebox.showinfo("Success", f"Questions added to '{selected_quiz}'")
                        prompt_input.delete(0, "end")
                    else:
                        messagebox.showerror("Error", "AI generation failed. Check API key/Console.")

                app.after(0, update_ui)

            threading.Thread(target=run_ai, daemon=True).start()

        generate_btn = ctk.CTkButton(
            input_row,
            text="Generate",
            width=120,
            height=40,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=handle_ai
        )
        generate_btn.grid(row=0, column=2)

        ctk.CTkLabel(
            ai_card,
            text="Tip: Mention difficulty or topic in the prompt.",
            text_color="gray",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=25, pady=(0, 20))
    def show_create_quiz():
        clear_content()

        ctk.CTkLabel(
            content,
            text="Create Quiz",
            font=("Segoe UI", 24, "bold")
        ).pack(pady=30)

        title_entry = ctk.CTkEntry(
            content,
            width=350,
            placeholder_text="Enter Quiz Title"
        )
        title_entry.pack(pady=10)

        subject_entry = ctk.CTkEntry(
            content,
            width=350,
            placeholder_text="Enter Subject"
        )
        subject_entry.pack(pady=10)

        def create():
            title = title_entry.get()
            subject = subject_entry.get()

            if not title or not subject:
                messagebox.showerror("Error", "All fields required")
                return

            create_quiz(title, subject)
            messagebox.showinfo("Success", "Quiz Created Successfully")
            manage()

        ctk.CTkButton(
            content,
            text="Create Quiz",
            command=create,
            width=200
        ).pack(pady=20)

        ctk.CTkButton(
            content,
            text="⬅ Back",
            command=manage,
            fg_color="gray"
        ).pack(pady=10)
        

    def show_manage_existing():
        clear_content()

        ctk.CTkLabel(
            content,
            text="Existing Quizzes",
            font=("Segoe UI", 24, "bold")
        ).pack(pady=20)

        scroll = ctk.CTkScrollableFrame(content)
        scroll.pack(fill="both", expand=True, padx=40, pady=20)

        quizzes = get_all_quizzes()

        if not quizzes:
            ctk.CTkLabel(scroll, text="No Quiz Available").pack(pady=20)
            return

        for quiz in quizzes:
            quiz_id = quiz[0]
            title = quiz[1]
            subject = quiz[2]

            card = ctk.CTkFrame(
                scroll,
                fg_color="#141414",
                corner_radius=15
            )
            card.pack(fill="x", pady=10)

            ctk.CTkLabel(
                card,
                text=f"{title} ({subject})",
                font=("Segoe UI", 16, "bold")
            ).pack(anchor="w", padx=20, pady=5)

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(anchor="e", padx=20, pady=10)

            ctk.CTkButton(
                btn_frame,
                text="View Questions",
                command=lambda q=quiz_id: open_quiz_screen(q)
            ).pack(side="left", padx=5)

            ctk.CTkButton(
                btn_frame,
                text="Delete",
                fg_color="red",
                command=lambda q=quiz_id: delete_quiz(q)
            ).pack(side="left", padx=5)

        ctk.CTkButton(
            content,
            text="⬅ Back",
            command=manage,
            fg_color="gray"
        ).pack(pady=10)

    def refresh_manage_quiz_table(frame, parent_screen):
        for widget in frame.winfo_children():
            widget.destroy()

        quizzes = get_all_quizzes()

        for i, quiz in enumerate(quizzes):

            quiz_id = quiz[0]

            row_frame = ctk.CTkFrame(frame)
            row_frame.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(row_frame, text=f"ID: {quiz[0]}", width=80).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=quiz[1], width=200).pack(side="left", padx=5)
            ctk.CTkLabel(row_frame, text=quiz[2], width=150).pack(side="left", padx=5)

            ctk.CTkButton(row_frame, text="Open",
                        width=80,
                        command=lambda q=quiz_id: open_quiz_screen(q)
                        ).pack(side="right", padx=5)

            ctk.CTkButton(row_frame, text="Delete",
                        width=80,
                        fg_color="red",
                        command=lambda q=quiz_id: delete_quiz_action(frame, parent_screen, q)
                        ).pack(side="right", padx=5)

            ctk.CTkButton(row_frame, text="Edit",
                        width=80,
                        command=lambda q=quiz_id: edit_quiz_screen(parent_screen, q)
                        ).pack(side="right", padx=5)

    def delete_quiz_action(frame, parent, quiz_id):

        confirm = messagebox.askyesno("Confirm", "Delete this quiz?")
        if confirm:
            delete_quiz(quiz_id)
            messagebox.showinfo("Deleted", "Quiz deleted successfully")
            refresh_manage_quiz_table(frame, parent)

    def edit_quiz_screen(root, quiz_id):

        quiz = get_quiz_by_id(quiz_id)

        screen = ctk.CTkToplevel(root)
        screen.title("Edit Quiz")
        screen.geometry("400x350")

        ctk.CTkLabel(screen, text="Edit Quiz",
                    font=ctk.CTkFont(size=20, weight="bold")
                    ).pack(pady=20)

        title_entry = ctk.CTkEntry(screen, width=250)
        title_entry.pack(pady=10)
        title_entry.insert(0, quiz[1])

        subject_entry = ctk.CTkEntry(screen, width=250)
        subject_entry.pack(pady=10)
        subject_entry.insert(0, quiz[2])

        def update_action():
            update_quiz(quiz_id, title_entry.get(), subject_entry.get())
            messagebox.showinfo("Success", "Quiz Updated")
            screen.destroy()

        ctk.CTkButton(screen, text="Update", command=update_action).pack(pady=20)

    def open_quiz_screen(quiz_id):

        clear_content()
        content.configure(fg_color="#0b0b0f")

        container = ctk.CTkFrame(content)
        container.pack(fill="both", expand=True)

        # Back Button
        ctk.CTkButton(
            container,
            text="← Back",
            command=show_manage_existing
        ).pack(anchor="w", padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text="Questions in Quiz",
            font=("Segoe UI", 24, "bold"),
            text_color="#a78bfa"
        ).pack(pady=10)

        # ✅ ADD QUESTION BUTTON (Always Visible)
        ctk.CTkButton(
            container,
            text="+ Add Question",
            fg_color="#22c55e",
            command=lambda qid=quiz_id: add_question_screen(qid)
        ).pack(pady=10)

        questions_frame = ctk.CTkScrollableFrame(container)
        questions_frame.pack(fill="both", expand=True, padx=40, pady=20)

        questions = get_questions_by_quiz(quiz_id)

        if not questions:
            ctk.CTkLabel(
                questions_frame,
                text="No questions added to this quiz yet.",
                text_color="gray"
            ).pack(pady=20)

        else:
            for q in questions:

                row = ctk.CTkFrame(
                    questions_frame,
                    fg_color="#141414",
                    corner_radius=10
                )
                row.pack(fill="x", pady=8, padx=10)

                ctk.CTkLabel(
                    row,
                    text=f"ID: {q[0]}",
                    width=80
                ).pack(side="left", padx=10)

                ctk.CTkLabel(
                    row,
                    text=q[1],
                    wraplength=700,
                    justify="left"
                ).pack(side="left", padx=10)

                ctk.CTkButton(
                    row,
                    text="Remove",
                    fg_color="red",
                    width=80,
                    command=lambda question_id=q[0]:
                        remove_question_action(quiz_id, question_id)
                ).pack(side="right", padx=10)

    def add_question_screen(quiz_id):

        clear_content()
        content.configure(fg_color="#0b0b0f")

        container = ctk.CTkFrame(content)
        container.pack(fill="both", expand=True)

        ctk.CTkButton(
            container,
            text="← Back",
            command=lambda: open_quiz_screen(quiz_id)
        ).pack(anchor="w", padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text="Add Question",
            font=("Segoe UI", 24, "bold"),
            text_color="#a78bfa"
        ).pack(pady=10)

        form = ctk.CTkScrollableFrame(container)
        form.pack(fill="both", expand=True, padx=40, pady=20)

        # Question
        question_box = ctk.CTkTextbox(form, width=800, height=120)
        question_box.pack(pady=10)

        # Options
        option_a = ctk.CTkEntry(form, placeholder_text="Option A", width=600)
        option_a.pack(pady=5)

        option_b = ctk.CTkEntry(form, placeholder_text="Option B", width=600)
        option_b.pack(pady=5)

        option_c = ctk.CTkEntry(form, placeholder_text="Option C", width=600)
        option_c.pack(pady=5)

        option_d = ctk.CTkEntry(form, placeholder_text="Option D", width=600)
        option_d.pack(pady=5)

        correct_option = ctk.CTkOptionMenu(form, values=["A", "B", "C", "D"])
        correct_option.pack(pady=10)

        subject_entry = ctk.CTkEntry(form, placeholder_text="Subject", width=400)
        subject_entry.pack(pady=5)

        difficulty_menu = ctk.CTkOptionMenu(
            form,
            values=["Easy", "Medium", "Hard"]
        )
        difficulty_menu.pack(pady=5)

        def save_question():
            q = question_box.get("1.0", "end").strip()
            a = option_a.get().strip()
            b = option_b.get().strip()
            c = option_c.get().strip()
            d = option_d.get().strip()
            correct = correct_option.get()
            if(correct == "A"):
                correct = a
            elif(correct == "B"):
                correct = b
            elif(correct == "C"):
                correct = c
            elif(correct == "D"):
                correct = d

            subject = subject_entry.get().strip()
            difficulty = difficulty_menu.get()

            if not all([q, a, b, c, d, subject]):
                messagebox.showerror("Error", "All fields required")
                return

            # IMPORTANT → must pass quiz_id
            add_question(
                quiz_id,
                q, a, b, c, d,
                correct,
                subject,
                difficulty
            )

            messagebox.showinfo("Success", "Question Added")
            open_quiz_screen(quiz_id)

        ctk.CTkButton(
            form,
            text="Save Question",
            fg_color="#22c55e",
            command=save_question
        ).pack(pady=20)

    

    def remove_question_action(quiz_id, question_id):

        remove_question_from_quiz(quiz_id, question_id)
        messagebox.showinfo("Removed", "Question removed")
        open_quiz_screen(quiz_id)


    def view_all_quiz_screen():
        clear_content()
        content.configure(fg_color="#0b0b0f")

        container = ctk.CTkFrame(content)
        container.pack(fill="both", expand=True)

        ctk.CTkLabel(
            container,
            text="📚 All Available Quizzes",
            font=("Segoe UI", 26, "bold"),
            text_color="#a78bfa"
        ).pack(pady=30)

        quiz_frame = ctk.CTkScrollableFrame(container)
        quiz_frame.pack(fill="both", expand=True, padx=40, pady=20)

        quizzes = get_all_quizzes()

        if not quizzes:
            ctk.CTkLabel(
                quiz_frame,
                text="No quizzes available.",
                text_color="gray"
            ).pack(pady=20)
            return

        for quiz in quizzes:
            quiz_id = quiz[0]
            title = quiz[1]
            subject = quiz[2]

            card = ctk.CTkScrollableFrame(quiz_frame, fg_color="#141414", corner_radius=15)
            card.pack(fill="x", pady=10, padx=20)

            ctk.CTkLabel(
                card,
                text=f"{title} ({subject})",
                font=("Segoe UI", 18, "bold")
            ).pack(anchor="w", padx=20, pady=10)

            ctk.CTkButton(
                card,
                text="View Questions",
                fg_color="#0ea5e9",
                command=lambda qid=quiz_id, t=title: view_single_quiz_screen(qid, t)
            ).pack(anchor="e", padx=20, pady=10)

    def view_single_quiz_screen(quiz_id, title):
        clear_content()
        content.configure(fg_color="#0b0b0f")

        container = ctk.CTkFrame(content)
        container.pack(fill="both", expand=True)

        ctk.CTkButton(
            container,
            text="← Back",
            command=view_all_quiz_screen
        ).pack(anchor="w", padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text=f"{title} - Questions",
            font=("Segoe UI", 24, "bold"),
            text_color="#a78bfa"
        ).pack(pady=20)

        question_frame = ctk.CTkScrollableFrame(container)
        question_frame.pack(fill="both", expand=True, padx=40, pady=20)

        questions = get_questions_by_quiz(quiz_id)

        if not questions:
            ctk.CTkLabel(
                question_frame,
                text="No questions added to this quiz yet.",
                text_color="gray"
            ).pack(pady=20)
            return

        for index, q in enumerate(questions, start=1):
            question_text = q[1]  # because q is tuple

            card = ctk.CTkFrame(question_frame, fg_color="#141414", corner_radius=15)
            card.pack(fill="x", pady=10, padx=10)

            ctk.CTkLabel(
                card,
                text=f"{index}. {question_text}",
                wraplength=900,
                justify="left"
            ).pack(anchor="w", padx=20, pady=15)


    # ================= RESULTS =================


    def show_results():
        clear_content()
        con = ctk.CTkScrollableFrame(content)
        con.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(con, text="Results", font=("Segoe UI", 22, "bold")).pack(pady=20)

        attempts = get_all_attempts()
        if not attempts:
            ctk.CTkLabel(con, text="No quiz attempts yet.", text_color="gray").pack(pady=20)
            return

        for u, q, s, t, d in attempts:
            card = ctk.CTkFrame(
                con,
                fg_color="#141414",
                corner_radius=15,
                border_width=1,
                border_color="#000000"
            )
            card.pack(padx=60, pady=10, fill="both")

            ctk.CTkLabel(card, text=f"User: {u}", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20)
            ctk.CTkLabel(card, text=f"Quiz: {q} | Score: {s}/{t}").pack(anchor="w", padx=20)
            ctk.CTkLabel(card, text=f"Attempted on: {d}", text_color="gray").pack(anchor="w", padx=20)


   

    # ui_admin_dashboard.py

    def show_ml():
        from ai_gpt_engine import get_platform_growth_predictions,get_user_performance_predictions
        clear_content()
        content.configure(fg_color="#0b0b0f")
        
        scroll = ctk.CTkScrollableFrame(content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=30, pady=20)

        # 1. FETCH DATA FROM THE TWO FUNCTIONS
        platform_stats = get_platform_growth_predictions(get_connection, get_daily_attempts)
        user_preds = get_user_performance_predictions(get_all_users_admin, get_user_attempts)

        # Header
        ctk.CTkLabel(scroll, text="🤖 ML Insights & Predictions", font=("Segoe UI", 28, "bold"), text_color="#22d3ee").pack(pady=10)

        # --- TOP CARDS (Using platform_stats) ---
        top_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        top_frame.pack(fill="x", pady=20)

        def info_card(parent, title, value, detail, color):
            card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=15, border_width=1, border_color="#333")
            card.pack(side="left", expand=True, padx=10, fill="both")
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 12), text_color="gray").pack(pady=(15, 0))
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 36, "bold"), text_color=color).pack()
            ctk.CTkLabel(card, text=detail, font=("Segoe UI", 12, "italic")).pack(pady=(0, 15))

        info_card(top_frame, "USER ACQUISITION", f"+{platform_stats['predicted_new_users']}", "Expected joins (7 days)", "#38bdf8")
        info_card(top_frame, "ENGAGEMENT FORECAST", f"{platform_stats['predicted_attempts']}", "Expected attempts (7 days)", "#c084fc")

        # --- USER REPORT (Using user_preds) ---
        ctk.CTkLabel(scroll, text="Student Performance Forecast", font=("Segoe UI", 18, "bold")).pack(pady=(20, 10), anchor="w")

        for item in user_preds:
            card = ctk.CTkFrame(scroll, fg_color="#1a1a1e", corner_radius=10)
            card.pack(fill="x", pady=5)
            
            color_map = {"Excellent": "#4caf50", "Average": "#fbbf24", "At Risk": "#f43f5e", "New User": "#9ca3af"}
            status_color = color_map.get(item['status'], "#e5e7eb")

            # Left: Info
            info_grp = ctk.CTkFrame(card, fg_color="transparent")
            info_grp.pack(side="left", padx=20, pady=10)
            ctk.CTkLabel(info_grp, text=item['user'], font=("Segoe UI", 16, "bold")).pack(anchor="w")
            ctk.CTkLabel(info_grp, text=item['desc'], font=("Segoe UI", 12), text_color="gray").pack(anchor="w")

            # Right: Probability
            badge_val = f"{item['pred']}%" if isinstance(item['pred'], int) else item['pred']
            ctk.CTkLabel(card, text=item['status'].upper(), text_color=status_color, font=("Segoe UI", 11, "bold")).pack(side="right", padx=20)
            ctk.CTkLabel(card, text=badge_val, font=("Segoe UI", 20, "bold"), text_color=status_color).pack(side="right", padx=10)

    def nav_btn(text, cmd):
        return ctk.CTkButton(
            sidebar, text=text, width=180, height=42,
            corner_radius=12, fg_color="#1f1f1f",
            hover_color="#3510c9", anchor="w", command=cmd
        )

    nav_btn("Dashboard", show_dashboard).pack(pady=8)
    nav_btn("User Details", show_users).pack(pady=8)
    nav_btn("Manage Questions", manage).pack(pady=8)
    nav_btn("Result", show_results).pack(pady=8)
    nav_btn("ML Insights", show_ml).pack(pady=8)

    def logout():
        app.destroy()
        root.deiconify()

    nav_btn("Logout", logout).pack(side="bottom", pady=20)

    show_dashboard()

    # to call any function write  funct()
    # kongaresanket@gmail.com
    # to import the fuction from file to  your current file , importing may give you error so use like this
    # def logout():
    #     from ap import open_main
    #     open_main()
    # import within fuction if you want to avoid circular import error,circular import error occurs when two files import each other directly or indirectly

    # app.mainloop()  # this isnot require due to app = ctk.CTkToplevel()
