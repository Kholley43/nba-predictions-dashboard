import sqlite3

conn = sqlite3.connect('predictions.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE predictions (
        id INTEGER PRIMARY KEY,
        date TEXT,
        player TEXT,
        market TEXT,
        line REAL,
        prediction TEXT,
        result TEXT DEFAULT 'Pending',
        hit_rate REAL
    )
''')
conn.commit()
conn.close()
