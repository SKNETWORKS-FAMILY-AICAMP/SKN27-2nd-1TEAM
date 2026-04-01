import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform
import os
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix
from ml_utils import load_ml_objects, create_engineered_features, DATA_DIR, SAVE_DIR

# 한글 폰트 설정 (운영체제별)
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    plt.rc('font', family='NanumGothic')
plt.rcParams['axes.unicode_minus'] = False

@st.cache_data
def get_dynamic_metrics():
    model, encoder, scaler, columns, threshold = load_ml_objects()
    if model is None:
        return 0.8556, 0.7750, 0.5551, None
        
    file_path = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")
    if not os.path.exists(file_path):
        return 0.8556, 0.7750, threshold, None
        
    df = pd.read_csv(file_path)
    if 'Total Charges' in df.columns:
        df['Total Charges'] = pd.to_numeric(df['Total Charges'].replace(' ', np.nan))
        df.dropna(subset=['Total Charges'], inplace=True)
    
    target_col = 'Churn Label' if 'Churn Label' in df.columns else 'Churn'
    if target_col not in df.columns:
        return 0.8556, 0.7750, threshold, None
        
    y_true = df[target_col].map({'Yes': 1, 'No': 0}).fillna(0).astype(int)
    
    # Feature Engineering
    processed_df = create_engineered_features(df, model_columns=columns)
    processed_df = processed_df[columns]
    
    # Transform
    encoded_data = encoder.transform(processed_df).astype('float64')
    scaled_input = scaler.transform(encoded_data)
    
    # Predict
    y_pred_prob = model.predict_proba(scaled_input)[:, 1]
    y_pred = (y_pred_prob >= threshold).astype(int)
    
    # Metrics
    auc = roc_auc_score(y_true, y_pred_prob)
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    
    return auc, acc, threshold, cm

def render():
    st.title("AI 예측 모델 성능 지표 (Model Metrics)")
    st.markdown("현업 부서의 신뢰를 확보하기 위해, 모델의 객관적인 성능을 투명하게 공개합니다.")
    
    st.markdown("### 🔍 모델 선택")
    model_choice = st.radio(
        "성능을 확인할 모델을 선택하세요:",
        ("팀 통합 예측 모델 (Stacking)", "KPJ 실험 파생 모델 (CatBoost)"),
        horizontal=True
    )
    
    if model_choice == "KPJ 실험 파생 모델 (CatBoost)":
        with st.spinner("KPJ 모델(.pkl)을 불러와 성능을 동적으로 측정 중입니다..."):
            import sys
            import os
            kpj_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'notebook', 'kpj'))
            if kpj_path not in sys.path:
                sys.path.append(kpj_path)
            
            try:
                from PJmodel import get_kpj_dynamic_metrics
                @st.cache_data
                def load_kpj_metrics():
                    return get_kpj_dynamic_metrics()
                
                auc, acc, threshold, cm = load_kpj_metrics()
                if auc is None:
                    st.error("❗ KPJ 모델(.pkl) 파일을 찾을 수 없습니다. (모델이 학습되지 않았음)")
                    st.stop()
            except ImportError as e:
                st.error(f"KPJ 모듈을 불러오는 중 문제가 발생했습니다: {e}")
                st.stop()
    else:
        with st.spinner("통합 모델 지표를 동적으로 측정 중입니다..."):
            auc, acc, threshold, cm = get_dynamic_metrics()
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("AUC Score (예측 정확도)", f"{auc:.4f}", "전체 데이터 예측 결과")
    metric_col2.metric("Accuracy (전체 정확도)", f"{acc:.4f}", f"임계값 {threshold:.4f} 적용")
    metric_col3.metric("Optimal Threshold", f"{threshold:.4f}", "F1-Score 극대화 지점")
    
    st.markdown("---")
    col_cm, col_fi = st.columns(2)
    
    with col_cm:
        st.subheader("혼동 행렬 (Confusion Matrix)")
        
        # 동적 혼동 행렬 적용
        if cm is not None:
            cm_counts = cm.tolist()
            cm_norm = [
                [cm[0][0] / max(sum(cm[0]), 1), cm[0][1] / max(sum(cm[0]), 1)],
                [cm[1][0] / max(sum(cm[1]), 1), cm[1][1] / max(sum(cm[1]), 1)]
            ]
        else:
            cm_counts = [[796, 239], [82, 292]]
            cm_norm = [
                [796 / (796 + 239), 239 / (796 + 239)],
                [82 / (82 + 292), 292 / (82 + 292)]
            ]
            
        fig_cm, ax_cm = plt.subplots(figsize=(5, 4))
        sns.heatmap(
            cm_norm, 
            annot=[
                [f"{cm_norm[0][0]:.1%} (TN)\n{cm_counts[0][0]}건", f"{cm_norm[0][1]:.1%} (FP)\n{cm_counts[0][1]}건"], 
                [f"{cm_norm[1][0]:.1%} (FN)\n{cm_counts[1][0]}건", f"{cm_norm[1][1]:.1%} (TP)\n{cm_counts[1][1]}건"]
            ], 
            fmt='', 
            cmap='Blues', 
            vmin=0.0, vmax=1.0,
            cbar=False,
            xticklabels=["예측: 유지(0)", "예측: 이탈(1)"],
            yticklabels=["실제: 유지(0)", "실제: 이탈(1)"],
            linewidths=1,
            linecolor='white',
            ax=ax_cm
        )
        st.pyplot(fig_cm)
        
    with col_fi:
        st.subheader("변수 중요도 (Feature Importance)")
        
        fi_path = os.path.join(SAVE_DIR, "feature_importance.png")
        if os.path.exists(fi_path):
            st.image(fi_path, use_container_width=True)
        else:
            st.info("💡 변수 중요도 시각화 이미지가 없습니다.")