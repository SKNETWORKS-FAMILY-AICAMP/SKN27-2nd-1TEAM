import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ml_utils import load_ml_objects, predict_churn, THRESHOLD
from db_utils import save_prediction, init_db
from email_utils import send_alert, SMTP_USER


def gauge(prob):
    color = '#F44336' if prob >= THRESHOLD else '#4CAF50'
    fig = go.Figure(go.Indicator(
        mode='gauge+number', value=round(prob*100, 1),
        title={'text': '이탈 확률 (%)'},
        gauge={
            'axis': {'range': [0,100]},
            'bar':  {'color': color},
            'steps': [
                {'range':[0,30],   'color':'#E8F5E9'},
                {'range':[30,60],  'color':'#FFF9C4'},
                {'range':[60,100], 'color':'#FFEBEE'},
            ],
            'threshold': {'line':{'color':'red','width':4},'thickness':0.75,'value':THRESHOLD*100}
        }
    ))
    fig.update_layout(height=260, margin=dict(t=40,b=0,l=20,r=20))
    st.plotly_chart(fig, use_container_width=True)


def render():
    st.title('⚡ 실시간 고객 이탈 위험도 분석')
    st.caption('고객 정보를 입력하면 AI가 이탈 확률을 즉시 예측합니다.')

    init_db()
    model, scaler, feature_cols = load_ml_objects()

    if model is None:
        st.error('❌ 모델 파일이 없습니다.')
        st.info('notebook 폴더에서 03_model.py를 먼저 실행하세요.')
        return

    # 사이드바 이메일 설정
    with st.sidebar:
        st.markdown('---')
        st.markdown('#### 📧 이메일 알림')
        alert_email = st.text_input('알림 수신 이메일', placeholder='담당자@company.com')
        send_flag   = st.checkbox('이탈 위험 시 이메일 발송')
        if send_flag and not SMTP_USER:
            st.warning('SMTP 미설정\nemail_utils.py 확인 필요')

    # 고객 식별 정보
    st.subheader('① 고객 식별 정보')
    c1, c2 = st.columns(2)
    with c1: customer_name = st.text_input('고객명', placeholder='홍길동')
    with c2: customer_id   = st.text_input('고객 ID', placeholder='3668-QPYBK')

    # 고객 특성 입력
    st.subheader('② 고객 특성 입력')
    with st.form('predict_form'):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown('**인구통계 / 계약**')
            gender           = st.selectbox('성별',         ['Male','Female'])
            senior           = st.selectbox('고령자',       ['No','Yes'])
            partner          = st.selectbox('배우자',       ['No','Yes'])
            dependents       = st.selectbox('부양가족',     ['No','Yes'])
            contract         = st.selectbox('계약 형태',    ['Month-to-month','One year','Two year'])
            tenure           = st.number_input('이용 기간(개월)', 0, 100, 12)

        with col2:
            st.markdown('**재무 / 결제**')
            monthly          = st.number_input('월 요금($)',  0.0, 200.0, 75.0)
            total            = st.number_input('총 요금($)',  0.0, 10000.0, 900.0)
            payment          = st.selectbox('결제 방식', ['Electronic check','Mailed check',
                                                          'Bank transfer (automatic)','Credit card (automatic)'])
            paperless        = st.selectbox('전자 청구서',  ['Yes','No'])
            phone            = st.selectbox('전화 서비스',  ['Yes','No'])
            multi_lines      = st.selectbox('다중 회선',    ['No','Yes','No phone service'])

        with col3:
            st.markdown('**인터넷 / 부가서비스**')
            internet         = st.selectbox('인터넷 서비스', ['Fiber optic','DSL','No'])
            online_sec       = st.selectbox('온라인 보안',   ['No','Yes','No internet service'])
            online_bak       = st.selectbox('온라인 백업',   ['No','Yes','No internet service'])
            device_pro       = st.selectbox('기기 보호',     ['No','Yes','No internet service'])
            tech_sup         = st.selectbox('기술 지원',     ['No','Yes','No internet service'])
            stream_tv        = st.selectbox('스트리밍 TV',   ['No','Yes','No internet service'])
            stream_mv        = st.selectbox('스트리밍 영화', ['No','Yes','No internet service'])

        submitted = st.form_submit_button('🔍 이탈 위험도 분석', use_container_width=True, type='primary')

    if submitted:
        input_df = pd.DataFrame([{
            'Gender':gender,'Senior Citizen':senior,'Partner':partner,'Dependents':dependents,
            'Tenure Months':tenure,'Phone Service':phone,'Multiple Lines':multi_lines,
            'Internet Service':internet,'Online Security':online_sec,'Online Backup':online_bak,
            'Device Protection':device_pro,'Tech Support':tech_sup,
            'Streaming TV':stream_tv,'Streaming Movies':stream_mv,
            'Contract':contract,'Paperless Billing':paperless,
            'Payment Method':payment,'Monthly Charges':monthly,'Total Charges':total,
        }])

        try:
            prob, is_churn = predict_churn(input_df, model, scaler, feature_cols)

            save_prediction(
                customer_id=customer_id or '미입력',
                customer_name=customer_name or '미입력',
                churn_prob=prob, is_churn=is_churn,
                contract=contract, internet=internet,
                monthly_charges=monthly, tenure_months=tenure,
                payment_method=payment,
            )

            st.markdown('---')
            st.subheader('③ 분석 결과')
            cg, cr = st.columns(2)

            with cg:
                gauge(prob)

            with cr:
                name = f"**{customer_name}** 고객" if customer_name else "해당 고객"
                if is_churn:
                    st.error(f'### ⚠️ 이탈 위험')
                    st.metric('이탈 확률', f'{prob*100:.1f}%')
                    st.markdown('**즉시 조치 필요**')
                    if internet == 'Fiber optic':
                        st.warning('💡 Fiber optic → 서비스 품질 점검')
                    if contract == 'Month-to-month':
                        st.warning('💡 월별 계약 → 장기 전환 유도')
                    if payment == 'Electronic check':
                        st.warning('💡 전자수표 → 자동결제 전환 권장')
                    st.info('리텐션 팀 연락 / 할인 요금제 제안 / 장기 계약 인센티브')

                    if send_flag and alert_email:
                        ok = send_alert(customer_name or '미입력', customer_id or '미입력',
                                        prob, contract, monthly, tenure, alert_email)
                        st.success(f'📧 이메일 발송 완료') if ok else st.warning('이메일 발송 실패')
                else:
                    st.success(f'### ✅ 안정 고객')
                    st.metric('이탈 확률', f'{prob*100:.1f}%')
                    st.markdown('**유지 관리**')
                    st.info('정기 만족도 모니터링 / 업셀링 기회 탐색')

            st.caption('✅ 예측 결과가 DB에 자동 저장되었습니다.')

        except Exception as e:
            st.error(f'오류: {e}')
