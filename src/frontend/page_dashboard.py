import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db_utils import load_predictions, get_stats, init_db

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'Telco_customer_churn.csv')


@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(df['Total Charges'].astype(str).str.strip(), errors='coerce').fillna(0)
    return df


def render():
    st.title('📊 고객 이탈 분석 대시보드')
    st.caption('전체 현황 + 예측 이력을 한눈에 확인합니다.')

    tab1, tab2 = st.tabs(['📈 예측 이력 현황', '🔍 전체 데이터 분석'])

    # ── TAB 1: 예측 이력 ──────────────────────────────
    with tab1:
        init_db()
        stats = get_stats()

        if stats['total'] == 0:
            st.info('아직 예측 이력이 없습니다. 실시간 예측 페이지에서 고객을 분석해보세요!')
        else:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric('총 예측 수',    f"{stats['total']:,}건")
            c2.metric('이탈 위험 감지', f"{stats['churned']:,}명",
                      delta=f"이탈률 {stats['churn_rate']}%", delta_color='inverse')
            c3.metric('평균 이탈 확률', f"{stats['avg_prob']}%")
            c4.metric('오늘 예측',      f"{stats['today']:,}건")

            st.markdown('---')
            df_hist = load_predictions()

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                risk_f = st.selectbox('위험 상태', ['전체','⚠️ 위험만','✅ 안전만'])
            with col_f2:
                search = st.text_input('고객 ID 검색')

            df_show = df_hist.copy()
            if risk_f == '⚠️ 위험만':   df_show = df_show[df_show['이탈 위험']=='⚠️ 위험']
            elif risk_f == '✅ 안전만':  df_show = df_show[df_show['이탈 위험']=='✅ 안전']
            if search: df_show = df_show[df_show['고객 ID'].astype(str).str.contains(search, na=False)]

            st.dataframe(df_show.drop(columns=['id']), use_container_width=True)

            if len(df_hist) > 0:
                fig = px.histogram(df_hist, x='이탈 확률(%)', color='이탈 위험',
                                   color_discrete_map={'⚠️ 위험':'#F44336','✅ 안전':'#4CAF50'},
                                   nbins=20, title='예측 이탈 확률 분포')
                st.plotly_chart(fig, use_container_width=True)

    # ── TAB 2: 전체 데이터 분석 ───────────────────────
    with tab2:
        try:
            df = load_raw()
        except:
            st.error('데이터 파일을 찾을 수 없습니다.')
            return

        total   = len(df)
        churned = df['Churn Value'].sum()
        rate    = churned/total*100
        loss    = df[df['Churn Value']==1]['CLTV'].sum() if 'CLTV' in df.columns else 0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric('전체 고객',    f'{total:,}명')
        c2.metric('이탈 고객',    f'{churned:,}명')
        c3.metric('이탈률',       f'{rate:.1f}%')
        c4.metric('총 손실 CLTV', f'${loss:,.0f}')

        st.markdown('---')
        col_l, col_r = st.columns(2)

        with col_l:
            ct = df.groupby('Contract')['Churn Value'].mean().reset_index()
            ct['이탈률(%)'] = (ct['Churn Value']*100).round(1)
            fig = px.bar(ct, x='Contract', y='이탈률(%)', color='Contract',
                         color_discrete_map={'Month-to-month':'#EF5350','One year':'#FFA726','Two year':'#66BB6A'},
                         text='이탈률(%)', title='계약 유형별 이탈률')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            pay = df.groupby('Payment Method')['Churn Value'].mean().reset_index()
            pay['이탈률(%)'] = (pay['Churn Value']*100).round(1)
            pay = pay.sort_values('이탈률(%)', ascending=True)
            fig = px.bar(pay, x='이탈률(%)', y='Payment Method', orientation='h',
                         color='이탈률(%)', color_continuous_scale='Reds',
                         text='이탈률(%)', title='결제 방식별 이탈률')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        fig = px.histogram(df, x='Tenure Months', color='Churn Label',
                           color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                           barmode='overlay', opacity=0.6, nbins=30,
                           title='이용 기간별 이탈/유지 분포')
        st.plotly_chart(fig, use_container_width=True)

        if 'Latitude' in df.columns:
            fig = px.scatter_mapbox(
                df.sample(min(2000,len(df))),
                lat='Latitude', lon='Longitude', color='Churn Label',
                color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                zoom=5.5, mapbox_style='open-street-map',
                opacity=0.5, height=450, title='캘리포니아 고객 이탈 분포'
            )
            fig.update_layout(margin=dict(t=50,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
