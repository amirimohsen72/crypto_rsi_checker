"""
ماژول امتیازدهی برای سیگنال‌های معاملاتی
"""


def calculate_advanced_score(rsi_values, rsi_trends, rsi_changes):
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
    timeframe_weights = {
        "1m": 0.35,
        "5m": 0.30,
        "15m": 0.20,
        "1h": 0.10,
        "4h": 0.05
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
    
    # محدود به بازه -100 تا +100
    total_score = max(min(total_score, 100), -100)
    
    return round(total_score, 2)


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