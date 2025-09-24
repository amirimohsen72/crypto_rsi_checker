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
        SELECT symbol, price, rsi_1m, updated_at 
        FROM market_info 
        ORDER BY rsi_1m asc
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
            "updated_at": dt_tehran.strftime("%Y-%m-%d %H:%M:%S")
        })

    return data

@app.route("/")
def index():
    data = get_data()
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)