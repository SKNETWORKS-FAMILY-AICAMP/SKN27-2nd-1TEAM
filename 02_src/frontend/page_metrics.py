import streamlit as st
import pandas as pd

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
        cm_df = pd.DataFrame(
            [["796 (TN)", "239 (FP)"], ["82 (FN)", "292 (TP)"]],
            columns=["예측: 유지(0)", "예측: 이탈(1)"],
            index=["실제: 유지(0)", "실제: 이탈(1)"]
        )
        st.table(cm_df)
        
    with col_fi:
        st.subheader("변수 중요도 (Feature Importance)")
        chart_data = pd.DataFrame(
            [0.85, 0.72, 0.65, 0.58, 0.45],
            index=['계약 형태', '가입 기간', '단기+고가', '인터넷 종류', '요금 비율'],
            columns=["중요도 가중치"]
        )
        st.bar_chart(chart_data)