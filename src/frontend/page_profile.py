import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from db_utils import get_conn, get_tables, load_table

DATA_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DATA_PATH = os.path.join(DATA_DIR, "Telco_customer_churn - Telco_Churn.csv")

@st.cache_data
def load_raw():
    df = pd.read_csv(DATA_PATH)
    df['Total Charges'] = pd.to_numeric(
        df['Total Charges'].replace(' ', np.nan), errors='coerce'
    ).fillna(0)
    return df

def get_customer_predictions(customer_id):
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT churn_prob, is_churn, contract, internet,
                       monthly_charges, tenure_months, payment_method, predicted_at
                FROM predictions
                WHERE customer_id = %s
                ORDER BY predicted_at DESC
            """, (customer_id,))
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()

def render():
    st.title("👤 고객 상세 프로필")
    st.caption("특정 고객의 전체 정보 + 이탈 히스토리를 확인합니다.")

    # 검색
    tables = get_tables()
    customer_tables = [t for t in tables if t != 'predictions' and t != 'alerts'
                       and t != 'campaigns' and t != 'campaign_targets']

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_table = st.selectbox("데이터셋", customer_tables if customer_tables else tables)
    with col2:
        search_id = st.text_input("Customer ID 검색", placeholder="예: 3668-QPYBK")
    with col3:
        st.write("")
        st.write("")
        search_btn = st.button("🔍 조회", use_container_width=True, type="primary")

    if not search_btn and 'profile_customer' not in st.session_state:
        st.info("고객 ID를 입력하고 조회 버튼을 클릭하세요.")
        return

    if search_btn and search_id.strip():
        df_all = load_table(selected_table)
        id_col = next((c for c in df_all.columns if c.lower() == 'customerid'), None)
        if id_col:
            result = df_all[df_all[id_col].astype(str).str.contains(search_id.strip(), case=False, na=False)]
            if not result.empty:
                st.session_state['profile_customer'] = result.iloc[0].to_dict()
                st.session_state['profile_id'] = result.iloc[0][id_col]
            else:
                st.error(f"'{search_id}' 에 해당하는 고객을 찾을 수 없습니다.")
                return

    if 'profile_customer' not in st.session_state:
        return

    customer = st.session_state['profile_customer']
    customer_id = st.session_state['profile_id']

    st.markdown("---")
    st.subheader(f"📋 {customer_id} 고객 프로필")

    # ── 기본 정보 ──────────────────────────────────
    col_info, col_hist = st.columns([1, 1])

    with col_info:
        st.markdown("**기본 정보**")

        def val(key):
            for k, v in customer.items():
                if k.lower().replace(' ','') == key.lower().replace(' ',''):
                    return v
            return '-'

        info_data = {
            '성별'          : val('Gender'),
            '고령자 여부'   : val('SeniorCitizen'),
            '배우자'        : val('Partner'),
            '부양가족'      : val('Dependents'),
            '이용 기간'     : f"{val('TenureMonths')}개월",
            '계약 형태'     : val('Contract'),
            '인터넷 서비스' : val('InternetService'),
            '결제 방식'     : val('PaymentMethod'),
            '월 요금'       : f"${val('MonthlyCharges')}",
            '총 요금'       : f"${val('TotalCharges')}",
            '이탈 여부'     : '⚠️ 이탈' if str(val('ChurnLabel')) == 'Yes' else '✅ 유지',
        }

        for k, v in info_data.items():
            col_k, col_v = st.columns([1, 1])
            col_k.markdown(f"**{k}**")
            col_v.markdown(str(v))

        st.markdown("---")
        st.markdown("**부가서비스 현황**")
        services = {
            '전화 서비스'   : val('PhoneService'),
            '온라인 보안'   : val('OnlineSecurity'),
            '온라인 백업'   : val('OnlineBackup'),
            '기기 보호'     : val('DeviceProtection'),
            '기술 지원'     : val('TechSupport'),
            '스트리밍 TV'   : val('StreamingTV'),
            '스트리밍 영화' : val('StreamingMovies'),
        }
        for k, v in services.items():
            icon = '✅' if str(v) == 'Yes' else '❌'
            st.markdown(f"{icon} {k}")

    # ── 예측 히스토리 ──────────────────────────────
    with col_hist:
        st.markdown("**📊 이탈 예측 히스토리**")
        df_pred = get_customer_predictions(customer_id)

        if df_pred.empty:
            st.info("이 고객의 예측 이력이 없습니다.")
        else:
            df_pred['churn_prob'] = df_pred['churn_prob'].astype(float)
            df_pred['predicted_at'] = pd.to_datetime(df_pred['predicted_at'])

            # 최신 이탈 확률
            latest = df_pred.iloc[0]
            prob   = latest['churn_prob']
            color  = '#F44336' if prob >= 0.5 else '#4CAF50'

            fig = go.Figure(go.Indicator(
                mode='gauge+number',
                value=round(prob*100, 1),
                title={'text': '현재 이탈 확률 (%)'},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar' : {'color': color},
                    'steps': [
                        {'range': [0, 30],   'color': '#E8F5E9'},
                        {'range': [30, 60],  'color': '#FFF9C4'},
                        {'range': [60, 100], 'color': '#FFEBEE'},
                    ],
                    'threshold': {'line': {'color': 'red', 'width': 4},
                                  'thickness': 0.75, 'value': 50}
                }
            ))
            fig.update_layout(height=220, margin=dict(t=40,b=0,l=20,r=20))
            st.plotly_chart(fig, use_container_width=True)

            # 이탈 확률 추이
            if len(df_pred) > 1:
                fig2 = px.line(df_pred.sort_values('predicted_at'),
                               x='predicted_at', y='churn_prob',
                               title='이탈 확률 추이', markers=True)
                fig2.update_layout(height=200, margin=dict(t=40,b=0),
                                   yaxis_tickformat='.0%',
                                   xaxis_title='예측 시간',
                                   yaxis_title='이탈 확률')
                fig2.add_hline(y=0.5, line_dash='dash', line_color='red',
                               annotation_text='위험 임계값')
                st.plotly_chart(fig2, use_container_width=True)

            # 예측 이력 테이블
            st.markdown("**예측 이력**")
            df_show = df_pred[['predicted_at','churn_prob','contract','monthly_charges']].copy()
            df_show['churn_prob'] = (df_show['churn_prob']*100).round(1).astype(str) + '%'
            df_show.columns = ['예측 시간','이탈 확률','계약 유형','월 요금']
            st.dataframe(df_show, use_container_width=True, hide_index=True)
