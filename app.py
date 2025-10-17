from datetime import datetime, timezone
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
        FROM market_info AS m
        JOIN symbols AS s 
            ON m.symbol_id = s.id
        WHERE s.active = 1
        ORDER BY ABS(score) DESC,ABS(m.rsi_1m - 50) DESC

    """)
    rows = cursor.fetchall()
    conn.close()

    
    # return rows
    
    tz_tehran = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz_tehran)
    data = []
    for row in rows:
        updated_at = row["updated_at"]
        updated_at_dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
        updated_at_dt = updated_at_dt.replace(tzinfo=timezone.utc).astimezone(tz_tehran)
        if updated_at_dt:
            diff = now - updated_at_dt
            minutes = diff.total_seconds() / 60
            if minutes <= 2:
                status = "✅"
                color = "green"
            elif minutes <= 10:
                status = "⚠️ با تأخیر (ریسک متوسط)"
                color = "orange"
            else:
                status = "🚨 قدیمی (ریسک بالا)"
                color = "red"
        else:
            status = "⏳ بدون داده"
            color = "gray"

        # فرض: updated_at به صورت ISO string (مثلا: 2025-09-24 14:22:10) در DB ذخیره شده   
        dt_utc = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")  
        dt_utc = pytz.utc.localize(dt_utc)  # به UTC تبدیل کنیم
        dt_tehran = dt_utc.astimezone(tehran_tz)  # تبدیل به تهران

        data.append({
            "symbol": row["base_symbol"],
            "price": row["price"],
            "rsi_1m": row["rsi_1m"],
            "rsi_5m": row["rsi_5m"],
            "rsi_15m": row["rsi_15m"],
            "rsi_1h": row["rsi_1h"],
            "rsi_4h": row["rsi_4h"],
            "price_change": row["price_change"],
            "score": row["score"],
            "updated_at": dt_tehran.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "color": color
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


    
@app.route("/symbol/<symbol>")
def symbol_detail(symbol):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    query = """
        SELECT 
            symbol_id,
            s.name,
            s.base_symbol,
            s.spot_symbol,
            s.future_symbol,
            s.active,
            m.price,
            m.rsi_1m,
            m.rsi_5m,
            m.rsi_15m,
            m.rsi_1h,
            m.rsi_4h,
            m.price_change,
            m.score,
            m.updated_at
        FROM market_info AS m
        JOIN symbols AS s 
            ON m.symbol_id = s.id
        WHERE s.base_symbol = ?
    """
    cursor.execute(query, (symbol.upper(),))
    row = cursor.fetchone()
    # conn.close()

    if not row:
        return f"<h3>🚫 اطلاعاتی برای {symbol} یافت نشد.</h3>"

    columns = [desc[0] for desc in cursor.description]
    data = dict(zip(columns, row))
    if data["updated_at"]:
        # تبدیل رشته به datetime
        dt_utc = datetime.strptime(data["updated_at"], "%Y-%m-%d %H:%M:%S")
        # منطقه زمانی تهران
        tz_tehran = pytz.timezone("Asia/Tehran")
        dt_tehran = pytz.utc.localize(dt_utc).astimezone(tz_tehran)
        data["updated_at"] = dt_tehran.strftime("%Y-%m-%d %H:%M:%S")

        # 🔹 بررسی مقدار تغییر قیمت و فرمت آن
    price_change = data.get("price_change")
    print(price_change)
    if price_change is not None:
        if price_change > 0:
            data["price_change_str"] = f"+{price_change:.4f}"
            data["color"] = "green"
        elif price_change < 0:
            data["price_change_str"] = f"{price_change:.4f}"
            data["color"] = "red"
        else:
            data["price_change_str"] = f"{price_change:.4f}"
            data["color"] = "gray"
    else:
        data["price_change_str"] = "-"
        data["color"] = "gray"

    symbol_id = data['symbol_id']
    
    # گرفتن داده‌های نمودار برای هر تایم‌فریم
    chart_data = {}
    timeframes = ["1m", "5m", "15m", "1h", "4h"]

    for tf in timeframes:
        if tf in ["1m", "5m", "15m"]:
            # تایم‌فریم‌های کوتاه: همه رکوردها (مثلا 200 آخر)
            query = """
                SELECT timestamp, rsi, price
                FROM rsi_data
                WHERE symbol_id = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT 200
            """
            cursor.execute(query, (symbol_id, tf))
            results = cursor.fetchall()
            results.reverse()
        else:
            # تایم‌فریم‌های بزرگ: گروپ‌بندی بر اساس start ساعت/چهار ساعت
            query = f"""
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) AS grp_time,
                    AVG(rsi) as rsi,
                    AVG(price) as price
                FROM rsi_data
                WHERE symbol_id = ? AND timeframe = ?
                GROUP BY grp_time
                ORDER BY grp_time DESC
                LIMIT 50
            """
            cursor.execute(query, (symbol_id, tf))
            results = cursor.fetchall()
            results.reverse()

        chart_data[tf] = {
            "timestamps": [row[0] for row in results],
            "rsi_values": [row[1] for row in results],
            "prices": [row[2] for row in results]
        }

    
    conn.close()
    return render_template("symbol_detail.html", data=data, chart_data=chart_data)
