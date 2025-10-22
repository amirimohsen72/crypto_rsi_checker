import time
import winsound
import ccxt
import pandas as pd
import ta
import os
import sqlite3
import pytz
from datetime import datetime, timedelta




COUNT_BEST = 0
SLEEP_INTERVAL = 7   # 300 ثانیه = 5 دقیقه
last_rsi = None
last_best_C = ""
tz_tehran = pytz.timezone("Asia/Tehran")

exchange = ccxt.bybit({
    'options': {'defaultType': 'future'}
})

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"]
rsi_values = {}


def clear_console():
    """Clears the console screen."""
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux
    else:
        os.system('clear')

def get_active_symbols():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id,future_symbol,base_symbol FROM symbols WHERE active = 1 AND future_symbol IS NOT NULL")
    symbols = cursor.fetchall()
    conn.close()
    return symbols

def get_lastrsi_save_times(cursor, symbol_id):
    """
    یه بار همه آخرین timestamp‌ها رو برای همه تایم‌فریم‌ها میگیره
    """
    cursor.execute("""
        SELECT 
            timeframe,
            MAX(timestamp) as last_time
        FROM rsi_data
        WHERE symbol_id = ?
        GROUP BY timeframe
    """, (symbol_id,))
    results = cursor.fetchall()
    
    # تبدیل به دیکشنری برای دسترسی سریع
    return {row[0]: row[1] for row in results}


def get_previous_rsi(cursor, symbol_id, timeframe):
    """
    برمی‌گردونه آخرین مقدار RSI از تایم‌فریم قبلی در بازه [target ± tolerance]
    خروجی: dict با فیلدهای rsi، timestamp یا None اگه چیزی پیدا نشد
    """
    intervals = {
        "1m":  {"target": 1,   "tolerance": 0.5},   # ±30 ثانیه
        "5m":  {"target": 5,   "tolerance": 2},     # ±2 دقیقه
        "15m": {"target": 15,  "tolerance": 5},
        "1h":  {"target": 60,  "tolerance": 15},
        "4h":  {"target": 240, "tolerance": 60}
    }

    cfg = intervals.get(timeframe, {"target": 5, "tolerance": 2})

    # هدف: زمان تقریبی بازه قبلی
    target_time = datetime.now(tz_tehran) - timedelta(minutes=cfg["target"])
    min_time = target_time - timedelta(minutes=cfg["tolerance"])
    max_time = target_time + timedelta(minutes=cfg["tolerance"])
    

    # جست‌وجو در بازه مجاز
    query = """
        SELECT rsi, timestamp 
        FROM rsi_data
        WHERE symbol_id = ? AND timeframe = ?
        AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp DESC
        LIMIT 1
    """
    cursor.execute(query, (
        symbol_id,
        timeframe,
        min_time.strftime("%Y-%m-%d %H:%M:%S"),
        max_time.strftime("%Y-%m-%d %H:%M:%S")
    ))
    row = cursor.fetchone()

    # اگر در بازه چیزی پیدا نشد، نزدیک‌ترین رکورد ممکن رو بیار
    if not row:
        fallback_query = """
            SELECT rsi, timestamp 
            FROM rsi_data
            WHERE symbol_id = ? AND timeframe = ?
            ORDER BY ABS((julianday(?) - julianday(timestamp)) * 24 * 60)
            LIMIT 1
        """
        cursor.execute(fallback_query, (
            symbol_id,
            timeframe,
            datetime.now(tz_tehran).strftime("%Y-%m-%d %H:%M:%S")
        ))
        row = cursor.fetchone()

    if row:
        return {"rsi": row[0], "timestamp": row[1]}
    return None

def detect_rsi_trend(current_rsi, previous_rsi, threshold=0.1 ):
    """
    تشخیص جهت روند RSI
    threshold: حداقل تغییر معنادار (پیش‌فرض 2 واحد)
    """
    if previous_rsi is None:
        return "unknown", 0
    
    change = current_rsi - previous_rsi
    
    if (abs(change) < threshold) or (change == 0):
        return "flat", change
    elif change > 0:
        return "up", change
    else:
        return "down", change

def is_allowed_to_save(last_save_times, timeframe):
    """
    چک میکنه که آیا مجاز به ذخیره هستیم یا نه
    """
    
    # تعیین حد مجاز برای هر تایم‌فریم (به دقیقه)
    intervals = {
        "1m": 30,
        "5m": 2,
        "15m": 5,
        "1h": 20,
        "4h": 60
    }
    
    # اگه تایم‌فریم توی دیکشنری نیست یا None هست، مجازه
    if timeframe not in last_save_times or last_save_times[timeframe] is None:
        return True
    
    # گرفتن آخرین زمان ذخیره
    last_timestamp = last_save_times[timeframe]
    last_time = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    # محاسبه اختلاف زمانی (به دقیقه)
    time_diff = (now - last_time).total_seconds()
    if (timeframe == "1m"):
        return time_diff >= intervals.get("1m")

    else :
        # //به دقیقه
        time_diff = time_diff / 60 
        
        # بررسی اینکه آیا زمان کافی گذشته
        allowed_interval = intervals.get(timeframe, 5)
        return time_diff >= allowed_interval

def calculate_score(rsi_values):
    """
    ورودی: دیکشنری از RSIهای تایم‌فریم‌ها
    خروجی: عدد امتیاز نهایی بین -100 تا +100
    """
    score = 0
    weights = {
        "1m": 0.40,
        "5m": 0.30,
        "15m": 0.15,
        "1h": 0.10,
        "4h": 0.05
    }

    for tf, rsi in rsi_values.items():
        if rsi is None:
            continue

        # 30 تا 70 محدوده تعادل
        if rsi < 35:
            score += (35 - rsi) * weights[tf] * 2  # هر چی پایین‌تر، امتیاز مثبت‌تر (خرید احتمالی)
        elif rsi > 65:
            score -= (rsi - 65) * weights[tf] * 2  # هر چی بالاتر، امتیاز منفی‌تر (فروش احتمالی)
        elif rsi >50 and rsi<=65:
            score -= (rsi - 50) * weights[tf]       # میل به فروش
        elif rsi <50 and rsi>=35:
            score += (50 - rsi) * weights[tf]
    # محدودسازی امتیاز بین -100 تا +100
    score = max(min(score, 100), -100)
    return round(score, 2)

# اتصال به دیتابیس
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()
 


def run_fetcher_loop():
    tz_tehran = pytz.timezone("Asia/Tehran")
    global last_best_C, COUNT_BEST, last_rsi
    frequency =2222
    duration =200
    countreq = 0
    while True:
        symbols = get_active_symbols()

        print(f"count best position rmi : {COUNT_BEST} \n **************************")
        if last_best_C :
            print(last_best_C)
            last_best_C = ""
        for id,future_symbol,base_symbol in symbols:
            try:
                symbol_id = id
                
                SYMBOL = future_symbol
                print(SYMBOL)
                cursor.execute("SELECT price FROM market_info WHERE symbol_id=?", (symbol_id,))
                row = cursor.fetchone()

                for TIMEFRAME in TIMEFRAMES:
                    last_save_times = get_lastrsi_save_times(cursor, symbol_id)
                    if is_allowed_to_save(last_save_times, TIMEFRAME):
                        countreq += 1
                        
                        # گرفتن کندل‌ها
                        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
                        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

                        df["RSI_EMA"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=False).rsi()  # ta خودش EMA استفاده میکنه
                        

                        print(f"crypto name : {SYMBOL}" )

                        df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

                        last_price = df["close"].iloc[-1]
                        last_rsi = round(df["RSI"].iloc[-1], 2)
                        
                        last_rsi_ema = df["RSI_EMA"].iloc[-1]

                        # print(f"Price: {last_price:.4f}")
                        # print(f"RSI Wilder: {last_rsi_wilder:.2f}")
                        # print(f"RSI EMA: {last_rsi_ema:.2f}")
                        # print(f"RSI  : {last_rsi:.2f}")
                        now_tehran = datetime.now(tz_tehran).strftime("%Y-%m-%d %H:%M:%S")

                        prev_data = get_previous_rsi(cursor, symbol_id, TIMEFRAME)
                        if prev_data:
                            prev_rsi = prev_data["rsi"]
                        else : prev_rsi = None

                        direction, rsi_change = detect_rsi_trend(last_rsi, prev_rsi, threshold=0.1)

                        cursor.execute(
                            "INSERT INTO rsi_data (symbol_id, price, rsi, timeframe, timestamp,rsi_change ,rsi_trend ) VALUES (?, ?, ?, ?, ?,?,?)",
                            (symbol_id, last_price, last_rsi, TIMEFRAME, now_tehran,rsi_change ,direction )
                        )
                        

                        # انتخاب ستون مناسب بر اساس تایم‌فریم
                        col_name = {
                            "1m": "rsi_1m",
                            "5m": "rsi_5m",
                            "15m": "rsi_15m",
                            "1h": "rsi_1h",
                            "4h": "rsi_4h"
                        }[TIMEFRAME]
                        rsi_values[TIMEFRAME] = last_rsi

                        # اول اگه نبود اضافه کن
                        cursor.execute("INSERT OR IGNORE INTO market_info (symbol_id) VALUES (?)", (symbol_id,))

                        if row and row[0] is not None:
                            prev_price = row[0]
                            price_change = round(last_price - prev_price, 4)
                        else:
                            price_change = 0
                        # بعد ستون مربوطه رو آپدیت کن
                        cursor.execute(f"""
                            UPDATE market_info
                            SET price=?, {col_name}=?, price_change=?, updated_at=CURRENT_TIMESTAMP 
                            WHERE symbol_id=?
                        """, (last_price, last_rsi, price_change, symbol_id))

                        conn.commit()
                        # هشدار هم میشه اضافه کرد
                        if last_rsi > 75 :
                            COUNT_BEST +=1
                            winsound.Beep(frequency, duration) # frequency in Hz, duration in milliseconds
                            print("🚨 RSI is high! "+TIMEFRAME)
                            print(f"Price: {last_price:.4f}")
                            print(f"RSI  : {last_rsi:.2f}")
                            last_best_C += f'{SYMBOL}    '

                        elif last_rsi < 30 :
                            COUNT_BEST+=1
                            winsound.Beep(frequency, duration) # frequency in Hz, duration in milliseconds
                            print("📉 RSI is low! " +TIMEFRAME)
                            print(f"Price: {last_price:.4f}")
                            print(f"RSI  : {last_rsi:.2f}")
                            last_best_C += f'{SYMBOL}   '
                        else :
                            print(f"RSI is normal : {last_rsi:.2f} | "+TIMEFRAME)
                        time.sleep(1) 
                    else:
                        print(" --------------- not need to fetch data because we have data in this time frame")
                    print("count request : "+ str(countreq))
                # print("----------------------------------------------")
                if rsi_values:
                    score = calculate_score(rsi_values)
                    cursor.execute("UPDATE market_info SET score=? WHERE symbol_id=?", (score, symbol_id))
                    conn.commit()

            except Exception as e:
                print("⚠️ Error:", e)

            print(f"--- waiting {SLEEP_INTERVAL}sec to reload --- now : {time.strftime('%H:%M:%S')}\n")
            time.sleep(SLEEP_INTERVAL) 
        
        clear_console()
    time.sleep(7) 
if __name__ == "__main__":
    run_fetcher_loop()
 