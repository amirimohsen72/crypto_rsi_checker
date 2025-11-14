"""
ماژول امتیازدهی برای سیگنال‌های معاملاتی
"""


from datetime import datetime
import json
import winsound
import pytz
import advanced_indicator as ai
import pattern_recognition as pr
import statistical_analysis as sa

tz_tehran = pytz.timezone("Asia/Tehran")


def save_signals_v6_sell_only(cursor, symbol_id, SYMBOL, last_price, rsi_values, rsi_trends, rsi_changes, score):
    """
    ✅ نسخه 6: فقط SELL سیگنال‌های باکیفیت
    بر اساس آنالیز: SELL ها 76% win rate دارن!
    """
    result = calculate_advanced_score_v5(
        cursor, symbol_id, last_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    final_score = result['score']
    confidence = result['confidence']
    risk_level = result['risk_level']
    
    # ✅ فیلتر 0: فقط SELL
    if final_score > 0:
        return False  # رد کردن همه BUY ها
    
    print(f"\n{'═'*75}")
    print(f"🔍 {SYMBOL} - Version 6 (SELL ONLY)")
    print(f"{'═'*75}")
    print(f"\n📊 Score: {final_score:+.1f} | Conf: {confidence:.1f}% | Risk: {risk_level:.1f}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # فیلترهای سخت‌تر برای SELL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # Penalty/Bonus
    adjusted_confidence = confidence
    
    if result['stat_analysis']:
        bb = result['stat_analysis']['bollinger']
        bb_position = bb['current_position']
        
        # بونوس برای SELL در overbought
        if bb['signal'] == 'overbought' and bb_position > 80:
            print(f"✅ BONUS: Sell at extreme overbought!")
            adjusted_confidence *= 1.2
        
        # پنالتی برای SELL در oversold
        if bb['signal'] == 'oversold':
            print(f"⚠️ WARNING: Sell at oversold (pos: {bb_position:.1f}%)")
            
            if bb_position < 15:
                adjusted_confidence *= 0.6
            elif bb_position < 25:
                adjusted_confidence *= 0.75
    
    adjusted_confidence = max(min(adjusted_confidence, 100), 0)
    
    # Thresholds سخت‌تر
    min_confidence = 80  # از 72 به 80
    min_score = 40       # از 25 به 40
    
    print(f"\n🔍 V6 Filter:")
    print(f"   Required: Conf ≥ {min_confidence}%, Score ≤ -{min_score}")
    print(f"   Actual: Conf = {adjusted_confidence:.1f}%, Score = {final_score:+.1f}")
    
    # فیلترها
    if adjusted_confidence < min_confidence:
        print(f"❌ REJECTED: Confidence too low")
        return False
    
    if abs(final_score) < min_score:
        print(f"❌ REJECTED: Score too weak")
        return False
    
    if risk_level > 70:
        print(f"❌ REJECTED: Risk too high ({risk_level:.1f})")
        return False
    
    # ذخیره
    signal_label = get_score_description2(final_score, risk_level)
    now = datetime.now(tz_tehran)
    
    full_data = {
        'rsi': rsi_values,
        'v4_score': result.get('v4_score', 0),
        'stat_score': result.get('statistical_score', 0),
        'risk_level': risk_level,
        'adjusted_confidence': adjusted_confidence
    }
    
    try:
        trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
        convergence_count = max(trends_list.count("up"), trends_list.count("down"))
        
        cursor.execute(
            """INSERT INTO signals 
            (symbol_id, price, symbol_name, rsi_values, signal_type, advance_score, score, 
             signal_label, quality, convergence_count, price_trend, time, testmode) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (symbol_id, last_price, SYMBOL,
             json.dumps(rsi_values),
             json.dumps(full_data, default=str),
             final_score, score, signal_label,
             int(adjusted_confidence), convergence_count,
             result['stat_analysis']['bollinger']['signal'] if result['stat_analysis'] else 'neutral',
             now, 'v6_sell_only')  # ✅ testmode جدید
        )
        
        # آلارم
        for _ in range(4):
            winsound.Beep(2200, 150)
        print(f"\n🔔🔔🔔🔔 V6 SELL SIGNAL! {SYMBOL}")
        print(f"Score: {final_score:+.1f} | Conf: {adjusted_confidence:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def save_signals_v7_ultra_premium(cursor, symbol_id, SYMBOL, last_price, rsi_values, rsi_trends, rsi_changes, score):
    """
    ✅ نسخه 7: Ultra Premium - سخت‌ترین فیلترها
    هدف: کمترین تعداد، بالاترین کیفیت
    """
    result = calculate_advanced_score_v5(
        cursor, symbol_id, last_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    final_score = result['score']
    confidence = result['confidence']
    risk_level = result['risk_level']
    
    print(f"\n{'═'*75}")
    print(f"🔍 {SYMBOL} - Version 7 (ULTRA PREMIUM)")
    print(f"{'═'*75}")
    
    # Penalty/Bonus
    adjusted_confidence = confidence
    
    if result['stat_analysis']:
        bb = result['stat_analysis']['bollinger']
        bb_position = bb['current_position']
        
        # بونوس فقط برای extreme positions
        if final_score > 0 and bb['signal'] == 'oversold' and bb_position < 10:
            adjusted_confidence *= 1.25
        elif final_score < 0 and bb['signal'] == 'overbought' and bb_position > 90:
            adjusted_confidence *= 1.25
        
        # رد کردن سیگنال‌های مخالف
        if (final_score > 0 and bb['signal'] == 'overbought') or \
           (final_score < 0 and bb['signal'] == 'oversold'):
            print(f"❌ REJECTED: Signal conflicts with Bollinger")
            return False
    
    adjusted_confidence = max(min(adjusted_confidence, 100), 0)
    
    # Thresholds خیلی سخت
    min_confidence = 85  # خیلی بالا!
    min_score = 50       # خیلی بالا!
    max_risk = 60        # ریسک پایین
    
    print(f"\n🔍 V7 Ultra Filter:")
    print(f"   Conf ≥ {min_confidence}% | Score ≥ {min_score} | Risk ≤ {max_risk}")
    print(f"   Actual: {adjusted_confidence:.1f}% | {abs(final_score):.1f} | {risk_level:.1f}")
    
    # فیلترها
    if adjusted_confidence < min_confidence:
        print(f"❌ REJECTED: Confidence too low")
        return False
    
    if abs(final_score) < min_score:
        print(f"❌ REJECTED: Score too weak")
        return False
    
    if risk_level > max_risk:
        print(f"❌ REJECTED: Risk too high")
        return False
    
    # چک همگرایی قوی
    v4_score = result.get('v4_score', 0)
    stat_score = result.get('statistical_score', 0)
    
    # باید همجهت و هر دو قوی باشن
    if not ((v4_score > 30 and stat_score > 30) or (v4_score < -30 and stat_score < -30)):
        print(f"❌ REJECTED: Weak convergence (V4: {v4_score:+.1f}, Stat: {stat_score:+.1f})")
        return False
    
    # ذخیره
    signal_label = get_score_description2(final_score, risk_level)
    now = datetime.now(tz_tehran)
    
    full_data = {
        'rsi': rsi_values,
        'v4_score': v4_score,
        'stat_score': stat_score,
        'risk_level': risk_level,
        'adjusted_confidence': adjusted_confidence
    }
    
    try:
        trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
        convergence_count = max(trends_list.count("up"), trends_list.count("down"))
        
        cursor.execute(
            """INSERT INTO signals 
            (symbol_id, price, symbol_name, rsi_values, signal_type, advance_score, score, 
             signal_label, quality, convergence_count, price_trend, time, testmode) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (symbol_id, last_price, SYMBOL,
             json.dumps(rsi_values),
             json.dumps(full_data, default=str),
             final_score, score, signal_label,
             int(adjusted_confidence), convergence_count,
             result['stat_analysis']['bollinger']['signal'] if result['stat_analysis'] else 'neutral',
             now, 'v7_ultra')  # ✅ testmode جدید
        )
        
        # آلارم ویژه!
        for _ in range(5):
            winsound.Beep(2500, 100)
        print(f"\n🔔🔔🔔🔔🔔 V7 ULTRA PREMIUM! {SYMBOL}")
        print(f"Score: {final_score:+.1f} | Conf: {adjusted_confidence:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def calculate_advanced_score_v5(cursor, symbol_id, current_price, rsi_values, rsi_trends, rsi_changes):
    """
    ✅ نسخه 5: ترکیب کامل - Indicators + Patterns + Statistics
    
    وزن‌ها:
    - V4 (Indicators + Patterns): 60%
    - Statistical Analysis: 25%
    - Risk Adjustment: 15%
    """
    # 1️⃣ امتیاز نسخه 4
    v4_result = calculate_advanced_score_v4(
        cursor, symbol_id, current_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    # 2️⃣ تحلیل آماری
    stat_analysis = sa.analyze_statistical(cursor, symbol_id, current_price)
    
    if not stat_analysis:
        # اگه دیتا کمه، فقط v4 رو برمیگردونیم
        return {
            **v4_result,
            'statistical_score': 0,
            'risk_level': 50,
            'stat_analysis': None,
            'version': 'v5_no_stats'
        }
    
    # 3️⃣ ترکیب امتیازها
    v4_score = v4_result['score']
    stat_score = stat_analysis['score']
    
    # وزن‌دهی
    base_score = (v4_score * 0.60) + (stat_score * 0.25)
    
    # 4️⃣ تنظیم بر اساس ریسک
    risk_level = stat_analysis['risk_level']
    risk_multiplier = calculate_risk_multiplier(risk_level)
    
    final_score = base_score * risk_multiplier
    
    # 5️⃣ محاسبه اعتماد ترکیبی
    v4_confidence = v4_result['confidence']
    stat_confidence = stat_analysis['confidence']
    
    combined_confidence = (v4_confidence * 0.60) + (stat_confidence * 0.40)
    
    # ✅ بونوس/پنالتی بر اساس Bollinger Bands
    bb_signal = stat_analysis['bollinger']['signal']
    
    if (v4_score > 0 and bb_signal == 'oversold') or (v4_score < 0 and bb_signal == 'overbought'):
        # همجهت با BB
        combined_confidence += 10
        final_score *= 1.15
    elif (v4_score > 0 and bb_signal == 'overbought') or (v4_score < 0 and bb_signal == 'oversold'):
        # مخالف با BB
        combined_confidence *= 0.75
        final_score *= 0.80
    
    # ✅ پنالتی نوسانات بالا
    if stat_analysis['atr']['volatility'] == 'very_high':
        combined_confidence *= 0.7
        final_score *= 0.85
    
    # محدود کردن
    final_score = max(min(final_score, 100), -100)
    combined_confidence = max(min(combined_confidence, 100), 0)
    
    return {
        **v4_result,
        'score': round(final_score, 2),
        'v4_score': round(v4_score, 2),
        'statistical_score': round(stat_score, 2),
        'risk_level': round(risk_level, 2),
        'confidence': round(combined_confidence, 2),
        'stat_analysis': stat_analysis,
        'version': 'v5_complete'
    }



def calculate_risk_multiplier(risk_level):
    """
    محاسبه ضریب کاهش بر اساس ریسک
    
    ریسک بالا = کاهش امتیاز (محافظه‌کارانه‌تر)
    """
    if risk_level > 85:
        return 0.70  # ریسک خیلی بالا
    elif risk_level > 70:
        return 0.80
    elif risk_level > 55:
        return 0.90
    elif risk_level < 30:
        return 1.10  # ریسک پایین = فرصت بهتر
    else:
        return 1.0

def save_signals_v5(cursor, symbol_id, SYMBOL, last_price, rsi_values, rsi_trends, rsi_changes, score):
    """
    ✅ ذخیره سیگنال نسخه 5 - تحلیل کامل (اصلاح شده)
    """
    result = calculate_advanced_score_v5(
        cursor, symbol_id, last_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    final_score = result['score']
    confidence = result['confidence']
    risk_level = result['risk_level']
    
    print(f"\n{'═'*75}")
    print(f"🔍 {SYMBOL} - Version 5 Complete Analysis")
    print(f"{'═'*75}")
    
    # نمایش امتیازها
    print(f"\n📊 Score Breakdown:")
    print(f"   V4 (Ind+Pat):    {result['v4_score']:+7.2f}")
    print(f"   Statistical:     {result['statistical_score']:+7.2f}")
    print(f"   {'─'*55}")
    print(f"   FINAL:           {final_score:+7.2f}")
    print(f"   Confidence:      {confidence:.1f}%")
    print(f"   Risk Level:      {risk_level:.1f}/100")
    
    # نمایش آمار
    if result['stat_analysis']:
        stat = result['stat_analysis']
        
        print(f"\n📊 Statistical Indicators:")
        print(f"   ATR:        {stat['atr']['atr_percent']:.2f}% ({stat['atr']['volatility']})")
        print(f"   Bollinger:  {stat['bollinger']['signal']} (pos: {stat['bollinger']['current_position']:.1f}%)")
        print(f"   Momentum:   {stat['momentum']['momentum']} (ROC: {stat['momentum']['roc']:+.2f}%)")
        print(f"   Volatility: {stat['volatility']['volatility_index']:.1f}/100 ({stat['volatility']['trend']})")
        print(f"\n   💡 {stat['recommendation']}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔍 اول penalty/bonus رو اعمال می‌کنیم
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    adjusted_confidence = confidence
    
    if result['stat_analysis']:
        bb = result['stat_analysis']['bollinger']
        bb_position = bb['current_position']
        
        # ✅ بونوس برای همجهت با BB
        if final_score > 0 and bb['signal'] == 'oversold' and bb_position < 20:
            print(f"\n✅ BONUS: Strong buy at extreme oversold!")
            adjusted_confidence *= 1.15
        
        if final_score < 0 and bb['signal'] == 'overbought' and bb_position > 80:
            print(f"\n✅ BONUS: Strong sell at extreme overbought!")
            adjusted_confidence *= 1.15
        
        # ⚠️ پنالتی برای مخالف با BB
        if final_score > 0 and bb['signal'] == 'overbought':
            print(f"\n⚠️ WARNING: Buy at overbought (pos: {bb_position:.1f}%)")
            
            if bb_position > 85:
                adjusted_confidence *= 0.65
            elif bb_position > 75:
                adjusted_confidence *= 0.75
        
        if final_score < 0 and bb['signal'] == 'oversold':
            print(f"\n⚠️ WARNING: Sell at oversold (pos: {bb_position:.1f}%)")
            
            if bb_position < 15:
                adjusted_confidence *= 0.65
            elif bb_position < 25:
                adjusted_confidence *= 0.75
    
    # محدود کردن
    adjusted_confidence = max(min(adjusted_confidence, 100), 0)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 🔍 فیلترهای اصلی (با confidence اصلاح شده)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # تعیین threshold ها
    if result['stat_analysis']:
        bb_signal = result['stat_analysis']['bollinger']['signal']
        bb_position = result['stat_analysis']['bollinger']['current_position']
        
        # Score threshold
        if bb_signal == 'oversold' and bb_position < 15:
            min_score = 25
        elif bb_signal == 'overbought' and bb_position > 85:
            min_score = 25
        elif bb_signal in ['oversold', 'overbought']:
            min_score = 30
        else:
            min_score = 40
    else:
        bb_signal = 'neutral'
        min_score = 35
    
    # Confidence threshold
    min_confidence = 72 if risk_level > 80 else 68 if risk_level > 70 else 65
    
    # 🔍 DEBUG INFO
    print(f"\n🔍 Filter Check:")
    print(f"   Required Score: {min_score:+.1f} | Actual: {final_score:+.1f} | Pass: {'✅' if abs(final_score) >= min_score else '❌'}")
    print(f"   Required Conf:  {min_confidence:.1f}% | Actual: {adjusted_confidence:.1f}% | Pass: {'✅' if adjusted_confidence >= min_confidence else '❌'}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ فیلتر 1: Confidence
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if adjusted_confidence < min_confidence:
        print(f"\n❌ REJECTED: Confidence too low ({adjusted_confidence:.1f}% < {min_confidence}%)")
        return False
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ فیلتر 2: Score
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if abs(final_score) < min_score:
        print(f"\n❌ REJECTED: Score too weak ({final_score:.1f} < {min_score})")
        return False
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ فیلتر 3: Risk Level
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if risk_level > 80 and adjusted_confidence < 75:
        print(f"\n❌ REJECTED: High risk ({risk_level:.1f}) needs confidence ≥75%")
        return False
    
    if risk_level > 65 and adjusted_confidence < 70:
        print(f"\n❌ REJECTED: Moderate-high risk ({risk_level:.1f}) needs confidence ≥70%")
        return False
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ فیلتر 4: Indicator Conflict
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    v4_score = result.get('v4_score', 0)
    stat_score = result.get('statistical_score', 0)
    
    if (v4_score > 0 and stat_score < -20) or (v4_score < 0 and stat_score > 20):
        print(f"\n⚠️ WARNING: Indicators conflict!")
        print(f"   V4: {v4_score:+.1f} | Statistical: {stat_score:+.1f}")
        
        if adjusted_confidence < 72:
            print(f"❌ REJECTED: Conflicting signals with low confidence")
            return False
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ✅ همه فیلترها رد شد - ذخیره سیگنال
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    signal_label = get_score_description2(final_score, risk_level)
    now = datetime.now(tz_tehran)
    
    # آماده‌سازی دیتای JSON
    full_data = {
        'rsi': rsi_values,
        'v4_score': result['v4_score'],
        'stat_score': result['statistical_score'],
        'risk_level': risk_level,
        'original_confidence': confidence,
        'adjusted_confidence': adjusted_confidence
    }
    
    if result['stat_analysis']:
        full_data['statistics'] = {
            'atr': result['stat_analysis']['atr'],
            'bollinger': result['stat_analysis']['bollinger'],
            'momentum': result['stat_analysis']['momentum'],
            'volatility': result['stat_analysis']['volatility']
        }
    
    try:
        trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
        convergence_count = max(trends_list.count("up"), trends_list.count("down"))
        
        cursor.execute(
            """INSERT INTO signals 
            (symbol_id, price, symbol_name, rsi_values, signal_type, advance_score, score, 
             signal_label, quality, convergence_count, price_trend, time, testmode) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (symbol_id, last_price, SYMBOL,
             json.dumps(rsi_values),
             json.dumps(full_data, default=str),
             final_score, score, signal_label,
             int(adjusted_confidence), convergence_count,
             result['stat_analysis']['bollinger']['signal'] if result['stat_analysis'] else 'neutral',
             now, 'v5_fixed')
        )
        
        # آلارم بر اساس کیفیت
        if adjusted_confidence >= 80 and risk_level < 60:
            for _ in range(5):
                winsound.Beep(2400, 120)
            print(f"\n🔔🔔🔔🔔🔔 EXCEPTIONAL! {SYMBOL}")
            
        elif adjusted_confidence >= 75:
            for _ in range(4):
                winsound.Beep(2200, 150)
            print(f"\n🔔🔔🔔🔔 EXCELLENT! {SYMBOL}")
            
        elif adjusted_confidence >= 70:
            for _ in range(3):
                winsound.Beep(2000, 200)
            print(f"\n🔔🔔🔔 VERY GOOD! {SYMBOL}")
            
        elif adjusted_confidence >= 65:
            for _ in range(2):
                winsound.Beep(1600, 250)
            print(f"\n🔔🔔 GOOD! {SYMBOL}")
        else:
            winsound.Beep(1200, 300)
            print(f"\n🔔 Signal: {SYMBOL}")
        
        print(f"Score: {final_score:+.1f} | Conf: {adjusted_confidence:.1f}% | Risk: {risk_level:.1f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error saving signal: {e}")
        return False


def calculate_advanced_score_v4(cursor, symbol_id, current_price, rsi_values, rsi_trends, rsi_changes):
    """
    ✅ نسخه 4: ترکیب اندیکاتورها + الگوها
    
    وزن‌ها:
    - RSI + Indicators (v3): 70%
    - Pattern Recognition: 30%
    """
    # 1️⃣ امتیاز نسخه 3 (RSI + MACD + ADX + EMA)
    v3_result = calculate_advanced_score_v3(
        cursor, symbol_id, current_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    # 2️⃣ تحلیل الگوها
    pattern_analysis = pr.analyze_patterns(cursor, symbol_id, current_price)
    
    if not pattern_analysis:
        # اگه دیتا کمه، فقط v3 رو برمیگردونیم
        return {
            **v3_result,
            'pattern_score': 0,
            'pattern_analysis': None,
            'version': 'v4_no_patterns'
        }
    
    # 3️⃣ ترکیب امتیازها
    v3_score = v3_result['score']
    pattern_score = pattern_analysis['score']
    
    # وزن‌دهی
    final_score = (v3_score * 0.70) + (pattern_score * 0.30)
    
    # 4️⃣ محاسبه اعتماد ترکیبی
    v3_confidence = v3_result['confidence']
    pattern_confidence = pattern_analysis['confidence']
    
    combined_confidence = (v3_confidence * 0.65) + (pattern_confidence * 0.35)
    
    # ✅ بونوس: اگه همه همجهت باشن
    if (v3_score > 0 and pattern_score > 0) or (v3_score < 0 and pattern_score < 0):
        combined_confidence += 10
        final_score *= 1.1  # تقویت 10%
    
    # ✅ پنالتی: اگه مخالف باشن
    if (v3_score > 0 and pattern_score < -20) or (v3_score < 0 and pattern_score > 20):
        combined_confidence *= 0.7
        final_score *= 0.8  # کاهش 20%
    
    final_score = max(min(final_score, 100), -100)
    combined_confidence = max(min(combined_confidence, 100), 0)
    
    return {
        **v3_result,
        'score': round(final_score, 2),
        'v3_score': round(v3_score, 2),
        'pattern_score': round(pattern_score, 2),
        'confidence': round(combined_confidence, 2),
        'pattern_analysis': pattern_analysis,
        'version': 'v4_with_patterns'
    }


def save_signals_v4(cursor, symbol_id, SYMBOL, last_price, rsi_values, rsi_trends, rsi_changes, score):
    """
    ✅ ذخیره سیگنال نسخه 4 - با Pattern Recognition
    """
    result = calculate_advanced_score_v4(
        cursor, symbol_id, last_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    final_score = result['score']
    confidence = result['confidence']
    
    print(f"\n{'═'*70}")
    print(f"🔍 {SYMBOL} - Version 4 Analysis")
    print(f"{'═'*70}")
    
    # نمایش امتیازها
    print(f"\n📊 Score Breakdown:")
    print(f"   V3 (Indicators): {result['v3_score']:+7.2f}")
    print(f"   Patterns:        {result['pattern_score']:+7.2f}")
    print(f"   {'─'*50}")
    print(f"   FINAL:           {final_score:+7.2f} | Confidence: {confidence:.1f}%")
    
    # نمایش الگوها
    if result['pattern_analysis']:
        pa = result['pattern_analysis']
        
        print(f"\n🎨 Pattern Signals:")
        if pa['signals']:
            for sig in pa['signals']:
                print(f"   • {sig}")
        else:
            print(f"   ℹ️ No patterns detected")
        
        # حمایت/مقاومت
        sr = pa['support_resistance']
        print(f"\n📊 Support/Resistance:")
        print(f"   Position: {sr['position']}")
        print(f"   Support:    ${sr['nearest_support']} ({sr['distance_to_support']:+.2f}%)")
        print(f"   Resistance: ${sr['nearest_resistance']} ({sr['distance_to_resistance']:+.2f}%)")
    
    # ✅ فیلترهای ذخیره
    if confidence < 60:
        print(f"\n❌ REJECTED: Confidence too low ({confidence:.1f}%)")
        return False
    
    if abs(final_score) < 30:
        print(f"\n❌ REJECTED: Score too weak ({final_score})")
        return False
    
    # ✅ فیلتر ویژه: اگه نزدیک مقاومت باشه و سیگنال خرید بده
    if result['pattern_analysis']:
        sr = result['pattern_analysis']['support_resistance']
        
        if final_score > 0 and sr['position'] == 'near_resistance':
            print(f"\n⚠️ WARNING: Buy signal near resistance - Risk High!")
            confidence *= 0.7
            
            if confidence < 55:
                print(f"❌ REJECTED: Too risky")
                return False
        
        if final_score < 0 and sr['position'] == 'near_support':
            print(f"\n⚠️ WARNING: Sell signal near support - Risk High!")
            confidence *= 0.7
            
            if confidence < 55:
                print(f"❌ REJECTED: Too risky")
                return False
    
    # ذخیره در دیتابیس
    signal_label = get_score_description(final_score)
    now = datetime.now(tz_tehran)
    
    # آماده‌سازی دیتای JSON
    pattern_data = None
    if result['pattern_analysis']:
        pattern_data = {
            'candlestick': result['pattern_analysis']['candlestick'],
            'support': result['pattern_analysis']['support_resistance']['nearest_support'],
            'resistance': result['pattern_analysis']['support_resistance']['nearest_resistance'],
            'position': result['pattern_analysis']['support_resistance']['position'],
            'signals': result['pattern_analysis']['signals']
        }
    
    try:

        trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
        up_count = trends_list.count("up")
        down_count = trends_list.count("down")
        convergence_count = max(up_count, down_count)
        cursor.execute(
            """INSERT INTO signals 
            (symbol_id, price, symbol_name, rsi_values, signal_type, advance_score, score, 
             signal_label, quality, convergence_count, price_trend, time, testmode) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (symbol_id, last_price, SYMBOL,
             json.dumps(rsi_values),
             json.dumps(pattern_data, default=str) if pattern_data else json.dumps(rsi_trends),
             final_score, score, signal_label,
             int(confidence), convergence_count,
             result['pattern_analysis']['support_resistance']['position'] if result['pattern_analysis'] else 'neutral',
             now, 'v4_patterns: PR')
        )
        
        # آلارم با سطح‌های مختلف
        if confidence >= 80:
            for _ in range(4):
                winsound.Beep(2200, 150)
            print(f"\n🔔🔔🔔🔔 EXCEPTIONAL! {SYMBOL}")
            print(f"Score: {final_score} | Confidence: {confidence:.1f}%")
        elif confidence >= 70:
            for _ in range(3):
                winsound.Beep(2000, 200)
            print(f"\n🔔🔔🔔 EXCELLENT! {SYMBOL}")
            print(f"Score: {final_score} | Confidence: {confidence:.1f}%")
        elif confidence >= 60:
            for _ in range(2):
                winsound.Beep(1600, 250)
            print(f"\n🔔🔔 GOOD! {SYMBOL}")
            print(f"Score: {final_score} | Confidence: {confidence:.1f}%")
        else:
            winsound.Beep(1200, 300)
            print(f"\n🔔 Signal: {SYMBOL}")
            print(f"Score: {final_score} | Confidence: {confidence:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error saving signal: {e}")
        return False



def calculate_advanced_score_v3(cursor, symbol_id, current_price, rsi_values, rsi_trends, rsi_changes):
    """
    ✅ نسخه 3 با اندیکاتورهای پیشرفته
    
    ترکیب:
    - RSI (وزن: 30%)
    - MACD (وزن: 25%)
    - ADX (وزن: 20%)
    - EMA Momentum (وزن: 15%)
    - Volume (وزن: 10%)
    """
    # 1️⃣ امتیاز پایه RSI
    base_rsi_score = calculate_rsi_base_score(rsi_values, rsi_trends, rsi_changes)
    
    # 2️⃣ دریافت DataFrame برای محاسبات
    df = ai.get_dataframe_from_cursor(cursor, symbol_id, limit=200)
    
    if df is None or len(df) < 50:
        # اگه دیتا کمه، فقط RSI رو برمیگردونیم
        return {
            'score': base_rsi_score,
            'rsi_score': base_rsi_score,
            'macd_score': 0,
            'adx_score': 0,
            'ema_score': 0,
            'volume_score': 0,
            'confidence': 30,
            'indicators': None
        }
    
    # 3️⃣ محاسبه اندیکاتورها
    indicators = ai.calculate_combined_momentum(df)
    
    # 4️⃣ محاسبه امتیازها
    weights = {
        'rsi': 0.30,
        'macd': 0.25,
        'adx': 0.20,
        'ema': 0.15,
        'volume': 0.10
    }
    
    # امتیاز MACD
    macd_score = calculate_macd_score(indicators['macd'])
    
    # امتیاز ADX
    adx_score = calculate_adx_score(indicators['adx'], base_rsi_score)
    
    # امتیاز EMA
    ema_score = calculate_ema_score(indicators['ema'])
    
    # امتیاز Volume
    volume_status, volume_ratio = calculate_volume_trend(cursor, symbol_id)
    volume_score = calculate_volume_score(volume_status, volume_ratio)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ترکیب نهایی
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    final_score = (
        base_rsi_score * weights['rsi'] +
        macd_score * weights['macd'] +
        adx_score * weights['adx'] +
        ema_score * weights['ema'] +
        volume_score * weights['volume']
    )
    
    # محاسبه اعتماد
    confidence = calculate_confidence(
        indicators,
        base_rsi_score,
        macd_score,
        adx_score,
        ema_score
    )
    
    final_score = max(min(final_score, 100), -100)
    
    return {
        'score': round(final_score, 2),
        'rsi_score': round(base_rsi_score, 2),
        'macd_score': round(macd_score, 2),
        'adx_score': round(adx_score, 2),
        'ema_score': round(ema_score, 2),
        'volume_score': round(volume_score, 2),
        'confidence': round(confidence, 2),
        'indicators': indicators
    }



def calculate_rsi_base_score(rsi_values, rsi_trends, rsi_changes):
    """محاسبه امتیاز پایه RSI (مثل قبل)"""
    from scoring import calculate_advanced_score  # import از فایل قبلی
    return calculate_advanced_score(rsi_values, rsi_trends, rsi_changes)


def calculate_macd_score(macd_data):
    """
    محاسبه امتیاز MACD
    
    - Golden Cross = +80 تا +100
    - Death Cross = -80 تا -100
    - Bullish = +30 تا +70
    - Bearish = -30 تا -70
    """
    score = 0
    
    if macd_data['crossover'] == 'golden':
        score += 80 + (macd_data['strength'] * 0.2)
    elif macd_data['crossover'] == 'death':
        score -= 80 + (macd_data['strength'] * 0.2)
    elif macd_data['trend'] == 'bullish':
        score += 30 + (macd_data['strength'] * 0.4)
    elif macd_data['trend'] == 'bearish':
        score -= 30 + (macd_data['strength'] * 0.4)
    
    return max(min(score, 100), -100)


def calculate_adx_score(adx_data, base_signal_score):
    """
    محاسبه امتیاز ADX
    
    ADX نشون میده روند چقدر قویه
    اگه روند قوی باشه، امتیاز سیگنال رو تقویت میکنه
    """
    # ADX خودش سیگنال نمیده، فقط قدرت رو نشون میده
    # پس امتیاز بر اساس جهت base_signal میگیریم
    
    strength_multiplier = {
        'weak': 0.3,
        'moderate': 0.6,
        'strong': 1.0,
        'very_strong': 1.3
    }.get(adx_data['trend_strength'], 0.5)
    
    if adx_data['direction'] == 'up':
        return 60 * strength_multiplier
    elif adx_data['direction'] == 'down':
        return -60 * strength_multiplier
    else:
        return 0  # روند sideways



def calculate_ema_score(ema_data):
    """محاسبه امتیاز EMA Momentum"""
    momentum_scores = {
        'strong_up': 80,
        'weak_up': 40,
        'neutral': 0,
        'weak_down': -40,
        'strong_down': -80
    }
    return momentum_scores.get(ema_data['momentum'], 0)


def calculate_volume_score(volume_status, volume_ratio):
    """محاسبه امتیاز حجم"""
    if volume_status == "high":
        return 50  # حجم بالا = تایید سیگنال
    elif volume_status == "normal":
        return 0
    else:
        return -30  # حجم پایین = سیگنال ضعیف


def calculate_confidence(indicators, rsi_score, macd_score, adx_score, ema_score):
    """
    محاسبه درصد اعتماد به سیگنال
    
    بر اساس:
    - همجهت بودن اندیکاتورها
    - قدرت ADX
    - شدت MACD
    """
    confidence = 50
    
    # ✅ همه اندیکاتورها همجهت باشن
    scores = [rsi_score, macd_score, adx_score, ema_score]
    positive_count = sum(1 for s in scores if s > 0)
    negative_count = sum(1 for s in scores if s < 0)
    
    if positive_count == 4:
        confidence += 30
    elif positive_count >= 3:
        confidence += 20
    elif negative_count == 4:
        confidence += 30
    elif negative_count >= 3:
        confidence += 20
    else:
        confidence -= 10  # اندیکاتورها مخالف هم
    
    # ✅ ADX قوی
    if indicators['adx']['trend_strength'] in ['strong', 'very_strong']:
        confidence += 15
    
    # ✅ MACD Crossover
    if indicators['macd']['crossover'] != 'none':
        confidence += 10
    
    return max(min(confidence, 100), 0)


def calculate_advanced_score_v2(cursor, symbol_id, current_price, rsi_values, rsi_trends, rsi_changes):
    """
    ✅ نسخه پیشرفته با چک‌های بیشتر
    """
    # 1️⃣ امتیاز اصلی (RSI)
    base_score = calculate_advanced_score(rsi_values, rsi_trends, rsi_changes)
    
    # 2️⃣ روند قیمت
    price_trend, price_change = calculate_price_trend_by_timeframe(cursor, symbol_id, current_price)
    
    # 3️⃣ حجم معاملات
    volume_status, volume_ratio = calculate_volume_trend(cursor, symbol_id)
    
    # 4️⃣ شتاب RSI
    rsi_momentum = calculate_rsi_momentum(rsi_values, rsi_changes)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ترکیب امتیازها
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    final_score = base_score
    quality_multiplier = 1.0
    
    # ✅ چک روند قیمت ملایم تر
    if base_score > 0 and price_trend == "down":
        final_score *= 0.7  # سیگنال خرید ولی قیمت داره میریزه
        quality_multiplier *= 0.7
    elif base_score < 0 and price_trend == "up":
        final_score *= 0.7  # سیگنال فروش ولی قیمت داره میره بالا
        quality_multiplier *= 0.7
    elif base_score > 0 and price_trend == "up":
        final_score *= 1.15  # سیگنال خرید و قیمت هم صعودیه (عالی!)
        quality_multiplier *= 1.2
    elif base_score < 0 and price_trend == "down":
        final_score *= 1.15  # سیگنال فروش و قیمت هم نزولیه (عالی!)
        quality_multiplier *= 1.2
    
    # ✅ چک حجم
    if volume_status == "low":
        quality_multiplier *= 0.85  # حجم کم = سیگنال ضعیف‌تر
    elif volume_status == "high":
        quality_multiplier *= 1.15  # حجم بالا = تایید سیگنال
    
    # ✅ چک شتاب RSI
    if base_score > 0 and rsi_momentum > 0:
        final_score *= 1.08  # RSI داره برمیگرده از oversold
    elif base_score < 0 and rsi_momentum < 0:
        final_score *= 1.08  # RSI داره برمیگرده از overbought
    
    final_score = max(min(final_score, 100), -100)
    
    return {
        'score': round(final_score, 2),
        'price_trend': price_trend,
        'price_change': price_change,
        'volume_status': volume_status,
        'volume_ratio': volume_ratio,
        'rsi_momentum': rsi_momentum,
        'quality_multiplier': quality_multiplier
    }


def calculate_advanced_score(rsi_values, rsi_trends, rsi_changes, price_trend=None):
    """
    محاسبه امتیاز پیشرفته اصلی
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
        total_score = total_score * 0.85  
    elif max_trend < 3:
        total_score = total_score * 0.92  
    
    # محدود به بازه -100 تا +100
    
    if price_trend:
        if total_score > 0 and price_trend == "down":
            # سیگنال خرید ولی قیمت داره میریزه → کاهش امتیاز
            total_score = total_score * 0.75
        elif total_score < 0 and price_trend == "up":
            # سیگنال فروش ولی قیمت داره میره بالا → کاهش امتیاز
            total_score = total_score * 0.75

    
    total_score = max(min(total_score, 100), -100)
    
    return round(total_score, 2)


def calculate_price_trend_for_scalping(cursor, symbol_id, current_price):
    """
    ✅ روند قیمت برای scalping (کوتاه‌مدت)
    
    فقط 10-15 تا قیمت اخیر رو چک میکنه
    """
    query = """
        SELECT price
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 15
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 5:
        return "neutral"
    
    prices = [r[0] for r in results]
    
    # میانگین 5 تا اخیر vs میانگین 10-15 تا اخیر
    recent_avg = sum(prices[:5]) / 5
    older_avg = sum(prices[5:]) / len(prices[5:])
    
    change_percent = ((recent_avg - older_avg) / older_avg) * 100
    
    if change_percent > 0.3:
        return "up"
    elif change_percent < -0.3:
        return "down"
    else:
        return "neutral"
    
def calculate_price_trend_by_timeframe(cursor, symbol_id, current_price):
    """
    ✅ محاسبه روند قیمت با تایم‌فریم درست
    fallback و error handling
    برای scalping: 5-15 دقیقه اخیر
    """
    # تشخیص چند دقیقه پیش میخوایم ببینیم
    minutes_lookback = 15  # 15 دقیقه برای scalping
    
    # محاسبه تعداد دیتا (هر 30 ثانیه = 2 دیتا در دقیقه)
    data_count = minutes_lookback * 2
    
    query = """
        SELECT price, timestamp
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    cursor.execute(query, (symbol_id, data_count))
    results = cursor.fetchall()
    
    # ✅ اگه دیتا کمه، neutral برمیگردونیم
    if len(results) < 5:
        print(f"  ⚠️ Not enough data for trend: {len(results)}/5 - returning neutral")
        return "neutral", 0
    
    prices = [r[0] for r in results]
    
    # میانگین اول و آخر
    recent_avg = sum(prices[:5]) / 5  # 5 تا اخیر (2.5 دقیقه)
    older_avg = sum(prices[-5:]) / 5  # 5 تا قدیمی (15 دقیقه قبل)    

    recent_count = min(5, len(prices))
    older_count = min(5, len(prices) - recent_count)
    
    if older_count < 2:
        return "neutral", 0
    
    recent_count = min(5, len(prices))
    older_count = min(5, len(prices) - recent_count)
    
    if older_count < 2:
        return "neutral", 0
    recent_avg = sum(prices[:recent_count]) / recent_count
    older_avg = sum(prices[-older_count:]) / older_count
    
    change_percent = ((recent_avg - older_avg) / older_avg) * 100
    
    # تشخیص روند
    if change_percent > 0.2: 
        return "up", change_percent
    elif change_percent < -0.2:  
        return "down", change_percent
    else:
        return "neutral", change_percent   
    return "neutral", 0


def calculate_multi_timeframe_trend(cursor, symbol_id, current_price):
    """
    ✅ محاسبه روند در چند سطح زمانی
    
    Returns:
        dict: {
            'short': 'up/down/neutral',  # 5-10 قیمت اخیر
            'medium': 'up/down/neutral', # 20-30 قیمت اخیر
            'long': 'up/down/neutral'    # 50 قیمت اخیر
        }
    """
    query = """
        SELECT price
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 50
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 5:
        return {'short': 'neutral', 'medium': 'neutral', 'long': 'neutral'}
    
    prices = [r[0] for r in results]
    
    trends = {}
    
    # روند کوتاه‌مدت (5-10 قیمت)
    if len(prices) >= 5:
        short_avg = sum(prices[:5]) / 5
        short_change = ((current_price - short_avg) / short_avg) * 100
        trends['short'] = 'up' if short_change > 0.2 else 'down' if short_change < -0.2 else 'neutral'
    else:
        trends['short'] = 'neutral'
    
    # روند میان‌مدت (20-30 قیمت)
    if len(prices) >= 20:
        medium_avg = sum(prices[:20]) / 20
        medium_change = ((current_price - medium_avg) / medium_avg) * 100
        trends['medium'] = 'up' if medium_change > 0.3 else 'down' if medium_change < -0.3 else 'neutral'
    else:
        trends['medium'] = 'neutral'
    
    # روند بلندمدت (50 قیمت)
    if len(prices) >= 50:
        long_avg = sum(prices[:50]) / 50
        long_change = ((current_price - long_avg) / long_avg) * 100
        trends['long'] = 'up' if long_change > 0.5 else 'down' if long_change < -0.5 else 'neutral'
    else:
        trends['long'] = 'neutral'
    
    return trends


def get_dominant_trend(trends):
    """
    ✅ تعیین روند غالب از روندهای چند سطحی
    """
    # اولویت: short > medium > long
    if trends['short'] != 'neutral':
        return trends['short']
    elif trends['medium'] != 'neutral':
        return trends['medium']
    elif trends['long'] != 'neutral':
        return trends['long']
    else:
        return 'neutral'
    


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


def calculate_volume_trend(cursor, symbol_id):
    """
    ✅ بررسی روند حجم معاملات
     بررسی روند حجم با fallback
    حجم بالا = تایید روند
    حجم پایین = روند ضعیف
    """
    query = """
        SELECT volume
        FROM rsi_data
        WHERE symbol_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
    """
    cursor.execute(query, (symbol_id,))
    results = cursor.fetchall()
    
    if len(results) < 10:
        return "neutral", 1.0
    
    volumes = [r[0] for r in results if r[0] is not None]
    
    if len(volumes) < 10:
        return "neutral", 1.0
    
    recent_vol = sum(volumes[:5]) / 5
    avg_vol = sum(volumes) / len(volumes)
    
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
    
    if vol_ratio > 1.5:
        return "high", vol_ratio  # حجم بالا
    elif vol_ratio > 1.0:
        return "normal", vol_ratio
    else:
        return "low", vol_ratio  # حجم پایین (احتیاط)
    


def save_signals_v3(cursor, symbol_id, SYMBOL, last_price, rsi_values, rsi_trends, rsi_changes, score):
    """
    ✅ ذخیره سیگنال نسخه 3 با اندیکاتورهای پیشرفته
    """
    result = calculate_advanced_score_v3(
        cursor, symbol_id, last_price,
        rsi_values, rsi_trends, rsi_changes
    )
    
    final_score = result['score']
    confidence = result['confidence']
    
    print(f"\n{'─'*60}")
    print(f"🔍 {SYMBOL}")
    print(f"{'─'*60}")
    print(f"📊 Scores Breakdown:")
    print(f"   RSI:    {result['rsi_score']:+7.2f}")
    print(f"   MACD:   {result['macd_score']:+7.2f}")
    print(f"   ADX:    {result['adx_score']:+7.2f}")
    print(f"   EMA:    {result['ema_score']:+7.2f}")
    print(f"   Volume: {result['volume_score']:+7.2f}")
    print(f"   {'─'*40}")
    print(f"   FINAL:  {final_score:+7.2f} | Confidence: {confidence}%")
    
    if result['indicators']:
        ind = result['indicators']
        print(f"\n📈 Indicators:")
        print(f"   MACD: {ind['macd']['trend']} ({ind['macd']['crossover']})")
        print(f"   ADX:  {ind['adx']['adx']} - {ind['adx']['trend_strength']} ({ind['adx']['direction']})")
        print(f"   EMA:  {ind['ema']['momentum']} (slope: {ind['ema']['ema_slope']:.2f}%)")
    
    # ✅ فیلترهای ذخیره
    if confidence < 55:
        print(f"❌ Confidence too low: {confidence}%")
        return False
    
    if abs(final_score) < 25:
        print(f"❌ Score too weak: {final_score}")
        return False
    
    # ✅ چک همجهتی با روند ADX
    if result['indicators']:
        adx_dir = result['indicators']['adx']['direction']
        if final_score > 0 and adx_dir == 'down':
            print(f"⚠️ Buy signal but ADX shows downtrend - Quality reduced")
            confidence *= 0.7
        elif final_score < 0 and adx_dir == 'up':
            print(f"⚠️ Sell signal but ADX shows uptrend - Quality reduced")
            confidence *= 0.7
    
    # ذخیره در دیتابیس
    signal_label = get_score_description(final_score)
    now = datetime.now(tz_tehran)
    

    trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
    up_count = trends_list.count("up")
    down_count = trends_list.count("down")
    convergence_count = max(up_count, down_count)
    try:
        cursor.execute(
            """INSERT INTO signals 
            (symbol_id, price, symbol_name, rsi_values, signal_type, advance_score, score, 
             signal_label, quality, convergence_count, price_trend, time, testmode) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (symbol_id, last_price, SYMBOL, 
             json.dumps(rsi_values), 
             json.dumps(result['indicators'], default=str),  # ذخیره اندیکاتورها
             final_score, score, signal_label, 
             int(confidence), convergence_count, 
             result['indicators']['adx']['direction'] if result['indicators'] else 'neutral',
             now, 'v3_indicators')
        )
        
        # آلارم
        if confidence >= 75:
            for _ in range(3):
                winsound.Beep(2000, 200)
            print(f"🔔🔔🔔 EXCELLENT! {SYMBOL}")
        elif confidence >= 60:
            for _ in range(2):
                winsound.Beep(1600, 250)
            print(f"🔔🔔 GOOD! {SYMBOL}")
        else:
            winsound.Beep(1200, 300)
            print(f"🔔 Signal: {SYMBOL}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving: {e}")
        return False



def calculate_rsi_momentum(rsi_values, rsi_changes):
    """
    ✅ محاسبه شتاب RSI (آیا داره تند میره بالا/پایین؟)
    """
    # بررسی تایم‌فریم‌های کوتاه (1m, 5m)
    short_tf = ['1m', '5m']
    
    momentum = 0
    count = 0
    
    for tf in short_tf:
        if tf in rsi_values and tf in rsi_changes:
            rsi = rsi_values[tf]
            change = rsi_changes[tf]
            
            if rsi is None:
                continue
            # شتاب = RSI × تغییر
            if rsi < 30 and change > 2:
                momentum += 1  # داره از oversold برمیگرده (خوب برای خرید)
            elif rsi > 70 and change < -2:
                momentum -= 1  # داره از overbought برمیگرده (خوب برای فروش)
            
            count += 1
    
    if count == 0:
        return 0
    
    return momentum / count


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


def save_signals_v2(cursor, symbol_id, SYMBOL, last_price, rsi_values, rsi_trends, rsi_changes, score):
    """
    ذخیره با چک‌های پیشرفته
    """
    # محاسبه امتیاز پیشرفته
    result = calculate_advanced_score_v2(
        cursor, symbol_id, last_price, 
        rsi_values, rsi_trends, rsi_changes
    )
    
    advanced_score = result['score']
    quality_base = calculate_signal_quality(rsi_values, rsi_trends, advanced_score, result['price_trend'])
    quality_final = int(quality_base * result['quality_multiplier'])
    
    # فیلتر ذخیره
    if quality_final < 45:  # آستانه بالاتر
        print(f"  ❌ Quality too low: {quality_final}")
        return False
    
    if abs(advanced_score) < 15:  # سیگنال خیلی ضعیف
        print(f"  ❌ Score too weak: {advanced_score}")
        return False
    
    # ذخیره
    # ... کد ذخیره
    
    print(f"✅ Signal: {SYMBOL} | Score: {advanced_score} | Quality: {quality_final}")
    print(f"   Price: {result['price_trend']} ({result['price_change']:+.2f}%)")
    print(f"   Volume: {result['volume_status']} ({result['volume_ratio']:.2f}x)")
    print(f"   RSI Momentum: {result['rsi_momentum']:+.2f}")
    
    # ذخیره سیگنال
    signal_label = get_score_description(advanced_score)
    trends_list = [t for t in rsi_trends.values() if t in ["up", "down"]]
    up_count = trends_list.count("up")
    down_count = trends_list.count("down")
    convergence_count = max(up_count, down_count)
    now = datetime.now(tz_tehran)
    try:
        cursor.execute(
            """INSERT INTO signals 
            (symbol_id, price, symbol_name, rsi_values, signal_type, advance_score, score, 
             signal_label, quality, convergence_count, price_trend, time,testmode) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (symbol_id, last_price, SYMBOL, json.dumps(rsi_values), json.dumps(rsi_trends),
             advanced_score, score, signal_label, quality_final, convergence_count, 
             result['price_trend'], now,'savesignal2')
        )
        
        # آلارم
        if quality_final >= 75:
            for _ in range(3):
                winsound.Beep(2000, 200)
            print(f"🔔🔔🔔 EXCELLENT! {SYMBOL} | Score: {advanced_score} | Quality: {quality_final}%")
            
        elif quality_final >= 60:
            for _ in range(2):
                winsound.Beep(1600, 250)
            print(f"🔔🔔 GOOD! {SYMBOL} | Score: {advanced_score} | Quality: {quality_final}%")
            
        else:
            winsound.Beep(1200, 300)
            print(f"🔔 Signal: {SYMBOL} | Score: {advanced_score} | Quality: {quality_final}%")
        
        print(f"   💰 Price: {result['price_trend']} ({result['price_change']:+.2f}%)")
        print(f"   📊 Volume: {result['volume_status']} ({result['volume_ratio']:.2f}x)")
        print(f"   🚀 RSI Momentum: {result['rsi_momentum']:+.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error saving signal: {e}")
        return False

def save_signals(c_cursor , symbol_id , SYMBOL , last_price, rsi_values, rsi_trends, advanced_score , score):
    """
    ذخیره سیگنال های مهم
    """
    # save_signals(cursor , symbol_id , SYMBOL , last_price, rsi_values, rsi_trends, advanced_score , score)
    # price_trend = calculate_price_trend(c_cursor, symbol_id)
    # price_trend = calculate_price_trend_simple(c_cursor, symbol_id, last_price) #پر خطا
    price_trend = calculate_price_trend_smart(c_cursor, symbol_id, last_price, rsi_values) #یکم بهتر

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
            "INSERT INTO signals (symbol_id, price, symbol_name, rsi_values, signal_type ,advance_score ,score , signal_label, quality, convergence_count,price_trend,time,testmode ) VALUES (?, ?,?, ?, ?, ?, ?,?,?,?,?,?,?)",
            (symbol_id, last_price, SYMBOL, json.dumps(rsi_values), json.dumps(rsi_trends) ,advanced_score ,score ,signal_label, quality, convergence_count, price_trend,now, 'savesignal')
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
    

    
def get_score_description2(score, risk_level):
    """توضیح امتیاز با در نظر گرفتن ریسک"""
    risk_warning = ""
    
    if risk_level > 80:
        risk_warning = " ⚠️ ریسک بسیار بالا"
    elif risk_level > 65:
        risk_warning = " ⚠️ ریسک بالا"
    
    if score >= 70:
        return f"🟢 خرید قوی{risk_warning}"
    elif score >= 50:
        return f"🟢 خرید{risk_warning}"
    elif score >= 30:
        return f"🟡 خرید احتیاطی{risk_warning}"
    elif score >= -30:
        return f"⚪ خنثی{risk_warning}"
    elif score >= -50:
        return f"🟡 فروش احتیاطی{risk_warning}"
    elif score >= -70:
        return f"🔴 فروش{risk_warning}"
    else:
        return f"🔴 فروش قوی{risk_warning}"