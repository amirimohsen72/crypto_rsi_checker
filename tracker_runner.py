"""
اسکریپت اجرای خودکار Performance Tracker

این فایل رو به صورت جداگانه اجرا کنید:
    python tracker_runner.py

یا در main.py به عنوان thread جداگانه اجرا کنید
"""

import sqlite3
import time
import schedule
from datetime import datetime
import performance_tracker as pt


def setup_database():
    """راه‌اندازی دیتابیس و جداول"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # ساخت جدول performance
    pt.create_performance_table(cursor)
    conn.commit()
    
    return conn, cursor


def job():
    """Job اصلی که هر ساعت اجرا می‌شه"""
    try:
        conn, cursor = setup_database()
        pt.run_tracking_job(cursor)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error in tracking job: {e}")


def run_once():
    """اجرای یکباره برای تست"""
    print("🚀 Running tracker once...")
    job()


def run_scheduler():
    """اجرای دوره‌ای (هر 1 ساعت)"""
    print("🚀 Starting Performance Tracker Scheduler")
    print("⏰ Will run every 1 hour")
    print("Press Ctrl+C to stop\n")
    
    # اجرای فوری
    job()
    
    # برنامه‌ریزی برای هر ساعت
    schedule.every(1).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # چک هر دقیقه


def analyze_existing_signals():
    """
    تحلیل سیگنال‌های موجود (برای اولین بار)
    این تابع همه سیگنال‌های قدیمی رو track می‌کنه
    """
    conn, cursor = setup_database()
    
    print("\n" + "="*80)
    print("📊 Analyzing Existing Signals")
    print("="*80)
    
    # گرفتن تعداد کل سیگنال‌ها
    cursor.execute("SELECT COUNT(*) FROM signals")
    total_signals = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM signal_performance")
    tracked_signals = cursor.fetchone()[0]
    
    print(f"\n📈 Total Signals: {total_signals}")
    print(f"✅ Tracked Signals: {tracked_signals}")
    print(f"⏳ Pending: {total_signals - tracked_signals}")
    
    if total_signals - tracked_signals > 0:
        print(f"\n⏳ Tracking old signals... (این ممکنه چند دقیقه طول بکشه)")
        print(f"\n⏳ Tracking old signals...")
        # Track در دسته‌های 1500 تایی تا همه رو بگیره
        total_tracked = 0
        batch_size = 1500
        # از 24 ساعت تا 30 روز (720 ساعت)
        for hours in [24, 48, 72, 168, 336, 720]:
            print(f"\n🔍 Checking signals older than {hours}h ({hours//24} days)...")
            tracked = pt.track_old_signals(cursor, hours_ago=hours, batch_size=batch_size)
            if tracked > 0:
                total_tracked += tracked
                conn.commit()
                print(f"   ✅ Committed {tracked} signals to database")
            
            if tracked < batch_size:
                print(f"   ✅ No more signals for this period")
                break  # دیگه سیگنال قدیمی نداریم
        
        print(f"\n{'='*80}")
        print(f"✅ Total tracked in this run: {total_tracked}")
        print(f"{'='*80}")
    # نمایش گزارش
    print("\n")
    pt.print_performance_report(cursor)
    
    # Export برای ML
    print(f"\n📦 Exporting dataset for ML...")
    pt.export_for_ml(cursor)
    
    conn.close()
    print(f"\n✅ Analysis complete!")




def track_all_signals():
    """
    Track کردن تمام سیگنال‌های موجود (بدون محدودیت زمانی)
    برای اولین بار که می‌خواید همه 5000 تا سیگنال رو track کنید
    """
    conn, cursor = setup_database()
    print("\n" + "="*80)
    print("🚀 TRACKING ALL SIGNALS - No Time Limit")
    print("="*80)
    cursor.execute("SELECT COUNT(*) FROM signals")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM signal_performance")
    tracked = cursor.fetchone()[0]
    pending = total - tracked

    print(f"\n📊 Status:")
    print(f"   Total signals:   {total}")
    print(f"   Already tracked: {tracked}")
    print(f"   Pending:         {pending}")

    if pending == 0:
        print("\n✅ All signals already tracked!")
        conn.close()
        return
    print(f"\n⏳ This may take several minutes...")
    print(f"   Estimated time: {pending * 0.5 / 60:.1f} minutes")
    input("\nPress ENTER to continue...")
    total_tracked = 0
    batch_size = 1500

    while True:
        # Track بدون محدودیت زمانی (720 ساعت = 30 روز)
        tracked_batch = pt.track_old_signals(cursor, hours_ago=720, batch_size=batch_size)
        if tracked_batch == 0:
            break
        total_tracked += tracked_batch
        conn.commit()
        # وضعیت فعلی
        cursor.execute("SELECT COUNT(*) FROM signal_performance")
        current_tracked = cursor.fetchone()[0]
        remaining = total - current_tracked
        print(f"\n📊 Progress: {current_tracked}/{total} ({current_tracked/total*100:.1f}%)")
        print(f"   Remaining: {remaining}")
        if remaining == 0:
            break
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED!")
    print(f"   Tracked in this run: {total_tracked}")
    print(f"{'='*80}")
    # نمایش گزارش
    pt.print_performance_report(cursor)
    # Export
    pt.export_for_ml(cursor)
    conn.close()

def compare_methods():
    """
    مقایسه دقیق روش‌های مختلف
    """
    conn, cursor = setup_database()
    
    print("\n" + "="*100)
    print("🔬 DETAILED METHOD COMPARISON")
    print("="*100)
    
    methods = [
        'savesignal',      # V1
        'savesignal2',     # V2
        'v3_indicators',   # V3
        'v4_patterns',     # V4
        'v5_complete : sa',      # V5
        'v4_patterns: PR' ,     # V4
        'v5_fixed',      # V5
        'v5_complete'      # V5
    ]
    
    results = []
    
    for method in methods:
        stats = pt.calculate_win_rate(cursor, testmode=method)
        if stats:
            results.append(stats[0])
    
    if not results:
        print("⚠️ هنوز دیتای کافی نداریم!")
        conn.close()
        return
    
    # چاپ جدول مقایسه
    print(f"\n{'Method':<20} {'Signals':<10} {'Conf%':<8} {'1h Win%':<10} {'1h Avg%':<10} {'24h Win%':<10} {'24h Avg%':<10}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['testmode']:<20} "
              f"{r['total_signals']:<10} "
              f"{r['avg_confidence']:<8.1f} "
              f"{r['win_rate_1h']:<10.1f} "
              f"{r['avg_return_1h']:<+10.2f} "
              f"{r['win_rate_24h']:<10.1f} "
              f"{r['avg_return_24h']:<+10.2f}")
    
    # بهترین روش
    best = max(results, key=lambda x: (x['win_rate_1h'], x['avg_return_1h']))
    print("\n" + "="*100)
    print(f"🏆 WINNER: {best['testmode']}")
    print(f"   Win Rate (1h): {best['win_rate_1h']:.1f}%")
    print(f"   Avg Return (1h): {best['avg_return_1h']:+.2f}%")
    print("="*100)
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "once":
            # اجرای یکباره
            run_once()
        
        elif command == "analyze":
            # تحلیل سیگنال‌های موجود
            analyze_existing_signals()
        
        elif command == "compare":
            # مقایسه روش‌ها
            compare_methods()
        
        elif command == "schedule":
            # اجرای دوره‌ای
            run_scheduler()

        elif command == "track-all":
            # اجرای دوره‌ای
            track_all_signals()
        
        else:
            print("❌ Unknown command!")
            print("Usage:")
            print("  python tracker_runner.py once      - Run once")
            print("  python tracker_runner.py analyze   - Analyze existing signals")
            print("  python tracker_runner.py compare   - Compare methods")
            print("  python tracker_runner.py schedule  - Run every hour")
    
    else:
        # پیش‌فرض: تحلیل + یک بار اجرا
        print("🎯 Default mode: Analyze + Run once\n")
        analyze_existing_signals()