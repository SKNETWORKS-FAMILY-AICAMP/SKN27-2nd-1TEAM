import pandas as pd
import numpy as np
import joblib
import os
import streamlit as st

# [전역 설정]
OPTIMAL_THRESHOLD = 0.5551
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "03_saved_models"))

@st.cache_resource
def load_ml_objects():
    try:
        model = joblib.load(os.path.join(SAVE_DIR, 'churn_stacking_model.pkl'))
        encoder = joblib.load(os.path.join(SAVE_DIR, 'target_encoder.pkl'))
        scaler = joblib.load(os.path.join(SAVE_DIR, 'scaler.pkl'))
        columns = joblib.load(os.path.join(SAVE_DIR, 'model_columns.pkl'))
        return model, encoder, scaler, columns
    except Exception as e:
        st.error(f"⚠️ 모델 로드 실패: {e}")
        return None, None, None, None

def create_engineered_features(input_df, model_columns=None):
    df = input_df.copy()

    # 1. 수치형 기초 정제 (타입 일치화)
    df['Total Charges'] = pd.to_numeric(df['Total Charges'], errors='coerce').fillna(0).astype('float64')
    df['Monthly Charges'] = pd.to_numeric(df['Monthly Charges'], errors='coerce').fillna(0).astype('float64')
    df['Tenure Months'] = pd.to_numeric(df['Tenure Months'], errors='coerce').fillna(0).astype('int64')
    df['Senior Citizen'] = pd.to_numeric(df['Senior Citizen'], errors='coerce').fillna(0).astype('int64')

    # 2. 서비스 카운트 기반 변수 (int64)
    internet_services = ['Online Security', 'Online Backup', 'Device Protection', 'Tech Support', 'Streaming TV', 'Streaming Movies']
    df['Total_Internet_Services'] = (df[internet_services] == 'Yes').sum(axis=1).astype('int64')
    df['Total_Streaming'] = (df[['Streaming TV', 'Streaming Movies']] == 'Yes').sum(axis=1).astype('int64')
    df['Total_Security'] = (df[['Online Security', 'Online Backup', 'Device Protection', 'Tech Support']] == 'Yes').sum(axis=1).astype('int64')

    # 3. 요금 및 비율 변수 (float64)
    df['Extra_Charges'] = (df['Total Charges'] - (df['Monthly Charges'] * df['Tenure Months'])).astype('float64')
    df['Price_per_Service'] = (df['Monthly Charges'] / (df['Total_Internet_Services'] + 1)).astype('float64')
    df['Total_to_Monthly_Ratio'] = (df['Total Charges'] / (df['Monthly Charges'] + 1e-5)).astype('float64')
    df['Tenure_to_Monthly_Ratio'] = (df['Tenure Months'] / (df['Monthly Charges'] + 1e-5)).astype('float64')
    
    TRAIN_MEDIAN_MONTHLY = 70.35 
    df['Monthly_to_Median_Ratio'] = (df['Monthly Charges'] / TRAIN_MEDIAN_MONTHLY).astype('float64')
    df['CLTV'] = (df['Total Charges'] * (df['Tenure Months'] + 1)).astype('float64')

    # 4. 그룹 통계 (float64/int64)
    df['Avg_Monthly_by_Contract'] = df['Monthly Charges'].astype('float64')
    df['Diff_from_Contract_Monthly'] = 0.0
    df['Avg_Tenure_by_Contract'] = df['Tenure Months'].astype('int64')
    df['Diff_from_Contract_Tenure'] = 0.0

    # 5. 세그먼트 플래그 (int64)
    df['Is_Full_Family'] = ((df['Partner'] == 'Yes') & (df['Dependents'] == 'Yes')).astype('int64')
    df['Is_Single_Senior'] = ((df['Senior Citizen'] == 1) & (df['Partner'] == 'No')).astype('int64')
    df['Is_Independent_Youth'] = ((df['Senior Citizen'] == 0) & (df['Partner'] == 'No')).astype('int64')
    df['Is_New_Customer'] = (df['Tenure Months'] <= 6).astype('int64')
    df['Is_Long_Term_Customer'] = (df['Tenure Months'] >= 60).astype('int64')
    df['Has_Internet_But_No_Service'] = ((df['Internet Service'] != 'No') & (df['Total_Internet_Services'] == 0)).astype('int64')
    df['Has_All_Services'] = (df['Total_Internet_Services'] == 6).astype('int64')
    df['Is_Auto_Payment'] = df['Payment Method'].astype(str).str.contains('automatic', case=False).astype('int64')

    # 6. 위험군 플래그 (int64)
    df['Risk_Fiber_MtM'] = ((df['Internet Service'] == 'Fiber optic') & (df['Contract'] == 'Month-to-month')).astype('int64')
    df['Risk_Payment_Friction'] = ((df['Payment Method'] == 'Electronic check') & (df['Paperless Billing'] == 'Yes')).astype('int64')
    df['Risk_High_Charge_MtM'] = ((df['Contract'] == 'Month-to-month') & (df['Monthly Charges'] > TRAIN_MEDIAN_MONTHLY)).astype('int64')
    df['Risk_No_TechSupport_Fiber'] = ((df['Internet Service'] == 'Fiber optic') & (df['Tech Support'] == 'No')).astype('int64')

    # 7. 비선형 변수
    df['Tenure_Sq'] = (df['Tenure Months'] ** 2).astype('int64')
    df['Monthly_Charges_Sq'] = (df['Monthly Charges'] ** 2).astype('float64')
    df['Tenure_x_Monthly'] = (df['Tenure Months'] * df['Monthly Charges']).astype('float64')

    # 8. 무결성 보장
    if model_columns is not None:
        for col in model_columns:
            if col not in df.columns:
                df[col] = 0

    return df