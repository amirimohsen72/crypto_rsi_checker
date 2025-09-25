import threading
import time
from db_setup import create_tables
from app import app
from main import run_fetcher_loop

def run_flask():
    app.run(debug=True, port=5000, use_reloader=False)

if __name__ == "__main__":
    create_tables()  # اطمینان از ساخت دیتابیس

    t1 = threading.Thread(target=run_fetcher_loop, daemon=True)
    t2 = threading.Thread(target=run_flask, daemon=True)

    t1.start()
    t2.start()

    while True:
        time.sleep(1)
