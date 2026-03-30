import sys
import os
import streamlit as st
from streamlit_option_menu import option_menu

# 경로 설정
current_dir  = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, 'src', 'frontend')
utils_dir    = os.path.join(current_dir, 'src', 'utils')

for path in [frontend_dir, utils_dir]:
    if path not in sys.path:
        sys.path.append(path)

# 페이지 설정
st.set_page_config(
    page_title='통신사 이탈 예측',
    page_icon='📡',
    layout='wide',
    initial_sidebar_state='expanded'
)

# 모듈 로드
try:
    import page_predict
    import page_dashboard
    import page_marketing
    import page_history
    import page_manage
    import page_metrics
    loaded = True
except ImportError as e:
    st.error(f'모듈 로드 실패: {e}')
    loaded = False

if loaded:
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding:15px 0;'>
            <h2 style='color:#1f77b4; margin:0;'>📡 고객 분석 시스템</h2>
            <p style='color:#888; font-size:13px; margin:5px 0;'>Telco Churn Analytics</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('---')

        menu = option_menu(
            menu_title=None,
            options=[
                '대시보드',
                '실시간 이탈 예측',
                '마케팅 액션 플랜',
                '예측 이력 조회',
                '고객 데이터 관리',
                '모델 성능 지표',
            ],
            icons=[
                'speedometer2',
                'lightning-charge-fill',
                'megaphone-fill',
                'clock-history',
                'people-fill',
                'bar-chart-line-fill',
            ],
            default_index=0,
            styles={
                'container'        : {'padding':'0!important','background-color':'transparent'},
                'icon'             : {'color':'#4B5563','font-size':'16px'},
                'nav-link'         : {
                    'font-size':'14px','text-align':'left','margin':'3px 0',
                    '--hover-color':'#e2e8f0','color':'#374151','font-weight':'500'
                },
                'nav-link-selected': {
                    'background-color':'#2563eb','color':'white','font-weight':'bold'
                },
            }
        )

        st.markdown('---')
        st.caption('SKN27-2nd-1TEAM')
        st.caption('Model: Stacking (AUC 0.85)')
        st.caption('Powered by Streamlit')

    # 페이지 라우팅
    if   menu == '대시보드':            page_dashboard.render()
    elif menu == '실시간 이탈 예측':    page_predict.render()
    elif menu == '마케팅 액션 플랜':    page_marketing.render()
    elif menu == '예측 이력 조회':      page_history.render()
    elif menu == '고객 데이터 관리':    page_manage.render()
    elif menu == '모델 성능 지표':      page_metrics.render()