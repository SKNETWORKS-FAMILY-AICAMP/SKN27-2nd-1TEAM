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
                st.error(f"해당 고객은 이탈 위험 고객으로 적극적인 방어 마케팅이 필요합니다.")
                
                # --- [START] Prescriptive AI: 맞춤형 유지 엑션 추천 ---
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("💡 AI 맞춤형 리텐션(유지) 액션 추천")
                st.markdown("현재 입력된 고객의 핵심 데이터 특성을 분석하여 도출된 최적의 방어 전략입니다.")
                
                actions = []
                # 1. 계약 조건 분석
                if contract == "Month-to-month":
                    actions.append("🏷️ **단기 계약 리스크:** 매월 갱신되는 Month-to-month 계약 고객입니다. **약정 할인(1년/2년 계약) 프로모션 쿠폰**을 발송하여 즉각적인 락인(Lock-in)을 유도하세요.")
                
                # 2. 가입 기간 분석
                if tenure < 12:
                    actions.append("🌱 **초기 이탈 리스크:** 가입 1년 미만의 신규/초기 고객입니다. 서비스 불만이 쌓이기 전에 **온보딩 케어 안내 콜(Care Call) 배정 및 웰컴 패키지 혜택**을 제공하세요.")
                    
                # 3. 주요 부가서비스 부재 (Tech Support, Security)
                if internet == "Fiber optic" and tech == "No":
                    actions.append("👨‍💻 **기술 마찰 리스크:** 고가/고품질인 Fiber Optic 망을 쓰지만 '기술 지원(Tech Support)' 서비스가 없습니다. 장애 발생 시 가장 먼저 이탈하므로 **기술지원 부가서비스 3개월 무료 체험**을 권유하세요.")
                elif internet != "No" and security == "No":
                    actions.append("🛡️ **보안 서비스 부재:** 인터넷 가입자이나 통신망 '온라인 보안(Online Security)'에 미가입 상태입니다. **네트워크 보안 결합 특가 할인**으로 서비스 의존도를 높이세요.")
                    
                # 4. 요금 부담 분석
                if monthly > 70.0:
                    actions.append("💰 **요금 부담 리스크:** 최상위 구간에 속하는 높은 월 청구 요금($70 이상)을 내고 있습니다. 무리한 서비스보다 **데이터 이용량 맞춤형 요금제 하향 컨설팅이나 5% 청구 할인 쿠폰**을 제안하여 가격 민감도를 낮추세요.")
                    
                # 5. 시니어 고객 접근
                if senior == 1:
                    actions.append("👴 **시니어 특화 케어:** 고령자 고객군입니다. 복잡한 시스템이나 긴 ARS 대기줄 대신 **시니어 전용 직통 상담사 연결** 프로세스로 고객 만족도 최상급을 유지하세요.")
                
                if actions:
                    for action in actions:
                        st.info(action)
                else:
                    st.info("🎯 해당 고객은 뚜렷한 리스크 변수 지표가 보이지 않습니다. 종합적인 **일반 VIP 관리 유지 혜택(포인트 적립 등)**을 제안합니다.")
                # --- [END] Prescriptive AI ---

            else:
                st.success(f"해당 고객은 이탈 확률이 낮은 안전 고객입니다.")

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