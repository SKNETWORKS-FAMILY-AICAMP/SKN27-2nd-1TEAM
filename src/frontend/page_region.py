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
    st.title("🗺️ 지역 분석")
    st.caption("캘리포니아 지역별 고객 이탈 현황을 분석합니다.")

    try:
        df = load_raw()
    except:
        st.error("데이터 파일을 찾을 수 없습니다.")
        return

    if 'Latitude' not in df.columns or 'City' not in df.columns:
        st.error("지역 정보 컬럼이 없습니다.")
        return

    tab1, tab2, tab3 = st.tabs(["🗺️ 이탈 분포 지도", "🏙️ 도시별 분석", "📋 지역 고객 조회"])

    # ── TAB 1: 지도 ───────────────────────────────
    with tab1:
        st.subheader("캘리포니아 고객 이탈 분포")

        col1, col2 = st.columns(2)
        with col1:
            map_type = st.selectbox("표시 유형", ["이탈/유지 분포", "이탈 확률 히트맵"])
        with col2:
            churn_filter = st.selectbox("고객 필터", ["전체", "이탈 고객만", "유지 고객만"])

        df_map = df.copy()
        if churn_filter == "이탈 고객만":
            df_map = df_map[df_map['Churn Label'] == 'Yes']
        elif churn_filter == "유지 고객만":
            df_map = df_map[df_map['Churn Label'] == 'No']

        # KPI
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("표시 고객 수",   f"{len(df_map):,}명")
        k2.metric("이탈 고객",      f"{int(df_map['Churn Value'].sum()):,}명")
        k3.metric("이탈률",         f"{df_map['Churn Value'].mean()*100:.1f}%")
        k4.metric("평균 월 요금",   f"${df_map['Monthly Charges'].mean():.1f}")

        st.markdown("---")

        if map_type == "이탈/유지 분포":
            fig = px.scatter_mapbox(
                df_map.sample(min(3000, len(df_map))),
                lat='Latitude', lon='Longitude',
                color='Churn Label',
                color_discrete_map={'Yes': '#F44336', 'No': '#4CAF50'},
                hover_data={'Latitude': False, 'Longitude': False,
                            'City': True, 'Contract': True,
                            'Monthly Charges': True, 'Churn Label': True},
                zoom=5.5, mapbox_style='open-street-map',
                opacity=0.6, height=550,
                title='캘리포니아 고객 이탈 분포'
            )
            fig.update_layout(margin=dict(t=50,b=0,l=0,r=0),
                              legend_title='이탈 여부')
        else:
            fig = px.density_mapbox(
                df_map[df_map['Churn Label']=='Yes'],
                lat='Latitude', lon='Longitude',
                radius=10, zoom=5.5,
                mapbox_style='open-street-map',
                color_continuous_scale='Reds',
                height=550, title='이탈 고객 밀집 지역 히트맵'
            )
            fig.update_layout(margin=dict(t=50,b=0,l=0,r=0))

        st.plotly_chart(fig, use_container_width=True)

    # ── TAB 2: 도시별 분석 ────────────────────────
    with tab2:
        st.subheader("도시별 이탈 현황")

        city_stats = df.groupby('City').agg(
            총고객수=('Churn Value', 'count'),
            이탈수=('Churn Value', 'sum'),
            평균월요금=('Monthly Charges', 'mean'),
            평균이용기간=('Tenure Months', 'mean'),
        ).reset_index()
        city_stats['이탈률(%)'] = (city_stats['이탈수'] / city_stats['총고객수'] * 100).round(1)
        city_stats['평균월요금'] = city_stats['평균월요금'].round(1)
        city_stats['평균이용기간'] = city_stats['평균이용기간'].round(1)
        city_stats = city_stats[city_stats['총고객수'] >= 5]

        col_l, col_r = st.columns(2)

        with col_l:
            # 이탈률 TOP 10
            top10_churn = city_stats.nlargest(10, '이탈률(%)')
            fig = px.bar(top10_churn, x='이탈률(%)', y='City',
                         orientation='h',
                         color='이탈률(%)',
                         color_continuous_scale='Reds',
                         text='이탈률(%)',
                         title='이탈률 TOP 10 도시')
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=400, margin=dict(t=50,b=0),
                              yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            # 고객 수 TOP 10
            top10_count = city_stats.nlargest(10, '총고객수')
            fig = px.bar(top10_count, x='총고객수', y='City',
                         orientation='h',
                         color='이탈률(%)',
                         color_continuous_scale='RdYlGn_r',
                         text='총고객수',
                         title='고객 수 TOP 10 도시 (색=이탈률)')
            fig.update_traces(texttemplate='%{text:,}명', textposition='outside')
            fig.update_layout(height=400, margin=dict(t=50,b=0),
                              yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # 도시별 상세 테이블
        st.subheader("도시별 상세 통계")
        sort_col = st.selectbox("정렬 기준", ["이탈률(%)", "총고객수", "평균월요금", "평균이용기간"])
        city_show = city_stats.sort_values(sort_col, ascending=False).reset_index(drop=True)
        city_show.columns = ['도시','총 고객수','이탈 수','평균 월요금($)','평균 이용기간(월)','이탈률(%)']

        st.dataframe(city_show, use_container_width=True, hide_index=True)

        csv = city_show.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 도시별 통계 다운로드", csv,
                           f"city_stats_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

        st.markdown("---")

        # 산점도: 월요금 vs 이탈률
        fig = px.scatter(city_stats, x='평균월요금', y='이탈률(%)',
                         size='총고객수', color='이탈률(%)',
                         color_continuous_scale='Reds',
                         hover_name='City',
                         title='도시별 평균 월요금 vs 이탈률',
                         labels={'평균월요금': '평균 월요금 ($)', '이탈률(%)': '이탈률 (%)'},
                         height=400)
        fig.update_layout(margin=dict(t=50,b=0))
        st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3: 지역 고객 조회 ─────────────────────
    with tab3:
        st.subheader("지역별 고객 조회")

        col1, col2, col3 = st.columns(3)
        with col1:
            cities = sorted(df['City'].unique().tolist())
            selected_city = st.selectbox("도시 선택", ["전체"] + cities)
        with col2:
            churn_f = st.selectbox("이탈 여부", ["전체", "이탈", "유지"])
        with col3:
            contract_f = st.multiselect("계약 유형",
                                        ['Month-to-month','One year','Two year'],
                                        default=['Month-to-month'])

        df_filtered = df.copy()
        if selected_city != "전체":
            df_filtered = df_filtered[df_filtered['City'] == selected_city]
        if churn_f == "이탈":
            df_filtered = df_filtered[df_filtered['Churn Label'] == 'Yes']
        elif churn_f == "유지":
            df_filtered = df_filtered[df_filtered['Churn Label'] == 'No']
        if contract_f:
            df_filtered = df_filtered[df_filtered['Contract'].isin(contract_f)]

        k1, k2, k3 = st.columns(3)
        k1.metric("필터 결과",   f"{len(df_filtered):,}명")
        k2.metric("이탈 고객",   f"{int(df_filtered['Churn Value'].sum()):,}명")
        k3.metric("이탈률",      f"{df_filtered['Churn Value'].mean()*100:.1f}%")

        show_cols = [c for c in ['CustomerID','City','Contract','Internet Service',
                                  'Monthly Charges','Tenure Months','Churn Label'] if c in df_filtered.columns]
        st.dataframe(df_filtered[show_cols].head(200).reset_index(drop=True),
                     use_container_width=True, hide_index=True)

        csv = df_filtered[show_cols].to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 고객 리스트 다운로드", csv,
                           f"region_{selected_city}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
