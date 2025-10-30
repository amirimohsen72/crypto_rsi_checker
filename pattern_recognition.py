"""
ماژول تشخیص الگوهای کندل استیک و سطوح حمایت/مقاومت
Phase 2: Pattern Recognition
"""

import pandas as pd
import numpy as np
from datetime import datetime


def detect_candlestick_patterns(df):
    """
    تشخیص الگوهای کندل استیک معروف
    
    Returns:
        dict: {
            'doji': bool,
            'hammer': bool,
            'shooting_star': bool,
            'engulfing_bullish': bool,
            'engulfing_bearish': bool,
            'morning_star': bool,
            'evening_star': bool,
            'pattern_score': int (-100 to +100)
        }
    """
    if len(df) < 3:
        return _empty_pattern_result()
    
    # محاسبه body و shadow
    df = df.copy()
    df['body'] = abs(df['close'] - df['open'])
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
    df['total_range'] = df['high'] - df['low']
    
    patterns = {
        'doji': False,
        'hammer': False,
        'shooting_star': False,
        'engulfing_bullish': False,
        'engulfing_bearish': False,
        'morning_star': False,
        'evening_star': False
    }
    
    score = 0
    
    # آخرین کندل
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None
    
    # ✅ Doji (بدنه خیلی کوچک)
    if last['body'] < last['total_range'] * 0.1:
        patterns['doji'] = True
        score += 0  # خنثی
    
    # ✅ Hammer (چکش - سیگنال خرید)
    if (last['lower_shadow'] > last['body'] * 2 and 
        last['upper_shadow'] < last['body'] * 0.3 and
        last['close'] > last['open']):
        patterns['hammer'] = True
        score += 60
    
    # ✅ Shooting Star (ستاره دنباله‌دار - سیگنال فروش)
    if (last['upper_shadow'] > last['body'] * 2 and 
        last['lower_shadow'] < last['body'] * 0.3 and
        last['close'] < last['open']):
        patterns['shooting_star'] = True
        score -= 60
    
    # ✅ Engulfing Patterns (پوشاننده)
    if prev is not None:
        # Bullish Engulfing
        if (prev['close'] < prev['open'] and  # کندل قبلی نزولی
            last['close'] > last['open'] and  # کندل فعلی صعودی
            last['open'] < prev['close'] and
            last['close'] > prev['open']):
            patterns['engulfing_bullish'] = True
            score += 70
        
        # Bearish Engulfing
        if (prev['close'] > prev['open'] and  # کندل قبلی صعودی
            last['close'] < last['open'] and  # کندل فعلی نزولی
            last['open'] > prev['close'] and
            last['close'] < prev['open']):
            patterns['engulfing_bearish'] = True
            score -= 70
    
    # ✅ Morning Star / Evening Star (3 کندلی)
    if len(df) >= 3:
        candle_1 = df.iloc[-3]
        candle_2 = df.iloc[-2]
        candle_3 = df.iloc[-1]
        
        # Morning Star (سیگنال خرید)
        if (candle_1['close'] < candle_1['open'] and  # نزولی
            candle_2['body'] < candle_1['body'] * 0.3 and  # بدنه کوچک
            candle_3['close'] > candle_3['open'] and  # صعودی
            candle_3['close'] > (candle_1['open'] + candle_1['close']) / 2):
            patterns['morning_star'] = True
            score += 80
        
        # Evening Star (سیگنال فروش)
        if (candle_1['close'] > candle_1['open'] and  # صعودی
            candle_2['body'] < candle_1['body'] * 0.3 and  # بدنه کوچک
            candle_3['close'] < candle_3['open'] and  # نزولی
            candle_3['close'] < (candle_1['open'] + candle_1['close']) / 2):
            patterns['evening_star'] = True
            score -= 80
    
    patterns['pattern_score'] = max(min(score, 100), -100)
    
    return patterns


def detect_support_resistance(df, current_price, lookback=50):
    """
    تشخیص سطوح حمایت و مقاومت
    
    Returns:
        dict: {
            'support_levels': [price1, price2, ...],
            'resistance_levels': [price1, price2, ...],
            'nearest_support': float,
            'nearest_resistance': float,
            'distance_to_support': float (درصد),
            'distance_to_resistance': float (درصد),
            'position': 'near_support/near_resistance/middle'
        }
    """
    if len(df) < lookback:
        lookback = len(df)
    
    recent_df = df.tail(lookback)
    
    # پیدا کردن local minima (حمایت) و maxima (مقاومت)
    highs = recent_df['high'].values
    lows = recent_df['low'].values
    
    support_levels = []
    resistance_levels = []
    
    # الگوریتم ساده: پیدا کردن نقاط برگشت
    window = 5
    
    for i in range(window, len(lows) - window):
        # حمایت: کمترین مقدار در پنجره
        if lows[i] == min(lows[i-window:i+window+1]):
            support_levels.append(lows[i])
        
        # مقاومت: بیشترین مقدار در پنجره
        if highs[i] == max(highs[i-window:i+window+1]):
            resistance_levels.append(highs[i])
    
    # حذف سطوح نزدیک به هم (clustering)
    support_levels = _cluster_levels(support_levels, current_price, 0.005)
    resistance_levels = _cluster_levels(resistance_levels, current_price, 0.005)
    
    # پیدا کردن نزدیک‌ترین سطوح
    supports_below = [s for s in support_levels if s < current_price]
    resistances_above = [r for r in resistance_levels if r > current_price]
    
    nearest_support = max(supports_below) if supports_below else min(support_levels) if support_levels else current_price * 0.95
    nearest_resistance = min(resistances_above) if resistances_above else max(resistance_levels) if resistance_levels else current_price * 1.05
    
    # محاسبه فاصله
    dist_to_support = ((current_price - nearest_support) / current_price) * 100
    dist_to_resistance = ((nearest_resistance - current_price) / current_price) * 100
    
    # تعیین موقعیت
    if dist_to_support < 0.5:
        position = 'near_support'
    elif dist_to_resistance < 0.5:
        position = 'near_resistance'
    else:
        position = 'middle'
    
    return {
        'support_levels': sorted(support_levels),
        'resistance_levels': sorted(resistance_levels),
        'nearest_support': round(nearest_support, 4),
        'nearest_resistance': round(nearest_resistance, 4),
        'distance_to_support': round(dist_to_support, 2),
        'distance_to_resistance': round(dist_to_resistance, 2),
        'position': position
    }


def detect_chart_patterns(df):
    """
    تشخیص الگوهای نموداری (Chart Patterns)
    
    - Head and Shoulders
    - Double Top/Bottom
    - Triangle
    - Wedge
    """
    if len(df) < 20:
        return {
            'pattern': 'none',
            'confidence': 0,
            'signal': 'neutral'
        }
    
    highs = df['high'].tail(20).values
    lows = df['low'].tail(20).values
    
    # الگوریتم ساده برای Double Top/Bottom
    pattern = 'none'
    confidence = 0
    signal = 'neutral'
    
    # Double Top
    max_idx = np.argsort(highs)[-2:]  # 2 قله اصلی
    if len(max_idx) == 2:
        peak1, peak2 = highs[max_idx[0]], highs[max_idx[1]]
        if abs(peak1 - peak2) / peak1 < 0.02:  # 2% اختلاف
            pattern = 'double_top'
            confidence = 60
            signal = 'sell'
    
    # Double Bottom
    min_idx = np.argsort(lows)[:2]  # 2 دره اصلی
    if len(min_idx) == 2:
        bottom1, bottom2 = lows[min_idx[0]], lows[min_idx[1]]
        if abs(bottom1 - bottom2) / bottom1 < 0.02:
            pattern = 'double_bottom'
            confidence = 60
            signal = 'buy'
    
    return {
        'pattern': pattern,
        'confidence': confidence,
        'signal': signal
    }


def calculate_pattern_score(candlestick_patterns, sr_levels, chart_patterns):
    """
    محاسبه امتیاز نهایی الگوها
    
    Returns:
        dict: {
            'score': int (-100 to +100),
            'confidence': int (0-100),
            'signals': list
        }
    """
    score = 0
    confidence = 50
    signals = []
    
    # ✅ امتیاز الگوهای کندل
    score += candlestick_patterns['pattern_score'] * 0.4
    
    if candlestick_patterns['hammer']:
        signals.append('Hammer (Buy)')
        confidence += 10
    if candlestick_patterns['shooting_star']:
        signals.append('Shooting Star (Sell)')
        confidence += 10
    if candlestick_patterns['engulfing_bullish']:
        signals.append('Bullish Engulfing (Buy)')
        confidence += 15
    if candlestick_patterns['engulfing_bearish']:
        signals.append('Bearish Engulfing (Sell)')
        confidence += 15
    
    # ✅ امتیاز سطوح حمایت/مقاومت
    position = sr_levels['position']
    
    if position == 'near_support':
        score += 50  # نزدیک حمایت = احتمال صعود
        signals.append(f"Near Support ({sr_levels['nearest_support']})")
        confidence += 20
    elif position == 'near_resistance':
        score -= 50  # نزدیک مقاومت = احتمال ریزش
        signals.append(f"Near Resistance ({sr_levels['nearest_resistance']})")
        confidence += 20
    
    # ✅ امتیاز الگوهای نموداری
    if chart_patterns['pattern'] == 'double_bottom':
        score += 60
        signals.append('Double Bottom (Buy)')
        confidence += chart_patterns['confidence'] * 0.3
    elif chart_patterns['pattern'] == 'double_top':
        score -= 60
        signals.append('Double Top (Sell)')
        confidence += chart_patterns['confidence'] * 0.3
    
    score = max(min(score, 100), -100)
    confidence = max(min(confidence, 100), 0)
    
    return {
        'score': round(score, 2),
        'confidence': round(confidence, 2),
        'signals': signals
    }


def analyze_patterns(cursor, symbol_id, current_price):
    """
    تحلیل کامل الگوها برای یک سیمبل
    """
    # دریافت دیتا
    query = """
        SELECT price as close, price as open, price as high, price as low, timestamp
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 100
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 20:
        return None
    
    # تبدیل به DataFrame
    df = pd.DataFrame(results, columns=['close', 'open', 'high', 'low', 'timestamp'])
    df = df.iloc[::-1].reset_index(drop=True)
    
    # تقریب high/low (در production باید OHLCV واقعی استفاده کنید)
    df['high'] = df['close'] * 1.002
    df['low'] = df['close'] * 0.998
    df['open'] = df['close'].shift(1).fillna(df['close'])
    
    # تشخیص الگوها
    candlestick = detect_candlestick_patterns(df)
    sr_levels = detect_support_resistance(df, current_price)
    chart_pattern = detect_chart_patterns(df)
    
    # محاسبه امتیاز نهایی
    result = calculate_pattern_score(candlestick, sr_levels, chart_pattern)
    
    return {
        'candlestick': candlestick,
        'support_resistance': sr_levels,
        'chart_pattern': chart_pattern,
        'score': result['score'],
        'confidence': result['confidence'],
        'signals': result['signals']
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# توابع کمکی
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _empty_pattern_result():
    """نتیجه خالی برای الگوها"""
    return {
        'doji': False,
        'hammer': False,
        'shooting_star': False,
        'engulfing_bullish': False,
        'engulfing_bearish': False,
        'morning_star': False,
        'evening_star': False,
        'pattern_score': 0
    }


def _cluster_levels(levels, reference_price, threshold=0.005):
    """
    ادغام سطوح نزدیک به هم
    threshold: 0.005 = 0.5% فاصله
    """
    if not levels:
        return []
    
    levels = sorted(levels)
    clustered = []
    current_cluster = [levels[0]]
    
    for level in levels[1:]:
        if abs(level - current_cluster[-1]) / reference_price < threshold:
            current_cluster.append(level)
        else:
            # میانگین cluster
            clustered.append(sum(current_cluster) / len(current_cluster))
            current_cluster = [level]
    
    # آخرین cluster
    clustered.append(sum(current_cluster) / len(current_cluster))
    
    return clustered


def print_pattern_analysis(symbol_name, analysis):
    """چاپ زیبای نتایج تحلیل الگو"""
    if not analysis:
        print(f"⚠️ Not enough data for pattern analysis: {symbol_name}")
        return
    
    print(f"\n{'═'*60}")
    print(f"🎨 Pattern Analysis: {symbol_name}")
    print(f"{'═'*60}")
    
    print(f"\n🕯️ Candlestick Patterns:")
    cs = analysis['candlestick']
    if cs['hammer']:
        print(f"   ✅ Hammer (Bullish)")
    if cs['shooting_star']:
        print(f"   ✅ Shooting Star (Bearish)")
    if cs['engulfing_bullish']:
        print(f"   ✅ Bullish Engulfing")
    if cs['engulfing_bearish']:
        print(f"   ✅ Bearish Engulfing")
    if cs['morning_star']:
        print(f"   ✅ Morning Star (Very Bullish)")
    if cs['evening_star']:
        print(f"   ✅ Evening Star (Very Bearish)")
    if not any([cs['hammer'], cs['shooting_star'], cs['engulfing_bullish'], 
                cs['engulfing_bearish'], cs['morning_star'], cs['evening_star']]):
        print(f"   ℹ️ No significant patterns")
    
    print(f"\n📊 Support/Resistance:")
    sr = analysis['support_resistance']
    print(f"   Support:    {sr['nearest_support']} ({sr['distance_to_support']:.2f}% away)")
    print(f"   Resistance: {sr['nearest_resistance']} ({sr['distance_to_resistance']:.2f}% away)")
    print(f"   Position:   {sr['position']}")
    
    print(f"\n📈 Chart Pattern:")
    cp = analysis['chart_pattern']
    if cp['pattern'] != 'none':
        print(f"   ✅ {cp['pattern'].replace('_', ' ').title()} (Confidence: {cp['confidence']}%)")
    else:
        print(f"   ℹ️ No chart pattern detected")
    
    print(f"\n🎯 Pattern Score: {analysis['score']}/100 (Confidence: {analysis['confidence']}%)")
    
    if analysis['signals']:
        print(f"\n🔔 Signals:")
        for signal in analysis['signals']:
            print(f"   • {signal}")