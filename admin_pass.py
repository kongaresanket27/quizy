from db.database import get_connection, hash_password

conn = get_connection()
cur = conn.cursor()

cur.execute(
    "INSERT INTO admins (username, password) VALUES (?, ?)",
    ("kongaresanket@gmail.com", hash_password("sanket@2006"))
)

conn.commit()
conn.close()

#############  to update the password and username of admin ############

## also you can use it in admin dashboard to manupulate the user information 

## run these to update admin
# conn = get_connection()
# cur = conn.cursor()

# cur.execute(
#     "UPDATE admins SET password=? WHERE username=?",
#     (hash_password("sanket@2006"),"kongaresanket@gmail.com")
# )

# conn.commit()
# conn.close()
