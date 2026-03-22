from db.database import get_connection, hash_password

# 1. Hash the password once outside the loop
new_password_hash = hash_password("user@123")

a = get_connection()
c = a.cursor()

# 2. Use parameterized queries for security and speed
for i in range(50):
    user_id = i + 5
    # Using '?' as a placeholder (standard for sqlite3)
    # If using MySQL/PostgreSQL, you might use '%s'
    c.execute("UPDATE users SET password = ? WHERE id = ?", (new_password_hash, user_id))

a.commit()
a.close()
