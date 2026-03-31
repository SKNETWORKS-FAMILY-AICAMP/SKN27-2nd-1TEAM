# =============================================================
# src/02_model.py — 모델 학습 및 저장
#
# 01_preprocess.py 실행 후 사용하세요.
#
# 전략:
#   - SMOTE로 불균형 처리 (이탈 26% vs 유지 74%)
#   - RF + XGB + LGB + CatBoost Stacking 앙상블
#   - 평가지표: ROC-AUC + F1-Score (Accuracy 사용 X)
#
# 실행: python src/02_model.py
# 결과물:
#   - model/churn_model.pkl
#   - model/evaluation_result.png
#   - model/feature_importance.png
# =============================================================

import os
import random
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import joblib
import platform

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.metrics import (
    roc_auc_score, roc_curve, auc,
    f1_score, classification_report, confusion_matrix
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from imblearn.over_sampling import SMOTE

# ─────────────────────────────────────────
# 📂 경로 설정 (폴더 구조에 맞게)
# ─────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE_DIR, 'data', 'Telco_customer_churn - Telco_Churn.csv')
MODEL_DIR   = os.path.join(BASE_DIR, 'model')
MODEL_PATH  = os.path.join(MODEL_DIR, 'churn_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'churn_scaler.pkl')
FEAT_PATH   = os.path.join(MODEL_DIR, 'feature_columns.txt')

os.makedirs(MODEL_DIR, exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE    = 0.2

# 한글 폰트
if platform.system() == 'Darwin':
    matplotlib.rc('font', family='AppleGothic')
else:
    matplotlib.rc('font', family='Malgun Gothic')
matplotlib.rc('axes', unicode_minus=False)


# ─────────────────────────────────────────
# 1. 랜덤 시드 고정
# 재현성을 위해 모든 랜덤 시드를 고정합니다.
# ─────────────────────────────────────────
def reset_seeds(seed=RANDOM_STATE):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)

reset_seeds()


# ─────────────────────────────────────────
# 2. 01_preprocess.py 파이프라인 재사용
# ─────────────────────────────────────────
def load_and_preprocess():
    """
    01_preprocess.py의 전처리 파이프라인을 그대로 실행합니다.
    동일한 전처리 기준을 보장합니다.
    """
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import RobustScaler

    print("[데이터 로드 및 전처리]")

    if DATA_PATH.endswith('.xlsx'):
        df = pd.read_excel(DATA_PATH)
    else:
        df = pd.read_csv(DATA_PATH)

    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].astype(str).str.strip(), errors='coerce'
    ).fillna(0)

    # 누수 변수 제거
    drop_cols = [
        'CustomerID','Count','Country','State','Lat Long',
        'Churn Label','Churn Score','Churn Reason','CLTV',
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # 이상치 캡핑
    for col in ['Monthly Charges','Total Charges']:
        Q1,Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3-Q1
        df[col] = np.clip(df[col], Q1-1.5*IQR, Q3+1.5*IQR)

    # 피처 엔지니어링 (EDA 기반)
    service_cols  = ['Phone Service','Multiple Lines','Online Security','Online Backup',
                     'Device Protection','Tech Support','Streaming TV','Streaming Movies']
    security_cols = ['Online Security','Online Backup','Device Protection','Tech Support']
    stream_cols   = ['Streaming TV','Streaming Movies']

    df['TotalServices']       = (df[service_cols]=='Yes').sum(axis=1)+(df['Internet Service']!='No').astype(int)
    df['AvgCost']             = df['Monthly Charges']/(df['TotalServices']+1)
    df['ContractScore']       = df['Contract'].map({'Month-to-month':0,'One year':1,'Two year':2})
    df['LoyaltyScore']        = df['Tenure Months']*(df['ContractScore']+1)
    df['ChargeDensity']       = df['Total Charges']/(df['Tenure Months']+1)
    df['ChargePerTenure']     = df['Monthly Charges']/(df['Tenure Months']+1)
    df['MonthlyToTotal']      = df['Monthly Charges']/(df['Total Charges']+1)
    df['IsFiber']             = (df['Internet Service']=='Fiber optic').astype(int)
    df['SecurityServices']    = (df[security_cols]=='Yes').sum(axis=1)
    df['StreamingCount']      = (df[stream_cols]=='Yes').sum(axis=1)
    df['StreamRatio']         = df['StreamingCount']/(df['TotalServices']+1)
    df['AutoPay']             = df['Payment Method'].isin(['Bank transfer (automatic)','Credit card (automatic)']).astype(int)
    df['IsElecCheck']         = (df['Payment Method']=='Electronic check').astype(int)
    df['HighRiskFlag']        = ((df['Online Security']=='No')&(df['Tech Support']=='No')&(df['IsFiber']==1)).astype(int)
    df['Is_High_Risk_Combo']  = ((df['Contract']=='Month-to-month')&(df['Internet Service']=='Fiber optic')).astype(int)
    df['IsMonthToMonth']      = (df['Contract']=='Month-to-month').astype(int)
    df['LowTenureHighCharge'] = ((df['Tenure Months']<12)&(df['Monthly Charges']>70)).astype(int)
    df['NoProtection']        = ((df['Device Protection']=='No')&(df['Online Backup']=='No')).astype(int)
    df['SeniorAlone']         = ((df['Senior Citizen']=='Yes')&(df['Partner']=='No')&(df['Dependents']=='No')).astype(int)
    df['TenureContractRatio'] = df['Tenure Months']/(df['ContractScore']+1)
    df['Value_Score']         = df['SecurityServices']/(df['Monthly Charges']+1)
    df['Contract_Risk']       = df['Contract'].map({'Month-to-month':2,'One year':1,'Two year':0})
    df['Payment_Risk']        = (df['Payment Method']=='Electronic check').astype(int)
    df['Spent_Intensity']     = df['Total Charges']/(df['Tenure Months']+1)
    df['Tenure_Group']        = pd.cut(
        df['Tenure Months'],
        bins=[0, 12, 24, 48, 100],
        labels=['New(0~12)', 'Watch(13~24)', 'Stable(25~48)', 'Loyal(49~)'],
        right=True
    ).astype(str).replace('nan', 'New(0~12)')

    # 이진 인코딩
    binary_map = {'Yes':1,'No':0,'Male':1,'Female':0}
    for col in ['Gender','Senior Citizen','Partner','Dependents','Phone Service','Paperless Billing']:
        if col in df.columns:
            df[col] = df[col].map(binary_map)

    # 분리
    X = df.drop(columns=['Churn Value'])
    y = df['Churn Value']
    X_train,X_test,y_train,y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    # GeoCluster
    if 'Latitude' in X_train.columns:
        km = KMeans(n_clusters=8, random_state=RANDOM_STATE, n_init='auto')
        X_train['GeoCluster'] = km.fit_predict(X_train[['Latitude','Longitude']])
        X_test['GeoCluster']  = km.predict(X_test[['Latitude','Longitude']])
        X_train = X_train.drop(columns=['Latitude','Longitude'])
        X_test  = X_test.drop(columns=['Latitude','Longitude'])

    # 빈도 인코딩
    for col in ['City','Zip Code']:
        if col in X_train.columns:
            freq = X_train[col].value_counts()/len(X_train)
            X_train[col] = X_train[col].map(freq).fillna(0)
            X_test[col]  = X_test[col].map(freq).fillna(0)

    # 원-핫 인코딩
    cats = X_train.select_dtypes(include=['object','category']).columns.tolist()
    X_train = pd.get_dummies(X_train, columns=cats)
    X_test  = pd.get_dummies(X_test,  columns=cats)
    X_test  = X_test.reindex(columns=X_train.columns, fill_value=0)
    X_train = X_train.fillna(0)
    X_test  = X_test.fillna(0)

    # 스케일링
    scaler = RobustScaler()
    X_tr   = scaler.fit_transform(X_train)
    X_te   = scaler.transform(X_test)
    joblib.dump(scaler, SCALER_PATH)

    # 피처 컬럼 저장
    with open(FEAT_PATH, 'w') as f:
        for col in X_train.columns:
            f.write(col + '\n')

    print(f"  피처 수: {X_train.shape[1]}개")
    print(f"  학습: {len(X_train):,}행 / 테스트: {len(X_test):,}행")

    return X_tr, X_te, y_train, y_test, X_train.columns.tolist()


# ─────────────────────────────────────────
# 3. SMOTE — 불균형 처리
# 이탈(26%) vs 유지(74%) 불균형 해소
# 반드시 학습 데이터에만 적용!
# ─────────────────────────────────────────
def apply_smote(X_train, y_train):
    print("\n[SMOTE 불균형 처리]")
    unique, counts = np.unique(y_train, return_counts=True)
    print(f"  전 → 유지(0): {counts[0]:,} / 이탈(1): {counts[1]:,}")

    reset_seeds()
    smote = SMOTE(random_state=RANDOM_STATE)
    X_res, y_res = smote.fit_resample(X_train, y_train)

    unique, counts = np.unique(y_res, return_counts=True)
    print(f"  후 → 유지(0): {counts[0]:,} / 이탈(1): {counts[1]:,}")
    return X_res, y_res


# ─────────────────────────────────────────
# 4. Stacking 앙상블 학습
#
# Layer 1 (베이스): RF + XGB + LGB + CatBoost
# Layer 2 (메타):   LogisticRegression
#
# Soft Voting보다 Stacking이 유리한 이유:
# 각 모델 예측 확률을 메타 모델이 학습 → 가중치 자동 최적화
# ─────────────────────────────────────────
def run_model(X_train, y_train, X_test, y_test):
    print("\n[Stacking 앙상블 학습]")
    print("  ⏳ 약 10~15분 소요됩니다...")

    base_models = [
        ('rf', RandomForestClassifier(
            n_estimators = 300,
            max_depth    = 10,
            class_weight = 'balanced',
            random_state = RANDOM_STATE,
            n_jobs       = -1
        )),
        ('xgb', XGBClassifier(
            n_estimators     = 300,
            learning_rate    = 0.05,
            max_depth        = 6,
            scale_pos_weight = 3,
            eval_metric      = 'logloss',
            verbosity        = 0,
            random_state     = RANDOM_STATE
        )),
        ('lgb', LGBMClassifier(
            n_estimators  = 300,
            learning_rate = 0.05,
            num_leaves    = 63,
            is_unbalance  = True,
            random_state  = RANDOM_STATE,
            verbose       = -1
        )),
        ('cat', CatBoostClassifier(
            iterations        = 300,
            learning_rate     = 0.05,
            depth             = 6,
            auto_class_weights= 'Balanced',
            verbose           = 0,
            random_state      = RANDOM_STATE
        )),
    ]

    stacking = StackingClassifier(
        estimators      = base_models,
        final_estimator = LogisticRegression(random_state=RANDOM_STATE),
        cv              = 5,
        stack_method    = 'predict_proba',
        n_jobs          = -1
    )

    reset_seeds()
    stacking.fit(X_train, y_train)

    y_prob = stacking.predict_proba(X_test)[:, 1]
    y_pred = stacking.predict(X_test)

    auc_score = roc_auc_score(y_test, y_prob)
    f1        = f1_score(y_test, y_pred)

    print(f"\n  ===== 최종 모델 성능 =====")
    print(f"  ROC-AUC  : {auc_score:.4f}  ← 핵심 지표")
    print(f"  F1-Score : {f1:.4f}  ← 핵심 지표")
    print()
    print(classification_report(y_test, y_pred,
          target_names=['유지(0)', '이탈(1)']))

    return stacking, y_prob, y_pred


# ─────────────────────────────────────────
# 5. 시각화 — ROC 커브 + 혼동행렬 저장
# ─────────────────────────────────────────
def plot_results(model, X_test, y_test, y_prob, y_pred):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('최종 모델 평가 결과 (데이터 누수 없음)',
                 fontsize=14, fontweight='bold')

    # ROC 커브
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)
    axes[0].plot(fpr, tpr, color='#F44336', lw=2.5,
                 label=f'Stacking (AUC={roc_auc:.4f})')
    axes[0].plot([0,1],[0,1],'k--',lw=1)
    axes[0].set_xlabel('False Positive Rate')
    axes[0].set_ylabel('True Positive Rate')
    axes[0].set_title('ROC 커브')
    axes[0].legend(loc='lower right')
    axes[0].grid(True, alpha=0.3)

    # 혼동 행렬
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['예측:유지(0)','예측:이탈(1)'],
                yticklabels=['실제:유지(0)','실제:이탈(1)'],
                linewidths=1, ax=axes[1],
                annot_kws={'size':14,'weight':'bold'})
    axes[1].set_title('혼동 행렬 (Confusion Matrix)')
    axes[1].set_ylabel('실제 값')
    axes[1].set_xlabel('예측 값')

    plt.tight_layout()
    save_path = os.path.join(MODEL_DIR, 'evaluation_result.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  평가 이미지 저장: {save_path}")


# ─────────────────────────────────────────
# 6. Feature Importance — 변수 중요도
# RandomForest 기준으로 어떤 변수가 중요한지 확인
# ─────────────────────────────────────────
def plot_feature_importance(model, feature_cols):
    # Stacking 내부의 RF 모델에서 feature importance 추출
    try:
        rf_model = dict(model.named_estimators_)['rf']
        imp_df = pd.DataFrame({
            'feature'   : feature_cols,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False).head(20)

        plt.figure(figsize=(10, 8))
        bars = plt.barh(imp_df['feature'][::-1],
                        imp_df['importance'][::-1],
                        color='#42A5F5', edgecolor='white')
        plt.xlabel('중요도 (Importance)')
        plt.title('변수 중요도 Top 20 (RandomForest 기준)',
                  fontsize=13, fontweight='bold')
        for bar in bars:
            plt.text(bar.get_width()+0.001,
                     bar.get_y()+bar.get_height()/2,
                     f'{bar.get_width():.3f}',
                     va='center', fontsize=8)
        plt.tight_layout()

        save_path = os.path.join(MODEL_DIR, 'feature_importance.png')
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  변수 중요도 이미지 저장: {save_path}")
    except Exception as e:
        print(f"  변수 중요도 저장 실패: {e}")


# ─────────────────────────────────────────
# 실행 진입점
# ─────────────────────────────────────────
if __name__ == '__main__':
    print('=' * 55)
    print('  모델 학습 시작')
    print('=' * 55)

    # 1. 전처리
    X_train, X_test, y_train, y_test, feature_cols = load_and_preprocess()

    # 2. SMOTE
    X_res, y_res = apply_smote(X_train, y_train)

    # 3. 학습
    model, y_prob, y_pred = run_model(X_res, y_res, X_test, y_test)

    # 4. 시각화
    print("\n[결과 시각화 저장]")
    plot_results(model, X_test, y_test, y_prob, y_pred)
    plot_feature_importance(model, feature_cols)

    # 5. 모델 저장
    joblib.dump(model, MODEL_PATH)
    print(f"\n  모델 저장: {MODEL_PATH}")
    print(f"  스케일러 : {SCALER_PATH}")
    print(f"  피처 목록: {FEAT_PATH}")

    print('\n' + '=' * 55)
    print('  ✅ 학습 완료! app.py에서 이 모델을 사용합니다.')
    print('=' * 55)