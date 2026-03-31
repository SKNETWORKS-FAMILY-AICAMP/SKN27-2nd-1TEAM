import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# 한글 폰트 설정 (운영체제별)
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    plt.rc('font', family='NanumGothic')
plt.rcParams['axes.unicode_minus'] = False

def render():
    st.title("AI 예측 모델 성능 지표 (Model Metrics)")
    st.markdown("현업 부서의 신뢰를 확보하기 위해, 모델의 객관적인 성능을 투명하게 공개합니다.")
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("AUC Score (예측 정확도)", "0.8556", "성능 검증 완료")
    metric_col2.metric("Accuracy (전체 정확도)", "0.7750", "최적 임계값 적용 기준")
    metric_col3.metric("Optimal Threshold", "0.5551", "F1-Score 극대화 지점")
    
    st.markdown("---")
    col_cm, col_fi = st.columns(2)
    
    with col_cm:
        st.subheader("혼동 행렬 (Confusion Matrix)")
        
        # Seaborn Heatmap 적용 (Normalized)
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
        
        # Seaborn Barplot 적용
        labels = ['계약 형태', '가입 기간', '단기+고가', '인터넷 종류', '요금 비율']
        values = [0.85, 0.72, 0.65, 0.58, 0.45]
        
        fig_fi, ax_fi = plt.subplots(figsize=(5, 4))
        sns.barplot(
            x=values, 
            y=labels, 
            hue=labels, 
            legend=False,
            palette='viridis', 
            ax=ax_fi
        )
        ax_fi.set_xlabel("중요도 가중치")
        st.pyplot(fig_fi)