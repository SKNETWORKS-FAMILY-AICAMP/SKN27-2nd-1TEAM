import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

def kaplan_meier(df, group_col=None, group_val=None):
    """간단한 Kaplan-Meier 생존율 계산"""
    if group_col and group_val:
        data = df[df[group_col] == group_val].copy()
    else:
        data = df.copy()

    max_t    = int(data['Tenure Months'].max())
    survival = []
    at_risk  = len(data)
    surv_val = 1.0

    for t in range(0, max_t + 1):
        events   = len(data[(data['Tenure Months'] == t) & (data['Churn Value'] == 1)])
        censored = len(data[(data['Tenure Months'] == t) & (data['Churn Value'] == 0)])
        if at_risk > 0:
            surv_val *= (1 - events / at_risk)
        survival.append({'time': t, 'survival': surv_val, 'at_risk': at_risk})
        at_risk -= (events + censored)
        if at_risk <= 0:
            break

    return pd.DataFrame(survival)

def render():
    st.title("📈 생존 분석")
    st.caption("Kaplan-Meier 생존 분석으로 고객 이탈 패턴을 분석합니다.")

    try:
        df = load_raw()
    except:
        st.error("데이터 파일을 찾을 수 없습니다.")
        return

    tab1, tab2, tab3 = st.tabs(["📊 전체 생존 곡선", "🔍 그룹별 비교", "💡 인사이트"])

    # ── TAB 1: 전체 생존 곡선 ─────────────────────
    with tab1:
        st.subheader("전체 고객 생존 곡선")
        st.caption("가입 기간에 따른 고객 잔존율을 보여줍니다.")

        k1, k2, k3 = st.columns(3)
        k1.metric("전체 고객",    f"{len(df):,}명")
        k2.metric("이탈 고객",    f"{int(df['Churn Value'].sum()):,}명")
        k3.metric("6개월 생존율", f"{df[df['Tenure Months']>=6]['Churn Value'].apply(lambda x: 1-x).mean()*100:.1f}%")

        surv = kaplan_meier(df)
        fig  = go.Figure()
        fig.add_trace(go.Scatter(
            x=surv['time'], y=surv['survival'],
            mode='lines', name='생존율',
            line=dict(color='#2196F3', width=2),
            fill='tozeroy', fillcolor='rgba(33,150,243,0.1)'
        ))
        fig.add_vline(x=6,  line_dash='dash', line_color='#F44336',
                      annotation_text='6개월 골든타임', annotation_position='top right')
        fig.add_vline(x=12, line_dash='dash', line_color='#FF9800',
                      annotation_text='12개월')
        fig.update_layout(
            title='전체 고객 Kaplan-Meier 생존 곡선',
            xaxis_title='이용 기간 (월)',
            yaxis_title='생존율 (잔존 확률)',
            yaxis=dict(tickformat='.0%', range=[0,1]),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info("""
        💡 **핵심 인사이트**
        - 가입 후 **6개월 이내**가 이탈 위험이 가장 높은 골든타임
        - 12개월 이상 유지 고객은 생존율이 안정적으로 유지됨
        - 초기 온보딩 케어가 장기 고객 유지의 핵심
        """)

    # ── TAB 2: 그룹별 비교 ────────────────────────
    with tab2:
        st.subheader("그룹별 생존 곡선 비교")

        group_col = st.selectbox("비교 기준", [
            "Contract", "Internet Service", "Payment Method",
            "Senior Citizen", "Partner"
        ])

        groups = df[group_col].unique().tolist()
        colors = ['#2196F3','#F44336','#4CAF50','#FF9800','#9C27B0']

        fig = go.Figure()
        for i, grp in enumerate(groups):
            surv = kaplan_meier(df, group_col, grp)
            n    = len(df[df[group_col]==grp])
            fig.add_trace(go.Scatter(
                x=surv['time'], y=surv['survival'],
                mode='lines', name=f"{grp} (n={n:,})",
                line=dict(color=colors[i % len(colors)], width=2)
            ))

        fig.add_vline(x=6, line_dash='dash', line_color='gray',
                      annotation_text='6개월')
        fig.update_layout(
            title=f'{group_col}별 생존 곡선 비교',
            xaxis_title='이용 기간 (월)',
            yaxis_title='생존율',
            yaxis=dict(tickformat='.0%', range=[0,1]),
            height=450, legend_title=group_col
        )
        st.plotly_chart(fig, use_container_width=True)

        # 6개월 시점 생존율 비교
        st.markdown("**6개월 시점 생존율 비교**")
        surv_6m = []
        for grp in groups:
            grp_df = df[df[group_col]==grp]
            s6     = grp_df[grp_df['Tenure Months']>=6]['Churn Value'].apply(lambda x:1-x).mean()
            surv_6m.append({'그룹': grp, '6개월 생존율(%)': round(s6*100,1),
                            '고객 수': len(grp_df)})
        st.dataframe(pd.DataFrame(surv_6m), use_container_width=True, hide_index=True)

    # ── TAB 3: 인사이트 ───────────────────────────
    with tab3:
        st.subheader("생존 분석 주요 인사이트")

        col1, col2 = st.columns(2)

        with col1:
            # 계약유형별 중앙 생존기간
            st.markdown("**계약 유형별 평균 이용 기간**")
            ct = df.groupby('Contract')['Tenure Months'].agg(['mean','median']).round(1).reset_index()
            ct.columns = ['계약 유형','평균(월)','중앙값(월)']
            fig = px.bar(ct, x='계약 유형', y='평균(월)', color='계약 유형',
                         color_discrete_map={
                             'Month-to-month':'#EF5350',
                             'One year':'#FFA726','Two year':'#66BB6A'},
                         text='평균(월)', title='계약 유형별 평균 이용 기간')
            fig.update_traces(texttemplate='%{text}개월', textposition='outside')
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 이탈 시점 분포
            st.markdown("**이탈 발생 시점 분포**")
            churned = df[df['Churn Value']==1]
            fig = px.histogram(churned, x='Tenure Months', nbins=30,
                               color_discrete_sequence=['#F44336'],
                               title='이탈 고객 이탈 시점 분포')
            fig.add_vline(x=6,  line_dash='dash', line_color='black',
                          annotation_text='6개월')
            fig.add_vline(x=churned['Tenure Months'].median(),
                          line_dash='dot', line_color='blue',
                          annotation_text=f'중앙값({churned["Tenure Months"].median():.0f}개월)')
            fig.update_layout(height=300, xaxis_title='이탈 시점(월)', yaxis_title='고객 수')
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("**📋 생존 분석 기반 권고사항**")
        st.info("""
**D+1 ~ D+30 (가입 초기)**
→ 웰컴 콜 + 서비스 가이드 제공

**D+30 ~ D+90 (위험 구간)**
→ 만족도 설문 + 무료 체험 제안

**D+90 ~ D+180 (골든타임)**
→ 1년 약정 전환 집중 유도

**D+180 이후 (안정 구간)**
→ VIP 혜택 + 장기 고객 리워드
        """)
