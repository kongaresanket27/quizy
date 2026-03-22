from db.database import get_connection, hash_password

con = get_connection()
cur = con.cursor()

cur.execute(
    "UPDATE users SET password=? WHERE id=?",
    (hash_password("12345678"), 3)### id = 3
)

con.commit()
con.close()