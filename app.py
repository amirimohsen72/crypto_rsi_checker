from datetime import datetime
from flask import Flask, render_template
import sqlite3
import pytz  # نصب کن: pip install pytz

app = Flask(__name__)
tehran_tz = pytz.timezone("Asia/Tehran")

def get_data():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * 
        FROM market_info 
        ORDER BY  ABS(rsi_1m - 50) desc
    """)
    rows = cursor.fetchall()
    conn.close()

    
    # return rows

    data = []
    for row in rows:
        updated_at = row["updated_at"]

        # فرض: updated_at به صورت ISO string (مثلا: 2025-09-24 14:22:10) در DB ذخیره شده   
        dt_utc = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")  
        dt_utc = pytz.utc.localize(dt_utc)  # به UTC تبدیل کنیم
        dt_tehran = dt_utc.astimezone(tehran_tz)  # تبدیل به تهران

        data.append({
            "symbol": row["symbol"],
            "price": row["price"],
            "rsi_1m": row["rsi_1m"],
            "rsi_5m": row["rsi_5m"],
            "rsi_15m": row["rsi_15m"],
            "rsi_1h": row["rsi_1h"],
            "rsi_4h": row["rsi_4h"],
            "updated_at": dt_tehran.strftime("%Y-%m-%d %H:%M:%S")
        })

    return data

def get_data2():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, price, rsi_1m, rsi_5m, rsi_15m, rsi_1h, rsi_4h, updated_at
        FROM market_info
        ORDER BY ABS(rsi_1m - 50) DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.template_filter("localtime")
def localtime_filter(utc_string):
    if not utc_string:
        return ""
    utc_time = datetime.strptime(utc_string, "%Y-%m-%d %H:%M:%S")
    tehran = pytz.timezone("Asia/Tehran")
    return utc_time.replace(tzinfo=pytz.utc).astimezone(tehran).strftime("%Y-%m-%d %H:%M:%S")


@app.route("/")
def index():
    data = get_data()
    return render_template("index.html", data=data)

@app.route("/list2")
def index2():
    data = get_data2()
    return render_template("cryptos_show.html", data=data)


# if __name__ == "__main__":
#     app.run(debug=True, port=5000) #called in run.py