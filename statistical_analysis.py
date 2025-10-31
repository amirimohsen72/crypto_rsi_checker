"""
ماژول تحلیل آماری و نوسانات
Phase 3: Statistical Analysis
- ATR (Average True Range)
- Bollinger Bands
- Volatility Index
- Price Momentum
- Correlation Analysis
"""

import pandas as pd
import numpy as np
import ta


def calculate_atr(df, period=14):
    """
    محاسبه ATR (Average True Range) - سنجش نوسانات
    
    ATR بالا = نوسانات زیاد = ریسک بیشتر
    ATR پایین = نوسانات کم = ریسک کمتر
    
    Returns:
        dict: {
            'atr': float,
            'atr_percent': float (درصد نسبت به قیمت),
            'volatility': 'very_low/low/normal/high/very_high',
            'risk_level': int (0-100)
        }
    """
    try:
        if len(df) < period:
            return _empty_atr_result()
        
        # محاسبه ATR
        atr_indicator = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], window=period
        )
        
        atr_value = atr_indicator.average_true_range().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # ATR به صورت درصد
        atr_percent = (atr_value / current_price) * 100
        
        # تعیین سطح نوسانات
        if atr_percent < 0.5:
            volatility = 'very_low'
            risk_level = 20
        elif atr_percent < 1.0:
            volatility = 'low'
            risk_level = 35
        elif atr_percent < 2.0:
            volatility = 'normal'
            risk_level = 50
        elif atr_percent < 3.5:
            volatility = 'high'
            risk_level = 75
        else:
            volatility = 'very_high'
            risk_level = 95
        
        return {
            'atr': round(atr_value, 4),
            'atr_percent': round(atr_percent, 2),
            'volatility': volatility,
            'risk_level': risk_level
        }
        
    except Exception as e:
        print(f"⚠️ ATR calculation error: {e}")
        return _empty_atr_result()


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """
    محاسبه Bollinger Bands
    
    وقتی قیمت به باند پایین نزدیکه = احتمال صعود
    وقتی قیمت به باند بالا نزدیکه = احتمال ریزش
    
    Returns:
        dict: {
            'upper_band': float,
            'middle_band': float,
            'lower_band': float,
            'current_position': float (0-100, 0=lower, 100=upper),
            'bandwidth': float (فاصله باندها),
            'signal': 'oversold/overbought/neutral'
        }
    """
    try:
        if len(df) < period:
            return _empty_bb_result()
        
        # محاسبه Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(
            df['close'], window=period, window_dev=std_dev
        )
        
        upper = bb_indicator.bollinger_hband().iloc[-1]
        middle = bb_indicator.bollinger_mavg().iloc[-1]
        lower = bb_indicator.bollinger_lband().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        
        # موقعیت فعلی (0-100)
        if upper != lower:
            position = ((current_price - lower) / (upper - lower)) * 100
        else:
            position = 50
        
        # عرض باند (نشان‌دهنده نوسانات)
        bandwidth = ((upper - lower) / middle) * 100
        
        # تعیین سیگنال
        if position < 20:
            signal = 'oversold'  # نزدیک باند پایین - خرید
        elif position > 80:
            signal = 'overbought'  # نزدیک باند بالا - فروش
        else:
            signal = 'neutral'
        
        return {
            'upper_band': round(upper, 4),
            'middle_band': round(middle, 4),
            'lower_band': round(lower, 4),
            'current_position': round(position, 2),
            'bandwidth': round(bandwidth, 2),
            'signal': signal
        }
        
    except Exception as e:
        print(f"⚠️ Bollinger Bands error: {e}")
        return _empty_bb_result()


def calculate_price_momentum(df, lookback=14):
    """
    محاسبه شتاب قیمت (Rate of Change)
    
    Returns:
        dict: {
            'roc': float (درصد تغییر),
            'momentum': 'strong_bullish/bullish/neutral/bearish/strong_bearish',
            'acceleration': float (تغییر سرعت)
        }
    """
    try:
        if len(df) < lookback + 5:
            return {
                'roc': 0,
                'momentum': 'neutral',
                'acceleration': 0
            }
        
        current_price = df['close'].iloc[-1]
        past_price = df['close'].iloc[-lookback]
        
        # Rate of Change
        roc = ((current_price - past_price) / past_price) * 100
        
        # شتاب (تغییر ROC)
        if len(df) >= lookback + 5:
            prev_roc = ((df['close'].iloc[-5] - df['close'].iloc[-lookback-5]) / 
                       df['close'].iloc[-lookback-5]) * 100
            acceleration = roc - prev_roc
        else:
            acceleration = 0
        
        # تعیین momentum
        if roc > 5:
            momentum = 'strong_bullish'
        elif roc > 2:
            momentum = 'bullish'
        elif roc > -2:
            momentum = 'neutral'
        elif roc > -5:
            momentum = 'bearish'
        else:
            momentum = 'strong_bearish'
        
        return {
            'roc': round(roc, 2),
            'momentum': momentum,
            'acceleration': round(acceleration, 2)
        }
        
    except Exception as e:
        print(f"⚠️ Momentum error: {e}")
        return {'roc': 0, 'momentum': 'neutral', 'acceleration': 0}


def calculate_volatility_index(df):
    """
    محاسبه شاخص نوسانات سفارشی
    
    ترکیب ATR + Standard Deviation + Price Range
    
    Returns:
        dict: {
            'volatility_index': float (0-100),
            'trend': 'increasing/stable/decreasing',
            'risk_adjusted_score': float
        }
    """
    try:
        if len(df) < 20:
            return {
                'volatility_index': 50,
                'trend': 'stable',
                'risk_adjusted_score': 0
            }
        
        # 1. Standard Deviation (20 دوره)
        std_dev = df['close'].rolling(window=20).std().iloc[-1]
        mean_price = df['close'].rolling(window=20).mean().iloc[-1]
        cv = (std_dev / mean_price) * 100  # Coefficient of Variation
        
        # 2. Price Range
        high_20 = df['high'].rolling(window=20).max().iloc[-1]
        low_20 = df['low'].rolling(window=20).min().iloc[-1]
        price_range = ((high_20 - low_20) / mean_price) * 100
        
        # 3. ترکیب
        volatility_index = (cv * 0.6) + (price_range * 0.4)
        volatility_index = min(volatility_index * 10, 100)  # نرمال‌سازی
        
        # روند نوسانات
        if len(df) >= 40:
            recent_vol = df['close'].iloc[-20:].std()
            past_vol = df['close'].iloc[-40:-20].std()
            
            if recent_vol > past_vol * 1.2:
                trend = 'increasing'
            elif recent_vol < past_vol * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'volatility_index': round(volatility_index, 2),
            'trend': trend,
            'std_dev': round(std_dev, 4)
        }
        
    except Exception as e:
        print(f"⚠️ Volatility index error: {e}")
        return {
            'volatility_index': 50,
            'trend': 'stable',
            'std_dev': 0
        }


def calculate_statistical_score(atr_data, bb_data, momentum_data, volatility_data):
    """
    محاسبه امتیاز آماری ترکیبی - بهینه شده
    
    Returns:
        dict: {
            'score': int (-100 to +100),
            'risk_level': int (0-100),
            'confidence': int (0-100),
            'recommendation': str
        }
    """
    score = 0
    risk_level = 50
    confidence = 50
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ امتیاز Bollinger Bands (50%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    bb_signal = bb_data['signal']
    bb_position = bb_data['current_position']
    
    # امتیاز قوی‌تر برای oversold/overbought
    if bb_signal == 'oversold':
        score += 50
        confidence += 20
        # هرچی پایین‌تر باشه، امتیاز بیشتر
        if bb_position < 10:
            score += 30  # خیلی پایین
        elif bb_position < 20:
            score += 15
    elif bb_signal == 'overbought':
        score -= 50
        confidence += 20
        if bb_position > 90:
            score -= 30  # خیلی بالا
        elif bb_position > 80:
            score -= 15
    
    # ✅ امتیاز بر اساس موقعیت دقیق (حتی اگه neutral باشه)
    if bb_position < 30:
        score += 20
    elif bb_position > 70:
        score -= 20
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ امتیاز Momentum (30%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    momentum_scores = {
        'strong_bullish': 30,
        'bullish': 15,
        'neutral': 0,
        'bearish': -15,
        'strong_bearish': -30
    }
    momentum_score = momentum_scores.get(momentum_data['momentum'], 0)
    score += momentum_score
    
    # شتاب مثبت = اعتماد بیشتر
    if abs(momentum_data['acceleration']) > 1:
        confidence += 10
    
    # بونوس برای momentum قوی
    if momentum_data['momentum'] in ['strong_bullish', 'strong_bearish']:
        confidence += 15
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ تنظیم ریسک بر اساس ATR (20%)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    risk_level = atr_data['risk_level']
    
    # نوسانات بالا = کاهش اعتماد
    if atr_data['volatility'] in ['high', 'very_high']:
        confidence *= 0.85  # کمتر از قبل
        risk_level += 10
    elif atr_data['volatility'] in ['very_low', 'low']:
        confidence *= 1.05
        risk_level -= 5
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4️⃣ چک volatility index
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if volatility_data['trend'] == 'increasing':
        risk_level += 5
        confidence *= 0.95
    elif volatility_data['trend'] == 'decreasing':
        confidence *= 1.02
    
    # محدود کردن
    score = max(min(score, 100), -100)
    risk_level = max(min(risk_level, 100), 0)
    confidence = max(min(confidence, 100), 0)
    
    # توصیه
    if risk_level > 80:
        recommendation = "ریسک بسیار بالا - احتیاط شدید"
    elif risk_level > 60:
        recommendation = "ریسک بالا - مدیریت سرمایه دقیق"
    elif risk_level > 40:
        recommendation = "ریسک متوسط - قابل قبول"
    else:
        recommendation = "ریسک پایین - مناسب"
    
    return {
        'score': round(score, 2),
        'risk_level': round(risk_level, 2),
        'confidence': round(confidence, 2),
        'recommendation': recommendation
    }


def analyze_statistical(cursor, symbol_id, current_price):
    """
    تحلیل کامل آماری یک سیمبل
    
    این تابع در main.py صدا زده می‌شود
    """
    # دریافت دیتا
    query = """
        SELECT price as close, price as high, price as low, timestamp
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 100
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 30:
        return None
    
    # تبدیل به DataFrame
    df = pd.DataFrame(results, columns=['close', 'high', 'low', 'timestamp'])
    df = df.iloc[::-1].reset_index(drop=True)
    
    # تقریب high/low
    df['high'] = df['close'] * 1.005
    df['low'] = df['close'] * 0.995
    
    # محاسبه اندیکاتورها
    atr_data = calculate_atr(df)
    bb_data = calculate_bollinger_bands(df)
    momentum_data = calculate_price_momentum(df)
    volatility_data = calculate_volatility_index(df)
    
    # امتیاز نهایی
    stat_score = calculate_statistical_score(atr_data, bb_data, momentum_data, volatility_data)
    
    return {
        'atr': atr_data,
        'bollinger': bb_data,
        'momentum': momentum_data,
        'volatility': volatility_data,
        'score': stat_score['score'],
        'risk_level': stat_score['risk_level'],
        'confidence': stat_score['confidence'],
        'recommendation': stat_score['recommendation']
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _empty_atr_result():
    return {
        'atr': 0,
        'atr_percent': 0,
        'volatility': 'unknown',
        'risk_level': 50
    }


def _empty_bb_result():
    return {
        'upper_band': 0,
        'middle_band': 0,
        'lower_band': 0,
        'current_position': 50,
        'bandwidth': 0,
        'signal': 'neutral'
    }


def print_statistical_analysis(symbol_name, analysis):
    """چاپ زیبای نتایج تحلیل آماری"""
    if not analysis:
        print(f"⚠️ Not enough data for statistical analysis: {symbol_name}")
        return
    
    print(f"\n{'═'*65}")
    print(f"📊 Statistical Analysis: {symbol_name}")
    print(f"{'═'*65}")
    
    # ATR
    atr = analysis['atr']
    print(f"\n📉 ATR (Volatility):")
    print(f"   Value:      {atr['atr']} ({atr['atr_percent']:.2f}%)")
    print(f"   Level:      {atr['volatility']}")
    print(f"   Risk:       {atr['risk_level']}/100")
    
    # Bollinger Bands
    bb = analysis['bollinger']
    print(f"\n📊 Bollinger Bands:")
    print(f"   Upper:      {bb['upper_band']}")
    print(f"   Middle:     {bb['middle_band']}")
    print(f"   Lower:      {bb['lower_band']}")
    print(f"   Position:   {bb['current_position']:.1f}% ({bb['signal']})")
    print(f"   Bandwidth:  {bb['bandwidth']:.2f}%")
    
    # Momentum
    mom = analysis['momentum']
    print(f"\n🚀 Price Momentum:")
    print(f"   ROC:        {mom['roc']:+.2f}%")
    print(f"   Status:     {mom['momentum']}")
    print(f"   Accel:      {mom['acceleration']:+.2f}%")
    
    # Volatility Index
    vol = analysis['volatility']
    print(f"\n📈 Volatility Index:")
    print(f"   Index:      {vol['volatility_index']:.1f}/100")
    print(f"   Trend:      {vol['trend']}")
    
    # Final Score
    print(f"\n🎯 Statistical Score:")
    print(f"   Score:      {analysis['score']:+.2f}/100")
    print(f"   Risk:       {analysis['risk_level']:.1f}/100")
    print(f"   Confidence: {analysis['confidence']:.1f}%")
    print(f"   📝 {analysis['recommendation']}")