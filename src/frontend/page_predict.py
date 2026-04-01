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
        st.markdown("### 🔍 1. 시뮬레이션 대상 고객 검색")
    
        
        # 세련된 검색바 배치를 위해 컨테이너 내부 폼 정렬
        col_id, col_btn = st.columns([5, 1])
        with col_id:
<<<<<<< HEAD
            customer_id = st.text_input("Customer ID 검색", placeholder="일부만 입력해도 됩니다 (예: 3668)")
=======
            customer_id = st.text_input(
                "Customer ID 검색", 
                placeholder="🔎 검색할 고객 ID를 입력하세요. (예: 3668-QPYBK)", 
                label_visibility="collapsed"
            )
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
        with col_btn:
            search_clicked = st.button("데이터 조회", type="primary", use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)

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
<<<<<<< HEAD
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
=======
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
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a

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

<<<<<<< HEAD
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
=======
        with st.form("what_if_simulator"):
            st.markdown("#### ⚙️ 시뮬레이션 변수 세부 조정")
            st.caption("고객의 서비스 가입 세부 상태 및 약정 조건을 자유롭게 변경하여 이탈 방지 전략을 탐색하세요.")
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("##### 👤 기본 인적 사항")
                gender   = st.selectbox("성별", g_opts, index=safe_index(g_opts, get_val("Gender", "Female")))
                senior   = st.selectbox("고령자 여부 (Senior)", [0, 1], index=init_senior, format_func=lambda x: "Yes" if x == 1 else "No")
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
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
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
<<<<<<< HEAD
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
=======
                    st.info("🎯 뚜렷한 위험 요소가 없습니다. 현재 상태를 유지하며 일반적인 모니터링 체제를 가동하십시오.")
                    
    # =========================================================
    # 앱 하단: 전체 고객 지리적 분포 및 이탈 리스크 지도 시각화
    # =========================================================
    st.markdown("<hr style='margin: 60px 0 30px 0; border-color: var(--border-base);'>", unsafe_allow_html=True)
    st.subheader("🗺️ 전체 고객 지리적 분포 및 리스크 통계")
    st.markdown("데이터베이스에 존재하는 위도(Latitude)와 경도(Longitude) 정보를 바탕으로 고객들의 위치 분포와 이탈 확률을 시각화합니다. (빨강: 고위험, 노랑: 경고, 초록: 안전군)")

    target_tbl = db_tables[0] if db_tables else None
    if target_tbl:
        with st.spinner("지도 데이터를 분석 중입니다..."):
            try:
                import page_manage
                # 이미 page_manage에 만들어진 일괄 분석 함수(캐싱됨) 재사용
                map_df = load_data_from_db(target_tbl)
                risk_df = page_manage.get_batch_predictions(target_tbl)
                
                if not map_df.empty and risk_df is not None:
                    # 위/경도 컬럼 탐색 (포괄적인 이름 패턴 매칭)
                    lat_col = next((c for c in map_df.columns if c.lower() in ['lat', 'latitude', '위도', 'y']), None)
                    lon_col = next((c for c in map_df.columns if c.lower() in ['lon', 'longitude', 'lng', '경도', 'x']), None)
                    
                    if lat_col and lon_col:
                        map_df['lat'] = pd.to_numeric(map_df[lat_col], errors='coerce')
                        map_df['lon'] = pd.to_numeric(map_df[lon_col], errors='coerce')
                        
                        id_col = next((c for c in map_df.columns if c.lower() == 'customerid'), None)
                        if id_col and 'Customer ID' in risk_df.columns:
                            merged_df = map_df.merge(risk_df, left_on=id_col, right_on='Customer ID', how='inner')
                        else:
                            merged_df = map_df
                            
                        # 위경도가 없는(NaN) 데이터 드랍
                        merged_df = merged_df.dropna(subset=['lat', 'lon'])
                        
                        if not merged_df.empty:
                            # Risk Status 기반 색상 지정 (High Risk: Red, Warning: Orange, Safe: Green)
                            def get_color(status):
                                if status == 'High Risk': return '#ef4444' # Red
                                elif status == 'Warning': return '#f59e0b' # Amber/Orange
                                elif status == 'Safe': return '#10b981' # Emerald/Green
                                return '#3b82f6' # Blue Default
                                
                            if 'Risk Status' in merged_df.columns:
                                merged_df['color'] = merged_df['Risk Status'].apply(get_color)
                            else:
                                merged_df['color'] = '#3b82f6'
                                
                            # Streamlit 네이티브 map. 하이엔드 어두운 테마와 찰떡으로 렌더링됨
                            st.map(merged_df, latitude='lat', longitude='lon', color='color', use_container_width=True)
                        else:
                            st.info("지도에 표시할 수 있는 유효한 위경도 좌표 데이터가 없습니다.")
                    else:
                        st.info(f"현재 연결된 데이터셋(`{target_tbl}`) 내부에 지역 좌표(위도, 경도) 컬럼이 존재하지 않아 지도를 생성할 수 없습니다.")
            except Exception as e:
                import traceback
                st.error(f"지도 렌더링 중 오류가 발생했습니다: {e}")
                st.info(f"디버그 로그:\n{traceback.format_exc()}")
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
