from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_data():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, price, rsi_1m, updated_at 
        FROM market_info 
        ORDER BY rsi_1m asc
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route("/")
def index():
    data = get_data()
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True, port=5000)