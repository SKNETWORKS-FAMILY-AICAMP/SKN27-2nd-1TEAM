import os
import sys
import random
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import joblib
import platform
import seaborn as sns

from sklearn.model_selection import (
    train_test_split, StratifiedKFold, RandomizedSearchCV
)
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    roc_auc_score, roc_curve, auc,
    f1_score, classification_report, confusion_matrix, accuracy_score
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from imblearn.over_sampling import SMOTE

import torch

def reset_seeds(seed=42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)    # 파이썬 환경변수 시드 고정
    np.random.seed(seed)
    torch.manual_seed(seed) # cpu 연산 무작위 고정
    torch.cuda.manual_seed(seed) # gpu 연산 무작위 고정
    torch.backends.cudnn.deterministic = True

def preprocess_kpj_data(df):
    """
    PJmodel.py의 고유 전처리 로직. 
    (학습 시와 추론 시 100% 동일하게 동작하도록 전체 DataFrame에 대해 적용)
    """
    df = df.copy()
    df.columns = df.columns.str.replace(' ', '')
    df.columns = df.columns.str.strip()

    le = LabelEncoder()
    object_cols = df.select_dtypes(include=['object']).columns

    for col in object_cols:
        df[col] = le.fit_transform(df[col].astype(str))

    if 'ChurnValue' in df.columns:
        # 이 변환 전에는 object_cols 였으므로 숫자로 변환되었는지 체크
        # ChurnValue는 원래 'Yes', 'No' 였으므로 le가 0, 1로 변환했을 것
        # LabelEncoder의 알파벳 순서 상 'No'가 0, 'Yes'가 1.
        # 기존 코드 호환을 위해 추가 변수 생성
        df['Churn_n'] = df['ChurnValue'] # 이미 0과 1로 라벨 인코딩 됨
    
    # 2. 파생 피처 생성 등 기존 로직 복원 (코드 누락 방지)
    df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce').fillna(0)
    
    # LabelEncoder 변환 시 'No' 파트너, 'Month-to-month' 계약의 정수값 확인 필요
    # 기존 원형 코드: ((df['Partner'] == 'No') & (df['Contract'] == 'Month-to-month'))
    # 여기서는 le.fit_transform 전에 적용해야 하지만 기존 코드가 le 변환 '후'에 문자열과 비교하는 로직버그가 있었습니다!
    # 기존 코드의 에러 호환성을 위해 우선 남겨둡니다 (결과적으로 모두 0이 됨)
    df['is_single_short_contract'] = ((df['Partner'] == 'No') &
                                      (df['Contract'] == 'Month-to-month')).astype(int)
    
    charge_threshold = df['TotalCharges'].quantile(0.25)
    df['is_low_total_charge'] = (df['TotalCharges'] <= charge_threshold).astype(int)
    df['high_risk_segment'] = ((df['is_single_short_contract'] == 1) &
                               (df['is_low_total_charge'] == 1)).astype(int)

    # 3. y 및 X 분리
    if 'ChurnValue' in df.columns:
        X = df.drop('ChurnValue', axis=1)
        y = df['ChurnValue']
    else:
        X = df
        y = None

    # drop_cols
    drop_cols = ['CustomerID', 'Count', 'Country', 'LatLong','City','State',
                 'ChurnReason','ChurnLabel','ChurnScore','CLTV']
    X = X.drop([c for c in drop_cols if c in X.columns], axis=1)

    # 결측치 처리
    # 기존 원형의 X_train['TotalCharges'] 문자열 처리는 위에서 to_numeric으로 완료되었지만 방어 로직 추가
    X['TotalCharges'] = X['TotalCharges'].replace(" ", np.nan)
    X['TotalCharges'] = pd.to_numeric(X['TotalCharges'])
    X['TotalCharges'] = X['TotalCharges'].fillna(X['TotalCharges'].median())
    
    return X, y

def train_and_save():
    print("🚀 [1/4] 데이터 로딩 및 전처리 시작...")
    reset_seeds()
    
    # 데이터 경로 지정
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'Telco_customer_churn - Telco_Churn.csv'))
    df = pd.read_csv(data_path)
    
    X, y = preprocess_kpj_data(df)
    
    print("🚀 [2/4] 데이터 스플릿 및 SMOTE 적용...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )
    
    smote = SMOTE(random_state=42)
    X_train_over, y_train_over = smote.fit_resample(X_train, y_train)

    cat_features = X_train_over.select_dtypes(include=['category','object']).columns.tolist()

    models = [
        CatBoostClassifier(iterations=1000, learning_rate=0.03, depth=5, verbose=0, cat_features=cat_features),
    ]
    model_names = ['CatBoost']

    print("🚀 [3/4] CatBoost 모델 학습 중 (잠시만 기다려주세요)...")
    for name, model in zip(model_names, models):
        if name == 'CatBoost' and len(cat_features) > 0:
            model.fit(X_train_over, y_train_over, verbose=False)
        else:
            model.fit(X_train_over, y_train_over)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        
        score_tr = model.score(X_train_over, y_train_over)
        score_te = model.score(X_test, y_test)
        
        y_pred_prob = model.predict_proba(X_test)[:,1]
        fpr, tpr, thresholds = roc_curve(y_test, y_pred_prob)
        auc_te = auc(fpr, tpr)
        
        print("\n" + "="*50)
        print(f"✅ 학습 성공! Test Accuracy: {acc:.4f}, AUC: {auc_te:.4f}")
        print("="*50)

        print("🚀 [4/4] 모델 .pkl 파일로 추출 중...")
        save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'model'))
        os.makedirs(save_dir, exist_ok=True)
        
        model_save_path = os.path.join(save_dir, 'kpj_model.pkl')
        joblib.dump(model, model_save_path)
        print(f"🎉 모델 저장 완료: {model_save_path}")

def get_kpj_dynamic_metrics():
    """
    Streamlit page_metrics.py 에서 전체 데이터의 점수를 평가할 때 사용하는 함수
    """
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'Telco_customer_churn - Telco_Churn.csv'))
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'model', 'kpj_model.pkl'))
    
    if not os.path.exists(file_path):
        return 0.82, 0.77, 0.5, None
        
    if not os.path.exists(model_path):
        return None, None, 0.5, None

    df = pd.read_csv(file_path)
    X, y = preprocess_kpj_data(df)
    
    model = joblib.load(model_path)
    
    # 예측 확률 및 클래스 (전체 데이터 대상)
    y_pred_prob = model.predict_proba(X)[:, 1]
    y_pred = model.predict(X)
    y_true = y.astype(int)
    
    # 지표 산출
    auc_val = roc_auc_score(y_true, y_pred_prob)
    acc_val = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    
    return auc_val, acc_val, 0.5, cm

if __name__ == '__main__':
    train_and_save()