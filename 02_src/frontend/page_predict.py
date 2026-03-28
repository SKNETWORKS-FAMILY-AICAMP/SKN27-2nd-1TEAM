import streamlit as st
import pandas as pd
import numpy as np
from ml_utils import load_ml_objects, create_engineered_features, OPTIMAL_THRESHOLD

def render():
    st.title("실시간 고객 이탈 위험도 분석")
    model, encoder, scaler, model_columns = load_ml_objects()

    if model is None:
        st.error("❌ 시스템 준비 중: 모델 구성 요소를 로드하지 못했습니다.")
        return

    with st.form("churn_prediction_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            gender = st.selectbox("성별", ["Female", "Male"])
            senior = st.selectbox("고령자 여부", [0, 1])
            partner = st.selectbox("배우자 유무", ["No", "Yes"])
            dep = st.selectbox("부양가족 유무", ["No", "Yes"])
            contract = st.selectbox("계약 형태", ["Month-to-month", "One year", "Two year"])
            tenure = st.number_input("가입 기간(월)", 1, 100, 12)
        with col2:
            monthly = st.number_input("월 요금($)", 0.0, 200.0, 70.0)
            total = st.number_input("총 요금($)", 0.0, 10000.0, 800.0)
            paperless = st.selectbox("전자청구서 사용", ["Yes", "No"])
            payment = st.selectbox("결제 방식", ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"])
            phone = st.selectbox("전화 서비스", ["No", "Yes"])
            lines = st.selectbox("다중 회선", ["No", "Yes", "No phone service"])
        with col3:
            internet = st.selectbox("인터넷 서비스", ["Fiber optic", "DSL", "No"])
            security = st.selectbox("온라인 보안", ["No", "Yes", "No internet service"])
            backup = st.selectbox("온라인 백업", ["No", "Yes", "No internet service"])
            dev_prot = st.selectbox("기기 보호", ["No", "Yes", "No internet service"])
            tech = st.selectbox("기술 지원", ["No", "Yes", "No internet service"])
            tv = st.selectbox("스트리밍 TV", ["No", "Yes", "No internet service"])
            mov = st.selectbox("스트리밍 영화", ["No", "Yes", "No internet service"])

        submit = st.form_submit_button("분석 실행")

    if submit:
        try:
            # [A] 입력 데이터 구성
            input_data = pd.DataFrame([{
                'Gender': gender, 'Senior Citizen': senior, 'Partner': partner, 
                'Dependents': dep, 'Tenure Months': tenure, 'Phone Service': phone, 
                'Multiple Lines': lines, 'Internet Service': internet, 
                'Online Security': security, 'Online Backup': backup, 
                'Device Protection': dev_prot, 'Tech Support': tech, 
                'Streaming TV': tv, 'Streaming Movies': mov, 
                'Contract': contract, 'Paperless Billing': paperless, 
                'Payment Method': payment, 'Monthly Charges': monthly, 'Total Charges': total
            }])

            # [B] 피처 엔지니어링 및 순서 고정
            processed_df = create_engineered_features(input_data, model_columns=model_columns)
            processed_df = processed_df[model_columns]

            # [C] ⭐ [isnan 에러 핵심 방어] 타입 강제 수치화
            # 문자열인 원본 데이터가 섞여 있어도 무조건 숫자로 변환합니다.
            # 인코딩 전에 시도하여 타입 안정성을 확보합니다.
            for col in processed_df.columns:
                if processed_df[col].dtype == 'object':
                    continue # 범주형은 인코더가 처리하도록 둠
                processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce').fillna(0)

            # [D] 인코딩
            encoded_data = encoder.transform(processed_df)
            
            # [E] 결과물을 float64 데이터프레임으로 강제 확정
            # ColumnTransformer 출력물을 받아 모든 컬럼을 float64로 변환하여 isnan 에러 차단
            final_df = pd.DataFrame(encoded_data, columns=model_columns).astype('float64')

            # [F] 스케일링 및 예측
            scaled_input = scaler.transform(final_df)
            prob = model.predict_proba(scaled_input)[0, 1]

            st.markdown("---")
            st.subheader(f"🔮 예측 결과: 이탈 확률 {prob*100:.2f}%")
            if prob >= OPTIMAL_THRESHOLD:
                st.error("🚨 고위험군: 적극적인 방어 마케팅이 필요합니다.")
            else:
                st.success("✅ 안전군: 현재 관계 유지가 양호합니다.")

        except Exception as e:
            st.error(f"⚠️ 예측 실패: {e}")