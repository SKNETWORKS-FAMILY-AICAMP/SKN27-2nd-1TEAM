import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_and_process():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    # 이진 인코딩
    binary_map = {'Yes':1,'No':0,'Male':1,'Female':0}
    for col in ['Gender','Senior Citizen','Partner','Dependents',
                'Phone Service','Paperless Billing']:
        if col in df.columns:
            df[col] = df[col].map(binary_map).fillna(df[col])
    # 수치형만
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return df, num_cols

def render():
    st.title("🔗 상관관계 분석")
    st.caption("변수 간 상관관계와 이탈에 영향을 미치는 핵심 요인을 분석합니다.")

    df, num_cols = load_and_process()

    tab1, tab2, tab3 = st.tabs(["🌡️ 상관관계 히트맵", "📊 이탈 상관 TOP 10", "🔬 변수 심층 분석"])

    # ── TAB 1: 히트맵 ─────────────────────────────
    with tab1:
        st.subheader("변수 간 상관관계 히트맵")

        key_cols = [c for c in num_cols if c in [
            'Churn Value','Tenure Months','Monthly Charges','Total Charges',
            'Senior Citizen','Partner','Dependents','Phone Service','Paperless Billing'
        ]]

        corr = df[key_cols].corr()
        fig  = px.imshow(corr, text_auto='.2f',
                         color_continuous_scale='RdBu_r',
                         zmin=-1, zmax=1,
                         title='핵심 변수 상관관계 히트맵',
                         aspect='auto', height=500)
        fig.update_layout(margin=dict(t=50,b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.info("""
        💡 **해석 방법**
        - **빨간색 (+1 근처)**: 양의 상관관계 → 함께 증가
        - **파란색 (-1 근처)**: 음의 상관관계 → 반대로 움직임
        - **흰색 (0 근처)**: 상관관계 없음
        """)

    # ── TAB 2: 이탈 상관 TOP 10 ───────────────────
    with tab2:
        st.subheader("이탈(Churn Value)과 상관관계 TOP 10")

        if 'Churn Value' in num_cols:
            corr_churn = df[num_cols].corr()['Churn Value'].drop('Churn Value')
            corr_churn = corr_churn.dropna().sort_values(key=abs, ascending=False).head(10)

            colors = ['#F44336' if v > 0 else '#4CAF50' for v in corr_churn.values]

            fig = go.Figure(go.Bar(
                x=corr_churn.values,
                y=corr_churn.index,
                orientation='h',
                marker_color=colors,
                text=[f'{v:.3f}' for v in corr_churn.values],
                textposition='outside'
            ))
            fig.update_layout(
                title='이탈과 상관관계 TOP 10 변수',
                xaxis_title='상관계수',
                yaxis_title='변수',
                height=450,
                xaxis=dict(range=[-1,1]),
                shapes=[dict(type='line', x0=0, x1=0, y0=-0.5,
                             y1=len(corr_churn)-0.5,
                             line=dict(color='black', width=1, dash='dash'))]
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**상관관계 해석**")
            for var, val in corr_churn.items():
                if abs(val) >= 0.2:
                    direction = "높을수록 이탈 위험 증가 ⬆️" if val > 0 else "높을수록 이탈 위험 감소 ⬇️"
                    st.write(f"- **{var}** ({val:.3f}): {direction}")

    # ── TAB 3: 변수 심층 분석 ─────────────────────
    with tab3:
        st.subheader("변수 심층 분석")

        # Y축 Churn Value 고정
        x_var = st.selectbox("X축 변수 선택", [c for c in num_cols if c != 'Churn Value'])
        y_var = 'Churn Value'
        st.caption("Y축은 이탈 여부(Churn Value)로 고정됩니다.")

        fig = px.scatter(df, x=x_var, y=y_var,
                         color='Churn Value',
                         color_continuous_scale=['#4CAF50','#F44336'],
                         opacity=0.5, height=400,
                         title=f'{x_var} vs 이탈 여부')
        fig.update_layout(
            yaxis_title='이탈 여부 (0=유지, 1=이탈)',
            coloraxis_colorbar=dict(tickvals=[0,1], ticktext=['유지','이탈'])
        )
        st.plotly_chart(fig, use_container_width=True)

        # t-test
        group0 = df[df['Churn Value']==0][x_var].dropna()
        group1 = df[df['Churn Value']==1][x_var].dropna()
        t_stat, p_val = stats.ttest_ind(group0, group1)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("유지 고객 평균", f"{group0.mean():.2f}")
        col_b.metric("이탈 고객 평균", f"{group1.mean():.2f}")
        col_c.metric("p-value", f"{p_val:.4f}",
                     delta="통계적으로 유의미" if p_val < 0.05 else "유의미하지 않음",
                     delta_color="normal" if p_val < 0.05 else "inverse")

        if p_val < 0.05:
            st.success(f"✅ **{x_var}** 는 이탈과 통계적으로 유의미한 차이가 있습니다. (p={p_val:.4f})")
        else:
            st.warning(f"⚠️ **{x_var}** 는 이탈과 통계적으로 유의미한 차이가 없습니다. (p={p_val:.4f})")
