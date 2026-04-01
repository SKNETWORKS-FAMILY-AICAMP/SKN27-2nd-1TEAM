import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

def categorize_reason(reason):
    reason = str(reason).lower()
    if any(k in reason for k in ['competitor','better','more data','more speed','more','offer']):
        return '경쟁사 이탈'
    elif any(k in reason for k in ['attitude','support','service','staff','expert']):
        return '서비스 불만'
    elif any(k in reason for k in ['price','expensive','charge','fee','cost','afford']):
        return '요금 불만'
    elif any(k in reason for k in ['move','moved','relocate','area']):
        return '이사/지역'
    elif any(k in reason for k in ['network','reliability','download','upload','internet']):
        return '품질 불만'
    elif any(k in reason for k in ['product','features','device']):
        return '제품/기능'
    elif any(k in reason for k in ['deceased','dead','pass']):
        return '사망'
    else:
        return '기타'

def render():
    st.title("💬 이탈 사유 분석")
    st.caption("이탈 고객의 사유를 텍스트 분석하고 대분류로 정리합니다.")

    try:
        df = load_raw()
    except:
        st.error("데이터 파일을 찾을 수 없습니다.")
        return

    if 'Churn Reason' not in df.columns:
        st.error("Churn Reason 컬럼이 없습니다.")
        return

    # 이탈 고객만
    df_churn = df[df['Churn Value'] == 1].copy()
    df_churn = df_churn[df_churn['Churn Reason'].notna()]
    df_churn['이탈 대분류'] = df_churn['Churn Reason'].apply(categorize_reason)

    tab1, tab2 = st.tabs(["📊 대분류 분석", "🔍 상세 사유 분석"])

    k1, k2, k3 = st.columns(3)
    k1.metric("이탈 고객 수",   f"{len(df_churn):,}명")
    k2.metric("사유 기록 건수", f"{df_churn['Churn Reason'].notna().sum():,}건")
    k3.metric("고유 사유 수",   f"{df_churn['Churn Reason'].nunique():,}개")

    st.markdown("---")

    # ── TAB 1: 대분류 분석 ────────────────────────
    with tab1:
        st.subheader("이탈 사유 대분류 분석")

        cat_stats = df_churn['이탈 대분류'].value_counts().reset_index()
        cat_stats.columns = ['대분류', '건수']
        cat_stats['비율(%)'] = (cat_stats['건수'] / len(df_churn) * 100).round(1)

        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.pie(cat_stats, names='대분류', values='건수',
                         title='이탈 사유 대분류 비율', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            fig = px.bar(cat_stats, x='건수', y='대분류',
                         orientation='h', color='건수',
                         color_continuous_scale='Reds',
                         text='비율(%)', title='대분류별 이탈 건수')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=400,
                              yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(cat_stats, use_container_width=True, hide_index=True)

        # 대분류별 월 요금 비교
        st.markdown("---")
        st.markdown("**대분류별 평균 월 요금 비교**")
        cat_charge = df_churn.groupby('이탈 대분류')['Monthly Charges'].mean().reset_index()
        cat_charge.columns = ['대분류', '평균 월 요금($)']
        cat_charge['평균 월 요금($)'] = cat_charge['평균 월 요금($)'].round(1)
        fig = px.bar(cat_charge, x='대분류', y='평균 월 요금($)',
                     color='평균 월 요금($)', color_continuous_scale='Blues',
                     text='평균 월 요금($)', title='대분류별 평균 월 요금')
        fig.update_traces(texttemplate='$%{text:.1f}', textposition='outside')
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── TAB 2: 상세 사유 분석 ─────────────────────
    with tab2:
        st.subheader("상세 이탈 사유 분석")

        col1, col2 = st.columns(2)
        with col1:
            cat_filter = st.selectbox("대분류 필터",
                                      ["전체"] + df_churn['이탈 대분류'].unique().tolist())
        with col2:
            top_n = st.slider("TOP N 사유", 5, 20, 10)

        df_filtered = df_churn if cat_filter == "전체" else df_churn[df_churn['이탈 대분류']==cat_filter]

        reason_cnt = df_filtered['Churn Reason'].value_counts().head(top_n).reset_index()
        reason_cnt.columns = ['사유', '건수']

        fig = px.bar(reason_cnt, x='건수', y='사유',
                     orientation='h', color='건수',
                     color_continuous_scale='Reds',
                     text='건수', title=f'상세 이탈 사유 TOP {top_n}')
        fig.update_traces(textposition='outside')
        fig.update_layout(height=500,
                          yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

        # 계약유형별 이탈 사유
        st.markdown("**계약 유형별 주요 이탈 사유**")
        for contract in df_filtered['Contract'].unique():
            sub = df_filtered[df_filtered['Contract']==contract]
            top_reason = sub['Churn Reason'].value_counts().head(3)
            with st.expander(f"📋 {contract} ({len(sub):,}명)"):
                for reason, cnt in top_reason.items():
                    st.write(f"- **{reason}**: {cnt}건")
