import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from db_utils import get_conn, get_stats, load_predictions_raw

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    try:
        df = pd.read_csv(DATA_PATH)
        df['Total Charges'] = pd.to_numeric(
            df['Total Charges'].replace(' ', np.nan), errors='coerce'
        ).fillna(0)
        return df
    except Exception as e:
        st.error(f"데이터 파일 로드 실패: {e}")
        return pd.DataFrame()

def render():
    st.title("📊 전체 대시보드")
    st.caption("전체 고객 현황과 이탈 위험 고객을 한눈에 확인합니다.")

    tab1, tab2 = st.tabs(["🔴 이탈 위험 현황", "📈 전체 데이터 분석"])

    with tab1:
        stats = get_stats()
        df_pred = load_predictions_raw(limit=500)

        if not stats or stats.get('total', 0) == 0:
            st.info("아직 예측 이력이 없습니다. 실시간 예측 페이지에서 고객을 분석해보세요!")
            return

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("총 예측 고객",   f"{stats['total']:,}명")
        k2.metric("이탈 위험 감지", f"{stats['churned']:,}명",
                  delta=f"이탈률 {stats['rate']}%", delta_color='inverse')
        k3.metric("평균 이탈 확률", f"{stats['avg']}%")
        k4.metric("오늘 신규 분석", f"{stats['today']:,}건")

        st.markdown("---")

        if df_pred.empty:
            st.warning("예측 데이터가 없습니다.")
            return

        df_pred['churn_prob'] = df_pred['churn_prob'].astype(float)
        df_pred['predicted_at'] = pd.to_datetime(df_pred['predicted_at'])
        df_pred['위험등급'] = df_pred['churn_prob'].apply(
            lambda p: '🔴 High Risk' if p >= 0.7 else ('🟡 Warning' if p >= 0.4 else '🟢 Safe')
        )

        col_pie, col_bar = st.columns([1, 2])
        with col_pie:
            st.markdown("#### 위험 세그먼트 분포")
            seg = df_pred['위험등급'].value_counts().reset_index()
            seg.columns = ['등급', '수']
            fig = px.pie(seg, names='등급', values='수', hole=0.4,
                         color='등급', color_discrete_map={
                             '🔴 High Risk': '#F44336',
                             '🟡 Warning'  : '#FFC107',
                             '🟢 Safe'     : '#4CAF50'})
            fig.update_layout(height=300, margin=dict(t=20,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_bar:
            st.markdown("#### 계약 유형별 위험 분포")
            if 'contract' in df_pred.columns:
                ct = df_pred.groupby(['contract','위험등급']).size().reset_index(name='수')
                fig = px.bar(ct, x='contract', y='수', color='위험등급',
                             color_discrete_map={'🔴 High Risk':'#F44336','🟡 Warning':'#FFC107','🟢 Safe':'#4CAF50'},
                             barmode='stack', height=300)
                fig.update_layout(margin=dict(t=20,b=0))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔍 심층 위험 분석")
        ch1, ch2 = st.columns(2)

        with ch1:
            if 'payment_method' in df_pred.columns:
                pm = df_pred.groupby(['payment_method','위험등급']).size().reset_index(name='수')
                fig = px.bar(pm, x='payment_method', y='수', color='위험등급',
                             color_discrete_map={'🔴 High Risk':'#F44336','🟡 Warning':'#FFC107','🟢 Safe':'#4CAF50'},
                             barmode='stack', title='결제 방식별 위험 분포', height=300)
                fig.update_layout(margin=dict(t=40,b=0), xaxis_tickangle=-20)
                st.plotly_chart(fig, use_container_width=True)

        with ch2:
            if 'internet' in df_pred.columns:
                inet = df_pred.groupby(['internet','위험등급']).size().reset_index(name='수')
                fig = px.bar(inet, x='internet', y='수', color='위험등급',
                             color_discrete_map={'🔴 High Risk':'#F44336','🟡 Warning':'#FFC107','🟢 Safe':'#4CAF50'},
                             barmode='stack', title='인터넷 서비스별 위험 분포', height=300)
                fig.update_layout(margin=dict(t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)

        ch3, ch4 = st.columns(2)
        with ch3:
            if 'tenure_months' in df_pred.columns:
                fig = px.scatter(df_pred, x='tenure_months', y='churn_prob',
                                 color='위험등급',
                                 color_discrete_map={'🔴 High Risk':'#F44336','🟡 Warning':'#FFC107','🟢 Safe':'#4CAF50'},
                                 title='이용기간별 이탈 확률', height=300, opacity=0.7)
                fig.update_layout(margin=dict(t=40,b=0))
                fig.update_yaxes(tickformat='.0%')
                st.plotly_chart(fig, use_container_width=True)

        with ch4:
            if 'monthly_charges' in df_pred.columns:
                df_pred['요금구간'] = pd.cut(
                    df_pred['monthly_charges'].astype(float),
                    bins=[0,30,50,70,90,200],
                    labels=['$0~30','$30~50','$50~70','$70~90','$90+']
                )
                mc = df_pred.groupby(['요금구간','위험등급'], observed=True).size().reset_index(name='수')
                fig = px.bar(mc, x='요금구간', y='수', color='위험등급',
                             color_discrete_map={'🔴 High Risk':'#F44336','🟡 Warning':'#FFC107','🟢 Safe':'#4CAF50'},
                             barmode='stack', title='월 요금별 위험 분포', height=300)
                fig.update_layout(margin=dict(t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("#### ⚠️ 이탈 위험 고객 TOP 리스트")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            grade_f = st.selectbox("위험 등급 필터", ["전체","🔴 High Risk","🟡 Warning","🟢 Safe"])
        with col_f2:
            search = st.text_input("고객 ID 검색")

        df_show = df_pred.sort_values('churn_prob', ascending=False).copy()
        if grade_f != "전체":
            df_show = df_show[df_show['위험등급'] == grade_f]
        if search:
            df_show = df_show[df_show['customer_id'].astype(str).str.contains(search, na=False)]

        df_table = df_show[['customer_id','churn_prob','위험등급','contract','internet','monthly_charges','tenure_months','predicted_at']].copy()
        df_table['churn_prob'] = (df_table['churn_prob']*100).round(1).astype(str) + '%'
        df_table.columns = ['고객 ID','이탈 확률','위험 등급','계약 유형','인터넷','월 요금($)','이용기간(월)','예측 시간']
        st.dataframe(df_table.reset_index(drop=True), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 💰 비즈니스 임팩트")
        avg_cltv   = 4149
        high_risk  = len(df_pred[df_pred['위험등급']=='🔴 High Risk'])
        warning    = len(df_pred[df_pred['위험등급']=='🟡 Warning'])
        total_risk = high_risk + warning
        b1, b2, b3 = st.columns(3)
        b1.metric("이탈 위험 고객", f"{total_risk:,}명", delta=f"High Risk {high_risk}명 포함", delta_color='inverse')
        b2.metric("예상 손실 CLTV", f"${total_risk*avg_cltv:,.0f}")
        b3.metric("30% 방어 시 절약", f"${int(total_risk*0.3*avg_cltv):,.0f}", delta="리텐션 캠페인 권장")

    with tab2:
        df = load_raw()
        if df.empty:
            st.error("데이터 파일을 찾을 수 없습니다.")
            return

        total   = len(df)
        churned = int(df['Churn Value'].sum()) if 'Churn Value' in df.columns else 0
        rate    = churned / total * 100 if total > 0 else 0
        loss    = int(df[df['Churn Value']==1]['CLTV'].sum()) if 'CLTV' in df.columns else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("전체 고객",    f"{total:,}명")
        k2.metric("이탈 고객",    f"{churned:,}명")
        k3.metric("이탈률",       f"{rate:.1f}%")
        k4.metric("총 손실 CLTV", f"${loss:,.0f}")

        st.markdown("---")
        col_l, col_r = st.columns(2)
        with col_l:
            if 'Contract' in df.columns:
                ct = df.groupby('Contract')['Churn Value'].mean().reset_index()
                ct['이탈률(%)'] = (ct['Churn Value']*100).round(1)
                fig = px.bar(ct, x='Contract', y='이탈률(%)', color='Contract',
                             color_discrete_map={'Month-to-month':'#EF5350','One year':'#FFA726','Two year':'#66BB6A'},
                             text='이탈률(%)', title='계약 유형별 이탈률')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            if 'Payment Method' in df.columns:
                pay = df.groupby('Payment Method')['Churn Value'].mean().reset_index()
                pay['이탈률(%)'] = (pay['Churn Value']*100).round(1)
                pay = pay.sort_values('이탈률(%)', ascending=True)
                fig = px.bar(pay, x='이탈률(%)', y='Payment Method', orientation='h',
                             color='이탈률(%)', color_continuous_scale='Reds',
                             text='이탈률(%)', title='결제 방식별 이탈률')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

        if 'Tenure Months' in df.columns and 'Churn Label' in df.columns:
            fig = px.histogram(df, x='Tenure Months', color='Churn Label',
                               color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                               barmode='overlay', opacity=0.6, nbins=30,
                               title='이용 기간별 이탈/유지 분포')
            fig.update_layout(xaxis_title="이용 기간 (월)", yaxis_title="고객 수")
            st.plotly_chart(fig, use_container_width=True)

        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            fig = px.scatter_mapbox(
                df.sample(min(2000, len(df))),
                lat='Latitude', lon='Longitude',
                color='Churn Label',
                color_discrete_map={'Yes':'#F44336','No':'#4CAF50'},
                zoom=5.5, mapbox_style='open-street-map',
                opacity=0.5, height=450, title='캘리포니아 고객 이탈 분포'
            )
            fig.update_layout(margin=dict(t=50,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
