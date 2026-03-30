import pandas as pd
import numpy as np
import joblib
import os
import streamlit as st
import sklearn.utils._encode

# =====================================================================
# [중요 버그 픽스] Scikit-Learn TargetEncoder의 문자열 isnan() 충돌 우회 멍키패치
# Jupyter Notebook에서는 fit_transform만 수행되어 에러가 숨어 있었으나, 
# Streamlit에서 transform() 시 범주형 컬럼에 np.isnan을 시도하는 프레임워크 자체 버그가 있습니다.
# =====================================================================
_original_check_unknown = sklearn.utils._encode._check_unknown

def safe_check_unknown(values, known_values, return_mask=False):
    valid_mask = np.in1d(values, known_values)
    
    # 원본 코드의 if xp.any(xp.isnan(known_values)): 에서 발생하는 TypeError 차단
    try:
        # Pandas의 isna()는 객체/문자열 배열에서도 안전하게 동작합니다.
        if pd.isna(known_values).any():
            valid_mask = valid_mask | pd.isna(values)
    except Exception:
        pass

    diff = values[~valid_mask]
    if return_mask:
        return diff, valid_mask
    return diff

# 모듈이 로드될 때 안전한 패치 함수로 바꿔치기
sklearn.utils._encode._check_unknown = safe_check_unknown
# =====================================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR    = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "model"))
DATA_DIR    = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "data"))

@st.cache_data
def get_training_stats():
    """
    훈련 데이터셋의 중앙값 및 그룹 평균값을 캐싱합니다.
    인퍼런스(예측) 시 데이터 개수가 부족하더라도 모델 훈련 당시에 쓰인 수학적 기준점을 반영하기 위함입니다.
    """
    file_path = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")
    if not os.path.exists(file_path):
        # 만약 data 폴더에 원본 데이터가 없을 경우를 대비한 텔코 데이터 기본 통계 상수
        return {
            'monthly_median': 70.35, 
            'avg_monthly_by_contract': {'Month-to-month': 66.4, 'One year': 65.0, 'Two year': 60.8},
            'avg_tenure_by_contract': {'Month-to-month': 18.0, 'One year': 42.0, 'Two year': 57.0}
        }
    
    df = pd.read_csv(file_path)
    df['Total Charges'] = pd.to_numeric(df['Total Charges'].replace(' ', np.nan))
    df.dropna(subset=['Total Charges'], inplace=True)
    
    monthly_median = df['Monthly Charges'].median()
    avg_monthly = df.groupby('Contract')['Monthly Charges'].mean().to_dict()
    avg_tenure = df.groupby('Contract')['Tenure Months'].mean().to_dict()
    
    return {
        'monthly_median': monthly_median,
        'avg_monthly_by_contract': avg_monthly,
        'avg_tenure_by_contract': avg_tenure
    }

@st.cache_resource
def load_ml_objects():
    """
    최신 hwan_model_2.ipynb 모델에서 저장한 객체들로 교체합니다.
    """
    required = {
        'churn_model.pkl':      os.path.join(SAVE_DIR, 'churn_stacking_model.pkl'),
        'target_encoder.pkl':   os.path.join(SAVE_DIR, 'target_encoder.pkl'),
        'churn_scaler.pkl':     os.path.join(SAVE_DIR, 'scaler.pkl'),
        'model_columns.pkl':    os.path.join(SAVE_DIR, 'model_columns.pkl'),
    }

    missing = [name for name, path in required.items() if not os.path.exists(path)]
    if missing:
        st.error(
            f"model/ 폴더에 다음 필수 파일이 누락되었습니다: {', '.join(missing)}\n\n"
            f"탐색 경로: {SAVE_DIR}\n\n"
            "데이터 재학습을 통해 파일을 다시 생성하십시오."
        )
        return None, None, None, None, None

    try:
        model   = joblib.load(required['churn_model.pkl'])
        encoder = joblib.load(required['target_encoder.pkl'])
        scaler  = joblib.load(required['churn_scaler.pkl'])

        # 최신 방식에서는 리스트 객체 pkl을 불러옴
        columns = joblib.load(required['model_columns.pkl'])

        thresh_path = os.path.join(SAVE_DIR, 'optimal_threshold.pkl')
        threshold   = joblib.load(thresh_path) if os.path.exists(thresh_path) else 0.3906

        return model, encoder, scaler, columns, threshold

    except Exception as e:
        st.error(f"모델 객체 로드 중 시스템 예외가 발생했습니다: {e}")
        return None, None, None, None, None

def create_engineered_features(input_df, model_columns=None):
    """
    최신 hwan_model_2.ipynb 기준으로 대규모 파생 변수를 생성합니다.
    """
    df = input_df.copy()

    # ── 1. 기본 타입 정제 및 Target Encoder 충돌 방지 ─────────────────────────
    # 범주형 컬럼 명시
    cat_features = [
        'Gender', 'Partner', 'Dependents', 'Phone Service', 'Multiple Lines', 
        'Internet Service', 'Online Security', 'Online Backup', 'Device Protection', 
        'Tech Support', 'Streaming TV', 'Streaming Movies', 'Contract', 
        'Paperless Billing', 'Payment Method'
    ]

    # 객체(문자열) 컬럼이거나 명시적 범주형인 경우 혼합타입/NaN을 방지하여 TargetEncoder 에러 원천 차단
    for col in df.columns:
        if col in cat_features or df[col].dtype == 'object':
            df[col] = df[col].fillna('Unknown').astype(str)

    if 'Senior Citizen' in df.columns:
        df['Senior Citizen'] = df['Senior Citizen'].map(
            {0: 0, 1: 1, '0': 0, '1': 1, 'No': 0, 'Yes': 1, 'Unknown': 0}
        ).fillna(0).astype(int)

    for col in ['Monthly Charges', 'Total Charges', 'Tenure Months']:
        if col in df.columns:
            # 문자열이 섞여있거나 빈칸일 경우 NaN 전환 후 0으로 채움
            if df[col].dtype == 'object':
                df[col] = df[col].replace({'': np.nan, ' ': np.nan, 'Unknown': np.nan})
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # ── 2. 대규모 파생 변수 (hwan_model_2 로직과 100% 동일) ─────────────
    # 서비스 카운트 기반 변수
    internet_services = ['Online Security', 'Online Backup', 'Device Protection', 'Tech Support', 'Streaming TV', 'Streaming Movies']
    df['Total_Internet_Services'] = (df[[c for c in internet_services if c in df.columns]] == 'Yes').sum(axis=1)
    df['Total_Streaming'] = (df[[c for c in ['Streaming TV', 'Streaming Movies'] if c in df.columns]] == 'Yes').sum(axis=1)
    df['Total_Security'] = (df[[c for c in ['Online Security', 'Online Backup', 'Device Protection', 'Tech Support'] if c in df.columns]] == 'Yes').sum(axis=1)

    # 요금 기반 연속형 비율 변수
    df['Extra_Charges'] = df['Total Charges'] - (df['Monthly Charges'] * df['Tenure Months'])
    df['Price_per_Service'] = df['Monthly Charges'] / (df['Total_Internet_Services'] + 1)
    df['Total_to_Monthly_Ratio'] = df['Total Charges'] / (df['Monthly Charges'] + 1e-5)
    df['Tenure_to_Monthly_Ratio'] = df['Tenure Months'] / (df['Monthly Charges'] + 1e-5)
    
    # 훈련 데이터 통계 모듈 호출
    stats = get_training_stats()
    df['Monthly_to_Median_Ratio'] = df['Monthly Charges'] / stats['monthly_median']

    # 그룹 통계 기반 변수
    if 'Contract' in df.columns:
        df['Avg_Monthly_by_Contract'] = df['Contract'].map(stats['avg_monthly_by_contract']).fillna(stats['monthly_median'])
        df['Avg_Tenure_by_Contract'] = df['Contract'].map(stats['avg_tenure_by_contract']).fillna(0)
    else:
        df['Avg_Monthly_by_Contract'] = stats['monthly_median']
        df['Avg_Tenure_by_Contract'] = 0

    df['Diff_from_Contract_Monthly'] = df['Monthly Charges'] - df['Avg_Monthly_by_Contract']
    df['Diff_from_Contract_Tenure'] = df['Tenure Months'] - df['Avg_Tenure_by_Contract']

    # 고객 인구통계 및 관계 기반
    if 'Partner' in df.columns and 'Dependents' in df.columns:
        df['Is_Full_Family'] = ((df['Partner'] == 'Yes') & (df['Dependents'] == 'Yes')).astype(int)
        df['Is_Single_Senior'] = ((df['Senior Citizen'] == 1) & (df['Partner'] == 'No') & (df['Dependents'] == 'No')).astype(int)
        df['Is_Independent_Youth'] = ((df['Senior Citizen'] == 0) & (df['Partner'] == 'No') & (df['Dependents'] == 'No')).astype(int)
    else:
        for c in ['Is_Full_Family', 'Is_Single_Senior', 'Is_Independent_Youth']:
            df[c] = 0

    # 행동 및 가입 특성 기반
    df['Is_New_Customer'] = (df['Tenure Months'] <= 6).astype(int)
    df['Is_Long_Term_Customer'] = (df['Tenure Months'] >= 60).astype(int)
    if 'Internet Service' in df.columns:
        df['Has_Internet_But_No_Service'] = ((df['Internet Service'] != 'No') & (df['Total_Internet_Services'] == 0)).astype(int)
    else:
        df['Has_Internet_But_No_Service'] = 0
    df['Has_All_Services'] = (df['Total_Internet_Services'] == 6).astype(int)
    if 'Payment Method' in df.columns:
        df['Is_Auto_Payment'] = df['Payment Method'].astype(str).str.contains('automatic', case=False).astype(int)
    else:
        df['Is_Auto_Payment'] = 0

    # 복합 가설 기반 이탈 위험군 (High Risk Flags)
    if 'Internet Service' in df.columns and 'Contract' in df.columns:
        df['Risk_Fiber_MtM'] = ((df['Internet Service'] == 'Fiber optic') & (df['Contract'] == 'Month-to-month')).astype(int)
    else:
        df['Risk_Fiber_MtM'] = 0
        
    if 'Payment Method' in df.columns and 'Paperless Billing' in df.columns:
        df['Risk_Payment_Friction'] = ((df['Payment Method'] == 'Electronic check') & (df['Paperless Billing'] == 'Yes')).astype(int)
    else:
        df['Risk_Payment_Friction'] = 0

    if 'Contract' in df.columns:
        df['Risk_High_Charge_MtM'] = ((df['Contract'] == 'Month-to-month') & (df['Monthly Charges'] > stats['monthly_median'])).astype(int)
    else:
        df['Risk_High_Charge_MtM'] = 0
        
    if 'Internet Service' in df.columns and 'Tech Support' in df.columns:
        df['Risk_No_TechSupport_Fiber'] = ((df['Internet Service'] == 'Fiber optic') & (df['Tech Support'] == 'No')).astype(int)
    else:
        df['Risk_No_TechSupport_Fiber'] = 0

    # 비선형(다항) 파생 변수
    df['Tenure_Sq'] = df['Tenure Months'] ** 2
    df['Monthly_Charges_Sq'] = df['Monthly Charges'] ** 2
    df['Tenure_x_Monthly'] = df['Tenure Months'] * df['Monthly Charges']

    # ── 3. Target Encoder 통과 전 데이터 준비 ─────────────
    # TargetEncoder는 범주형 카테고리를 찾지 못하면 글로벌 0 또는 평균으로 반환하므로 안전하게 'Unknown' 혹은 0으로 결측 필터 처리
    if model_columns is not None:
        for col in model_columns:
            if col not in df.columns:
                if col in cat_features:
                    df[col] = 'Unknown'
                else:
                    df[col] = 0

    return df