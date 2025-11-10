"""
ماژول ردیابی عملکرد سیگنال‌ها
Phase 4: Performance Tracking & Feature Engineering

این ماژول:
1. سیگنال‌های قدیمی رو چک می‌کنه
2. محاسبه می‌کنه که چند درصد سود/ضرر دادن
3. Win Rate هر روش رو محاسبه می‌کنه
4. Feature های لازم برای ML رو آماده می‌کنه
"""

import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import json
import pytz

tz_tehran = pytz.timezone("Asia/Tehran")


def create_performance_table(cursor):
    """
    ساخت جدول برای ذخیره عملکرد سیگنال‌ها
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            symbol_id INTEGER,
            symbol_name TEXT,
            entry_price REAL,
            entry_time TIMESTAMP,
            
            -- قیمت در زمان‌های مختلف
            price_after_15m REAL,
            price_after_30m REAL,
            price_after_1h REAL,
            price_after_4h REAL,
            price_after_24h REAL,
            
            -- درصد تغییر
            change_15m REAL,
            change_30m REAL,
            change_1h REAL,
            change_4h REAL,
            change_24h REAL,
            
            -- وضعیت
            signal_direction TEXT,  -- 'buy' or 'sell'
            is_profitable_15m INTEGER,
            is_profitable_30m INTEGER,
            is_profitable_1h INTEGER,
            is_profitable_4h INTEGER,
            is_profitable_24h INTEGER,
            
            -- متادیتا
            testmode TEXT,
            confidence REAL,
            score REAL,
            tracked_at TIMESTAMP,
            
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal_performance 
        ON signal_performance(signal_id, testmode)
    """)


def get_price_at_time(cursor, symbol_id, target_time):
    """
    گرفتن قیمت در یک زمان خاص
    
    Args:
        target_time: datetime object
    
    Returns:
        float or None
    """
    # جستجوی نزدیک‌ترین قیمت به زمان مورد نظر (±5 دقیقه)
    time_min = (target_time - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    time_max = (target_time + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    query = """
        SELECT price, timestamp
        FROM rsi_data
        WHERE symbol_id = ? 
        AND timestamp BETWEEN ? AND ?
        ORDER BY ABS(julianday(?) - julianday(timestamp))
        LIMIT 1
    """
    
    cursor.execute(query, (symbol_id, time_min, time_max, 
                          target_time.strftime("%Y-%m-%d %H:%M:%S")))
    result = cursor.fetchone()
    
    return result[0] if result else None


def track_signal_performance(cursor, signal_id, symbol_id, symbol_name, 
                             entry_price, entry_time, signal_score, 
                             confidence, testmode):
    """
    ردیابی عملکرد یک سیگنال
    
    این تابع باید بعد از 24 ساعت از ثبت سیگنال صدا زده بشه
    """
    # تبدیل entry_time به datetime
    if isinstance(entry_time, str):
        # entry_time = entry_time.strptime("%Y-%m-%d %H:%M:%S")
        # # entry_time = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S") 
        entry_time = datetime.fromisoformat(entry_time)

    
    
    # محاسبه زمان‌های چک
    times = {
        '15m': entry_time + timedelta(minutes=15),
        '30m': entry_time + timedelta(minutes=30),
        '1h': entry_time + timedelta(hours=1),
        '4h': entry_time + timedelta(hours=4),
        '24h': entry_time + timedelta(hours=24)
    }
    
    # گرفتن قیمت‌ها
    prices = {}
    changes = {}
    is_profitable = {}
    
    signal_direction = 'buy' if signal_score > 0 else 'sell'

    for period, target_time in times.items():
        price = get_price_at_time(cursor, symbol_id, target_time)
        
        if price:
            prices[period] = price
            change_percent = ((price - entry_price) / entry_price) * 100
            changes[period] = change_percent
            
            # تعیین سودآوری
            if signal_direction == 'buy':
                is_profitable[period] = 1 if change_percent > 0 else 0
            else:  # sell
                is_profitable[period] = 1 if change_percent < 0 else 0
        else:
            prices[period] = None
            changes[period] = None
            is_profitable[period] = None
    # ذخیره در دیتابیس
    cursor.execute("""
        INSERT INTO signal_performance 
        (signal_id, symbol_id, symbol_name, entry_price, entry_time,
         price_after_15m, price_after_30m, price_after_1h, price_after_4h, price_after_24h,
         change_15m, change_30m, change_1h, change_4h, change_24h,
         signal_direction, is_profitable_15m, is_profitable_30m, 
         is_profitable_1h, is_profitable_4h, is_profitable_24h,
         testmode, confidence, score, tracked_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        signal_id, symbol_id, symbol_name, entry_price, entry_time,
        prices.get('15m'), prices.get('30m'), prices.get('1h'), 
        prices.get('4h'), prices.get('24h'),
        changes.get('15m'), changes.get('30m'), changes.get('1h'),
        changes.get('4h'), changes.get('24h'),
        signal_direction,
        is_profitable.get('15m'), is_profitable.get('30m'),
        is_profitable.get('1h'), is_profitable.get('4h'), is_profitable.get('24h'),
        testmode, confidence, signal_score, datetime.now(tz_tehran)
    ))
    
    return {
        'prices': prices,
        'changes': changes,
        'is_profitable': is_profitable
    }



def track_old_signals(cursor, hours_ago=24, batch_size=500):
    """
    ردیابی سیگنال‌های قدیمی که هنوز track نشدن
    
    Args:
        hours_ago: سیگنال‌هایی که بیش از این ساعت قدیمی هستن رو چک می‌کنه
        batch_size: تعداد سیگنال در هر دسته (default: 500)
    """
    cutoff_time = datetime.now(tz_tehran) - timedelta(hours=hours_ago)
    
    # پیدا کردن سیگنال‌های track نشده
    query = """
        SELECT s.id, s.symbol_id, s.symbol_name, s.price, s.time, 
               s.advance_score, s.quality, s.testmode
        FROM signals s
        LEFT JOIN signal_performance sp ON s.id = sp.signal_id
        WHERE sp.signal_id IS NULL
        AND s.time < ?
        ORDER BY s.time ASC
        LIMIT ?
    """
    
    cursor.execute(query, (cutoff_time.strftime("%Y-%m-%d %H:%M:%S"), batch_size))
    old_signals = cursor.fetchall()
    if not old_signals:
        print(f"✅ No more signals to track (older than {hours_ago}h)")
        return 0
    tracked_count = 0
    failed_count = 0

    print(f"\n⏳ Tracking {len(old_signals)} signals...")
    for i, signal in enumerate(old_signals, 1):
        signal_id, symbol_id, symbol_name, price, time_str, score, confidence, testmode = signal
        
        try:
            result = track_signal_performance(
                cursor, signal_id, symbol_id, symbol_name,
                price, time_str, score, confidence, testmode
            )
            tracked_count += 1
            # نمایش progress

            if tracked_count % 50 == 0:
                print(f"   Progress: {tracked_count}/{len(old_signals)} ({(tracked_count/len(old_signals)*100):.1f}%)")
            print(f"✅ Tracked: {symbol_name} | Entry: ${price} | 1h: {result['changes'].get('1h', 'N/A'):+.2f}% | time:{time_str} ")
            
        except Exception as e:
            failed_count += 1
            if failed_count < 5:  # فقط 5 تا اول رو نشون بده
                print(f"⚠️ Error tracking signal {signal_id}: {e}")
    print(f"\n✅ Tracked: {tracked_count} | ❌ Failed: {failed_count}")
    return tracked_count


def calculate_win_rate(cursor, testmode=None, min_confidence=0):
    """
    محاسبه Win Rate برای هر روش
    
    Args:
        testmode: فیلتر بر اساس روش (مثلا 'v5_complete')
        min_confidence: حداقل confidence برای فیلتر
    
    Returns:
        dict: آمار کامل
    """
    where_clause = "WHERE 1=1"
    params = []
    
    if testmode:
        where_clause += " AND testmode = ?"
        params.append(testmode)
    
    if min_confidence > 0:
        where_clause += " AND confidence >= ?"
        params.append(min_confidence)
    
    query = f"""
        SELECT 
            testmode,
            COUNT(*) as total_signals,
            AVG(confidence) as avg_confidence,
            AVG(score) as avg_score,
            
            -- Win rates
            AVG(CASE WHEN is_profitable_15m = 1 THEN 1 ELSE 0 END) * 100 as win_rate_15m,
            AVG(CASE WHEN is_profitable_30m = 1 THEN 1 ELSE 0 END) * 100 as win_rate_30m,
            AVG(CASE WHEN is_profitable_1h = 1 THEN 1 ELSE 0 END) * 100 as win_rate_1h,
            AVG(CASE WHEN is_profitable_4h = 1 THEN 1 ELSE 0 END) * 100 as win_rate_4h,
            AVG(CASE WHEN is_profitable_24h = 1 THEN 1 ELSE 0 END) * 100 as win_rate_24h,
            
            -- Average returns
            AVG(change_15m) as avg_return_15m,
            AVG(change_30m) as avg_return_30m,
            AVG(change_1h) as avg_return_1h,
            AVG(change_4h) as avg_return_4h,
            AVG(change_24h) as avg_return_24h
            
        FROM signal_performance
        {where_clause}
        GROUP BY testmode
        ORDER BY win_rate_1h DESC
    """
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    stats = []
    for row in results:
        stats.append({
            'testmode': row[0],
            'total_signals': row[1],
            'avg_confidence': round(row[2], 2) if row[2] else 0,
            'avg_score': round(row[3], 2) if row[3] else 0,
            'win_rate_15m': round(row[4], 2) if row[4] else 0,
            'win_rate_30m': round(row[5], 2) if row[5] else 0,
            'win_rate_1h': round(row[6], 2) if row[6] else 0,
            'win_rate_4h': round(row[7], 2) if row[7] else 0,
            'win_rate_24h': round(row[8], 2) if row[8] else 0,
            'avg_return_15m': round(row[9], 2) if row[9] else 0,
            'avg_return_30m': round(row[10], 2) if row[10] else 0,
            'avg_return_1h': round(row[11], 2) if row[11] else 0,
            'avg_return_4h': round(row[12], 2) if row[12] else 0,
            'avg_return_24h': round(row[13], 2) if row[13] else 0
        })
    
    return stats


def get_best_performing_method(cursor):
    """
    تشخیص بهترین روش بر اساس Win Rate
    """
    stats = calculate_win_rate(cursor)
    
    if not stats:
        return None
    
    # مرتب‌سازی بر اساس Win Rate 1h و Average Return
    best = max(stats, key=lambda x: (x['win_rate_1h'], x['avg_return_1h']))
    
    return best


def print_performance_report(cursor):
    """
    چاپ گزارش کامل عملکرد
    """
    stats = calculate_win_rate(cursor)
    
    if not stats:
        print("⚠️ هنوز هیچ سیگنالی track نشده!")
        return
    
    print(f"\n{'═'*100}")
    print(f"📊 PERFORMANCE REPORT - Signal Analysis")
    print(f"{'═'*100}")
    
    for stat in stats:
        print(f"\n{'─'*100}")
        print(f"🔹 Method: {stat['testmode']}")
        print(f"   Total Signals: {stat['total_signals']}")
        print(f"   Avg Confidence: {stat['avg_confidence']:.1f}%")
        print(f"   Avg Score: {stat['avg_score']:+.2f}")
        
        print(f"\n   📈 Win Rates:")
        print(f"      15m: {stat['win_rate_15m']:.1f}%  |  Avg Return: {stat['avg_return_15m']:+.2f}%")
        print(f"      30m: {stat['win_rate_30m']:.1f}%  |  Avg Return: {stat['avg_return_30m']:+.2f}%")
        print(f"      1h:  {stat['win_rate_1h']:.1f}%  |  Avg Return: {stat['avg_return_1h']:+.2f}%")
        print(f"      4h:  {stat['win_rate_4h']:.1f}%  |  Avg Return: {stat['avg_return_4h']:+.2f}%")
        print(f"      24h: {stat['win_rate_24h']:.1f}%  |  Avg Return: {stat['avg_return_24h']:+.2f}%")
    
    # بهترین روش
    best = get_best_performing_method(cursor)
    if best:
        print(f"\n{'═'*100}")
        print(f"🏆 BEST METHOD: {best['testmode']}")
        print(f"   Win Rate (1h): {best['win_rate_1h']:.1f}%")
        print(f"   Avg Return (1h): {best['avg_return_1h']:+.2f}%")
        print(f"{'═'*100}")


def export_for_ml(cursor, output_file='ml_dataset.csv'):
    """
    آماده‌سازی دیتاست برای Machine Learning
    
    ترکیب signal_performance + signals + market_info
    """
    query = """
        SELECT 
            sp.*,
            s.rsi_values,
            s.signal_type,
            s.signal_label,
            s.convergence_count,
            s.price_trend
        FROM signal_performance sp
        JOIN signals s ON sp.signal_id = s.id
        WHERE sp.change_1h IS NOT NULL
    """
    
    df = pd.read_sql_query(query, cursor.connection)
    
    # استخراج feature ها
    if not df.empty:
        # Parse JSON fields
        if 'rsi_values' in df.columns:
            rsi_df = df['rsi_values'].apply(lambda x: json.loads(x) if x else {})
            for tf in ['1m', '5m', '15m', '1h', '4h']:
                df[f'rsi_{tf}'] = rsi_df.apply(lambda x: x.get(tf, None))
        
        # Target variable: آیا سودآور بود؟
        df['target_1h'] = df['is_profitable_1h']
        
        # Save
        df.to_csv(output_file, index=False)
        print(f"✅ Dataset exported: {output_file} ({len(df)} rows)")
        
        return df
    
    return None


def run_tracking_job(cursor):
    """
    Job اصلی برای اجرای دوره‌ای (هر ساعت یکبار)
    """
    print(f"\n{'═'*80}")
    print(f"🔄 Running Performance Tracking Job - {datetime.now(tz_tehran)}")
    print(f"{'═'*80}")
    
    # Track سیگنال‌های قدیمی
    tracked = track_old_signals(cursor, hours_ago=24)
    print(f"\n✅ Tracked {tracked} old signals")
    
    # نمایش گزارش
    print_performance_report(cursor)
    
    # Export برای ML
    export_for_ml(cursor)
    
    print(f"\n{'═'*80}")
    print(f"✅ Tracking Job Completed")
    print(f"{'═'*80}\n")