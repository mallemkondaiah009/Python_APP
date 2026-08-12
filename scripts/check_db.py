import sqlite3

conn = sqlite3.connect("data.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", tables)

if ("customers",) in tables:
    rows = conn.execute("SELECT * FROM customers").fetchall()
    print("Customer rows:", rows)

conn.close()