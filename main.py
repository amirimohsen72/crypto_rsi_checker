import ccxt
import pandas as pd
import ta
import os



SYMBOL = "MYX/USDT:USDT"
TIMEFRAME = "1m"
COUNT_BEST = 0
SLEEP_INTERVAL = 45   # 300 ثانیه = 5 دقیقه
last_rsi = None

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

while True:
    try:

        # گرفتن کندل‌ها
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])

        df["RSI_EMA"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=False).rsi()  # ta خودش EMA استفاده میکنه
        clear_console()
        
        print(f"count best position rmi : {COUNT_BEST}")
        if last_rsi != None :
            print(f"last rsi : {last_rsi:.2f} \n -----------------")
        print(f"crypto name : {SYMBOL}" )

        df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

        last_price = df["close"].iloc[-1]
        last_rsi = df["RSI"].iloc[-1]
        last_rsi_ema = df["RSI_EMA"].iloc[-1]

        print(f"Price: {last_price:.4f}")
        # print(f"RSI Wilder: {last_rsi_wilder:.2f}")
        print(f"RSI EMA: {last_rsi_ema:.2f}")
        print(f"RSI  : {last_rsi:.2f}")


        # هشدار هم میشه اضافه کرد
        if last_rsi > 75 :
            COUNT_BEST +=1

            print("🚨 RSI is high!")
        elif last_rsi < 30 :
            COUNT_BEST+=1
            print("📉 RSI is low!")


    except Exception as e:
        print("⚠️ Error:", e)

    # print(f"--- waiting {SLEEP_INTERVAL}sec to reload --- now : {time.strftime('%H:%M:%S')}\n")
 