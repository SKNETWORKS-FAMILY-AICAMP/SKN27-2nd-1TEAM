import streamlit as st
import pandas as pd
from ml_utils import load_ml_objects, create_engineered_features, OPTIMAL_THRESHOLD

def render():
    st.title("실시간 고객 이탈 위험도 분석")
    st.markdown("신규 또는 기존 고객의 16가지 특성을 입력하여 즉각적인 이탈 확률을 시뮬레이션합니다.")
    
    model, encoder, scaler, model_columns = load_ml_objects()
    
    with st.container():
        st.subheader("고객 식별 정보")
        customer_name = st.text_input("고객명 (또는 Customer ID)", placeholder="예: 홍길동 또는 CUST-001")
        
        st.subheader("핵심 특성 입력")
        with st.form("churn_prediction_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**[인구통계 및 계약 정보]**")
                senior_citizen = st.selectbox("고령자 여부 (Senior)", [0, 1], format_func=lambda x: "예" if x == 1 else "아니오")
                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    partner = st.selectbox("배우자 (Partner)", ["No", "Yes"])
                with sub_col2:
                    dependents = st.selectbox("부양가족 (Dependents)", ["No", "Yes"])
                contract = st.selectbox("계약 형태 (Contract)", ["Month-to-month", "One year", "Two year"])
                tenure_months = st.number_input("가입 기간 (개월)", min_value=0, max_value=100, value=12)
                
            with col2:
                st.markdown("**[재무 및 결제 정보]**")
                monthly_charges = st.number_input("월 청구 요금 ($)", min_value=0.0, max_value=200.0, value=75.0)
                total_charges = st.number_input("누적 청구 요금 ($)", min_value=0.0, max_value=10000.0, value=900.0)
                payment_method = st.selectbox("결제 방식 (Payment)", ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"])
                paperless_billing = st.selectbox("전자 청구서 (Paperless)", ["Yes", "No"])
                
            with col3:
                st.markdown("**[인터넷 및 방어 서비스]**")
                internet_service = st.selectbox("인터넷 서비스", ["Fiber optic", "DSL", "No"])
                sub_col3, sub_col4 = st.columns(2)
                with sub_col3:
                    online_security = st.selectbox("온라인 보안", ["No", "Yes", "No internet service"])
                    online_backup = st.selectbox("온라인 백업", ["No", "Yes", "No internet service"])
                    streaming_tv = st.selectbox("스트리밍 TV", ["No", "Yes", "No internet service"])
                with sub_col4:
                    tech_support = st.selectbox("기술 지원", ["No", "Yes", "No internet service"])
                    device_protection = st.selectbox("기기 보호", ["No", "Yes", "No internet service"])
                    streaming_movies = st.selectbox("스트리밍 영화", ["No", "Yes", "No internet service"])
            
            st.markdown("---")
            submit_button = st.form_submit_button("이탈 위험도 산출 실행")
            
        if submit_button:
            if model is None:
                st.error("모델 파일(.pkl) 로드 실패. 03_saved_models 경로를 점검하십시오.")
                return
                
            input_data = pd.DataFrame([{
                'Senior Citizen': senior_citizen, 'Partner': partner, 'Dependents': dependents,
                'Tenure Months': tenure_months, 'Contract': contract, 'Paperless Billing': paperless_billing,
                'Payment Method': payment_method, 'Monthly Charges': monthly_charges, 'Total Charges': total_charges,
                'Internet Service': internet_service, 'Online Security': online_security, 'Online Backup': online_backup,
                'Device Protection': device_protection, 'Tech Support': tech_support, 'Streaming TV': streaming_tv,
                'Streaming Movies': streaming_movies
            }])
            
            processed_df = create_engineered_features(input_data)
            
            try:
                for col in model_columns:
                    if col not in processed_df.columns:
                        processed_df[col] = 0
                processed_df = processed_df[model_columns]
                
                cat_cols = processed_df.select_dtypes(include=['object', 'category']).columns.tolist()
                if len(cat_cols) > 0:
                    processed_df[cat_cols] = encoder.transform(processed_df[cat_cols])
                    
                num_cols = ['Tenure Months', 'Monthly Charges', 'Total Charges', 'Charge_per_Lockin', 'Monthly_to_Total_Ratio']
                num_cols = [col for col in num_cols if col in processed_df.columns]
                if len(num_cols) > 0:
                    processed_df[num_cols] = scaler.transform(processed_df[num_cols])
                    
                prob = model.predict_proba(processed_df)[0, 1]
                is_churn = prob >= OPTIMAL_THRESHOLD
                
                st.markdown("### 분석 결과 요약")
                res_col1, res_col2 = st.columns([1, 2])
                
                with res_col1:
                    if is_churn:
                        st.metric(label="이탈 확률 (Prediction)", value=f"{prob*100:.1f} %", delta=f"위험 임계값({OPTIMAL_THRESHOLD*100:.1f}%) 초과", delta_color="inverse")
                    else:
                        st.metric(label="이탈 확률 (Prediction)", value=f"{prob*100:.1f} %", delta=f"안전 수준 유지", delta_color="normal")
                        
                with res_col2:
                    if is_churn:
                        st.error("**고위험군 분류 사유 (Explainable AI 추정)**")
                        st.info("**권고 액션:** 즉시 1년 약정 전환 유도 및 프로모션 제안 요망")
                    else:
                        st.success("**안전군 분류**")
                        st.markdown("현재 고객은 이탈 위험도가 통제 가능한 수준입니다.")
            except Exception as e:
                st.error(f"연산 오류 발생: {e}")