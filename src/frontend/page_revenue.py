import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

def render():
    st.title("💰 수익 분석")
    st.caption("CLTV 분포 및 고객 등급별 수익을 분석하고 고가치 고객을 관리합니다.")

    try:
        df = load_raw()
    except:
        st.error("데이터 파일을 찾을 수 없습니다.")
        return

    if 'CLTV' not in df.columns:
        st.error("CLTV 컬럼이 없습니다.")
        return

    tab1, tab2, tab3 = st.tabs(["📊 CLTV 분포", "🏆 고객 등급 분석", "💎 고가치 고객 관리"])

    # ── TAB 1: CLTV 분포 ──────────────────────────
    with tab1:
        st.subheader("고객 생애 가치(CLTV) 분포")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("평균 CLTV",    f"${df['CLTV'].mean():,.0f}")
        k2.metric("최대 CLTV",    f"${df['CLTV'].max():,.0f}")
        k3.metric("총 CLTV",      f"${df['CLTV'].sum():,.0f}")
        k4.metric("이탈로 인한 손실", f"${df[df['Churn Value']==1]['CLTV'].sum():,.0f}")

        st.markdown("---")

        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.histogram(df, x='CLTV', color='Churn Label',
                               color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                               nbins=30, barmode='overlay', opacity=0.7,
                               title='CLTV 분포 (이탈/유지 비교)')
            fig.update_layout(xaxis_title='CLTV ($)', yaxis_title='고객 수', height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            fig = px.box(df, x='Churn Label', y='CLTV',
                         color='Churn Label',
                         color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                         title='이탈/유지 고객 CLTV 박스플롯')
            fig.update_layout(xaxis_title='이탈 여부', yaxis_title='CLTV ($)', height=350)
            st.plotly_chart(fig, use_container_width=True)

        # 계약유형별 CLTV
        st.markdown("**계약 유형별 평균 CLTV**")
        ct = df.groupby('Contract')['CLTV'].agg(['mean','median','sum']).round(0).reset_index()
        ct.columns = ['계약 유형','평균 CLTV','중앙값 CLTV','총 CLTV']
        fig = px.bar(ct, x='계약 유형', y='평균 CLTV', color='계약 유형',
                     color_discrete_map={
                         'Month-to-month':'#EF5350',
                         'One year':'#FFA726','Two year':'#66BB6A'},
                     text='평균 CLTV', title='계약 유형별 평균 CLTV')
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── TAB 2: 고객 등급 분석 ─────────────────────
    with tab2:
        st.subheader("고객 CLTV 등급 분석")

        # CLTV 기준 등급 분류
        q25 = df['CLTV'].quantile(0.25)
        q75 = df['CLTV'].quantile(0.75)
        q90 = df['CLTV'].quantile(0.90)

        def grade(cltv):
            if cltv >= q90: return '💎 VIP'
            elif cltv >= q75: return '🥇 Gold'
            elif cltv >= q25: return '🥈 Silver'
            else: return '🥉 Bronze'

        df['고객 등급'] = df['CLTV'].apply(grade)

        grade_stats = df.groupby('고객 등급').agg(
            고객수=('CLTV','count'),
            평균CLTV=('CLTV','mean'),
            총CLTV=('CLTV','sum'),
            이탈률=('Churn Value','mean'),
        ).round(2).reset_index()
        grade_stats['이탈률(%)'] = (grade_stats['이탈률']*100).round(1)
        grade_stats['평균CLTV']  = grade_stats['평균CLTV'].round(0)
        grade_stats['총CLTV']    = grade_stats['총CLTV'].round(0)

        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.pie(grade_stats, names='고객 등급', values='고객수',
                         title='고객 등급별 비율', hole=0.4,
                         color_discrete_sequence=['#9C27B0','#FFC107','#9E9E9E','#CD7F32'])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            fig = px.bar(grade_stats, x='고객 등급', y='이탈률(%)',
                         color='이탈률(%)', color_continuous_scale='Reds',
                         text='이탈률(%)', title='고객 등급별 이탈률')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(grade_stats, use_container_width=True, hide_index=True)

        # 등급별 총 CLTV 기여도
        st.markdown("**등급별 총 CLTV 기여도**")
        fig = px.bar(grade_stats, x='고객 등급', y='총CLTV',
                     color='고객 등급', text='총CLTV',
                     title='등급별 총 CLTV 기여액')
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3: 고가치 고객 관리 ───────────────────
    with tab3:
        st.subheader("💎 고가치 고객 관리")
        st.caption("VIP/Gold 등급 고객을 집중 관리합니다.")

        df['고객 등급'] = df['CLTV'].apply(grade)

        col1, col2, col3 = st.columns(3)
        with col1:
            grade_f = st.multiselect("등급 선택",
                                     ['💎 VIP','🥇 Gold','🥈 Silver','🥉 Bronze'],
                                     default=['💎 VIP','🥇 Gold'])
        with col2:
            churn_f = st.selectbox("이탈 여부", ["전체","이탈 위험만","유지 고객만"])
        with col3:
            contract_f = st.multiselect("계약 유형",
                                        ['Month-to-month','One year','Two year'],
                                        default=['Month-to-month'])

        df_vip = df[df['고객 등급'].isin(grade_f)]
        if churn_f == "이탈 위험만":
            df_vip = df_vip[df_vip['Churn Label']=='Yes']
        elif churn_f == "유지 고객만":
            df_vip = df_vip[df_vip['Churn Label']=='No']
        if contract_f:
            df_vip = df_vip[df_vip['Contract'].isin(contract_f)]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("필터 고객",     f"{len(df_vip):,}명")
        k2.metric("이탈 위험",     f"{int(df_vip['Churn Value'].sum()):,}명")
        k3.metric("평균 CLTV",     f"${df_vip['CLTV'].mean():,.0f}")
        k4.metric("총 손실 위험",  f"${df_vip[df_vip['Churn Value']==1]['CLTV'].sum():,.0f}")

        # 산점도
        fig = px.scatter(df_vip, x='Tenure Months', y='CLTV',
                         color='Churn Label', size='Monthly Charges',
                         color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                         hover_data={'CustomerID':True} if 'CustomerID' in df_vip.columns else {},
                         title='고가치 고객 이용기간 vs CLTV',
                         opacity=0.7, height=400)
        fig.update_layout(xaxis_title='이용 기간 (월)', yaxis_title='CLTV ($)')
        st.plotly_chart(fig, use_container_width=True)

        # 고객 리스트
        show_cols = [c for c in ['CustomerID','고객 등급','CLTV','Contract',
                                  'Monthly Charges','Tenure Months','Churn Label']
                     if c in df_vip.columns]
        st.dataframe(
            df_vip[show_cols].sort_values('CLTV', ascending=False).head(100).reset_index(drop=True),
            use_container_width=True, hide_index=True
        )

        csv = df_vip[show_cols].to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 고가치 고객 리스트 다운로드", csv,
                           f"vip_customers_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

        # 권고사항
        st.markdown("---")
        st.markdown("**📋 고가치 고객 관리 전략**")
        vip_churn = df_vip[df_vip['Churn Value']==1]
        if len(vip_churn) > 0:
            st.error(f"⚠️ 고가치 고객 중 **{len(vip_churn):,}명**이 이탈 위험! 즉각 대응 필요")
        st.info("""
**💎 VIP 고객**
→ 전담 관리자 배정 + 프리미엄 서비스 제공
→ 계약 만료 3개월 전 재계약 상담

**🥇 Gold 고객**
→ 정기 만족도 조사 + 업셀링 제안
→ Month-to-month → 장기 약정 전환 유도

**공통**
→ 이탈 감지 시 즉시 알림 센터에서 팀장 보고
        """)
