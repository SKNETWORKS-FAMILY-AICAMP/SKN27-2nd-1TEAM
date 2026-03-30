import streamlit as st
import pandas as pd
import numpy as np
import os
from ml_utils import load_ml_objects, create_engineered_features

import pymysql

def get_db_connection():
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3307,
            user='root',
            password='1234',
            database='churn_db',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        return None

def get_tables(conn):
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            return [list(t.values())[0] for t in tables]
    except Exception as e:
        return []

@st.cache_data(show_spinner=False)
def load_data_from_db(table_name):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}`")
            rows = cursor.fetchall()
            df = pd.DataFrame(rows)
            return df
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def safe_index(options, value, default=0):
    if pd.isna(value): return default
    val_str = str(value).strip().lower()
    for i, opt in enumerate(options):
        if str(opt).lower() == val_str:
            return i
    return default

def render():
    st.title("실시간 고객 이탈 위험도 시뮬레이터")
    st.markdown("특정 고객의 현재 위험도를 조회하고, 서비스 피처를 조절하여 기대되는 **이탈 위험률 변화(What-If 분석)**를 시뮬레이션합니다.")

    model, encoder, scaler, model_columns, optimal_threshold = load_ml_objects()
    if model is None:
        st.error("시스템 준비 중: 모델 구성 요소를 로드하지 못했습니다.")
        return

    conn = get_db_connection()
    db_tables = []
    if conn:
        db_tables = get_tables(conn)
        conn.close()
        
    if not db_tables:
        st.warning("데이터베이스(`churn_db`)에 분석 가능한 테이블이 없습니다. 데이터를 먼저 적재하세요.")
        return
        
    with st.container():
        st.markdown("### 🔍 1. 시뮬레이션 대상 고객 검색")
    
        
        # 세련된 검색바 배치를 위해 컨테이너 내부 폼 정렬
        col_id, col_btn = st.columns([5, 1])
        with col_id:
            customer_id = st.text_input(
                "Customer ID 검색", 
                placeholder="🔎 검색할 고객 ID를 입력하세요. (예: 3668-QPYBK)", 
                label_visibility="collapsed"
            )
        with col_btn:
            search_clicked = st.button("데이터 조회", type="primary", use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)

    if "current_customer_df" not in st.session_state:
        st.session_state["current_customer_df"] = None
    if "searched_customer_id" not in st.session_state:
        st.session_state["searched_customer_id"] = None
    if "base_prob" not in st.session_state:
        st.session_state["base_prob"] = None

    def get_prob(input_df):
        processed_df = create_engineered_features(input_df, model_columns=model_columns)
        processed_df = processed_df[model_columns]
        encoded_data = encoder.transform(processed_df).astype('float64')
        scaled_input = scaler.transform(encoded_data)
        return model.predict_proba(scaled_input)[0, 1]

    if search_clicked:
        if not customer_id.strip():
            st.error("Customer ID를 입력해 주세요.")
            st.session_state["current_customer_df"] = None
        else:
            found_cust_df = None
            found_table = None
            
            with st.spinner("DB 내부의 전체 고객 데이터를 검색 중입니다..."):
                for table in db_tables:
                    try:
                        df = load_data_from_db(table)
                        id_col = None
                        for c in df.columns:
                            if c.lower() == 'customerid':
                                id_col = c
                                break
                                
                        if id_col is not None:
                            matches = df[df[id_col] == customer_id.strip()]
                            if not matches.empty:
                                found_cust_df = matches.copy()
                                found_table = table
                                break # 찾았으면 즉시 중단
                    except Exception:
                        pass # 오류 발생 테이블은 무시하고 다음 탐색

            if found_cust_df is None:
                st.error(f"DB 내 전체 테이블을 검색했으나 Customer ID '{customer_id}'를 찾을 수 없습니다.")
                st.session_state["current_customer_df"] = None
            else:
                st.session_state["current_customer_df"] = found_cust_df.iloc[[0]].copy()
                st.session_state["searched_customer_id"] = customer_id.strip()
                prob = get_prob(st.session_state["current_customer_df"])
                st.session_state["base_prob"] = prob
                st.session_state["simulated_prob"] = prob
                if "simulated_features" in st.session_state:
                    del st.session_state["simulated_features"]
                st.success(f"고객 정보를 성공적으로 불러왔습니다. (데이터 출처: `{found_table}` 테이블)")

    cust_df = st.session_state.get("current_customer_df")
    if cust_df is not None:
        st.markdown("---")
        st.subheader(f"💡 [ {st.session_state['searched_customer_id']} ] 고객 What-If 시뮬레이터")
        base_prob = st.session_state["base_prob"]
        
        def get_val(col_name, default_val):
            for c in cust_df.columns:
                if c.lower() == col_name.lower():
                    return cust_df[c].iloc[0]
            return default_val
            
        g_opts = ["Female", "Male"]
        p_opts = ["No", "Yes"]
        d_opts = ["No", "Yes"]
        c_opts = ["Month-to-month", "One year", "Two year"]
        pl_opts = ["Yes", "No"]
        pm_opts = ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
        ph_opts = ["No", "Yes"]
        l_opts = ["No", "Yes", "No phone service"]
        i_opts  = ["Fiber optic", "DSL", "No"]
        s_opts  = ["No", "Yes", "No internet service"]
        
        init_senior = 1 if str(get_val("Senior Citizen", 0)).strip().lower() in ['yes', '1'] else 0
        raw_tenure = get_val("Tenure Months", 12)
        init_tenure = int(raw_tenure) if pd.notna(raw_tenure) else 12
        raw_monthly = get_val("Monthly Charges", 70.0)
        init_monthly = float(raw_monthly) if pd.notna(raw_monthly) else 70.0
        raw_total = get_val("Total Charges", 800.0)
        try:
            init_total = float(str(raw_total).replace(' ',''))
        except:
            init_total = 0.0

        with st.form("what_if_simulator"):
            st.markdown("#### ⚙️ 시뮬레이션 변수 세부 조정")
            st.caption("고객의 서비스 가입 세부 상태 및 약정 조건을 자유롭게 변경하여 이탈 방지 전략을 탐색하세요.")
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("##### 👤 기본 인적 사항")
                gender   = st.selectbox("성별", g_opts, index=safe_index(g_opts, get_val("Gender", "Female")))
                senior   = st.selectbox("고령자 여부 (Senior)", [0, 1], index=init_senior)
                partner  = st.selectbox("배우자 유무 (Partner)", p_opts, index=safe_index(p_opts, get_val("Partner", "No")))
                dep      = st.selectbox("부양가족 유무 (Dependents)", d_opts, index=safe_index(d_opts, get_val("Dependents", "No")))
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("##### 📞 주요 통신 라인")
                phone     = st.selectbox("전화 서비스", ph_opts, index=safe_index(ph_opts, get_val("Phone Service", "Yes")))
                lines     = st.selectbox("다중 회선 (Multiple Lines)", l_opts, index=safe_index(l_opts, get_val("Multiple Lines", "No")))
                
            with col2:
                st.markdown("##### 🌐 인터넷 및 부가서비스")
                internet  = st.selectbox("인터넷 서비스 타입", i_opts, index=safe_index(i_opts, get_val("Internet Service", "Fiber optic")))
                security  = st.selectbox("🛡️ 온라인 보안", s_opts, index=safe_index(s_opts, get_val("Online Security", "No")))
                backup    = st.selectbox("💾 온라인 백업", s_opts, index=safe_index(s_opts, get_val("Online Backup", "No")))
                dev_prot  = st.selectbox("📱 기기 보호 플랜", s_opts, index=safe_index(s_opts, get_val("Device Protection", "No")))
                tech      = st.selectbox("👨‍💻 프리미엄 기술 지원", s_opts, index=safe_index(s_opts, get_val("Tech Support", "No")))
                tv        = st.selectbox("📺 스트리밍 TV", s_opts, index=safe_index(s_opts, get_val("Streaming TV", "No")))
                mov       = st.selectbox("🎬 스트리밍 영화", s_opts, index=safe_index(s_opts, get_val("Streaming Movies", "No")))
                
            with col3:
                st.markdown("##### 📄 계약 및 결제 정보")
                contract  = st.selectbox("계약 형태 (Contract)", c_opts, index=safe_index(c_opts, get_val("Contract", "Month-to-month")))
                tenure    = st.number_input("가입 기간(월 기준)", 1, 100, init_tenure, help="고객이 서비스에 가입한 전체 개월 수입니다.")
                paperless = st.selectbox("모바일/전자청구서", pl_opts, index=safe_index(pl_opts, get_val("Paperless Billing", "Yes")))
                payment   = st.selectbox("결제/납부 방식", pm_opts, index=safe_index(pm_opts, get_val("Payment Method", "Electronic check")))
                monthly   = st.number_input("월 청구 요금($)", 0.0, 200.0, init_monthly, help="현재 매월 청구되는 예상 서비스 이용 요금입니다.")
                total     = st.number_input("누적 총 요금($)", 0.0, 10000.0, init_total)

            st.markdown("<hr style='margin: 15px 0 25px 0;'>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 적용 및 시뮬레이션 결과 확인", type="primary", use_container_width=True)

        if "simulated_features" not in st.session_state:
            st.session_state["simulated_prob"] = base_prob
            st.session_state["simulated_features"] = {
                'Gender': get_val('Gender', 'Female'), 'Senior Citizen': init_senior, 'Partner': get_val('Partner', 'No'),
                'Dependents': get_val('Dependents', 'No'), 'Tenure Months': init_tenure, 'Phone Service': get_val('Phone Service', 'Yes'),
                'Multiple Lines': get_val('Multiple Lines', 'No'), 'Internet Service': get_val('Internet Service', 'Fiber optic'),
                'Online Security': get_val('Online Security', 'No'), 'Online Backup': get_val('Online Backup', 'No'),
                'Device Protection': get_val('Device Protection', 'No'), 'Tech Support': get_val('Tech Support', 'No'),
                'Streaming TV': get_val('Streaming TV', 'No'), 'Streaming Movies': get_val('Streaming Movies', 'No'),
                'Contract': get_val('Contract', 'Month-to-month'), 'Paperless Billing': get_val('Paperless Billing', 'Yes'),
                'Payment Method': get_val('Payment Method', 'Electronic check'), 'Monthly Charges': init_monthly, 'Total Charges': init_total
            }

        if submitted:
            sim_input = pd.DataFrame([{
                'Gender': gender, 'Senior Citizen': senior, 'Partner': partner,
                'Dependents': dep, 'Tenure Months': tenure, 'Phone Service': phone,
                'Multiple Lines': lines, 'Internet Service': internet,
                'Online Security': security, 'Online Backup': backup,
                'Device Protection': dev_prot, 'Tech Support': tech,
                'Streaming TV': tv, 'Streaming Movies': mov,
                'Contract': contract, 'Paperless Billing': paperless,
                'Payment Method': payment, 'Monthly Charges': monthly, 'Total Charges': total
            }])
            
            try:
                with st.spinner("시뮬레이션 분석 중..."):
                    sim_prob = get_prob(sim_input)
                    st.session_state["simulated_prob"] = sim_prob
                    st.session_state["simulated_features"] = {
                        'Gender': gender, 'Senior Citizen': senior, 'Partner': partner,
                        'Dependents': dep, 'Tenure Months': tenure, 'Phone Service': phone,
                        'Multiple Lines': lines, 'Internet Service': internet,
                        'Online Security': security, 'Online Backup': backup,
                        'Device Protection': dev_prot, 'Tech Support': tech,
                        'Streaming TV': tv, 'Streaming Movies': mov,
                        'Contract': contract, 'Paperless Billing': paperless,
                        'Payment Method': payment, 'Monthly Charges': monthly, 'Total Charges': total
                    }
                    st.success("시뮬레이션 분석 완료!")
            except Exception as e:
                import traceback
                st.error(f"예측 실패: {e}")
                st.info(f"디버그 로그:\n{traceback.format_exc()}")
                
        st.markdown("<br>", unsafe_allow_html=True)
        r_col1, r_col2 = st.columns([1, 2])
        
        sim_prob = st.session_state["simulated_prob"]
        delta = (sim_prob - base_prob) * 100
        
        with r_col1:
            st.markdown("### 📊 기대 분석 지표")
            st.metric(label="현재 고객 이탈 확률 (Base)", value=f"{base_prob * 100:.2f}%")
            
            delta_color = "normal" if delta != 0 else "off"
            if delta < 0:
                delta_color = "inverse" # 감소 시 초록색 표시 유리
            elif delta > 0:
                delta_color = "inverse"
                
            st.metric(label="시뮬레이션 반영 후 이탈 확률", 
                      value=f"{sim_prob * 100:.2f}%", 
                      delta=f"{delta:.2f}%p 확률 변화", 
                      delta_color=delta_color)
                      
        with r_col2:
            st.markdown("### 💡 AI 맞춤형 리텐션(유지) 액션 추천")
            st.markdown("현재 시뮬레이션 설정값을 바탕으로 고객 맞춤형 대응 전략을 즉시 도출합니다.")
            
            sf = st.session_state["simulated_features"]
            actions = []
            
            if sim_prob >= optimal_threshold:
                st.error("⚠️ 주의: 해당 조건 유지 시 고객은 **이탈 고위험군**에 속하게 됩니다.")
                
                if sf['Contract'] == "Month-to-month":
                    actions.append("🏷️ **단기 계약 리스크:** 매월 갱신되는 불안정한 Month-to-month 계약 상태입니다. **약정 할인(1년/2년 계약) 프로모션 쿠폰**을 발송하여 락인 효과를 노리세요.")
                
                if sf['Tenure Months'] < 12:
                    actions.append("🌱 **초기 이탈 리스크:** 가입 1년 미만의 신규/비숙련 고객입니다. 초기 사용경험 저하를 막기 위해 **온보딩 케어 안내 콜(Care Call) 배정 및 웰컴 혜택**을 선제적으로 제공하세요.")
                    
                if sf['Internet Service'] == "Fiber optic" and sf['Tech Support'] == "No":
                    actions.append("👨‍💻 **기술 마찰 리스크:** 고품질인 Fiber Optic을 사용하나 '기술 지원(Tech Support)' 부재로 문제 해결에 어려움을 겪어 이탈할 가능성이 높습니다. **기술지원 3개월 무료 체험**을 권유하세요.")
                elif sf['Internet Service'] != "No" and sf['Online Security'] == "No":
                    actions.append("🛡️ **보안 취약 리스크:** 온라인 보안(Online Security) 서비스에 미가입 상태입니다. **네트워크 보안 결합 특가 할인**을 어필하여 당사 서비스 생태계 의존도를 구축하세요.")
                    
                if sf['Monthly Charges'] > 70.0:
                    actions.append("💰 **요금 부담 우려:** 최상위 구간에 속하는 높은 월 청구 요금을 내고 있습니다. 가격 저항선 해소를 위해 **데이터 맞춤형 요금제 컨설팅이나 5% 특별 청구 할인**을 제안해 가격 민감도를 낮추세요.")
                    
                if sf['Senior Citizen'] == 1:
                    actions.append("👴 **시니어 특화 케어 추천:** 고령자 특성을 지닌 고객입니다. 복잡한 ARS 대기줄 대신 **시니어 전용 직통 상담사 연결 프로세스**로 심리적 안정감을 제공하세요.")
            else:
                st.success("✅ 해당 조건에서(또는 반영 후) 고객은 **이탈 안전군**으로 분류됩니다.")
                if delta < -5:
                    actions.append("🎉 **시뮬레이션 우수!** 이번 피처 조정을 통해 이탈률이 상당 부분 크게 개선되었습니다. 실제 해당 고객에게 시뮬레이션된 혜택/변경을 제안하는 캠페인을 실행하세요.")
                
            if actions:
                for action in actions:
                    st.info(action)
            else:
                if sim_prob >= optimal_threshold:
                    st.info("🎯 뚜렷한 리스크 변수 지표가 단일화되지 않은 고위험군입니다. 종합적인 **일반 VIP 관리 유지 혜택(포인트 적립 등)**을 통한 록인(Lock-in)을 시도하십시오.")
                else:
                    st.info("🎯 뚜렷한 위험 요소가 없습니다. 현재 상태를 유지하며 일반적인 모니터링 체제를 가동하십시오.")