import os
import pandas as pd
import numpy as np
import joblib
import streamlit as st

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR   = os.path.join(BASE_DIR, 'model')
MODEL_PATH  = os.path.join(MODEL_DIR, 'churn_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'churn_scaler.pkl')
FEAT_PATH   = os.path.join(MODEL_DIR, 'feature_columns.txt')

THRESHOLD = 0.5


@st.cache_resource
def load_ml_objects():
    try:
        model  = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        with open(FEAT_PATH, 'r') as f:
            columns = [line.strip() for line in f.readlines()]
        return model, scaler, columns
    except FileNotFoundError:
        return None, None, None


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    service_cols  = ['Phone Service','Multiple Lines','Online Security','Online Backup',
                     'Device Protection','Tech Support','Streaming TV','Streaming Movies']
    security_cols = ['Online Security','Online Backup','Device Protection','Tech Support']
    stream_cols   = ['Streaming TV','Streaming Movies']

    d['TotalServices']       = (d[service_cols]=='Yes').sum(axis=1)+(d['Internet Service']!='No').astype(int)
    d['AvgCost']             = d['Monthly Charges']/(d['TotalServices']+1)
    d['ContractScore']       = d['Contract'].map({'Month-to-month':0,'One year':1,'Two year':2}).fillna(0)
    d['LoyaltyScore']        = d['Tenure Months']*(d['ContractScore']+1)
    d['ChargeDensity']       = d['Total Charges']/(d['Tenure Months']+1)
    d['ChargePerTenure']     = d['Monthly Charges']/(d['Tenure Months']+1)
    d['MonthlyToTotal']      = d['Monthly Charges']/(d['Total Charges']+1)
    d['IsFiber']             = (d['Internet Service']=='Fiber optic').astype(int)
    d['SecurityServices']    = (d[security_cols]=='Yes').sum(axis=1)
    d['StreamingCount']      = (d[stream_cols]=='Yes').sum(axis=1)
    d['StreamRatio']         = d['StreamingCount']/(d['TotalServices']+1)
    d['AutoPay']             = d['Payment Method'].isin(['Bank transfer (automatic)','Credit card (automatic)']).astype(int)
    d['IsElecCheck']         = (d['Payment Method']=='Electronic check').astype(int)
    d['HighRiskFlag']        = ((d['Online Security']=='No')&(d['Tech Support']=='No')&(d['IsFiber']==1)).astype(int)
    d['Is_High_Risk_Combo']  = ((d['Contract']=='Month-to-month')&(d['Internet Service']=='Fiber optic')).astype(int)
    d['IsMonthToMonth']      = (d['Contract']=='Month-to-month').astype(int)
    d['LowTenureHighCharge'] = ((d['Tenure Months']<12)&(d['Monthly Charges']>70)).astype(int)
    d['NoProtection']        = ((d['Device Protection']=='No')&(d['Online Backup']=='No')).astype(int)
    d['SeniorAlone']         = ((d['Senior Citizen']=='Yes')&(d['Partner']=='No')&(d['Dependents']=='No')).astype(int)
    d['TenureContractRatio'] = d['Tenure Months']/(d['ContractScore']+1)
    d['Value_Score']         = d['SecurityServices']/(d['Monthly Charges']+1)
    d['Contract_Risk']       = d['Contract'].map({'Month-to-month':2,'One year':1,'Two year':0}).fillna(0)
    d['Payment_Risk']        = (d['Payment Method']=='Electronic check').astype(int)
    d['Spent_Intensity']     = d['Total Charges']/(d['Tenure Months']+1)

    t = float(d['Tenure Months'].iloc[0])
    if   t <= 12: tg = 'New(0~12)'
    elif t <= 24: tg = 'Watch(13~24)'
    elif t <= 48: tg = 'Stable(25~48)'
    else:         tg = 'Loyal(49~)'
    d['Tenure_Group'] = tg

    binary_map = {'Yes':1,'No':0,'Male':1,'Female':0}
    for col in ['Gender','Senior Citizen','Partner','Dependents','Phone Service','Paperless Billing']:
        if col in d.columns:
            d[col] = d[col].map(binary_map).fillna(0)

    d['City']       = 0
    d['Zip Code']   = 0
    d['GeoCluster'] = 4
    return d


def predict_churn(input_df, model, scaler, feature_cols):
    processed = engineer_features(input_df)
    cats      = processed.select_dtypes(include=['object','category']).columns.tolist()
    processed = pd.get_dummies(processed, columns=cats)
    processed = processed.reindex(columns=feature_cols, fill_value=0).fillna(0)
    scaled    = scaler.transform(processed)
    prob      = float(model.predict_proba(scaled)[0][1])
    return prob, prob >= THRESHOLD
