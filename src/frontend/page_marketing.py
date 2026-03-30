import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'Telco_customer_churn.csv')


@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(df['Total Charges'].astype(str).str.strip(), errors='coerce').fillna(0)
    sc = ['Online Security','Online Backup','Device Protection','Tech Support','Streaming TV','Streaming Movies']
    df['TotalServices'] = (df[sc]=='Yes').sum(axis=1)
    return df


def render():
    st.title('🎯 마케팅 액션 플랜')
    st.caption('AI 예측 결과를 기반으로 타겟 고객을 선정하고 캠페인을 기획합니다.')

    try:
        df = load_raw()
    except:
        st.error('데이터 파일을 찾을 수 없습니다.')
        return

    tab1, tab2, tab3, tab4 = st.tabs(['🔴 타겟 선정','📣 캠페인 기획','⏰ 케어 플랜','📊 ROI 계산'])

    # ── TAB 1 ─────────────────────────────────────────
    with tab1:
        st.subheader('이탈 위험 고객 타겟 선정')
        c1, c2 = st.columns(2)
        with c1:
            contract_f = st.multiselect('계약 유형',['Month-to-month','One year','Two year'],default=['Month-to-month'])
            internet_f = st.multiselect('인터넷 서비스',['Fiber optic','DSL','No'],default=['Fiber optic'])
        with c2:
            tenure_r   = st.slider('이용 기간(개월)', 0, 72, (0,24))
            charge_r   = st.slider('월 요금($)', 0, 120, (60,120))

        mask = pd.Series([True]*len(df))
        if contract_f: mask &= df['Contract'].isin(contract_f)
        if internet_f: mask &= df['Internet Service'].isin(internet_f)
        mask &= df['Tenure Months'].between(*tenure_r)
        mask &= df['Monthly Charges'].between(*charge_r)
        tdf = df[mask]

        if len(tdf) == 0:
            st.warning('조건에 맞는 고객이 없습니다.')
        else:
            churned = tdf['Churn Value'].sum()
            rate    = churned/len(tdf)*100
            loss    = tdf[tdf['Churn Value']==1]['CLTV'].sum() if 'CLTV' in tdf.columns else 0

            c1,c2,c3,c4 = st.columns(4)
            c1.metric('타겟 고객',  f'{len(tdf):,}명')
            c2.metric('실제 이탈자',f'{churned:,}명')
            c3.metric('이탈률',     f'{rate:.1f}%')
            c4.metric('평균 월요금',f'${tdf["Monthly Charges"].mean():.0f}')

            if loss > 0:
                st.error(f'💸 이 고객군 방어 시 절약 가능: **${loss:,.0f}**')

            show_cols = [c for c in ['CustomerID','Contract','Internet Service','Monthly Charges','Tenure Months','Churn Label'] if c in tdf.columns]
            st.dataframe(tdf[show_cols].head(100), use_container_width=True)

            csv = tdf[show_cols].to_csv(index=False, encoding='utf-8-sig')
            st.download_button('📥 타겟 고객 다운로드', csv,
                               f'target_{datetime.now().strftime("%Y%m%d")}.csv', 'text/csv')

    # ── TAB 2 ─────────────────────────────────────────
    with tab2:
        st.subheader('EDA 기반 맞춤 캠페인')
        c1, c2, c3 = st.columns(3)

        with c1:
            n = len(df[(df['Contract']=='Month-to-month')&(df['Internet Service']=='Fiber optic')&(df['Tenure Months']<=12)])
            st.error('#### 🔴 캠페인 A — 긴급 리텐션')
            st.markdown(f"""
**대상** Month-to-month + Fiber + 12개월 이하  
**근거** 이탈률 65%+ / 6개월 골든타임  
**액션** 1년 약정 전환 시 3개월 30% 할인  
**비용** 고객당 $50~70  
**대상 고객** {n:,}명
            """)

        with c2:
            n = len(df[(df['Payment Method']=='Electronic check')&(df['Contract']=='Month-to-month')])
            st.warning('#### 🟡 캠페인 B — 자동결제 전환')
            st.markdown(f"""
**대상** Electronic check + Month-to-month  
**근거** Electronic check 이탈률 45%  
**액션** 자동결제 전환 시 월 5% 영구 할인  
**비용** 고객당 월 $3~5  
**대상 고객** {n:,}명
            """)

        with c3:
            se = ['Online Security','Online Backup','Device Protection','Tech Support']
            n  = len(df[(df['Internet Service']=='Fiber optic') & (df[se].eq('Yes').sum(axis=1)<=1)])
            st.success('#### 🟢 캠페인 C — 부가서비스 Lock-in')
            st.markdown(f"""
**대상** Fiber optic + 보안서비스 0~1개  
**근거** 서비스 6개 고객 이탈률 8%  
**액션** Online Security 3개월 무료 체험  
**비용** 고객당 $15  
**대상 고객** {n:,}명
            """)

    # ── TAB 3 ─────────────────────────────────────────
    with tab3:
        st.subheader('가입 초기 6개월 골든타임 케어 플랜')
        st.caption('생존 분석 결과: 가입 후 6개월 이내 이탈 위험이 가장 높습니다.')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=['가입 직후','1개월','3개월','6개월','12개월'],
            y=[30,45,35,20,10],
            mode='lines+markers+text',
            line=dict(color='#F44336',width=3),
            marker=dict(size=12),
            text=['30%','45%','35%','20%','10%'],
            textposition='top center'
        ))
        fig.update_layout(title='시점별 이탈 위험도 (생존 분석 기반)',
                          yaxis_title='이탈 위험도 (%)', height=350, yaxis=dict(range=[0,60]))
        st.plotly_chart(fig, use_container_width=True)

        care = pd.DataFrame({
            '시점'      : ['D+1 (가입 직후)','D+30 (1개월)','D+90 (3개월)','D+180 (6개월)','D+365 (1년)'],
            '액션'      : ['웰컴 문자 + 서비스 가이드','만족도 설문 + 무료 체험 제안','중간 점검 + $10 쿠폰','1년 약정 전환 제안','VIP 등록 + 연간 리워드'],
            '채널'      : ['문자/앱','앱 푸시/이메일','전화/문자','전화/이메일','앱/이메일'],
            '예상 비용' : ['$0','$15','$10','$50~70','$30'],
        })
        st.dataframe(care, use_container_width=True, hide_index=True)

    # ── TAB 4 ─────────────────────────────────────────
    with tab4:
        st.subheader('캠페인 ROI 시뮬레이터')

        c1, c2 = st.columns(2)
        with c1:
            defense_rate = st.slider('예상 이탈 방어율 (%)', 5, 50, 30)
            cost_per     = st.number_input('고객당 캠페인 비용 ($)', 0, 200, 50)
        with c2:
            target_n     = st.number_input('캠페인 대상 고객 수', 0, 10000, 500)
            avg_cltv     = df[df['Churn Value']==1]['CLTV'].mean() if 'CLTV' in df.columns else 4149

        defended  = int(target_n * defense_rate / 100)
        saved     = defended * avg_cltv
        cost      = target_n * cost_per
        net       = saved - cost
        roi       = net / cost * 100 if cost > 0 else 0

        st.markdown('---')
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('방어 예상 고객', f'{defended:,}명')
        c2.metric('절약 예상 수익', f'${saved:,.0f}')
        c3.metric('캠페인 총 비용', f'${cost:,.0f}')
        if net > 0:
            c4.metric('순 이익 (ROI)', f'${net:,.0f}', delta=f'ROI {roi:.0f}%')
        else:
            c4.metric('순 손실', f'${abs(net):,.0f}', delta=f'ROI {roi:.0f}%', delta_color='inverse')

        fig = go.Figure(go.Waterfall(
            orientation='v', measure=['relative','relative','total'],
            x=['절약 수익','캠페인 비용','순 이익'],
            y=[saved, -cost, net],
            text=[f'${saved:,.0f}', f'-${cost:,.0f}', f'${net:,.0f}'],
            textposition='outside',
            connector={'line':{'color':'rgb(63,63,63)'}},
            increasing={'marker':{'color':'#4CAF50'}},
            decreasing={'marker':{'color':'#F44336'}},
            totals={'marker':{'color':'#2196F3'}},
        ))
        fig.update_layout(title='캠페인 수익성 분석', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        if net > 0:
            st.success(f'✅ ROI {roi:.0f}% — ${ cost:,.0f} 투자 → ${net:,.0f} 순이익')
        else:
            st.warning('캠페인 비용이 예상 수익보다 큽니다. 조건을 조정해보세요.')
