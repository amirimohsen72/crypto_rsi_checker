"""
ماژول امتیازدهی برای سیگنال‌های معاملاتی
"""


from datetime import datetime
import json
import winsound
import pytz

tz_tehran = pytz.timezone("Asia/Tehran")



def calculate_advanced_score(rsi_values, rsi_trends, rsi_changes, price_trend=None):
    """
    محاسبه امتیاز پیشرفته با در نظر گرفتن RSI، روند و قدرت تغییر
    
    Args:
        rsi_values (dict): دیکشنری RSI برای هر تایم‌فریم {'1m': 45.2, '5m': 48.1, ...}
        rsi_trends (dict): دیکشنری روند برای هر تایم‌فریم {'1m': 'up', '5m': 'down', ...}
        rsi_changes (dict): دیکشنری تغییر RSI {'1m': 2.5, '5m': -1.3, ...}
    
    Returns:
        float: امتیاز بین -100 تا +100
    """
    total_score = 0
    # وزن هر تایم‌فریم

        # وزن‌ها برای ترید کوتاه‌مدت
    timeframe_weights = {
        "1m": 0.40,   # خیلی مهم برای اسکالپ
        "5m": 0.30,   # مهم
        "15m": 0.20,  # متوسط
        "1h": 0.07,   # کمتر مهم
        "4h": 0.03    # مرجع کلی
    }

    # وزن هر فاکتور
    factor_weights = {
        "rsi": 0.40,
        "trend": 0.30,
        "momentum": 0.20,
        "convergence": 0.10
    }
    
    for tf in ["1m", "5m", "15m", "1h", "4h"]:
        tf_weight = timeframe_weights.get(tf, 0)
        
        rsi = rsi_values.get(tf)
        trend = rsi_trends.get(tf)
        change = rsi_changes.get(tf, 0)
        
        if rsi is None:
            continue
        
        #  امتیاز RSI
        rsi_score = calculate_rsi_score(rsi)
        
        #  امتیاز روند
        trend_score = calculate_trend_score(rsi, trend)
        
        #  امتیاز قدرت تغییر
        momentum_score = calculate_momentum_score(rsi, change)
        
        # جمع امتیازها
        tf_total = (
            rsi_score * factor_weights["rsi"] +
            trend_score * factor_weights["trend"] +
            momentum_score * factor_weights["momentum"]
        )
        
        total_score += tf_total * tf_weight
    
    #  امتیاز همگرایی
    convergence_score = calculate_convergence_score(rsi_trends)

    total_score += convergence_score * factor_weights["convergence"]
    

    # ✅ کاهش امتیاز اگه همگرایی ضعیف باشه
    trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
    up_count = trends_list.count("up")
    down_count = trends_list.count("down")
    max_trend = max(up_count, down_count)
        
    if max_trend < 2:
        total_score = total_score * 0.7  # 30% کاهش (کمتر از قبل)
    elif max_trend < 3:
        total_score = total_score * 0.85  # 15% کاهش (کمتر از قبل)
    
    # محدود به بازه -100 تا +100
    
    if price_trend:
        if total_score > 0 and price_trend == "down":
            # سیگنال خرید ولی قیمت داره میریزه → کاهش امتیاز
            total_score = total_score * 0.6
        elif total_score < 0 and price_trend == "up":
            # سیگنال فروش ولی قیمت داره میره بالا → کاهش امتیاز
            total_score = total_score * 0.6

    
    total_score = max(min(total_score, 100), -100)
    
    return round(total_score, 2)



def calculate_price_trend_smart(cursor, symbol_id, current_price, rsi_values):
    """
    ✅ محاسبه روند قیمت متناسب با تایم‌فریم‌های فعال
    
    اگه فقط 1m و 5m داده داریم → روند کوتاه‌مدت چک میشه
    اگه تا 1h و 4h داده داریم → روند بلندمدت‌تر چک میشه
    """
    # تشخیص بالاترین تایم‌فریم موجود
    has_4h = '4h' in rsi_values and rsi_values['4h'] is not None
    has_1h = '1h' in rsi_values and rsi_values['1h'] is not None
    has_15m = '15m' in rsi_values and rsi_values['15m'] is not None
    
    # انتخاب تعداد قیمت بر اساس تایم‌فریم‌های موجود
    if has_4h:
        lookback = 50  # 50 تا قیمت (روند بلندمدت)
        threshold = 0.5  # آستانه 0.5%
    elif has_1h:
        lookback = 30  # 30 تا قیمت (روند متوسط)
        threshold = 0.4
    elif has_15m:
        lookback = 15  # 15 تا قیمت (روند کوتاه‌مدت)
        threshold = 0.3
    else:
        lookback = 10  # 10 تا قیمت (روند خیلی کوتاه‌مدت)
        threshold = 0.3
    
    # گرفتن قیمت‌ها
    query = """
        SELECT price
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    cursor.execute(query, (symbol_id, lookback))
    results = cursor.fetchall()
    
    if len(results) < max(3, lookback // 2):
        return "neutral"
    
    prices = [r[0] for r in results]
    
    # روش 1: مقایسه با میانگین (ساده)
    avg_price = sum(prices) / len(prices)
    change_percent = ((current_price - avg_price) / avg_price) * 100
    
    if change_percent > threshold:
        return "up"
    elif change_percent < -threshold:
        return "down"
    else:
        return "neutral"
    

    

def calculate_price_trend_simple(cursor, symbol_id, current_price):
    """
    ✅ روش ساده: مقایسه با میانگین 5 قیمت قبلی
    """
    query = """
        SELECT price
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 5
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 3:
        return "neutral"
    
    avg_previous_price = sum(r[0] for r in results) / len(results)
    change_percent = ((current_price - avg_previous_price) / avg_previous_price) * 100
    
    if change_percent > 0.3:
        return "up"
    elif change_percent < -0.3:
        return "down"
    else:
        return "neutral"



def calculate_price_trend(cursor, symbol_id):
    """
    ✅ محاسبه روند قیمت با EMA
    """
    # گرفتن 50 تا آخرین قیمت
    query = """
        SELECT price, timestamp
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 50
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 20:
        return "neutral"
    
    prices = [r[0] for r in reversed(results)]
    
    # محاسبه EMA کوتاه و بلند مدت
    import pandas as pd
    df = pd.DataFrame(prices, columns=['price'])
    df['ema_9'] = df['price'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['price'].ewm(span=21, adjust=False).mean()
    
    last_price = df['price'].iloc[-1]
    ema_9 = df['ema_9'].iloc[-1]
    ema_21 = df['ema_21'].iloc[-1]
    
    # تشخیص روند
    if ema_9 > ema_21 and last_price > ema_9:
        return "up"
    elif ema_9 < ema_21 and last_price < ema_9:
        return "down"
    else:
        return "neutral"

def calculate_signal_quality(rsi_values, rsi_trends, score, price_trend=None):
    """
    محاسبه کیفیت سیگنال (0 تا 100)
    """
    # quality = 50
    quality = 40  # ✅ شروع از 40 به جای 50
    # ✅ همگرایی
    trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
    up_count = trends_list.count("up")
    down_count = trends_list.count("down")
    max_trend = max(up_count, down_count)
    
    if max_trend >= 5:
        quality += 35  # ✅ همه تایم‌فریم‌ها
    elif max_trend >= 4:
        quality += 30  # ✅ 4 تا همجهت
    elif max_trend >= 3:
        quality += 20  # ✅ 3 تا همجهت
    elif max_trend >= 2:
        quality += 10  # ✅ 2 تا همجهت
    
    # ✅ شدت overbought/oversold  (بررسی همه تایم‌فریم‌ها)
    important_tf = ['1m', '5m', '15m']
    all_timeframes = ['1m', '5m', '15m', '1h', '4h'] 

    if score > 0:  # سیگنال خرید
        oversold_count = sum(1 for tf in all_timeframes if rsi_values.get(tf, 50) < 30)
        quality += oversold_count *  6  # هر تایم‌فریم oversold = +6
        
        # اگه RSI خیلی پایین باشه بهتره
        extreme_oversold = sum(1 for tf in all_timeframes if rsi_values.get(tf, 50) < 20)
        quality += extreme_oversold *  4  #  خیلی پایین = +4
        
    else:  # سیگنال فروش
        overbought_count = sum(1 for tf in all_timeframes if rsi_values.get(tf, 50) > 70)
        quality += overbought_count *  6
        
        # اگه RSI خیلی بالا باشه بهتره
        extreme_overbought = sum(1 for tf in all_timeframes if rsi_values.get(tf, 50) > 80)
        quality += extreme_overbought * 4
    
    # ✅ قدرت امتیاز
    if abs(score) > 70:
        quality +=  15  # امتیاز خیلی قوی
    elif abs(score) > 50:
        
        quality += 10

    elif abs(score) > 30:
        quality += 5
    
        # ✅ فیلتر جدید: کاهش کیفیت اگه با روند قیمت مخالف باشه
    if price_trend:
        if score > 0 and price_trend == "down":
            quality = quality * 0.5  # خرید در روند نزولی = کیفیت پایین
        elif score < 0 and price_trend == "up":
            quality = quality * 0.5  # فروش در روند صعودی = کیفیت پایین
        elif score > 0 and price_trend == "up":
            quality = quality * 1.2  # خرید در روند صعودی = بهتر
        elif score < 0 and price_trend == "down":
            quality = quality * 1.2  # فروش در روند نزولی = بهتر
    
    return min(int(quality), 100)


def calculate_rsi_score(rsi):
    """محاسبه امتیاز بر اساس مقدار RSI"""
    if rsi < 20:
        return 100
    elif rsi < 30:
        return 70 + (30 - rsi) * 3
    elif rsi < 40:
        return 30 + (40 - rsi) * 4
    elif rsi < 50:
        return (50 - rsi) * 3
    elif rsi == 50:
        return 0
    elif rsi < 60:
        return -(rsi - 50) * 3
    elif rsi < 70:
        return -30 - (rsi - 60) * 4
    elif rsi < 80:
        return -70 - (rsi - 70) * 3
    else:
        return -100


def calculate_trend_score(rsi, trend):
    """محاسبه امتیاز بر اساس روند"""
    if trend == "up":
        if rsi < 40:
            return 80
        elif rsi < 50:
            return 50
        elif rsi > 70:
            return -30
        else:
            return 20
    
    elif trend == "down":
        if rsi > 60:
            return -80
        elif rsi > 50:
            return -50
        elif rsi < 30:
            return 30
        else:
            return -20
    
    return 0


def calculate_momentum_score(rsi, change):
    """محاسبه امتیاز بر اساس قدرت تغییر"""
    abs_change = abs(change)
    
    if abs_change > 10:
        momentum_strength = 100
    elif abs_change > 5:
        momentum_strength = 70
    elif abs_change > 3:
        momentum_strength = 40
    elif abs_change > 1.5:
        momentum_strength = 20
    else:
        momentum_strength = 0
    
    if change > 0:
        if rsi < 40:
            return momentum_strength
        elif rsi > 70:
            return -momentum_strength * 0.5
        else:
            return momentum_strength * 0.7
    else:
        if rsi > 60:
            return -momentum_strength
        elif rsi < 30:
            return momentum_strength * 0.5
        else:
            return -momentum_strength * 0.7


def calculate_convergence_score(rsi_trends):
    """محاسبه امتیاز همگرایی تایم‌فریم‌ها"""
    trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
    
    if len(trends_list) >= 3:
        up_count = trends_list.count("up")
        down_count = trends_list.count("down")
        
        if up_count >= 4:
            return 100
        elif up_count >= 3:
            return 50
        elif down_count >= 4:
            return -100
        elif down_count >= 3:
            return -50
    
    return 0




def allowed_save(score, rsi_trends, rsi_values, price_trend=None):
    """
     بررسی محدوده های جذاب  = ذخیره
    
    Returns:
        True , False
    """
    quality = calculate_signal_quality(rsi_values, rsi_trends, score, price_trend)

    if price_trend:
        if (score > 0 and price_trend == "down") or (score < 0 and price_trend == "up"):
            # سیگنال مخالف روند
            if quality < 75:
                return False  # فقط کیفیت 75+ قبوله
    
    #   فقط سیگنال‌های با کیفیت بالای 50 ذخیره شن
    if quality < 50: # 60 to 50
        return False
 
    #  شرایط راحت‌تر
    if quality >= 75:
        return abs(score) >= 10  # هر سیگنالی با کیفیت عالی
    elif quality >= 60:
        return abs(score) >= 15  # سیگنال‌های ضعیف با کیفیت خوب
    elif quality >= 50:
        return abs(score) >= 25  # سیگنال‌های متوسط
    else:
        return abs(score) >= 40  # فقط سیگنال‌های قوی


def save_signals(c_cursor , symbol_id , SYMBOL , last_price, rsi_values, rsi_trends, advanced_score , score):
    """
    ذخیره سیگنال های مهم
    """
    # save_signals(cursor , symbol_id , SYMBOL , last_price, rsi_values, rsi_trends, advanced_score , score)
    # price_trend = calculate_price_trend(c_cursor, symbol_id)
    price_trend = calculate_price_trend_simple(c_cursor, symbol_id, last_price)
    if allowed_save(advanced_score, rsi_trends, rsi_values, price_trend):
        signal_label = get_score_description(advanced_score)
        quality = calculate_signal_quality(rsi_values, rsi_trends, advanced_score, price_trend)


        # شمارش همگرایی
        trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
        up_count = trends_list.count("up")
        down_count = trends_list.count("down")
        convergence_count = max(up_count, down_count)
        

        now = datetime.now(tz_tehran)
        c_cursor.execute(
            "INSERT INTO signals (symbol_id, price, symbol_name, rsi_values, signal_type ,advance_score ,score , signal_label, quality, convergence_count,price_trend,time ) VALUES (?,?, ?, ?, ?, ?,?,?,?,?,?,?)",
            (symbol_id, last_price, SYMBOL, json.dumps(rsi_values), json.dumps(rsi_trends) ,advanced_score ,score ,signal_label, quality, convergence_count, price_trend,now)
        )


        # آلارم بر اساس کیفیت
        if quality >= 85:
            for _ in range(3):
                winsound.Beep(2000, 200)
            print(f"🔔🔔🔔 EXCELLENT! {SYMBOL} | Score: {advanced_score} | Quality: {quality}% | Conv: {convergence_count}/5")
            
        elif quality >= 75:
            for _ in range(2):
                winsound.Beep(1600, 250)
            print(f"🔔🔔 GOOD! {SYMBOL} | Score: {advanced_score} | Quality: {quality}% | Conv: {convergence_count}/5")
            
        elif quality >= 60:
            winsound.Beep(1200, 300)
            print(f"🔔 Signal: {SYMBOL} | Score: {advanced_score} | Quality: {quality}% | Conv: {convergence_count}/5")

        elif advanced_score >30 or advanced_score<-30:
            freq = 1600 
            winsound.Beep(freq, 400)
            print(f"✅ signal saved: {SYMBOL} - {signal_label}")
        return True
        # conn.commit()
    return False


def get_score_label(score):
    """
    برچسب، رنگ و کلاس CSS برای نمایش امتیاز
    
    Returns:
        tuple: (label, color, css_class)
    """
    if score >= 70:
        return "🟢 خرید قوی", "green", "strong-buy"
    elif score >= 40:
        return "🟢 خرید", "green", "buy"
    elif score >= 10:
        return "🟡 خرید ضعیف", "olive", "weak-buy"
    elif score >= -10:
        return "⚪ خنثی", "gray", "neutral"
    elif score >= -40:
        return "🟡 فروش ضعیف", "orange", "weak-sell"
    elif score >= -70:
        return "🔴 فروش", "red", "sell"
    else:
        return "🔴 فروش قوی", "darkred", "strong-sell"


def get_score_description(score):
    """توضیح کامل امتیاز"""
    if score >= 70:
        return "سیگنال خرید بسیار قوی. فرصت مناسب برای ورود."
    elif score >= 40:
        return "سیگنال خرید خوب. میتوانید وارد معامله شوید."
    elif score >= 10:
        return "سیگنال خرید ضعیف. با احتیاط وارد شوید."
    elif score >= -10:
        return "بازار خنثی است. منتظر سیگنال بهتر بمانید."
    elif score >= -40:
        return "سیگنال فروش ضعیف. در صورت داشتن پوزیشن احتیاط کنید."
    elif score >= -70:
        return "سیگنال فروش. زمان خروج یا شورت."
    else:
        return "سیگنال فروش بسیار قوی. خروج فوری یا ورود به شورت."