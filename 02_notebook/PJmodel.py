import os
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
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, roc_curve, auc,
    f1_score, classification_report, confusion_matrix
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
  torch.backends.cudnn.deterministic = True  # cuda 라이브러리에서 Deterministic(결정론적)으로 예측하기 (예측에 대한 불확실성 제거 

#Load Data
reset_seeds() #랜덤 고정  !!!

# path 정보
df = pd.read_csv('../00_data/Telco_customer_churn - Telco_Churn.csv')
df.columns = df.columns.str.replace(' ', '')
df.columns = df.columns.str.strip()
print(df.columns)

#train test split
from sklearn.preprocessing import StandardScaler, LabelEncoder
le = LabelEncoder()
object_cols = df.select_dtypes(include=['object']).columns

for col in object_cols:
    df[col] = le.fit_transform(df[col].astype(str))

#feature enginering
#1. is_single_short_contract : 미혼이며 ,계약이 짧을경우, 결혼하거나 경제적 이유로 이탈율이 높다고 생각함
#2. is_low_total_charge: 누적 이용료 사용25%이하일 경우 이탈율 높음
#3. high_risk_segment : 위의 두 피처 &값 = 미혼이고 누적 기간이 짧다는 점은 결혼으로 통신사를 이탈할 젊은 고객을 예상하여 만듬
# 하지만 머신이 활용하지 않았음..
# 'Yes'는 1로, 'No'는 0으로 변환하여 새로운 컬럼 생성
df['Churn_n'] = df['ChurnValue'].apply(lambda x: 1 if x == 'Yes' else 0)
df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce').fillna(0)
# 3. 파생 피처 생성
df['is_single_short_contract'] = ((df['Partner'] == 'No') &
                                  (df['Contract'] == 'Month-to-month')).astype(int)
charge_threshold = df['TotalCharges'].quantile(0.25)
df['is_low_total_charge'] = (df['TotalCharges'] <= charge_threshold).astype(int)
df['high_risk_segment'] = ((df['is_single_short_contract'] == 1) &
                           (df['is_low_total_charge'] == 1)).astype(int)

#train test split
from sklearn.model_selection import train_test_split

# X: 특성(Features), y: 타겟(ChurnValue 여부)
X = df.drop('ChurnValue', axis=1)
y = df['ChurnValue']

# 데이터 분할 (8:2 비율)
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,        # 20%를 테스트용으로 사용
    random_state=42,
    stratify=y            # 정답(이탈/유지) 비율을 원본과 동일하게 유지
)
#print(f"학습용: {X_train.shape}, 테스트용: {X_test.shape}")

#Data preprocessing
# drop.column
drop_cols = ['CustomerID', 'Count', 'Country', 'LatLong','City','State','Country',
             'ChurnReason','ChurnLabel','ChurnScore','CLTV']

X_train.drop(drop_cols, axis=1, inplace= True)
X_test.drop(drop_cols, axis=1, inplace= True)

print(f'after: {X_train.shape} / {X_test.shape}')
# 결측치 확인
# TotalCharges 컬럼에 있는 빈 칸을 처리하는 게 핵심입니다.
X_train['TotalCharges'] = X_train['TotalCharges'].replace(" ", np.nan)
X_test['TotalCharges'] = X_test['TotalCharges'].replace(" ", np.nan)
# 문자가 섞여 있으면 학습이 안 되므로 숫자로 강제 변환합니다.
X_train['TotalCharges'] = pd.to_numeric(X_train['TotalCharges'])
X_test['TotalCharges'] = pd.to_numeric(X_test['TotalCharges'])
# 방법 B: 결측치를 평균값이나 중앙값으로 채우기
X_train['TotalCharges'] = X_train['TotalCharges'].fillna(X_train['TotalCharges'].median())
X_test['TotalCharges'] = X_test['TotalCharges'].fillna(X_test['TotalCharges'].median())

#SMOTE
smote = SMOTE(random_state=42)
X_train_over, y_train_over = smote.fit_resample(X_train, y_train)

from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, classification_report

cat_features = X_train_over.select_dtypes(include=['category','object']).columns.tolist()

# 2. 모델 리스트 생성
models = [
    CatBoostClassifier(iterations=1000, learning_rate=0.03, depth=5, verbose=0, cat_features=cat_features),

]
model_names = ['CatBoost']
# 3. 반복문을 통한 학습 및 평가
for name, model in zip(model_names, models):
    # CatBoost만 cat_features 인자가 필요하므로 조건부 처리
    if name == 'CatBoost':
        model.fit(X_train_over, y_train_over, verbose=False)
    else:
        model.fit(X_train_over, y_train_over)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

# print("\n" + "="*50)
# print(f"✅ 모델 정확도(Accuracy): {accuracy_score(y_test, y_pred):.4f}")
# print("-" * 50)
# print("📊 상세 성적표(Classification Report):")
# print(classification_report(y_test, y_pred))
# print("="*50)

#Evaluation 평가
score_tr = model.score(X_train_over, y_train_over)
score_te = model.score(X_test, y_test)

from sklearn.metrics import roc_curve, auc

y_pred = model.predict_proba(X_test)[:,1]
fpr, tpr, thresholds = roc_curve(y_test,y_pred)
auc_te = auc(fpr, tpr)

#피처 중요도'
df_feature_importances = pd.DataFrame(model.feature_importances_, X_train_over.columns).sort_values(by=[0], ascending=False).reset_index()

import easydict
args = easydict.EasyDict()
args.results.append(
    {
        'model': 'modelv1',
        'score_tr': score_tr,
        'score_te': score_te,
        'auc_te': auc_te,
        'len_features': X_train_over.shape[1],
        'feaute_importances': list(df_feature_importances['index'].values[:X_train_over.shape[1]]),
        'create_dt': ''
    }
)

args.results