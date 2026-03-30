import streamlit as st
import pandas as pd
import numpy as np
from ml_utils import load_ml_objects, create_engineered_features

def render():
    st.title("실시간 고객 이탈 위험도 분석")

    # threshold 함께 언패킹
    model, encoder, scaler, model_columns, optimal_threshold = load_ml_objects()

    if model is None:
        st.error("시스템 준비 중: 모델 구성 요소를 로드하지 못했습니다.")
        return

    with st.form("churn_prediction_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            gender   = st.selectbox("성별", ["Female", "Male"])
            # Senior Citizen UI는 0/1 유지, ml_utils에서 변환
            senior   = st.selectbox("고령자 여부", [0, 1])
            partner  = st.selectbox("배우자 유무", ["No", "Yes"])
            dep      = st.selectbox("부양가족 유무", ["No", "Yes"])
            contract = st.selectbox("계약 형태", ["Month-to-month", "One year", "Two year"])
            tenure   = st.number_input("가입 기간(월)", 1, 100, 12)
        with col2:
            monthly   = st.number_input("월 요금($)", 0.0, 200.0, 70.0)
            total     = st.number_input("총 요금($)", 0.0, 10000.0, 800.0)
            paperless = st.selectbox("전자청구서 사용", ["Yes", "No"])
            payment   = st.selectbox("결제 방식", ["Electronic check", "Mailed check",
                                                  "Bank transfer (automatic)", "Credit card (automatic)"])
            phone     = st.selectbox("전화 서비스", ["No", "Yes"])
            lines     = st.selectbox("다중 회선", ["No", "Yes", "No phone service"])
        with col3:
            internet  = st.selectbox("인터넷 서비스", ["Fiber optic", "DSL", "No"])
            security  = st.selectbox("온라인 보안", ["No", "Yes", "No internet service"])
            backup    = st.selectbox("온라인 백업", ["No", "Yes", "No internet service"])
            dev_prot  = st.selectbox("기기 보호", ["No", "Yes", "No internet service"])
            tech      = st.selectbox("기술 지원", ["No", "Yes", "No internet service"])
            tv        = st.selectbox("스트리밍 TV", ["No", "Yes", "No internet service"])
            mov       = st.selectbox("스트리밍 영화", ["No", "Yes", "No internet service"])

        submit = st.form_submit_button("분석 실행")

    if submit:
        try:
            with st.spinner("빅데이터 기반 고객 이탈 위험도를 실시간 분석 중입니다..."):
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

                # [B] 피처 엔지니어링
                processed_df = create_engineered_features(input_data, model_columns=model_columns)
                processed_df = processed_df[model_columns]

                # [C] 인코딩
                # ColumnTransformer 출력물(Numpy Array)을 그대로 활용하여 타입 오류 원천 차단
                encoded_data = encoder.transform(processed_df).astype('float64')

                # [D] 스케일링 및 예측
                # DataFrame 재구성 없이 Numpy Array를 직접 스케일러에 전달
                scaled_input = scaler.transform(encoded_data)
                prob = model.predict_proba(scaled_input)[0, 1]

            st.markdown("---")
            st.subheader(f"예측 결과: 이탈 확률 {prob * 100:.2f}%")

            # 동적 로드한 optimal_threshold 사용
            if prob >= optimal_threshold:
                st.error(f"고위험군: 적극적인 방어 마케팅이 필요합니다.")
            else:
                st.success(f"안전군: 현재 관계 유지가 양호합니다.")

        except Exception as e:
            import traceback
            import os
            # 로그 파일 절대 폴더 추적 기록
            log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "error_log.txt"))
            
            debug_info = traceback.format_exc() + "\n\n"
            try:
                debug_info += "=== processed_df.columns ===\n" + str(processed_df.columns.tolist()) + "\n\n"
                debug_info += "=== processed_df.dtypes ===\n" + str(processed_df.dtypes) + "\n\n"
                debug_info += "=== model_columns ===\n" + str(model_columns) + "\n\n"
                if hasattr(encoder, 'transformers_'):
                    debug_info += "=== encoder.transformers_ ===\n" + str(encoder.transformers_) + "\n\n"
            except Exception as inner_e:
                debug_info += f"Failed to dump variables: {inner_e}"
                
            with open(log_path, "w", encoding='utf-8') as f:
                f.write(debug_info)
                
            st.error(f"예측 실패: {e}")
            st.info(f"디버깅을 위한 상세 에러 로그가 생성되었습니다. (저장 위치: {log_path})")