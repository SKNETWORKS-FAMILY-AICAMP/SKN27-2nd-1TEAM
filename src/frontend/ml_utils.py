import pandas as pd
import joblib
import os
import streamlit as st

# 모델이 저장된 절대 경로 (구조에 맞게 재설정됨)
SAVE_DIR = r"C:\dev\SKN27-2nd-1TEAM\03_saved_models"
OPTIMAL_THRESHOLD = 0.5551

@st.cache_resource
def load_ml_objects():
    try:
        model = joblib.load(os.path.join(SAVE_DIR, 'churn_stacking_model.pkl'))
        encoder = joblib.load(os.path.join(SAVE_DIR, 'target_encoder.pkl'))
        scaler = joblib.load(os.path.join(SAVE_DIR, 'scaler.pkl'))
        columns = joblib.load(os.path.join(SAVE_DIR, 'model_columns.pkl'))
        return model, encoder, scaler, columns
    except Exception as e:
        return None, None, None, None

def create_engineered_features(input_df):
    df = input_df.copy()
    
    lockin_services = ['Online Security', 'Online Backup', 'Tech Support', 'Device Protection']
    df['Lockin_Service_Count'] = df[lockin_services].apply(lambda x: (x == 'Yes').sum(), axis=1)
    
    df['MtM_x_HighCharge'] = ((df['Contract'] == 'Month-to-month') & (df['Monthly Charges'] > 70.05)).astype(int)
    df['New_Fiber_Risk'] = ((df['Tenure Months'] <= 12) & (df['Internet Service'] == 'Fiber optic')).astype(int)
    df['LongTenure_MtM_Risk'] = ((df['Tenure Months'] >= 48) & (df['Contract'] == 'Month-to-month')).astype(int)
    df['Payment_Friction'] = ((df['Payment Method'] == 'Electronic check') & (df['Paperless Billing'] == 'Yes')).astype(int)
    df['Fiber_No_Lockin'] = ((df['Internet Service'] == 'Fiber optic') & (df['Lockin_Service_Count'] == 0)).astype(int)
    df['Charge_per_Lockin'] = df['Monthly Charges'] / (df['Lockin_Service_Count'] + 1)
    df['Monthly_to_Total_Ratio'] = df['Monthly Charges'] / (df['Total Charges'] + 1e-5)
    
    return df