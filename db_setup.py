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

    
    # جدول ارزها (دینامیک)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            base_symbol TEXT NOT NULL,
            future_symbol TEXT,
            spot_symbol TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_symbol TEXT NOT NULL UNIQUE,  -- مثل BTC
        name TEXT,                         -- مثل Bitcoin
        active INTEGER DEFAULT 1,          -- 1=فعال  0=غیرفعال
        spot_symbol TEXT,                  -- نماد اسپات مثل BTCUSDT
        future_symbol TEXT,                -- نماد فیوچر مثل BTCUSDT.P
        
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # بررسی وجود ستون price_change قبل از اضافه کردن
    cursor.execute("PRAGMA table_info(market_info)")
    columns = [col[1] for col in cursor.fetchall()]
    if "price_change" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN price_change REAL DEFAULT 0")

    cursor.execute("SELECT COUNT(*) FROM symbols")
    count = cursor.fetchone()[0]

    if count == 0:
        print("🔹 crypto symbol table is empty . inserting some symbols...")
        default_symbols = [
            ("BTC", "Bitcoin", 1, "BTC/USDT", "BTC/USDT:USDT	"),
            ("ETH", "Ethereum", 1, "ETH/USDT", "ETH/USDT:USDT"),
            ("BNB", "Binance Coin", 1, "BNB/USDT", "BNB/USDT:USDT"),
            ("SOL", "Solana", 1, "SOL/USDT", "SOL/USDT:USDT"),
            ("ADA", "Cardano", 1, "ADA/USDT", "ADA/USDT:USDT"),
            ("AVAX", "Avalanche", 1, "AVAX/USDT", "AVAX/USDT:USDT"),
            ("LINK", "Chainlink", 1, "LINK/USDT", "LINK/USDT:USDT"),
        ]

        cursor.executemany("""
            INSERT INTO symbols (base_symbol, name, active, spot_symbol, future_symbol)
            VALUES (?, ?, ?, ?, ?)
        """, default_symbols)


    conn.commit()

    conn.close()

if __name__ == "__main__":
    create_tables()
    print("✅ Tables created successfully")