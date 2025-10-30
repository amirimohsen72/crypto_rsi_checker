import sqlite3

DB_NAME = "data.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # جدول گزارش (تمام دیتا)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rsi_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER NOT NULL,
        timeframe TEXT,
        price REAL,
        rsi REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol_id) REFERENCES symbols(id)

    )
    """)

    # جدول لحظه‌ای (فقط آخرین RSIها برای هر نماد و تایم‌فریم)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_info (
        symbol_id INTEGER PRIMARY KEY,
        rsi_1m REAL,
        rsi_5m REAL,
        rsi_15m REAL,
        rsi_1h REAL,
        rsi_4h REAL,
        price REAL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol_id) REFERENCES symbols(id)

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
    if "score" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN score REAL DEFAULT 0")
    if "rsi_trend_1m" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_trend_1m TEXT")
    if "rsi_trend_5m" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_trend_5m TEXT")
    if "rsi_trend_15m" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_trend_15m TEXT")
    if "rsi_trend_1h" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_trend_1h TEXT")
    if "rsi_trend_4h" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_trend_4h TEXT")
    
    if "rsi_change_1m" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_change_1m REAL")
    if "rsi_change_5m" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_change_5m REAL")
    if "rsi_change_15m" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_change_15m REAL")
    if "rsi_change_1h" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_change_1h REAL")
    if "rsi_change_4h" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN rsi_change_4h REAL")
    if "advance_score" not in columns:
        cursor.execute("ALTER TABLE market_info ADD COLUMN advance_score REAL")
    

    # بررسی وجود ستون price_change قبل از اضافه کردن
    cursor.execute("PRAGMA table_info(rsi_data)")
    columns = [col[1] for col in cursor.fetchall()]
    if "rsi_trend" not in columns:
        cursor.execute("ALTER TABLE rsi_data ADD COLUMN rsi_trend TEXT; -- 'up', 'down', 'neutral'")
    if "rsi_change" not in columns:
        cursor.execute("ALTER TABLE rsi_data ADD COLUMN rsi_change REAL; -- مقدار تغییر")
    if "volume" not in columns:
        cursor.execute("ALTER TABLE rsi_data ADD COLUMN volume REAL;")

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

   
    
    # جدول ارزها (دینامیک)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL,
    symbol_name TEXT ,
    score REAL,
    advance_score REAL,
    signal_type TEXT, -- 'buy', 'sell', 'strong_buy', 'strong_sell'
    signal_label TEXT,
    rsi_values TEXT, -- JSON format
    price REAL NOT NULL,
    time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol_id) REFERENCES symbols (id)
)
    """)

    cursor.execute(""" CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(time); """)

    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_signals_symbol_id ON signals(symbol_id);  """)

    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(advance_score);     """)
    cursor.execute("PRAGMA table_info(signals)")
    columns = [col[1] for col in cursor.fetchall()]
    if "quality" not in columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN quality INTEGER")
    if "convergence_count" not in columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN convergence_count INTEGER")
    if "price_trend" not in columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN price_trend TEXT")
    if "testmode" not in columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN testmode TEXT")

    conn.commit()

    conn.close()

if __name__ == "__main__":
    create_tables()
    print("✅ Tables created successfully")