import sys, os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "Telco_customer_churn - Telco_Churn.csv"))

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    sc = ['Online Security','Online Backup','Device Protection','Tech Support','Streaming TV','Streaming Movies']
    df['TotalServices'] = (df[sc] == 'Yes').sum(axis=1)
    return df

def render():
    st.title("🎯 마케팅 액션 플랜")
    st.caption("AI 예측 결과를 기반으로 타겟 고객을 선정하고 캠페인을 기획합니다.")

    try:
        df = load_raw()
    except:
        st.error("데이터 파일을 찾을 수 없습니다.")
        return

    tab1, tab2, tab3 = st.tabs(["🔴 타겟 선정", "⏰ 케어 플랜", "📊 ROI 계산"])

    # ── TAB 1: 타겟 선정 ──────────────────────────────
    with tab1:
        st.subheader("이탈 위험 고객 타겟 선정")

        c1, c2 = st.columns(2)
        with c1:
            contract_f = st.multiselect("계약 유형", ['Month-to-month','One year','Two year'], default=['Month-to-month'])
            internet_f = st.multiselect("인터넷 서비스", ['Fiber optic','DSL','No'], default=['Fiber optic'])
        with c2:
            tenure_r = st.slider("이용 기간(개월)", 0, 72, (0, 24))
            charge_r = st.slider("월 요금($)", 0, 120, (60, 120))

        mask = pd.Series([True] * len(df))
        if contract_f: mask &= df['Contract'].isin(contract_f)
        if internet_f: mask &= df['Internet Service'].isin(internet_f)
        mask &= df['Tenure Months'].between(*tenure_r)
        mask &= df['Monthly Charges'].between(*charge_r)
        tdf = df[mask]

        if len(tdf) == 0:
            st.warning("조건에 맞는 고객이 없습니다.")
        else:
            churned = tdf['Churn Value'].sum()
            rate    = churned / len(tdf) * 100
            loss    = tdf[tdf['Churn Value']==1]['CLTV'].sum() if 'CLTV' in tdf.columns else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("타겟 고객",   f"{len(tdf):,}명")
            c2.metric("실제 이탈자", f"{int(churned):,}명")
            c3.metric("이탈률",      f"{rate:.1f}%")
            c4.metric("평균 월요금", f"${tdf['Monthly Charges'].mean():.0f}")

            if loss > 0:
                st.error(f"💸 이 고객군 방어 시 절약 가능: **${loss:,.0f}**")

            show_cols = [c for c in ['CustomerID','Contract','Internet Service','Monthly Charges','Tenure Months','Churn Label'] if c in tdf.columns]
            st.dataframe(tdf[show_cols].head(100), use_container_width=True)

            csv = tdf[show_cols].to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 타겟 고객 다운로드",
                               csv, f"target_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

    # ── TAB 2: 케어 플랜 ──────────────────────────────
    with tab2:
        st.subheader("가입 초기 6개월 골든타임 케어 플랜")
        st.caption("고객 유지율 분석 결과, 가입 후 6개월 이내 이탈 위험이 가장 높습니다. 아래 차트는 시점별 이탈 위험도를 보여주며, 표는 각 시점에 마케팅팀이 실행해야 할 구체적인 액션과 채널을 정리한 것입니다.")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=['가입 직후','1개월','3개월','6개월','12개월'],
            y=[30, 45, 35, 20, 10],
            mode='lines+markers+text',
            line=dict(color='#F44336', width=3),
            marker=dict(size=12),
            text=['30%','45%','35%','20%','10%'],
            textposition='top center'
        ))
        fig.update_layout(
            title='시점별 이탈 위험도 (생존 분석 기반)',
            yaxis_title='이탈 위험도 (%)',
            height=350, yaxis=dict(range=[0, 60])
        )
        st.plotly_chart(fig, use_container_width=True)

        care = pd.DataFrame({
            '시점'      : ['D+1','D+30 (1개월)','D+90 (3개월)','D+180 (6개월)','D+365 (1년)'],
            '액션'      : ['웰컴 문자 + 서비스 가이드','만족도 설문 + 무료 체험 제안',
                           '중간 점검 + $10 쿠폰','1년 약정 전환 제안','VIP 등록 + 연간 리워드'],
            '채널'      : ['문자/앱','앱 푸시/이메일','전화/문자','전화/이메일','앱/이메일'],
            '예상 비용' : ['$0','$15','$10','$50~70','$30'],
        })
        st.dataframe(care, use_container_width=True, hide_index=True)

    # ── TAB 3: ROI 계산 ──────────────────────────────
    with tab3:
        st.subheader("캠페인 ROI 시뮬레이터")
        st.caption("캠페인 대상 고객 수, 예상 방어율, 고객당 비용을 입력하면 순이익과 ROI를 자동으로 계산합니다.")
        st.info("**계산 공식**\n- 방어 인원 = 대상 고객 수 × 방어율\n- 절약 수익 = 방어 인원 × 평균 CLTV ($4,149)\n- 총 비용 = 대상 고객 수 × 고객당 비용\n- 순이익 = 절약 수익 - 총 비용\n- ROI = 순이익 / 총 비용 × 100%")

        c1, c2 = st.columns(2)
        with c1:
            defense_rate = st.slider("예상 이탈 방어율 (%)", 5, 50, 30)
            cost_per     = st.number_input("고객당 캠페인 비용 ($)", 0, 200, 50)
        with c2:
            target_n = st.number_input("캠페인 대상 고객 수", 0, 10000, 500)
            avg_cltv = df[df['Churn Value']==1]['CLTV'].mean() if 'CLTV' in df.columns else 4149

        defended = int(target_n * defense_rate / 100)
        saved    = defended * avg_cltv
        cost     = target_n * cost_per
        net      = saved - cost
        roi      = net / cost * 100 if cost > 0 else 0

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("방어 예상 고객", f"{defended:,}명")
        c2.metric("절약 예상 수익", f"${saved:,.0f}")
        c3.metric("캠페인 총 비용", f"${cost:,.0f}")
        if net > 0:
            c4.metric("순 이익 (ROI)", f"${net:,.0f}", delta=f"ROI {roi:.0f}%")
        else:
            c4.metric("순 손실", f"${abs(net):,.0f}", delta=f"ROI {roi:.0f}%", delta_color='inverse')

        fig = go.Figure(go.Waterfall(
            orientation='v', measure=['relative','relative','total'],
            x=['절약 수익','캠페인 비용','순 이익'],
            y=[saved, -cost, net],
            text=[f'${saved:,.0f}', f'-${cost:,.0f}', f'${net:,.0f}'],
            textposition='outside',
            increasing={'marker': {'color': '#4CAF50'}},
            decreasing={'marker': {'color': '#F44336'}},
            totals={'marker': {'color': '#2196F3'}},
        ))
        fig.update_layout(title='캠페인 수익성 분석', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        if net > 0:
            st.success(f"✅ ROI {roi:.0f}% — ${cost:,.0f} 투자 → ${net:,.0f} 순이익")
        else:
            st.warning("캠페인 비용이 예상 수익보다 큽니다. 조건을 조정해보세요.")