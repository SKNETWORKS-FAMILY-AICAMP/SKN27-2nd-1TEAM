import pandas as pd
import numpy as np
import joblib
import os
import streamlit as st

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR    = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "model"))

@st.cache_resource
def load_ml_objects():
    required = {
        'churn_model.pkl':      os.path.join(SAVE_DIR, 'churn_model.pkl'),
        'target_encoder.pkl':   os.path.join(SAVE_DIR, 'target_encoder.pkl'),
        'churn_scaler.pkl':     os.path.join(SAVE_DIR, 'churn_scaler.pkl'),
        'feature_columns.txt':  os.path.join(SAVE_DIR, 'feature_columns.txt'),
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

        with open(required['feature_columns.txt'], 'r', encoding='utf-8') as f:
            columns = [line.strip() for line in f if line.strip()]

        thresh_path = os.path.join(SAVE_DIR, 'optimal_threshold.pkl')
        threshold   = joblib.load(thresh_path) if os.path.exists(thresh_path) else 0.3986

        return model, encoder, scaler, columns, threshold

    except Exception as e:
        st.error(f"모델 객체 로드 중 시스템 예외가 발생했습니다: {e}")
        return None, None, None, None, None


def create_engineered_features(input_df, model_columns=None):
    df = input_df.copy()

    CAT_COLS = [
        'Gender', 'Senior Citizen', 'Partner', 'Dependents', 'Phone Service',
        'Multiple Lines', 'Internet Service', 'Online Security', 'Online Backup',
        'Device Protection', 'Tech Support', 'Streaming TV', 'Streaming Movies',
        'Contract', 'Paperless Billing', 'Payment Method'
    ]

    # 1. 범주형 데이터 강제 변환 및 결측치 선제 방어
    for col in CAT_COLS:
        if col in df.columns:
            if col == 'Senior Citizen':
                df[col] = df[col].map({0: 'No', 1: 'Yes', '0': 'No', '1': 'Yes'}).fillna(df[col]).astype(str)
            else:
                df[col] = df[col].astype(str)
        else:
            df[col] = 'No'

    # 2. 수치형 데이터 강제 변환 및 결측치 선제 방어
    num_cols = ['Total Charges', 'Monthly Charges', 'Tenure Months']
    for col in num_cols:
        if col not in df.columns:
            df[col] = 0.0
            
    df['Total Charges']   = pd.to_numeric(df['Total Charges'],   errors='coerce').fillna(0).astype('float64')
    df['Monthly Charges'] = pd.to_numeric(df['Monthly Charges'], errors='coerce').fillna(0).astype('float64')
    df['Tenure Months']   = pd.to_numeric(df['Tenure Months'],   errors='coerce').fillna(0).astype('int64')

    # 3. 서비스 카운트 기반 변수
    internet_services = ['Online Security', 'Online Backup', 'Device Protection', 'Tech Support', 'Streaming TV', 'Streaming Movies']
    df['Total_Internet_Services'] = (df[internet_services] == 'Yes').sum(axis=1).astype('int64')
    df['Total_Streaming']         = (df[['Streaming TV', 'Streaming Movies']] == 'Yes').sum(axis=1).astype('int64')
    df['Total_Security']          = (df[['Online Security', 'Online Backup', 'Device Protection', 'Tech Support']] == 'Yes').sum(axis=1).astype('int64')

    # 4. 요금 및 비율 변수
    df['Extra_Charges']           = (df['Total Charges'] - (df['Monthly Charges'] * df['Tenure Months'])).astype('float64')
    df['Price_per_Service']       = (df['Monthly Charges'] / (df['Total_Internet_Services'] + 1)).astype('float64')
    df['Total_to_Monthly_Ratio']  = (df['Total Charges']  / (df['Monthly Charges'] + 1e-5)).astype('float64')
    df['Tenure_to_Monthly_Ratio'] = (df['Tenure Months']  / (df['Monthly Charges'] + 1e-5)).astype('float64')

    TRAIN_MEDIAN_MONTHLY          = 70.35
    df['Monthly_to_Median_Ratio'] = (df['Monthly Charges'] / TRAIN_MEDIAN_MONTHLY).astype('float64')
    df['CLTV']                    = (df['Total Charges'] * (df['Tenure Months'] + 1)).astype('float64')

    # 5. 그룹 통계
    df['Avg_Monthly_by_Contract']    = df['Monthly Charges'].astype('float64')
    df['Diff_from_Contract_Monthly'] = 0.0
    df['Avg_Tenure_by_Contract']     = df['Tenure Months'].astype('int64')
    df['Diff_from_Contract_Tenure']  = 0.0

    # 6. 세그먼트 플래그
    df['Is_Full_Family']              = ((df['Partner'] == 'Yes') & (df['Dependents'] == 'Yes')).astype('int64')
    df['Is_Single_Senior']            = ((df['Senior Citizen'] == 'Yes') & (df['Partner'] == 'No')).astype('int64')
    df['Is_Independent_Youth']        = ((df['Senior Citizen'] == 'No')  & (df['Partner'] == 'No')).astype('int64')
    df['Is_New_Customer']             = (df['Tenure Months'] <= 6).astype('int64')
    df['Is_Long_Term_Customer']       = (df['Tenure Months'] >= 60).astype('int64')
    df['Has_Internet_But_No_Service'] = ((df['Internet Service'] != 'No') & (df['Total_Internet_Services'] == 0)).astype('int64')
    df['Has_All_Services']            = (df['Total_Internet_Services'] == 6).astype('int64')
    df['Is_Auto_Payment']             = df['Payment Method'].astype(str).str.contains('automatic', case=False).astype('int64')

    # 7. 위험군 플래그
    df['Risk_Fiber_MtM']           = ((df['Internet Service'] == 'Fiber optic') & (df['Contract'] == 'Month-to-month')).astype('int64')
    df['Risk_Payment_Friction']    = ((df['Payment Method'] == 'Electronic check') & (df['Paperless Billing'] == 'Yes')).astype('int64')
    df['Risk_High_Charge_MtM']     = ((df['Contract'] == 'Month-to-month') & (df['Monthly Charges'] > TRAIN_MEDIAN_MONTHLY)).astype('int64')
    df['Risk_No_TechSupport_Fiber']= ((df['Internet Service'] == 'Fiber optic') & (df['Tech Support'] == 'No')).astype('int64')

    # 8. 비선형 변수
    df['Tenure_Sq']          = (df['Tenure Months'] ** 2).astype('int64')
    df['Monthly_Charges_Sq'] = (df['Monthly Charges'] ** 2).astype('float64')
    df['Tenure_x_Monthly']   = (df['Tenure Months'] * df['Monthly Charges']).astype('float64')

    # 9. 무결성 최종 보장 (타입 엄격 분리)
    if model_columns is not None:
        for col in model_columns:
            if col not in df.columns:
                if col in CAT_COLS:
                    df[col] = 'No'
                else:
                    df[col] = 0.0

    return df