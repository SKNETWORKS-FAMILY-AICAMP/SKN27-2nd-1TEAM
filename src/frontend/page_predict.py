import streamlit as st
import pandas as pd
import numpy as np
from ml_utils import load_ml_objects, create_engineered_features
from db_utils import get_conn, get_tables, load_table, save_prediction


def load_data_from_db(table_name):
    return load_table(table_name)


def save_to_db(customer_id, churn_prob, optimal_threshold, sf):
    save_prediction(
        customer_id     = customer_id,
        customer_name   = customer_id,
        churn_prob      = churn_prob,
        is_churn        = 1 if churn_prob >= optimal_threshold else 0,
        contract        = sf.get('Contract', ''),
        internet        = sf.get('Internet Service', ''),
        monthly_charges = float(sf.get('Monthly Charges', 0)),
        tenure_months   = int(sf.get('Tenure Months', 0)),
        payment_method  = sf.get('Payment Method', ''),
    )


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

    conn = get_conn()
    db_tables = []
    if conn:
        db_tables = get_tables()
        conn.close()

    if not db_tables:
        st.warning("데이터베이스(`churn_db`)에 분석 가능한 테이블이 없습니다. 데이터를 먼저 적재하세요.")
        return

    # ── 1. 고객 검색 ──────────────────────────────────
    with st.container():
        st.subheader("1. 시뮬레이션 대상 고객 선택")
        col_file, col_id, col_btn = st.columns([2, 2, 1])
        with col_file:
            selected_file = st.selectbox("데이터셋(DB 테이블)", db_tables)
        with col_id:
            customer_id = st.text_input("Customer ID 검색", placeholder="일부만 입력해도 됩니다 (예: 3668)")
        with col_btn:
            st.write("")
            st.write("")
            search_clicked = st.button("고객 조회", use_container_width=True)

    # 세션 초기화
    if "current_customer_df" not in st.session_state:
        st.session_state["current_customer_df"] = None
    if "searched_customer_id" not in st.session_state:
        st.session_state["searched_customer_id"] = None
    if "base_prob" not in st.session_state:
        st.session_state["base_prob"] = None
    if "search_results" not in st.session_state:
        st.session_state["search_results"] = None

    def get_prob(input_df):
        processed_df = create_engineered_features(input_df, model_columns=model_columns)
        processed_df = processed_df[model_columns]
        encoded_data = encoder.transform(processed_df).astype('float64')
        scaled_input = scaler.transform(encoded_data)
        return model.predict_proba(scaled_input)[0, 1]

    # ── 2. 검색 실행 ──────────────────────────────────
    if search_clicked:
        if not customer_id.strip():
            st.error("Customer ID를 입력해 주세요.")
            st.session_state["search_results"] = None
        else:
            try:
                df = load_data_from_db(selected_file)
                id_col = None
                for c in df.columns:
                    if c == "CustomerID" or c.lower() == "customerid":
                        id_col = c
                        break

                if id_col is None:
                    st.error("선택한 데이터셋에 'CustomerID' 컬럼이 없습니다.")
                    st.session_state["search_results"] = None
                else:
                    # LIKE 검색 (한 글자도 OK)
                    results = df[
                        df[id_col].astype(str).str.contains(
                            customer_id.strip(), case=False, na=False
                        )
                    ].copy()

                    if results.empty:
                        st.error(f"'{customer_id}' 에 해당하는 고객을 찾을 수 없습니다.")
                        st.session_state["search_results"] = None
                    else:
                        st.session_state["search_results"] = results
                        st.session_state["id_col"] = id_col
                        # 세션 초기화
                        st.session_state["current_customer_df"] = None
                        st.session_state["base_prob"] = None
                        if "simulated_features" in st.session_state:
                            del st.session_state["simulated_features"]
            except Exception as e:
                st.error(f"검색 중 오류: {e}")
                st.session_state["search_results"] = None

    # ── 3. 검색 결과 목록 표시 + 선택 ────────────────
    results = st.session_state.get("search_results")
    if results is not None and not results.empty:
        id_col = st.session_state.get("id_col")
        st.markdown("---")

        if len(results) == 1:
            # 결과가 1명이면 바로 선택
            selected_row = results.iloc[[0]]
            st.success(f"고객 **{results.iloc[0][id_col]}** 을 찾았습니다.")
            st.session_state["current_customer_df"] = selected_row
            st.session_state["searched_customer_id"] = results.iloc[0][id_col]
            prob = get_prob(selected_row)
            st.session_state["base_prob"] = prob
            st.session_state["simulated_prob"] = prob
            if "simulated_features" in st.session_state:
                del st.session_state["simulated_features"]
        else:
            # 여러 명이면 테이블에서 클릭해서 선택
            st.info(f"**{len(results)}명**의 고객이 검색되었습니다. 행을 클릭해서 선택하세요.")

            show_cols = [c for c in [id_col, 'Contract', 'Internet Service',
                                      'Monthly Charges', 'Tenure Months', 'Churn Label']
                         if c in results.columns]

            # 체크박스 숨기고 행 클릭으로만 선택
            selected = st.dataframe(
                results[show_cols].reset_index(drop=True),
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config={
                    "_index": None  # 인덱스 숨김
                }
            )

            if selected and selected.selection.rows:
                row_idx      = selected.selection.rows[0]
                selected_row = results.iloc[[row_idx]]
                selected_id  = selected_row.iloc[0][id_col]

                if st.session_state.get("searched_customer_id") != selected_id:
                    st.session_state["current_customer_df"]   = selected_row
                    st.session_state["searched_customer_id"]  = selected_id
                    st.session_state["base_prob"]             = get_prob(selected_row)
                    st.session_state["simulated_prob"]        = st.session_state["base_prob"]
                    if "simulated_features" in st.session_state:
                        del st.session_state["simulated_features"]

                st.success(f"✅ **{selected_id}** 선택됨 — 아래에서 시뮬레이션하세요.")

    # ── 4. What-If 시뮬레이터 ─────────────────────────
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

        g_opts  = ["Female", "Male"]
        p_opts  = ["No", "Yes"]
        d_opts  = ["No", "Yes"]
        c_opts  = ["Month-to-month", "One year", "Two year"]
        pl_opts = ["Yes", "No"]
        pm_opts = ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
        ph_opts = ["No", "Yes"]
        l_opts  = ["No", "Yes", "No phone service"]
        i_opts  = ["Fiber optic", "DSL", "No"]
        s_opts  = ["No", "Yes", "No internet service"]

        init_senior  = 1 if str(get_val("Senior Citizen", 0)).strip().lower() in ['yes', '1'] else 0
        raw_tenure   = get_val("Tenure Months", 12)
        init_tenure  = int(raw_tenure) if pd.notna(raw_tenure) else 12
        raw_monthly  = get_val("Monthly Charges", 70.0)
        init_monthly = float(raw_monthly) if pd.notna(raw_monthly) else 70.0

        # ── 고객 기본 정보 (읽기 전용) ────────────────
        st.markdown("**📋 고객 기본 정보 (변경 불가)**")
        gender  = str(get_val("Gender",     "Female"))
        senior  = init_senior
        partner = str(get_val("Partner",    "No"))
        dep     = str(get_val("Dependents", "No"))
        ri1, ri2, ri3, ri4 = st.columns(4)
        ri1.text_input("성별",        value=gender,      disabled=True)
        ri2.text_input("고령자 여부", value=str(senior), disabled=True)
        ri3.text_input("배우자 유무", value=partner,     disabled=True)
        ri4.text_input("부양가족",    value=dep,         disabled=True)

        st.markdown("---")

        # ── 2컬럼: 왼쪽=조절항목 / 오른쪽=결과 ───────
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.markdown("**⚙️ 시뮬레이션 조절 항목**")
            c1, c2 = st.columns(2)
            with c1:
                contract = st.selectbox("계약 형태",   c_opts,  index=safe_index(c_opts,  get_val("Contract","Month-to-month")))
                tenure   = st.number_input("가입 기간(월)", 1, 100, init_tenure)
                phone    = st.selectbox("전화 서비스", ph_opts, index=safe_index(ph_opts, get_val("Phone Service","Yes")))
                lines    = st.selectbox("다중 회선",   l_opts,  index=safe_index(l_opts,  get_val("Multiple Lines","No")))
                internet = st.selectbox("인터넷",      i_opts,  index=safe_index(i_opts,  get_val("Internet Service","Fiber optic")))
                security = st.selectbox("온라인 보안", s_opts,  index=safe_index(s_opts,  get_val("Online Security","No")))
                backup   = st.selectbox("온라인 백업", s_opts,  index=safe_index(s_opts,  get_val("Online Backup","No")))
            with c2:
                monthly   = st.number_input("월 요금($)", 0.0, 200.0, init_monthly)
                total     = round(monthly * tenure, 2)
                st.info(f"총 요금: **${total:,.2f}**")
                paperless = st.selectbox("전자청구서",  pl_opts, index=safe_index(pl_opts, get_val("Paperless Billing","Yes")))
                payment   = st.selectbox("결제 방식",   pm_opts, index=safe_index(pm_opts, get_val("Payment Method","Electronic check")))
                dev_prot  = st.selectbox("기기 보호",   s_opts,  index=safe_index(s_opts,  get_val("Device Protection","No")))
                tech      = st.selectbox("기술 지원",   s_opts,  index=safe_index(s_opts,  get_val("Tech Support","No")))
                tv        = st.selectbox("스트리밍 TV", s_opts,  index=safe_index(s_opts,  get_val("Streaming TV","No")))
                mov       = st.selectbox("스트리밍 영화",s_opts, index=safe_index(s_opts,  get_val("Streaming Movies","No")))

        with right_col:
            # 실시간 확률 계산
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
                sim_prob = get_prob(sim_input)
            except Exception as e:
                st.error(f"예측 실패: {e}")
                sim_prob = base_prob

            sf = {
                'Gender': gender, 'Senior Citizen': senior, 'Partner': partner,
                'Dependents': dep, 'Tenure Months': tenure, 'Phone Service': phone,
                'Multiple Lines': lines, 'Internet Service': internet,
                'Online Security': security, 'Online Backup': backup,
                'Device Protection': dev_prot, 'Tech Support': tech,
                'Streaming TV': tv, 'Streaming Movies': mov,
                'Contract': contract, 'Paperless Billing': paperless,
                'Payment Method': payment, 'Monthly Charges': monthly, 'Total Charges': total
            }

            delta = (sim_prob - base_prob) * 100

            st.markdown("### 📊 기대 분석 지표")
            m1, m2 = st.columns(2)
            m1.metric("현재 이탈 확률", f"{base_prob*100:.2f}%")
            delta_color = "inverse" if delta != 0 else "off"
            m2.metric("시뮬레이션 후",  f"{sim_prob*100:.2f}%",
                      delta=f"{delta:.2f}%p", delta_color=delta_color)

            st.markdown("---")
            st.markdown("### 💡 AI 맞춤형 리텐션 액션 추천")

            actions = []
            if sim_prob >= optimal_threshold:
                st.error("⚠️ 이탈 고위험군")
                if sf['Contract'] == "Month-to-month":
                    actions.append("🏷️ **단기 계약:** 약정 할인 프로모션 쿠폰 발송")
                if sf['Tenure Months'] < 12:
                    actions.append("🌱 **신규 고객:** 온보딩 케어 콜 + 웰컴 혜택 제공")
                if sf['Internet Service'] == "Fiber optic" and sf['Tech Support'] == "No":
                    actions.append("👨‍💻 **기술 지원 부재:** 기술지원 3개월 무료 체험 권유")
                elif sf['Internet Service'] != "No" and sf['Online Security'] == "No":
                    actions.append("🛡️ **보안 미가입:** 네트워크 보안 결합 특가 할인")
                if sf['Monthly Charges'] > 70.0:
                    actions.append("💰 **고요금:** 맞춤형 요금제 컨설팅 / 5% 할인 제안")
                if sf['Senior Citizen'] == 1:
                    actions.append("👴 **고령자:** 시니어 전용 상담사 연결")
            else:
                st.success("✅ 이탈 안전군")
                if delta < -5:
                    actions.append("🎉 이탈률 크게 개선! 시뮬레이션 혜택을 실제 캠페인으로 실행하세요.")

            if actions:
                for action in actions:
                    st.info(action)
            else:
                if sim_prob >= optimal_threshold:
                    st.info("🎯 VIP 관리 유지 혜택으로 Lock-in을 시도하세요.")
                else:
                    st.info("🎯 뚜렷한 위험 요소 없음. 일반 모니터링 유지")

            st.markdown("---")
            if st.button("💾 분석 결과 저장", type="primary", use_container_width=True):
                save_to_db(
                    customer_id=st.session_state['searched_customer_id'],
                    churn_prob=sim_prob,
                    optimal_threshold=optimal_threshold,
                    sf=sf
                )
                st.success("✅ DB에 저장되었습니다.")