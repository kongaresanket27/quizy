
from db.database import validate_user, create_user
from ui.ui_user_dashboard import user_dashboard
import customtkinter as ctk

    

def user_login(root):
    app = ctk.CTkToplevel(root)
    app.title("User Login")
    a_width = app.winfo_screenwidth()
    a_leng = app.winfo_screenheight()
    app.geometry(f"{a_width} x {a_leng}+0+0")
    app.resizable(True, True)
    app.state('zoomed') 

    def login():
        username = entry_user.get()
        password = entry_pass.get()

        user_id = validate_user(username, password)

        if user_id:
            app.destroy()
            user_dashboard(root, user_id)

    def back():
        app.destroy()
        root.deiconify()

    def signup():
        username = entry_user.get()
        password = entry_pass.get()

        if not username or not password:
            return

        create_user(username, password)

    ctk.CTkLabel(app, text="User Login", font=("Segoe UI", 22, "bold")).pack(pady=20)

    entry_user = ctk.CTkEntry(app, placeholder_text="Username", width=260)
    entry_user.pack(pady=10)

    entry_pass = ctk.CTkEntry(app, placeholder_text="Password", show="*", width=260)
    entry_pass.pack(pady=10)

    ctk.CTkButton(app, text="Login", width=200, command=login).pack(pady=15)
    ctk.CTkButton(app, text="Create Account", width=200, command=signup).pack()
    ctk.CTkButton(app, text="Back", width=80, command=back).place(x = 40,y = 30)

