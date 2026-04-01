import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import re
import streamlit as st
import pandas as pd
from db_utils import get_tables, load_table, insert_customer, update_customer


def render():
    st.title("📝 고객 등록 / 수정")
    st.caption("새 고객을 직접 입력하거나 기존 고객 정보를 수정합니다.")

    tables  = get_tables()
    c_tables = [t for t in tables if t not in ['predictions','alerts','campaigns','campaign_targets']]

    tab1, tab2 = st.tabs(["➕ 신규 고객 등록", "✏️ 기존 고객 수정"])

    # ── TAB 1: 신규 등록 ──────────────────────────
    with tab1:
        st.subheader("신규 고객 정보 입력")
        selected_table = st.selectbox("저장할 테이블", c_tables, key='reg_table')

        with st.form("register_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**기본 정보**")
                cust_id   = st.text_input("Customer ID *", placeholder="0000-XXXXX")
                gender    = st.selectbox("성별", ["Male", "Female"])
                senior    = st.selectbox("고령자 여부", ["No", "Yes"])
                partner   = st.selectbox("배우자 유무", ["No", "Yes"])
                dep       = st.selectbox("부양가족 유무", ["No", "Yes"])
                tenure    = st.number_input("이용 기간(월)", 0, 100, 12)
            with col2:
                st.markdown("**계약 / 결제**")
                contract  = st.selectbox("계약 형태", ["Month-to-month", "One year", "Two year"])
                payment   = st.selectbox("결제 방식", ["Electronic check","Mailed check",
                                                        "Bank transfer (automatic)","Credit card (automatic)"])
                paperless = st.selectbox("전자청구서", ["Yes", "No"])
                monthly   = st.number_input("월 요금($)", 0.0, 200.0, 70.0)
                total     = st.number_input("총 요금($)", 0.0, 10000.0, 0.0)
                phone     = st.selectbox("전화 서비스", ["Yes", "No"])
                lines     = st.selectbox("다중 회선", ["No", "Yes", "No phone service"])
            with col3:
                st.markdown("**인터넷 / 부가서비스**")
                internet  = st.selectbox("인터넷 서비스", ["Fiber optic", "DSL", "No"])
                security  = st.selectbox("온라인 보안", ["No", "Yes", "No internet service"])
                backup    = st.selectbox("온라인 백업", ["No", "Yes", "No internet service"])
                dev_prot  = st.selectbox("기기 보호", ["No", "Yes", "No internet service"])
                tech      = st.selectbox("기술 지원", ["No", "Yes", "No internet service"])
                tv        = st.selectbox("스트리밍 TV", ["No", "Yes", "No internet service"])
                mov       = st.selectbox("스트리밍 영화", ["No", "Yes", "No internet service"])

            submitted = st.form_submit_button("✅ 고객 등록", type="primary", use_container_width=True)

        if submitted:
            if not cust_id.strip():
                st.error("Customer ID를 입력하세요.")
            elif not re.match(r'^\d{4}-[A-Za-z]{5}$', cust_id.strip()):
                st.error("Customer ID 형식이 올바르지 않습니다. (예: 4190-MFLUW)")
            else:
                data = {
                    'CustomerID': cust_id, 'Gender': gender,
                    'Senior Citizen': senior, 'Partner': partner,
                    'Dependents': dep, 'Tenure Months': tenure,
                    'Phone Service': phone, 'Multiple Lines': lines,
                    'Internet Service': internet, 'Online Security': security,
                    'Online Backup': backup, 'Device Protection': dev_prot,
                    'Tech Support': tech, 'Streaming TV': tv,
                    'Streaming Movies': mov, 'Contract': contract,
                    'Paperless Billing': paperless, 'Payment Method': payment,
                    'Monthly Charges': monthly, 'Total Charges': total,
                }
                if insert_customer(data, selected_table):
                    st.success(f"✅ {cust_id} 고객이 등록되었습니다!")

    # ── TAB 2: 기존 고객 수정 ─────────────────────
    with tab2:
        st.subheader("기존 고객 정보 수정")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: sel_table  = st.selectbox("테이블 선택", c_tables, key='edit_table')
        with col2: search_id  = st.text_input("Customer ID 검색", placeholder="3668-QPYBK")
        with col3:
            st.write("")
            st.write("")
            search_btn = st.button("🔍 조회", use_container_width=True)

        if search_btn and search_id.strip():
            df = load_table(sel_table)
            id_col = next((c for c in df.columns if c.lower() == 'customerid'), None)
            if id_col:
                result = df[df[id_col].astype(str).str.contains(search_id.strip(), case=False, na=False)]
                if not result.empty:
                    st.session_state['edit_customer'] = result.iloc[0].to_dict()
                    st.session_state['edit_id_col']   = id_col
                    st.success(f"✅ {result.iloc[0][id_col]} 고객 정보를 불러왔습니다.")
                else:
                    st.error("고객을 찾을 수 없습니다.")

        if 'edit_customer' in st.session_state:
            c = st.session_state['edit_customer']
            def v(key, default=''):
                for k in c:
                    if k.lower().replace(' ','') == key.lower().replace(' ',''):
                        return c[k]
                return default

            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    contract = st.selectbox("계약 형태",
                        ["Month-to-month","One year","Two year"],
                        index=["Month-to-month","One year","Two year"].index(
                            v('Contract','Month-to-month')))
                    payment  = st.selectbox("결제 방식",
                        ["Electronic check","Mailed check","Bank transfer (automatic)","Credit card (automatic)"],
                        index=["Electronic check","Mailed check","Bank transfer (automatic)","Credit card (automatic)"].index(
                            v('PaymentMethod','Electronic check')))
                    monthly  = st.number_input("월 요금($)", 0.0, 200.0, float(v('MonthlyCharges', 70)))
                with col2:
                    internet = st.selectbox("인터넷 서비스",
                        ["Fiber optic","DSL","No"],
                        index=["Fiber optic","DSL","No"].index(v('InternetService','Fiber optic')))
                    tenure   = st.number_input("이용 기간(월)", 0, 100, int(v('TenureMonths', 12)))
                    total    = st.number_input("총 요금($)", 0.0, 10000.0, float(v('TotalCharges', 0)))

                update_btn = st.form_submit_button("💾 수정 저장", type="primary", use_container_width=True)

            if update_btn:
                update_data = {
                    'Contract': contract, 'Payment Method': payment,
                    'Monthly Charges': monthly, 'Internet Service': internet,
                    'Tenure Months': tenure, 'Total Charges': total
                }
                id_col    = st.session_state['edit_id_col']
                cust_id   = st.session_state['edit_customer'][id_col]
                tbl       = st.session_state['edit_table']
                if update_customer(cust_id, update_data, tbl, id_col):
                    st.success(f"✅ {cust_id} 고객 정보가 수정되었습니다!")