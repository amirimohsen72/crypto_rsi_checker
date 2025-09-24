import time
import winsound
import ccxt
import pandas as pd
import ta
import os
import sqlite3



SYMBOL = "MYX/USDT:USDT"
TIMEFRAME = "1m"
COUNT_BEST = 0
SLEEP_INTERVAL = 35   # 300 ثانیه = 5 دقیقه
last_rsi = None
frequency =2222
duration =200
last_best_C = ""

exchange = ccxt.bybit({
    'options': {'defaultType': 'future'}
})



def clear_console():
    """Clears the console screen."""
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux
    else:
        os.system('clear')


# اتصال به دیتابیس
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# جدول اگه وجود نداره بساز
cursor.execute("""
CREATE TABLE IF NOT EXISTS rsi_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    price REAL,
    rsi REAL,
    timeframe TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

with open("symbols.txt", "r") as f:
    # SYMBOL = f.readline()
    symbols = [line.strip() for line in f.readlines() if line.strip()]
    # for symbol in symbols:
    #     SYMBOL = symbol

while True:
    
    print(f"count best position rmi : {COUNT_BEST} \n **************************")
    if last_best_C :
        print(last_best_C)
        last_best_C = ""
    for symbol in symbols:
        try:
            SYMBOL = symbol
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
            last_rsi = df["RSI"].iloc[-1]
            last_rsi_ema = df["RSI_EMA"].iloc[-1]

            # print(f"Price: {last_price:.4f}")
            # print(f"RSI Wilder: {last_rsi_wilder:.2f}")
            # print(f"RSI EMA: {last_rsi_ema:.2f}")
            # print(f"RSI  : {last_rsi:.2f}")
            cursor.execute("INSERT INTO rsi_data (symbol, price, rsi,timeframe) VALUES (?, ?, ?, ?)",
                           (symbol, last_price, last_rsi,TIMEFRAME))
            conn.commit()

            # هشدار هم میشه اضافه کرد
            if last_rsi > 75 :
                COUNT_BEST +=1
                winsound.Beep(frequency, duration) # frequency in Hz, duration in milliseconds
                print("🚨 RSI is high!")
                print(f"Price: {last_price:.4f}")
                print(f"RSI  : {last_rsi:.2f}")
                last_best_C += f'{SYMBOL}    '

            elif last_rsi < 30 :
                COUNT_BEST+=1
                winsound.Beep(frequency, duration) # frequency in Hz, duration in milliseconds
                print("📉 RSI is low!")
                print(f"Price: {last_price:.4f}")
                print(f"RSI  : {last_rsi:.2f}")
                last_best_C += f'{SYMBOL}   '
            else :
                print(f"RSI is normal : {last_rsi:.2f}")
            print("----------------------------------------------")

        except Exception as e:
            print("⚠️ Error:", e)

        print(f"--- waiting {SLEEP_INTERVAL}sec to reload --- now : {time.strftime('%H:%M:%S')}\n")
        time.sleep(SLEEP_INTERVAL) 
    time.sleep(30) 
    clear_console()