import sqlite3

DB_NAME = "data.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # جدول گزارش (تمام دیتا)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rsi_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        timeframe TEXT,
        price REAL,
        rsi REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # جدول لحظه‌ای (فقط آخرین RSIها برای هر نماد و تایم‌فریم)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_info (
        symbol TEXT PRIMARY KEY,
        rsi_1m REAL,
        rsi_5m REAL,
        rsi_15m REAL,
        rsi_1h REAL,
        rsi_4h REAL,
        price REAL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("✅ Tables created successfully")