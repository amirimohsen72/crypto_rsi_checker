import time
import winsound
import ccxt
import pandas as pd
import ta
import os
import sqlite3



SYMBOL = "MYX/USDT:USDT"
# TIMEFRAME = "1m"
COUNT_BEST = 0
SLEEP_INTERVAL = 25   # 300 ثانیه = 5 دقیقه
last_rsi = None
last_best_C = ""

exchange = ccxt.bybit({
    'options': {'defaultType': 'future'}
})

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"]


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

# اتصال به دیتابیس
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()
 


def run_fetcher_loop():
    global last_best_C, COUNT_BEST, last_rsi
    frequency =2222
    duration =200
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
                    # گرفتن کندل‌ها
                    bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
                    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

                    df["RSI_EMA"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=False).rsi()  # ta خودش EMA استفاده میکنه
                    # clear_console()
                    
                    # if last_rsi != None :
                    #     print(f"last rsi : {last_rsi:.2f} \n -----------------")
                    print(f"crypto name : {SYMBOL}" )

                    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

                    last_price = df["close"].iloc[-1]
                    last_rsi = round(df["RSI"].iloc[-1], 2)
                    
                    last_rsi_ema = df["RSI_EMA"].iloc[-1]

                    # print(f"Price: {last_price:.4f}")
                    # print(f"RSI Wilder: {last_rsi_wilder:.2f}")
                    # print(f"RSI EMA: {last_rsi_ema:.2f}")
                    # print(f"RSI  : {last_rsi:.2f}")
                    cursor.execute("INSERT INTO rsi_data (symbol_id, price, rsi,timeframe) VALUES (?, ?, ?, ?)",
                                (symbol_id, last_price, last_rsi,TIMEFRAME))
                    conn.commit()
                    

                    # انتخاب ستون مناسب بر اساس تایم‌فریم
                    col_name = {
                        "1m": "rsi_1m",
                        "5m": "rsi_5m",
                        "15m": "rsi_15m",
                        "1h": "rsi_1h",
                        "4h": "rsi_4h"
                    }[TIMEFRAME]

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
                # print("----------------------------------------------")

            except Exception as e:
                print("⚠️ Error:", e)

            print(f"--- waiting {SLEEP_INTERVAL}sec to reload --- now : {time.strftime('%H:%M:%S')}\n")
            time.sleep(SLEEP_INTERVAL) 
        time.sleep(10) 
        clear_console()

if __name__ == "__main__":
    run_fetcher_loop()
 