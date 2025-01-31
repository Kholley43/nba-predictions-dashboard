import sqlite3
import pandas as pd

def save_prediction(prediction):
    conn = sqlite3.connect('predictions.db')
    data = pd.DataFrame([{
        'date': prediction['Date'],
        'player': prediction['Player'],
        'market': prediction['Market Name'],
        'line': prediction['Line'],
        'prediction': 'Over',
        'result': 'Pending',
        'hit_rate': prediction['Weighted Hit Rate']
    }])
    data.to_sql('predictions', conn, if_exists='append', index=False)
    conn.close()

conn = sqlite3.connect('predictions.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
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
