import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

@st.cache_data
def run_kmeans(n_clusters):
    df = load_raw()
    features = ['Tenure Months', 'Monthly Charges', 'Total Charges']
    X = df[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    df['세그먼트'] = km.fit_predict(X_scaled).astype(str)
    return df

def render():
    st.title("👥 고객 세그먼트 분석")
    st.caption("K-Means 클러스터링으로 고객을 그룹화하고 특성을 분석합니다.")

    tab1, tab2, tab3 = st.tabs(["🔵 세그먼트 분류", "📊 그룹별 특성", "⚠️ 이탈 위험 분석"])

    # ── TAB 1: 세그먼트 분류 ──────────────────────
    with tab1:
        st.subheader("K-Means 클러스터링")

        n_clusters = st.slider("세그먼트 수", 2, 6, 4)
        df = run_kmeans(n_clusters)

        # 세그먼트명 자동 부여
        seg_stats = df.groupby('세그먼트').agg(
            평균이용기간=('Tenure Months','mean'),
            평균월요금=('Monthly Charges','mean'),
            이탈률=('Churn Value','mean')
        ).round(2)

        seg_labels = {}
        for seg in seg_stats.index:
            row = seg_stats.loc[seg]
            if row['이탈률'] >= 0.4:
                label = f"🔴 고위험 (Seg {seg})"
            elif row['평균이용기간'] >= 40:
                label = f"🟢 충성 (Seg {seg})"
            elif row['평균월요금'] >= 75:
                label = f"🟡 고가치 (Seg {seg})"
            else:
                label = f"🔵 일반 (Seg {seg})"
            seg_labels[seg] = label

        df['세그먼트명'] = df['세그먼트'].map(seg_labels)

        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.scatter(df.sample(min(2000,len(df))),
                             x='Tenure Months', y='Monthly Charges',
                             color='세그먼트명',
                             title='세그먼트별 이용기간 vs 월 요금',
                             opacity=0.6, height=400)
            fig.update_layout(xaxis_title='이용 기간 (월)', yaxis_title='월 요금 ($)')
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            seg_count = df['세그먼트명'].value_counts().reset_index()
            seg_count.columns = ['세그먼트','고객 수']
            fig = px.pie(seg_count, names='세그먼트', values='고객 수',
                         title='세그먼트별 고객 비율', hole=0.4)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    # ── TAB 2: 그룹별 특성 ────────────────────────
    with tab2:
        st.subheader("세그먼트별 특성 비교")
        df = run_kmeans(n_clusters)
        df['세그먼트명'] = df['세그먼트'].map(seg_labels)

        stats = df.groupby('세그먼트명').agg(
            고객수=('Churn Value','count'),
            평균이용기간=('Tenure Months','mean'),
            평균월요금=('Monthly Charges','mean'),
            평균총요금=('Total Charges','mean'),
            이탈률=('Churn Value','mean'),
        ).round(2).reset_index()
        stats['이탈률'] = (stats['이탈률']*100).round(1).astype(str) + '%'
        st.dataframe(stats, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(stats, x='세그먼트명', y='평균월요금',
                         color='세그먼트명', text='평균월요금',
                         title='세그먼트별 평균 월 요금')
            fig.update_traces(texttemplate='$%{text:.1f}', textposition='outside')
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(stats, x='세그먼트명', y='평균이용기간',
                         color='세그먼트명', text='평균이용기간',
                         title='세그먼트별 평균 이용 기간')
            fig.update_traces(texttemplate='%{text:.1f}개월', textposition='outside')
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

        # 계약유형 분포
        st.markdown("**세그먼트별 계약 유형 분포**")
        ct = df.groupby(['세그먼트명','Contract']).size().reset_index(name='수')
        fig = px.bar(ct, x='세그먼트명', y='수', color='Contract',
                     barmode='stack',
                     color_discrete_map={
                         'Month-to-month':'#EF5350',
                         'One year':'#FFA726','Two year':'#66BB6A'},
                     height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3: 이탈 위험 분석 ─────────────────────
    with tab3:
        st.subheader("세그먼트별 이탈 위험 분석")
        df = run_kmeans(n_clusters)
        df['세그먼트명'] = df['세그먼트'].map(seg_labels)

        churn_stats = df.groupby('세그먼트명').agg(
            총고객수=('Churn Value','count'),
            이탈수=('Churn Value','sum'),
        ).reset_index()
        churn_stats['이탈률(%)']  = (churn_stats['이탈수']/churn_stats['총고객수']*100).round(1)
        churn_stats['CLTV 손실'] = (churn_stats['이탈수'] * 4149).apply(lambda x: f'${x:,.0f}')

        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(churn_stats, x='세그먼트명', y='이탈률(%)',
                         color='이탈률(%)', color_continuous_scale='Reds',
                         text='이탈률(%)', title='세그먼트별 이탈률')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("**세그먼트별 비즈니스 임팩트**")
            st.dataframe(churn_stats, use_container_width=True, hide_index=True)
            high_risk = churn_stats.nlargest(1, '이탈률(%)')
            st.error(f"⚠️ 가장 위험한 세그먼트: **{high_risk.iloc[0]['세그먼트명']}** "
                     f"(이탈률 {high_risk.iloc[0]['이탈률(%)']:.1f}%)")
