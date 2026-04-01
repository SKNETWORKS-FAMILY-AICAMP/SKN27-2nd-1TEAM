import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db_utils import get_conn, get_stats, load_predictions_raw

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

def render():
    st.title("📑 리포트 자동 생성")
    st.caption("주간/월간 이탈 현황 리포트를 자동으로 생성합니다.")

    tab1, tab2 = st.tabs(["📅 기간별 리포트", "📥 리포트 다운로드"])

    # ── TAB 1: 기간별 리포트 ──────────────────────
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            report_type = st.selectbox("리포트 유형", ["주간 리포트", "월간 리포트", "전체 기간"])
        with col2:
            end_date   = st.date_input("종료일", datetime.now().date())
        with col3:
            if report_type == "주간 리포트":
                start_date = end_date - timedelta(days=7)
            elif report_type == "월간 리포트":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=365)
            st.date_input("시작일", start_date, disabled=True)

        st.markdown("---")

        # 예측 이력 기간 필터
        df_raw = load_predictions_raw(limit=1000)
        try:
            df = load_raw()
        except:
            st.error("데이터 파일을 찾을 수 없습니다.")
            return

        # ── 전체 현황 요약 ────────────────────────
        st.markdown("### 📊 전체 현황 요약")

        total   = len(df)
        churned = int(df['Churn Value'].sum())
        rate    = churned / total * 100
        loss    = int(df[df['Churn Value']==1]['CLTV'].sum()) if 'CLTV' in df.columns else 0
        avg_monthly = df[df['Churn Value']==1]['Monthly Charges'].mean()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("전체 고객",      f"{total:,}명")
        k2.metric("이탈 고객",      f"{churned:,}명")
        k3.metric("이탈률",         f"{rate:.1f}%")
        k4.metric("총 손실 CLTV",   f"${loss:,.0f}")

        st.markdown("---")

        # ── 핵심 인사이트 ─────────────────────────
        st.markdown("### 💡 핵심 인사이트")

        col_l, col_r = st.columns(2)

        with col_l:
            # 계약유형별 이탈률
            ct = df.groupby('Contract')['Churn Value'].agg(['sum','count']).reset_index()
            ct['이탈률(%)'] = (ct['sum']/ct['count']*100).round(1)
            ct.columns = ['계약 유형','이탈 수','전체 수','이탈률(%)']

            fig = px.bar(ct, x='계약 유형', y='이탈률(%)', color='계약 유형',
                         color_discrete_map={
                             'Month-to-month': '#EF5350',
                             'One year'      : '#FFA726',
                             'Two year'      : '#66BB6A'},
                         text='이탈률(%)', title='계약 유형별 이탈률')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            # 결제방식별 이탈률
            pay = df.groupby('Payment Method')['Churn Value'].mean().reset_index()
            pay['이탈률(%)'] = (pay['Churn Value']*100).round(1)
            pay = pay.sort_values('이탈률(%)', ascending=True)
            fig = px.bar(pay, x='이탈률(%)', y='Payment Method', orientation='h',
                         color='이탈률(%)', color_continuous_scale='Reds',
                         text='이탈률(%)', title='결제 방식별 이탈률')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # ── 위험 고객 현황 ────────────────────────
        st.markdown("### ⚠️ 위험 고객 현황")

        if not df_raw.empty:
            df_raw['churn_prob'] = df_raw['churn_prob'].astype(float)
            high  = len(df_raw[df_raw['churn_prob'] >= 0.7])
            warn  = len(df_raw[(df_raw['churn_prob'] >= 0.4) & (df_raw['churn_prob'] < 0.7)])
            safe  = len(df_raw[df_raw['churn_prob'] < 0.4])
            total_pred = len(df_raw)

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("총 분석 고객",   f"{total_pred:,}명")
            r2.metric("🔴 High Risk",   f"{high:,}명")
            r3.metric("🟡 Warning",     f"{warn:,}명")
            r4.metric("🟢 Safe",        f"{safe:,}명")

        # ── 비즈니스 임팩트 ───────────────────────
        st.markdown("### 💰 비즈니스 임팩트")

        avg_cltv = df[df['Churn Value']==1]['CLTV'].mean() if 'CLTV' in df.columns else 4149
        defense_30 = int(churned * 0.3 * avg_cltv)
        defense_50 = int(churned * 0.5 * avg_cltv)

        b1, b2, b3 = st.columns(3)
        b1.metric("평균 이탈 고객 CLTV", f"${avg_cltv:,.0f}")
        b2.metric("30% 방어 시 절약",    f"${defense_30:,.0f}")
        b3.metric("50% 방어 시 절약",    f"${defense_50:,.0f}")

        # ── 권고사항 ─────────────────────────────
        st.markdown("### 📋 권고사항")
        st.info("""
**1. 즉시 실행 (High Risk 고객)**
- Month-to-month + Fiber optic 고객 → 긴급 리텐션 캠페인 실행
- Electronic check 고객 → 자동결제 전환 유도

**2. 단기 (1개월 내)**
- 가입 6개월 이내 신규 고객 → 온보딩 케어 강화
- 보안 서비스 미가입 고객 → 부가서비스 체험 제공

**3. 중장기 (3개월 내)**
- 2년 약정 만료 예정 고객 → 사전 재계약 캠페인
- VIP 고객 (CLTV 상위 20%) → 전담 관리자 배정
        """)

    # ── TAB 2: 다운로드 ──────────────────────────
    with tab2:
        st.subheader("리포트 다운로드")

        try:
            df = load_raw()
        except:
            st.error("데이터 파일을 찾을 수 없습니다.")
            return

        st.markdown("**📊 전체 분석 데이터 CSV**")
        # 이탈/유지 현황 요약
        summary = df.groupby(['Contract','Internet Service'])['Churn Value'].agg(
            총고객수='count', 이탈수='sum'
        ).reset_index()
        summary['이탈률(%)'] = (summary['이탈수']/summary['총고객수']*100).round(1)

        st.dataframe(summary, use_container_width=True, hide_index=True)

        csv1 = summary.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 계약/인터넷 유형별 이탈 현황 다운로드",
            csv1, f"churn_report_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv"
        )

        st.markdown("---")
        st.markdown("**⚠️ 위험 고객 리스트 CSV**")
        df_raw = load_predictions_raw(limit=1000)
        if not df_raw.empty:
            df_raw['churn_prob'] = df_raw['churn_prob'].astype(float)
            df_high = df_raw[df_raw['churn_prob'] >= 0.5].sort_values('churn_prob', ascending=False)
            df_high['churn_prob'] = (df_high['churn_prob']*100).round(1).astype(str) + '%'
            st.dataframe(df_high, use_container_width=True, hide_index=True)
            csv2 = df_high.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 위험 고객 리스트 다운로드",
                csv2, f"high_risk_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv"
            )
