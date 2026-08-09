import sqlite3

conn = sqlite3.connect("playlist_assistant.db")

tables = conn.execute("""
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name
""").fetchall()

print("Tabellen:")
for table in tables:
    print("-", table[0])

print("\nSpalten:")
for table in tables:
    name = table[0]
    print(f"\n{name}")
    for col in conn.execute(f"PRAGMA table_info({name})"):
        print(col)

conn.close()