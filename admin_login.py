import customtkinter as ctk
from referencing import Anchor
from db.database import validate_admin
from ui.ui_admin_dashboard import admin_dashboard


def admin_login(root):
    app = ctk.CTkToplevel(root)
    app.title("Admin Login")

    screen_width = app.winfo_screenwidth()
    screen_height = app.winfo_screenheight()

# Set Toplevel size to full screen
    app.geometry(f"{screen_width}x{screen_height}+0+0")
# app.geometry("1920x1080")
    app.state('zoomed')  # Windows only

    app.resizable(True, True)

    # ---------------- LOGIN LOGIC ----------------
    def login():
        username = entry_user.get()     # for taking input as username
        password = entry_pass.get()

        admin_id = validate_admin(username, password)
        if admin_id:
            app.destroy()
            admin_dashboard(root)
        else:
            status.configure(text="Invalid admin credentials", text_color="red")

    # ---------------- UI ----------------
    ctk.CTkLabel(
        app, text="Admin Login",
        font=("Segoe UI", 22, "bold")
    ).pack(pady=25)

    entry_user = ctk.CTkEntry(
        app, placeholder_text="Admin Username", width=260
    )
    entry_user.pack(pady=10)

    entry_pass = ctk.CTkEntry(
        app, placeholder_text="Password", show="*", width=260
    )
    entry_pass.pack(pady=10)

    ctk.CTkButton(
        app, text="Login", width=200,
        command=login
    ).pack(pady=20)

    status = ctk.CTkLabel(app, text="")
    status.pack()
    def back():
        app.destroy()
        root.deiconify()##########
   

    ctk.CTkButton(app,text = "Back",hover_color="#f38472",command=back).place(x = 40,y =30)
