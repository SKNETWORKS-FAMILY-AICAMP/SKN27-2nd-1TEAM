# =============================================================
# src/01_preprocess.py — 피처 엔지니어링 + 전처리
#
# EDA 분석 결과를 바탕으로 데이터 누수 없이 전처리합니다.
#
# ❌ 제거한 누수 변수:
#   - Churn Score  : 이탈 발생 후 계산된 점수
#   - Churn Reason : 이탈 발생 후 수집된 사유
#   - CLTV         : 이탈 여부가 반영된 사후 계산값
#   - Churn Label  : Churn Value(1/0)로 대체
#
# 실행 방법: python src/01_preprocess.py
# 결과물:
#   - model/churn_scaler.pkl
#   - model/feature_columns.txt
#   - notebook/preprocessed_data.csv  (확인용)
# =============================================================

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans

# ─────────────────────────────────────────
# 📂 경로 설정 (폴더 구조에 맞게)
# ─────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE_DIR, 'data', 'Telco_customer_churn - Telco_Churn.csv')
MODEL_DIR   = os.path.join(BASE_DIR, 'model')
SCALER_PATH = os.path.join(MODEL_DIR, 'churn_scaler.pkl')
FEAT_PATH   = os.path.join(MODEL_DIR, 'feature_columns.txt')
OUTPUT_PATH = os.path.join(BASE_DIR, 'notebook', 'preprocessed_data.csv')

os.makedirs(MODEL_DIR, exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE    = 0.2


# ─────────────────────────────────────────
# Step 1. 데이터 로드
# ─────────────────────────────────────────
def load_data() -> pd.DataFrame:
    """원본 CSV 파일을 로드합니다."""
    if DATA_PATH.endswith('.xlsx'):
        df = pd.read_excel(DATA_PATH)
    else:
        df = pd.read_csv(DATA_PATH)

    # Total Charges: 문자열 → float 변환
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].astype(str).str.strip(),
        errors='coerce'
    ).fillna(0)

    print(f"  로드 완료: {len(df):,}행 {len(df.columns)}열")
    return df


# ─────────────────────────────────────────
# Step 2. 데이터 누수 변수 제거
# ─────────────────────────────────────────
def drop_leakage(df: pd.DataFrame) -> pd.DataFrame:
    """
    모델 학습에 사용하면 안 되는 변수를 제거합니다.

    제거 이유:
    - CustomerID     : 단순 식별자
    - Count          : 전부 1 (정보 없음)
    - Country        : 전부 United States (정보 없음)
    - State          : 전부 California (정보 없음)
    - Lat Long       : Latitude/Longitude 중복 문자열
    - Churn Label    : Churn Value(1/0)로 대체
    - Churn Score    : 이탈 후 계산된 값 → 데이터 누수
    - Churn Reason   : 이탈 후 수집된 값 → 데이터 누수
    - CLTV           : 이탈 여부 반영된 사후값 → 데이터 누수
    """
    drop_cols = [
        'CustomerID', 'Count', 'Country', 'State', 'Lat Long',
        'Churn Label', 'Churn Score', 'Churn Reason', 'CLTV',
    ]
    existing = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=existing)
    print(f"  누수 변수 {len(existing)}개 제거 → 남은 컬럼: {len(df.columns)}개")
    return df


# ─────────────────────────────────────────
# Step 3. 이상치 캡핑 (Tukey's Fences)
# ─────────────────────────────────────────
def handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    이상치를 제거하지 않고 상/하한으로 가두는 전략.
    정보 손실 최소화하면서 노이즈 제거.
    """
    cap_cols = ['Monthly Charges', 'Total Charges']
    for col in cap_cols:
        if col in df.columns:
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            df[col] = np.clip(df[col], Q1 - 1.5*IQR, Q3 + 1.5*IQR)
    print(f"  이상치 캡핑 완료: {cap_cols}")
    return df


# ─────────────────────────────────────────
# Step 4. 피처 엔지니어링
# EDA 분석 결과 기반으로 새 변수 생성
# ─────────────────────────────────────────
def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    EDA에서 발견한 인사이트를 바탕으로 파생 변수를 생성합니다.

    [EDA 근거]
    - 카이제곱 검정: Contract, Internet Service, Payment Method 모두 p<0.05
    - T-test: Monthly Charges, Tenure Months, Total Charges 모두 p<0.05
    - 생존 분석: 6개월 이내 이탈 위험 급증
    - 상관관계: ChargePerTenure +0.412, IsFiber +0.308, AutoPay -0.210
    """
    service_cols  = [
        'Phone Service', 'Multiple Lines', 'Online Security',
        'Online Backup', 'Device Protection', 'Tech Support',
        'Streaming TV', 'Streaming Movies'
    ]
    security_cols = ['Online Security', 'Online Backup', 'Device Protection', 'Tech Support']
    stream_cols   = ['Streaming TV', 'Streaming Movies']

    # ── 기본 집계 피처 ─────────────────────────────────
    # 총 가입 서비스 수
    df['TotalServices'] = (
        (df[service_cols] == 'Yes').sum(axis=1) +
        (df['Internet Service'] != 'No').astype(int)
    )

    # 서비스당 평균 비용 (요금 부담 지수)
    # 높을수록 서비스 대비 비용 부담 → 이탈 위험
    df['AvgCost'] = df['Monthly Charges'] / (df['TotalServices'] + 1)

    # ── 계약/충성도 피처 ────────────────────────────────
    # 계약 안정성 점수 (0=월별, 1=1년, 2=2년)
    # EDA: 계약 형태 카이제곱 p=5.86e-258 (가장 강력한 변수)
    df['ContractScore'] = df['Contract'].map({
        'Month-to-month': 0, 'One year': 1, 'Two year': 2
    })

    # 충성도 점수 (이용기간 × 계약 안정성)
    # 높을수록 오래된 장기 계약 고객
    df['LoyaltyScore'] = df['Tenure Months'] * (df['ContractScore'] + 1)

    # ── 요금 관련 피처 ──────────────────────────────────
    # 비용 밀도 (총요금 ÷ 이용기간)
    df['ChargeDensity'] = df['Total Charges'] / (df['Tenure Months'] + 1)

    # 월요금 ÷ 이용기간 (상관관계 +0.412 — 가장 강력한 수치 피처)
    # 단기+고요금 고객을 잡아내는 핵심 피처
    df['ChargePerTenure'] = df['Monthly Charges'] / (df['Tenure Months'] + 1)

    # 월요금 ÷ 총요금 비율
    df['MonthlyToTotal'] = df['Monthly Charges'] / (df['Total Charges'] + 1)

    # ── 인터넷/서비스 피처 ─────────────────────────────
    # Fiber optic 여부 (상관관계 +0.308)
    # EDA: Fiber optic 사용자 이탈률 69% vs 전체 26%
    df['IsFiber'] = (df['Internet Service'] == 'Fiber optic').astype(int)

    # 보안/지원 서비스 가입 수 (상관관계 -0.173)
    # 많을수록 Lock-in 효과 → 이탈률 낮음
    df['SecurityServices'] = (df[security_cols] == 'Yes').sum(axis=1)

    # 스트리밍 서비스 가입 수
    df['StreamingCount'] = (df[stream_cols] == 'Yes').sum(axis=1)

    # 스트리밍 비중 (스트리밍만 쓰는 고객 패턴)
    df['StreamRatio'] = df['StreamingCount'] / (df['TotalServices'] + 1)

    # ── 결제 피처 ───────────────────────────────────────
    # 자동결제 여부 (상관관계 -0.210)
    # EDA 생존분석: 자동결제 고객이 훨씬 오래 유지
    df['AutoPay'] = df['Payment Method'].isin([
        'Bank transfer (automatic)', 'Credit card (automatic)'
    ]).astype(int)

    # Electronic check 여부
    # EDA: Electronic check 이탈률 45% — 압도적 1위
    df['IsElecCheck'] = (df['Payment Method'] == 'Electronic check').astype(int)

    # ── 고위험 조합 피처 ────────────────────────────────
    # 극고위험 고객: 보안서비스 없음 + Fiber optic
    # EDA: 이 조합이 이탈률 가장 높음
    df['HighRiskFlag'] = (
        (df['Online Security'] == 'No') &
        (df['Tech Support']    == 'No') &
        (df['IsFiber']         == 1)
    ).astype(int)

    # 최악의 조합: 월별계약 + Fiber optic
    df['Is_High_Risk_Combo'] = (
        (df['Contract'] == 'Month-to-month') &
        (df['Internet Service'] == 'Fiber optic')
    ).astype(int)

    # 월별 계약 여부
    df['IsMonthToMonth'] = (df['Contract'] == 'Month-to-month').astype(int)

    # 단기+고요금 위험 고객
    # EDA 생존분석: 6개월 이내 이탈 위험 급증
    df['LowTenureHighCharge'] = (
        (df['Tenure Months'] < 12) & (df['Monthly Charges'] > 70)
    ).astype(int)

    # 기기 보호 없음
    df['NoProtection'] = (
        (df['Device Protection'] == 'No') & (df['Online Backup'] == 'No')
    ).astype(int)

    # 노인 + 혼자 사는 고객 (이탈 취약군)
    df['SeniorAlone'] = (
        (df['Senior Citizen'] == 'Yes') &
        (df['Partner']        == 'No') &
        (df['Dependents']     == 'No')
    ).astype(int)

    # 이용기간 ÷ 계약 안정성
    df['TenureContractRatio'] = df['Tenure Months'] / (df['ContractScore'] + 1)

    # 비용 효율성 (서비스 수 ÷ 월요금)
    df['Value_Score'] = df['SecurityServices'] / (df['Monthly Charges'] + 1)

    # 계약 위험성 점수 (높을수록 이탈 위험)
    df['Contract_Risk'] = df['Contract'].map({
        'Month-to-month': 2, 'One year': 1, 'Two year': 0
    })

    # 결제 위험성
    df['Payment_Risk'] = (df['Payment Method'] == 'Electronic check').astype(int)

    # 지출 밀도 (Total ÷ Tenure)
    df['Spent_Intensity'] = df['Total Charges'] / (df['Tenure Months'] + 1)

    # Tenure 구간화
    # EDA 생존분석: 신규(0~12개월)가 이탈 위험 가장 높음
    df['Tenure_Group'] = pd.cut(
        df['Tenure Months'],
        bins=[0, 12, 24, 48, 100],
        labels=['New(0~12)', 'Watch(13~24)', 'Stable(25~48)', 'Loyal(49~)'],
        right=True
    ).astype(str).replace('nan', 'New(0~12)')

    print(f"  피처 엔지니어링 완료: {len(df.columns)}개 컬럼")
    return df


# ─────────────────────────────────────────
# Step 5. 이진 변수 인코딩 (Yes/No → 1/0)
# ─────────────────────────────────────────
def encode_binary(df: pd.DataFrame) -> pd.DataFrame:
    """Yes/No, Male/Female 이진 변수를 1/0으로 변환합니다."""
    binary_map  = {'Yes': 1, 'No': 0, 'Male': 1, 'Female': 0}
    binary_cols = [
        'Gender', 'Senior Citizen', 'Partner', 'Dependents',
        'Phone Service', 'Paperless Billing'
    ]
    for col in binary_cols:
        if col in df.columns:
            df[col] = df[col].map(binary_map)
    print(f"  이진 인코딩 완료: {binary_cols}")
    return df


# ─────────────────────────────────────────
# Step 6. 학습/테스트 분리 + 인코딩 + 스케일링
# ─────────────────────────────────────────
def split_and_scale(df: pd.DataFrame):
    """
    분리를 먼저 수행한 뒤 모든 인코딩을 적용합니다.
    (데이터 누수 원천 차단)
    """
    X = df.drop(columns=['Churn Value'])
    y = df['Churn Value']

    # stratify=y: 이탈 비율을 train/test에 동일하게 유지
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size    = TEST_SIZE,
        random_state = RANDOM_STATE,
        stratify     = y
    )

    # ── GeoCluster: 위도/경도 군집화 ──────────────────
    # Fit은 train만, predict는 test에 적용 (누수 방지)
    if 'Latitude' in X_train.columns and 'Longitude' in X_train.columns:
        kmeans = KMeans(n_clusters=8, random_state=RANDOM_STATE, n_init='auto')
        X_train['GeoCluster'] = kmeans.fit_predict(X_train[['Latitude', 'Longitude']])
        X_test['GeoCluster']  = kmeans.predict(X_test[['Latitude', 'Longitude']])
        X_train = X_train.drop(columns=['Latitude', 'Longitude'])
        X_test  = X_test.drop(columns=['Latitude', 'Longitude'])
        print(f"  GeoCluster 생성 완료 (8개 군집)")

    # ── City, Zip Code 빈도 인코딩 ────────────────────
    # 고유값 너무 많아 원-핫 불가 → 빈도(비율)로 대체
    # Fit은 train만 (누수 방지)
    for col in ['City', 'Zip Code']:
        if col in X_train.columns:
            freq = X_train[col].value_counts() / len(X_train)
            X_train[col] = X_train[col].map(freq).fillna(0)
            X_test[col]  = X_test[col].map(freq).fillna(0)

    # ── 나머지 범주형 원-핫 인코딩 ───────────────────
    cat_cols = X_train.select_dtypes(include=['object', 'category']).columns.tolist()
    X_train  = pd.get_dummies(X_train, columns=cat_cols)
    X_test   = pd.get_dummies(X_test,  columns=cat_cols)

    # test에 없는 컬럼은 0으로 채우기 (train 기준으로 맞춤)
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)

    # NaN 정리
    X_train = X_train.fillna(0)
    X_test  = X_test.fillna(0)

    print(f"  최종 피처 수: {X_train.shape[1]}개")
    print(f"  학습: {len(X_train):,}행 ({y_train.mean()*100:.1f}% 이탈)")
    print(f"  테스트: {len(X_test):,}행 ({y_test.mean()*100:.1f}% 이탈)")

    # ── RobustScaler (이상치에 강한 스케일러) ─────────
    from sklearn.preprocessing import RobustScaler
    scaler         = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    # 스케일러 저장 (모델 예측 시 동일 기준 적용)
    joblib.dump(scaler, SCALER_PATH)
    print(f"  스케일러 저장: {SCALER_PATH}")

    return X_train_scaled, X_test_scaled, y_train, y_test, X_train.columns.tolist()


# ─────────────────────────────────────────
# Step 7. 결과 저장
# ─────────────────────────────────────────
def save_outputs(df: pd.DataFrame, feature_cols: list) -> None:
    """
    전처리 완료 데이터와 피처 컬럼 목록을 저장합니다.
    feature_columns.txt: 모델 예측 시 동일한 컬럼 순서 보장용
    """
    # 전처리 완료 CSV (확인용)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"  전처리 데이터 저장: {OUTPUT_PATH}")

    # 피처 컬럼 목록 저장
    with open(FEAT_PATH, 'w') as f:
        for col in feature_cols:
            f.write(col + '\n')
    print(f"  피처 컬럼 저장: {FEAT_PATH} ({len(feature_cols)}개)")


# ─────────────────────────────────────────
# 전체 파이프라인 실행
# ─────────────────────────────────────────
def run_pipeline():
    print('=' * 55)
    print('  전처리 파이프라인 시작')
    print('=' * 55)

    print('\n[Step 1] 데이터 로드')
    df = load_data()

    print('\n[Step 2] 누수 변수 제거')
    df = drop_leakage(df)

    print('\n[Step 3] 이상치 캡핑')
    df = handle_outliers(df)

    print('\n[Step 4] 피처 엔지니어링 (EDA 기반)')
    df = feature_engineering(df)

    print('\n[Step 5] 이진 변수 인코딩')
    df = encode_binary(df)

    print('\n[Step 6] 학습/테스트 분리 + 스케일링')
    X_train, X_test, y_train, y_test, feature_cols = split_and_scale(df)

    print('\n[Step 7] 결과 저장')
    save_outputs(df, feature_cols)

    print('\n' + '=' * 55)
    print(f'  ✅ 전처리 완료! 최종 피처: {len(feature_cols)}개')
    print('=' * 55)

    return X_train, X_test, y_train, y_test, feature_cols


# ─────────────────────────────────────────
# 실행 진입점
# ─────────────────────────────────────────
if __name__ == '__main__':
    X_train, X_test, y_train, y_test, feature_cols = run_pipeline()