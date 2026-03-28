import pandas as pd
import numpy as np
import joblib
import os
import streamlit as st

# [개선] 상대 경로 아키텍처 적용
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(CURRENT_DIR, "..", "..", "03_saved_models")
OPTIMAL_THRESHOLD = 0.5551

@st.cache_resource
def load_ml_objects():
    try:
        # 경로 정규화 (OS 간 호환성 확보)
        model = joblib.load(os.path.normpath(os.path.join(SAVE_DIR, 'churn_stacking_model.pkl')))
        encoder = joblib.load(os.path.normpath(os.path.join(SAVE_DIR, 'target_encoder.pkl')))
        scaler = joblib.load(os.path.normpath(os.path.join(SAVE_DIR, 'scaler.pkl')))
        columns = joblib.load(os.path.normpath(os.path.join(SAVE_DIR, 'model_columns.pkl')))
        return model, encoder, scaler, columns
    except Exception as e:
        st.error(f"모델 로드 중 치명적 오류: {e}")
        return None, None, None, None

def create_engineered_features(input_df):
    df = input_df.copy()
    
    # 0. 수치형 변수 강제 형변환 및 결측치 방어
    df['Total Charges'] = pd.to_numeric(df['Total Charges'], errors='coerce').fillna(0)
    df['Monthly Charges'] = pd.to_numeric(df['Monthly Charges'], errors='coerce').fillna(0)
    df['Tenure Months'] = pd.to_numeric(df['Tenure Months'], errors='coerce').fillna(0)

    # 1. 기본 카운트 및 단순 비율 변수
    lockin_services = ['Online Security', 'Online Backup', 'Tech Support', 'Device Protection']
    streaming_services = ['Streaming TV', 'Streaming Movies']
    
    df['Total_Security'] = df[lockin_services].apply(lambda x: (x == 'Yes').sum(), axis=1)
    df['Total_Streaming'] = df[streaming_services].apply(lambda x: (x == 'Yes').sum(), axis=1)
    df['Total_Internet_Services'] = df[['Internet Service']].apply(lambda x: 0 if x[0] == 'No' else 1, axis=1) # 로직 보강 필요
    
    # 2. 비즈니스 위험 지표 (에러 메시지 기반 복원)
    df['Risk_High_Charge_MtM'] = ((df['Contract'] == 'Month-to-month') & (df['Monthly Charges'] > 70)).astype(int)
    df['Risk_Fiber_MtM'] = ((df['Internet Service'] == 'Fiber optic') & (df['Contract'] == 'Month-to-month')).astype(int)
    df['Risk_No_TechSupport_Fiber'] = ((df['Internet Service'] == 'Fiber optic') & (df['Tech Support'] == 'No')).astype(int)
    df['Risk_Payment_Friction'] = ((df['Payment Method'] == 'Electronic check')).astype(int)
    
    # 3. 고급 파생 변수 (수학적 변환)
    df['Monthly_Charges_Sq'] = df['Monthly Charges'] ** 2
    df['Tenure_Sq'] = df['Tenure Months'] ** 2
    df['Tenure_x_Monthly'] = df['Tenure Months'] * df['Monthly Charges']
    df['Tenure_to_Monthly_Ratio'] = df['Tenure Months'] / (df['Monthly Charges'] + 1)
    df['Total_to_Monthly_Ratio'] = df['Total Charges'] / (df['Monthly Charges'] + 1)
    df['Monthly_to_Total_Ratio'] = df['Monthly Charges'] / (df['Total Charges'] + 1e-5)
    
    # 4. 고객 세그먼트 플래그
    df['Is_New_Customer'] = (df['Tenure Months'] <= 12).astype(int)
    df['Is_Long_Term_Customer'] = (df['Tenure Months'] >= 48).astype(int)
    df['Is_Auto_Payment'] = df['Payment Method'].str.contains('automatic').astype(int)
    df['Is_Single_Senior'] = ((df['Senior Citizen'] == 1) & (df['Partner'] == 'No')).astype(int)
    df['Is_Full_Family'] = ((df['Partner'] == 'Yes') & (df['Dependents'] == 'Yes')).astype(int)
    
    # 5. 가격 지표 ($CLTV$ 및 효율성)
    # 학습 데이터의 통계값(Mean/Median)이 필요하나, 없을 경우 입력값 기준으로 계산
    df['Price_per_Service'] = df['Monthly Charges'] / (df['Total_Security'] + df['Total_Streaming'] + 1)
    df['CLTV'] = df['Total Charges'] * df['Tenure Months'] # 예시 로직
    
    # 6. 기타 누락된 Placeholder (학습 시 사용된 컬럼 강제 생성)
    # 에러 메시지에 있는 모든 컬럼이 존재해야 하므로, 계산 불가능한 건 0으로 초기화
    missing_cols = [
        'Diff_from_Contract_Monthly', 'Phone Service', 'Avg_Monthly_by_Contract', 
        'Is_Independent_Youth', 'Has_Internet_But_No_Service', 'Avg_Tenure_by_Contract', 
        'Multiple Lines', 'Has_All_Services', 'Monthly_to_Median_Ratio', 
        'Diff_from_Contract_Tenure', 'Extra_Charges', 'Gender'
    ]
    for col in missing_cols:
        if col not in df.columns:
            df[col] = 0

    return df