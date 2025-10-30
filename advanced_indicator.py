"""
ماژول اندیکاتورهای پیشرفته برای تحلیل تکنیکال
MACD, ADX, Momentum Analysis
"""

import pandas as pd
import ta
from datetime import datetime


def calculate_macd_signal(df):
    """
    محاسبه MACD و تشخیص سیگنال
    
    Returns:
        dict: {
            'macd': float,
            'signal': float,
            'histogram': float,
            'trend': 'bullish/bearish/neutral',
            'strength': int (0-100),
            'crossover': 'golden/death/none'
        }
    """
    try:
        # محاسبه MACD
        macd = ta.trend.MACD(df['close'])
        
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]
        histogram = macd.macd_diff().iloc[-1]
        
        # تشخیص کراس اوور (2 کندل اخیر)
        prev_histogram = macd.macd_diff().iloc[-2] if len(df) > 1 else 0
        
        if histogram > 0 and prev_histogram <= 0:
            crossover = 'golden'  # سیگنال خرید
        elif histogram < 0 and prev_histogram >= 0:
            crossover = 'death'   # سیگنال فروش
        else:
            crossover = 'none'
        
        # تعیین روند
        if macd_line > signal_line and histogram > 0:
            trend = 'bullish'
        elif macd_line < signal_line and histogram < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        # محاسبه قدرت (بر اساس فاصله MACD و Signal)
        strength = min(int(abs(histogram) * 100), 100)
        
        return {
            'macd': round(macd_line, 4),
            'signal': round(signal_line, 4),
            'histogram': round(histogram, 4),
            'trend': trend,
            'strength': strength,
            'crossover': crossover
        }
        
    except Exception as e:
        print(f"⚠️ MACD calculation error: {e}")
        return {
            'macd': 0,
            'signal': 0,
            'histogram': 0,
            'trend': 'neutral',
            'strength': 0,
            'crossover': 'none'
        }


def calculate_adx_strength(df):
    """
    محاسبه ADX (Average Directional Index) برای قدرت روند
    
    ADX < 25: روند ضعیف
    ADX 25-50: روند متوسط
    ADX > 50: روند قوی
    
    Returns:
        dict: {
            'adx': float,
            'di_plus': float,
            'di_minus': float,
            'trend_strength': 'weak/moderate/strong/very_strong',
            'direction': 'up/down/sideways'
        }
    """
    try:
        # محاسبه ADX
        adx_indicator = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
        
        adx_value = adx_indicator.adx().iloc[-1]
        di_plus = adx_indicator.adx_pos().iloc[-1]
        di_minus = adx_indicator.adx_neg().iloc[-1]
        
        # تعیین قدرت روند
        if adx_value < 20:
            trend_strength = 'weak'
        elif adx_value < 25:
            trend_strength = 'moderate'
        elif adx_value < 50:
            trend_strength = 'strong'
        else:
            trend_strength = 'very_strong'
        
        # تعیین جهت
        if di_plus > di_minus and adx_value > 20:
            direction = 'up'
        elif di_minus > di_plus and adx_value > 20:
            direction = 'down'
        else:
            direction = 'sideways'
        
        return {
            'adx': round(adx_value, 2),
            'di_plus': round(di_plus, 2),
            'di_minus': round(di_minus, 2),
            'trend_strength': trend_strength,
            'direction': direction
        }
        
    except Exception as e:
        print(f"⚠️ ADX calculation error: {e}")
        return {
            'adx': 0,
            'di_plus': 0,
            'di_minus': 0,
            'trend_strength': 'weak',
            'direction': 'sideways'
        }


def calculate_ema_momentum(df):
    """
    محاسبه شتاب EMA (تغییرات EMA در زمان)
    
    Returns:
        dict: {
            'ema_9': float,
            'ema_21': float,
            'ema_diff': float,
            'ema_slope': float (درجه شیب),
            'momentum': 'strong_up/weak_up/neutral/weak_down/strong_down'
        }
    """
    try:
        # محاسبه EMA
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        ema_9_current = df['ema_9'].iloc[-1]
        ema_21_current = df['ema_21'].iloc[-1]
        
        # اختلاف EMA
        ema_diff = ema_9_current - ema_21_current
        
        # شیب EMA (تغییر در 5 کندل اخیر)
        if len(df) >= 5:
            ema_9_prev = df['ema_9'].iloc[-5]
            ema_slope = (ema_9_current - ema_9_prev) / ema_9_prev * 100
        else:
            ema_slope = 0
        
        # تعیین شتاب
        if ema_diff > 0 and ema_slope > 0.5:
            momentum = 'strong_up'
        elif ema_diff > 0 and ema_slope > 0:
            momentum = 'weak_up'
        elif ema_diff < 0 and ema_slope < -0.5:
            momentum = 'strong_down'
        elif ema_diff < 0 and ema_slope < 0:
            momentum = 'weak_down'
        else:
            momentum = 'neutral'
        
        return {
            'ema_9': round(ema_9_current, 4),
            'ema_21': round(ema_21_current, 4),
            'ema_diff': round(ema_diff, 4),
            'ema_slope': round(ema_slope, 4),
            'momentum': momentum
        }
        
    except Exception as e:
        print(f"⚠️ EMA momentum error: {e}")
        return {
            'ema_9': 0,
            'ema_21': 0,
            'ema_diff': 0,
            'ema_slope': 0,
            'momentum': 'neutral'
        }


def calculate_combined_momentum(df):
    """
    ترکیب تمام اندیکاتورها برای تحلیل جامع
    
    Returns:
        dict: {
            'macd': dict,
            'adx': dict,
            'ema': dict,
            'combined_score': int (-100 to +100),
            'confidence': int (0-100),
            'signal': 'strong_buy/buy/neutral/sell/strong_sell'
        }
    """
    macd_data = calculate_macd_signal(df)
    adx_data = calculate_adx_strength(df)
    ema_data = calculate_ema_momentum(df)
    
    # محاسبه امتیاز ترکیبی
    score = 0
    confidence = 0
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ امتیاز MACD (وزن: 40%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if macd_data['crossover'] == 'golden':
        score += 40
        confidence += 20
    elif macd_data['crossover'] == 'death':
        score -= 40
        confidence += 20
    
    if macd_data['trend'] == 'bullish':
        score += macd_data['strength'] * 0.2  # حداکثر 20
    elif macd_data['trend'] == 'bearish':
        score -= macd_data['strength'] * 0.2
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ امتیاز ADX (وزن: 30%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    adx_multiplier = {
        'weak': 0.3,
        'moderate': 0.6,
        'strong': 0.9,
        'very_strong': 1.2
    }.get(adx_data['trend_strength'], 0.5)
    
    if adx_data['direction'] == 'up':
        score += 30 * adx_multiplier
        confidence += adx_data['adx'] * 0.5  # ADX بالا = اعتماد بیشتر
    elif adx_data['direction'] == 'down':
        score -= 30 * adx_multiplier
        confidence += adx_data['adx'] * 0.5
    else:
        confidence -= 10  # روند ضعیف = اعتماد کمتر
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ امتیاز EMA Momentum (وزن: 30%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    momentum_scores = {
        'strong_up': 30,
        'weak_up': 15,
        'neutral': 0,
        'weak_down': -15,
        'strong_down': -30
    }
    score += momentum_scores.get(ema_data['momentum'], 0)
    
    if abs(ema_data['ema_slope']) > 0.3:
        confidence += 10
    
    # محدود کردن به بازه
    score = max(min(score, 100), -100)
    confidence = max(min(confidence, 100), 0)
    
    # تعیین سیگنال نهایی
    if score >= 60:
        signal = 'strong_buy'
    elif score >= 30:
        signal = 'buy'
    elif score >= -30:
        signal = 'neutral'
    elif score >= -60:
        signal = 'sell'
    else:
        signal = 'strong_sell'
    
    return {
        'macd': macd_data,
        'adx': adx_data,
        'ema': ema_data,
        'combined_score': round(score, 2),
        'confidence': round(confidence, 2),
        'signal': signal
    }


def get_dataframe_from_cursor(cursor, symbol_id, limit=200):
    """
    تبدیل دیتای دیتابیس به DataFrame برای محاسبات
    """
    query = """
        SELECT price as close, timestamp
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    cursor.execute(query, (symbol_id, limit))
    results = cursor.fetchall()
    
    if len(results) < 50:
        return None
    
    # تبدیل به DataFrame
    df = pd.DataFrame(results, columns=['close', 'timestamp'])
    df = df.iloc[::-1].reset_index(drop=True)  # معکوس کردن (قدیمی به جدید)
    
    # برای ADX نیاز به high و low داریم - فرض می‌کنیم close = high = low
    # (در نسخه واقعی باید از OHLCV استفاده کنید)
    df['high'] = df['close'] * 1.001  # تقریب
    df['low'] = df['close'] * 0.999
    
    return df


def analyze_symbol_with_indicators(cursor, symbol_id, symbol_name):
    """
    تحلیل کامل یک سیمبل با تمام اندیکاتورها
    
    این تابع را در main.py صدا بزنید
    """
    df = get_dataframe_from_cursor(cursor, symbol_id)
    
    if df is None or len(df) < 50:
        print(f"⚠️ Not enough data for {symbol_name}")
        return None
    
    result = calculate_combined_momentum(df)
    
    print(f"\n{'='*60}")
    print(f"📊 Analysis for {symbol_name}")
    print(f"{'='*60}")
    
    print(f"\n📈 MACD:")
    print(f"   Trend: {result['macd']['trend']} | Strength: {result['macd']['strength']}")
    print(f"   Crossover: {result['macd']['crossover']}")
    print(f"   Histogram: {result['macd']['histogram']}")
    
    print(f"\n💪 ADX (Trend Strength):")
    print(f"   Value: {result['adx']['adx']} | Strength: {result['adx']['trend_strength']}")
    print(f"   Direction: {result['adx']['direction']}")
    
    print(f"\n🚀 EMA Momentum:")
    print(f"   Momentum: {result['ema']['momentum']}")
    print(f"   Slope: {result['ema']['ema_slope']}%")
    
    print(f"\n🎯 Combined Analysis:")
    print(f"   Score: {result['combined_score']}/100")
    print(f"   Confidence: {result['confidence']}%")
    print(f"   Signal: {result['signal']}")
    
    return result