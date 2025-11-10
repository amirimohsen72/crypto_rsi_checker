"""
ماژول Feature Engineering
Phase 4: آماده‌سازی دیتا برای Machine Learning

این ماژول:
1. Feature های لازم رو از دیتا استخراج می‌کنه
2. Label ها رو آماده می‌کنه (سودآور/ضرر)
3. Dataset رو برای training آماده می‌کنه
"""

import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split


def extract_features_from_signals(df):
    """
    استخراج feature های اصلی از جدول signals
    
    Args:
        df: DataFrame حاوی signals + performance
    
    Returns:
        DataFrame با feature های آماده
    """
    features = pd.DataFrame()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1️⃣ RSI Features
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if 'rsi_values' in df.columns:
        rsi_data = df['rsi_values'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else x
        )
        
        features['rsi_1m'] = rsi_data.apply(lambda x: x.get('1m', 50) if x else 50)
        features['rsi_5m'] = rsi_data.apply(lambda x: x.get('5m', 50) if x else 50)
        features['rsi_15m'] = rsi_data.apply(lambda x: x.get('15m', 50) if x else 50)
        features['rsi_1h'] = rsi_data.apply(lambda x: x.get('1h', 50) if x else 50)
        features['rsi_4h'] = rsi_data.apply(lambda x: x.get('4h', 50) if x else 50)
        
        # RSI میانگین
        features['rsi_avg'] = features[['rsi_1m', 'rsi_5m', 'rsi_15m']].mean(axis=1)
        
        # RSI انحراف معیار (convergence)
        features['rsi_std'] = features[['rsi_1m', 'rsi_5m', 'rsi_15m']].std(axis=1)
        
        # آیا oversold/overbought هست؟
        features['is_oversold'] = (features['rsi_avg'] < 30).astype(int)
        features['is_overbought'] = (features['rsi_avg'] > 70).astype(int)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2️⃣ Score & Confidence Features
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if 'score' in df.columns:
        features['score'] = df['score'].fillna(0)
        features['score_abs'] = np.abs(features['score'])
        features['score_direction'] = np.sign(features['score'])
    
    if 'advance_score' in df.columns:
        features['advance_score'] = df['advance_score'].fillna(0)
    
    if 'confidence' in df.columns:
        features['confidence'] = df['confidence'].fillna(50)
    
    if 'quality' in df.columns:
        features['quality'] = df['quality'].fillna(50)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3️⃣ Trend Features
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if 'signal_type' in df.columns:
        # Parse JSON
        signal_type_data = df['signal_type'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else {}
        )
        
        # Count trends
        features['trend_up_count'] = signal_type_data.apply(
            lambda x: list(x.values()).count('up') if isinstance(x, dict) else 0
        )
        features['trend_down_count'] = signal_type_data.apply(
            lambda x: list(x.values()).count('down') if isinstance(x, dict) else 0
        )
        features['trend_convergence'] = (features['trend_up_count'] + 
                                         features['trend_down_count'])
    
    if 'convergence_count' in df.columns:
        features['convergence_count'] = df['convergence_count'].fillna(0)
    
    if 'price_trend' in df.columns:
        # Encode categorical
        trend_map = {'up': 1, 'down': -1, 'neutral': 0}
        features['price_trend_encoded'] = df['price_trend'].map(trend_map).fillna(0)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4️⃣ Method Feature (کدوم روش استفاده شده)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if 'testmode' in df.columns:
        # One-hot encoding
        method_dummies = pd.get_dummies(df['testmode'], prefix='method')
        features = pd.concat([features, method_dummies], axis=1)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5️⃣ Time Features
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if 'entry_time' in df.columns:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        features['hour'] = df['entry_time'].dt.hour
        features['day_of_week'] = df['entry_time'].dt.dayofweek
        features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
    
    return features


def create_ml_dataset(cursor, target_period='1h', min_confidence=0):
    """
    ساخت dataset کامل برای ML
    
    Args:
        cursor: database cursor
        target_period: '15m', '30m', '1h', '4h', '24h'
        min_confidence: حداقل confidence برای فیلتر
    
    Returns:
        X, y, feature_names
    """
    # گرفتن دیتا
    query = """
        SELECT 
            sp.*,
            s.rsi_values,
            s.signal_type,
            s.signal_label,
            s.convergence_count,
            s.price_trend,
            s.advance_score,
            s.score,
            s.quality,
            s.testmode
        FROM signal_performance sp
        JOIN signals s ON sp.signal_id = s.id
        WHERE sp.change_1h IS NOT NULL
    """
    
    if min_confidence > 0:
        query += f" AND sp.confidence >= {min_confidence}"
    
    df = pd.read_sql_query(query, cursor.connection)
    
    if df.empty:
        print("⚠️ No data available!")
        return None, None, None
    
    print(f"📊 Total records: {len(df)}")
    
    # استخراج features
    features = extract_features_from_signals(df)
    
    # Target variable
    target_col = f'is_profitable_{target_period}'
    if target_col not in df.columns:
        print(f"⚠️ Target column {target_col} not found!")
        return None, None, None
    
    y = df[target_col].fillna(0).astype(int)
    
    # حذف ردیف‌های با target null
    valid_mask = df[target_col].notna()
    features = features[valid_mask]
    y = y[valid_mask]
    
    # حذف NaN ها
    features = features.fillna(0)
    
    print(f"✅ Features: {features.shape[1]}")
    print(f"✅ Samples: {len(features)}")
    print(f"✅ Positive samples: {y.sum()} ({y.mean()*100:.1f}%)")
    
    return features, y, features.columns.tolist()


def prepare_train_test_split(X, y, test_size=0.2, random_state=42):
    """
    تقسیم دیتا به train/test
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    print(f"\n📊 Train/Test Split:")
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test:  {len(X_test)} samples")
    print(f"   Train positive: {y_train.sum()} ({y_train.mean()*100:.1f}%)")
    print(f"   Test positive:  {y_test.sum()} ({y_test.mean()*100:.1f}%)")
    
    return X_train, X_test, y_train, y_test


def normalize_features(X_train, X_test):
    """
    نرمال‌سازی features با StandardScaler
    """
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_test_scaled, scaler


def analyze_feature_importance(features, y, feature_names):
    """
    تحلیل اهمیت features با correlation
    """
    from scipy.stats import pointbiserialr
    
    print(f"\n{'═'*80}")
    print(f"📊 FEATURE IMPORTANCE ANALYSIS")
    print(f"{'═'*80}")
    
    correlations = []
    
    for i, feature in enumerate(feature_names):
        try:
            corr, pval = pointbiserialr(y, features.iloc[:, i])
            correlations.append({
                'feature': feature,
                'correlation': abs(corr),
                'direction': 'positive' if corr > 0 else 'negative',
                'p_value': pval
            })
        except:
            pass
    
    # مرتب‌سازی بر اساس correlation
    correlations = sorted(correlations, key=lambda x: x['correlation'], reverse=True)
    
    print(f"\n🔝 Top 15 Most Important Features:\n")
    print(f"{'Feature':<30} {'Correlation':<12} {'Direction':<12} {'P-value':<10}")
    print("-" * 80)
    
    for i, item in enumerate(correlations[:15], 1):
        print(f"{item['feature']:<30} {item['correlation']:<12.4f} "
              f"{item['direction']:<12} {item['p_value']:<10.4f}")
    
    return correlations


def export_processed_dataset(X, y, feature_names, filename='ml_ready_dataset.csv'):
    """
    Export dataset آماده برای ML
    """
    df_export = pd.DataFrame(X, columns=feature_names)
    df_export['target'] = y
    df_export.to_csv(filename, index=False)
    
    print(f"\n✅ Dataset exported: {filename}")
    print(f"   Shape: {df_export.shape}")
    
    return filename


if __name__ == "__main__":
    import sqlite3
    
    # Test
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    print("🚀 Creating ML Dataset...\n")
    
    X, y, feature_names = create_ml_dataset(cursor, target_period='1h', min_confidence=50)
    
    if X is not None:
        # Feature importance
        analyze_feature_importance(X, y, feature_names)
        
        # Train/test split
        X_train, X_test, y_train, y_test = prepare_train_test_split(X, y)
        
        # Export
        export_processed_dataset(X, y, feature_names)
    
    conn.close()