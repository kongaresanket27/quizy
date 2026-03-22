
import customtkinter as ctk
from db.database import init_db

from ui.ui_admin_dashboard import admin_dashboard
from ui.user_login import user_login

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# One CTk() → main window

# Dashboards & login → CTkToplevel(root)

# Logout destroys only the child

# Main window is restored using root.deiconify()


app = ctk.CTk()
app.title("Quizy")
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Set Toplevel size to full screen

app.geometry(f"{screen_width}x{screen_height}+0+0")
# app.geometry("1920x1080")
app.state('zoomed')  # Windows only

app.resizable(True, True)

# def open_admin():
#     app.withdraw()              # hide main window
#     admin_dashboard(app)        # pass root

from ui.admin_login import admin_login

def open_admin():
    app.withdraw()
    admin_login(app)


def open_user():
    app.withdraw()
    user_login(app)


# UI 

ctk.CTkLabel(
    app,
    text="Quizy",
    font=("Segoe UI", 32, "bold")
).pack(pady=(30, 5))

ctk.CTkLabel(
    app,
    text="Quiz Conduction System",
    font=("Segoe UI", 14)
).pack(pady=(0, 25))

card = ctk.CTkFrame(app, corner_radius=25)
card.pack(padx=60, pady=20, fill="both", expand=True)

ctk.CTkLabel(
    card,
    text="Select Your Role",
    font=("Segoe UI", 16, "bold")
).pack(pady=30)

ctk.CTkButton(
    card,
    text="Admin Dashboard",
    width=240,
    height=48,
    corner_radius=20,
    font=("Segoe UI", 14),
    command=open_admin
).pack(pady=15)

ctk.CTkButton(
    card,
    text="User Dashboard",
    width=240,
    height=48,
    corner_radius=20,
    font=("Segoe UI", 14),
    command=open_user
).pack(pady=10)


clo = ctk.CTkFrame(app,width=60,height=30,corner_radius=10,fg_color="#1c1c1e")
clo.pack(side = "left")
ctk.CTkButton(clo,text="CLOSE APP",width=30,height=30,corner_radius=10,fg_color="#2c2c2e",hover_color="#ff453a",command=app.destroy).pack()
######################### for glowing the button after the touch use hover_color="#ff453a"
# ONE MAINLOOP ONLY



init_db()

app.mainloop()
