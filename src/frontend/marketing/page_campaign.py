import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from db_utils import create_campaign, load_campaigns, update_campaign_status

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

def get_campaigns():
    return load_campaigns()


@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

def render():
    st.title("📣 캠페인 관리")
    st.caption("이탈 방어 캠페인을 생성하고 대상 고객을 관리합니다.")

    tab1, tab2, tab3 = st.tabs(["➕ 캠페인 생성", "📋 캠페인 현황", "📊 A/B 테스트 비교"])

    # ── TAB 1: 캠페인 생성 ────────────────────────
    with tab1:
        st.subheader("새 캠페인 만들기")

        try:
            df = load_raw()
        except:
            st.error("데이터 파일을 찾을 수 없습니다.")
            return

        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("캠페인 이름", placeholder="예: 3월 긴급 리텐션")
            c_type = st.selectbox("캠페인 유형", [
                "긴급 리텐션 (Month-to-month + Fiber)",
                "자동결제 전환 (Electronic check)",
                "부가서비스 Lock-in (Fiber + 보안서비스 0개)",
                "신규 고객 온보딩 (가입 6개월 이내)",
                "커스텀"
            ])
            discount = st.slider("할인율 (%)", 0, 50, 10)

        with col2:
            cost_per = st.number_input("고객당 캠페인 비용 ($)", 0, 200, 50)

            # 유형별 자동 타겟 계산
            if "긴급 리텐션" in c_type:
                targets = df[(df['Contract']=='Month-to-month') &
                             (df['Internet Service']=='Fiber optic')]
            elif "자동결제" in c_type:
                targets = df[df['Payment Method']=='Electronic check']
            elif "Lock-in" in c_type:
                se = ['Online Security','Online Backup','Device Protection','Tech Support']
                targets = df[(df['Internet Service']=='Fiber optic') &
                             (df[se].eq('Yes').sum(axis=1) <= 1)]
            elif "신규" in c_type:
                targets = df[df['Tenure Months'] <= 6]
            else:
                targets = df

            target_n = len(targets)
            churned  = int(targets['Churn Value'].sum()) if 'Churn Value' in targets.columns else 0
            loss     = int(targets[targets['Churn Value']==1]['CLTV'].sum()) if 'CLTV' in targets.columns else 0

            st.metric("예상 타겟 고객", f"{target_n:,}명")
            st.metric("실제 이탈자",    f"{churned:,}명")
            st.metric("방어 가능 손실", f"${loss:,.0f}")

        # ROI 미리보기
        st.markdown("---")
        st.markdown("**📊 ROI 미리보기**")
        avg_cltv = 4149
        defended = int(target_n * 0.3)
        saved    = defended * avg_cltv
        cost     = target_n * cost_per
        net      = saved - cost
        roi      = net / cost * 100 if cost > 0 else 0

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("30% 방어 시",    f"{defended:,}명")
        rc2.metric("절약 예상",      f"${saved:,.0f}")
        rc3.metric("총 비용",        f"${cost:,.0f}")
        rc4.metric("ROI",            f"{roi:.0f}%")

        st.markdown("---")
        if st.button("✅ 캠페인 생성", type="primary", use_container_width=True):
            if not c_name.strip():
                st.error("캠페인 이름을 입력하세요.")
            else:
                ok = create_campaign(c_name, c_type, target_n, discount, cost_per)
                if ok:
                    st.success(f"✅ '{c_name}' 캠페인이 생성되었습니다!")
                    st.balloons()
                else:
                    st.error("캠페인 생성 실패")

    # ── TAB 2: 캠페인 현황 ────────────────────────
    with tab2:
        st.subheader("진행 중인 캠페인")
        df_c = get_campaigns()

        if df_c.empty:
            st.info("생성된 캠페인이 없습니다. '캠페인 생성' 탭에서 만들어보세요!")
            return

        # 상태별 KPI
        total_c  = len(df_c)
        active   = len(df_c[df_c['status']=='진행중']) if 'status' in df_c.columns else 0
        done     = len(df_c[df_c['status']=='완료'])   if 'status' in df_c.columns else 0

        ck1, ck2, ck3 = st.columns(3)
        ck1.metric("전체 캠페인",  f"{total_c:,}개")
        ck2.metric("진행 중",      f"{active:,}개")
        ck3.metric("완료",         f"{done:,}개")

        st.markdown("---")

        for _, row in df_c.iterrows():
            with st.expander(f"📣 {row.get('campaign_name','캠페인')} — {row.get('status','진행중')}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**유형**: {row.get('campaign_type','-')}")
                    st.write(f"**타겟**: {row.get('target_count',0):,}명")
                    st.write(f"**할인율**: {row.get('discount_rate',0)}%")
                    st.write(f"**고객당 비용**: ${row.get('cost_per',0)}")
                    st.write(f"**생성일**: {row.get('created_at','-')}")

                with col_b:
                    total_cost = row.get('target_count',0) * row.get('cost_per',0)
                    st.metric("총 캠페인 비용", f"${total_cost:,.0f}")

                    new_status = st.selectbox("상태 변경",
                                              ["진행중","완료","중단"],
                                              index=["진행중","완료","중단"].index(row.get('status','진행중')),
                                              key=f"status_{row['id']}")
                    if st.button("상태 저장", key=f"save_{row['id']}"):
                        update_campaign_status(row['id'], new_status)
                        st.success("저장 완료!")
                        st.rerun()

    # ── TAB 3: A/B 테스트 비교 ────────────────────
    with tab3:
        st.subheader("캠페인 A/B 테스트 비교")
        st.caption("두 캠페인의 예상 효과를 비교합니다.")

        try:
            df = load_raw()
        except:
            st.error("데이터 파일을 찾을 수 없습니다.")
            return

        avg_cltv = df[df['Churn Value']==1]['CLTV'].mean() if 'CLTV' in df.columns else 4149

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### 🅰️ 캠페인 A")
            a_name     = st.text_input("캠페인 A 이름", "긴급 리텐션", key='a_name')
            a_target   = st.number_input("대상 고객 수", 0, 10000, 500, key='a_target')
            a_defense  = st.slider("예상 방어율(%)", 0, 50, 30, key='a_defense')
            a_cost     = st.number_input("고객당 비용($)", 0, 200, 70, key='a_cost')

            a_defended = int(a_target * a_defense / 100)
            a_saved    = a_defended * avg_cltv
            a_total    = a_target * a_cost
            a_net      = a_saved - a_total
            a_roi      = a_net / a_total * 100 if a_total > 0 else 0

            st.metric("방어 예상",  f"{a_defended:,}명")
            st.metric("절약 예상",  f"${a_saved:,.0f}")
            st.metric("총 비용",    f"${a_total:,.0f}")
            st.metric("순이익",     f"${a_net:,.0f}")
            st.metric("ROI",        f"{a_roi:.0f}%")

        with col_b:
            st.markdown("#### 🅱️ 캠페인 B")
            b_name     = st.text_input("캠페인 B 이름", "자동결제 전환", key='b_name')
            b_target   = st.number_input("대상 고객 수", 0, 10000, 800, key='b_target')
            b_defense  = st.slider("예상 방어율(%)", 0, 50, 20, key='b_defense')
            b_cost     = st.number_input("고객당 비용($)", 0, 200, 30, key='b_cost')

            b_defended = int(b_target * b_defense / 100)
            b_saved    = b_defended * avg_cltv
            b_total    = b_target * b_cost
            b_net      = b_saved - b_total
            b_roi      = b_net / b_total * 100 if b_total > 0 else 0

            st.metric("방어 예상",  f"{b_defended:,}명")
            st.metric("절약 예상",  f"${b_saved:,.0f}")
            st.metric("총 비용",    f"${b_total:,.0f}")
            st.metric("순이익",     f"${b_net:,.0f}")
            st.metric("ROI",        f"{b_roi:.0f}%")

        # 비교 차트
        st.markdown("---")
        compare = pd.DataFrame({
            '캠페인'  : [a_name, b_name],
            '절약 예상': [a_saved, b_saved],
            '총 비용'  : [a_total, b_total],
            '순이익'   : [a_net, b_net],
            'ROI(%)'  : [a_roi, b_roi],
        })

        fig = go.Figure()
        fig.add_trace(go.Bar(name='절약 예상', x=compare['캠페인'], y=compare['절약 예상'],
                             marker_color='#4CAF50'))
        fig.add_trace(go.Bar(name='총 비용',   x=compare['캠페인'], y=compare['총 비용'],
                             marker_color='#F44336'))
        fig.add_trace(go.Bar(name='순이익',    x=compare['캠페인'], y=compare['순이익'],
                             marker_color='#2196F3'))
        fig.update_layout(title='캠페인 A vs B 수익성 비교', barmode='group',
                          yaxis_title='금액 ($)', height=400)
        st.plotly_chart(fig, use_container_width=True)

        winner = a_name if a_roi > b_roi else b_name
        st.success(f"🏆 **{winner}** 캠페인이 ROI 기준으로 더 효과적입니다!")