import sys
import os
import streamlit as st
from streamlit_option_menu import option_menu

# [핵심 아키텍처] 하위 모듈 경로 강제 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, '02_src', 'frontend')

if frontend_dir not in sys.path:
    sys.path.append(frontend_dir)

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
    st.error(f"하위 모듈 로드 실패. 경로를 점검하십시오: {e}")
    modules_loaded = False

# 1. 페이지 및 전역 설정
st.set_page_config(page_title="Telco Churn Analytics", layout="wide", initial_sidebar_state="expanded")

# -------------------------------------------------------------------------
# [로딩 화면 애니메이션 구현 - 100% Pure CSS 무결점 아키텍처 적용]
# JS 차단 이슈 해결 및 파이썬 sleep() 병목 제거
# -------------------------------------------------------------------------

# 메인 로딩 로고 파일 경로 설정 (지정된 frontend/data 폴더 경로)
LOGO_PATH = os.path.join(current_dir, '02_src', 'frontend', 'data', 'loading_logo.png')
# 사이드바 서브 로고 파일 경로 설정 추가
SIDEBAR_LOGO_PATH = os.path.join(current_dir, '02_src', 'frontend', 'data', 'sub_logo.png')

# 세션 상태 초기화: 앱 실행 시 최초 1회만 로딩 화면 구동
if "has_loaded" not in st.session_state:
    st.session_state["has_loaded"] = False

# 앱 최초 로드 시 애니메이션 HTML 주입 (로고가 존재할 경우만)
if not st.session_state["has_loaded"] and modules_loaded and os.path.exists(LOGO_PATH):
    import base64
    with open(LOGO_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    # 자바스크립트 완전 배제, CSS만으로 페이드인, 로딩바, 화면 숨김(Visibility) 일괄 제어
    loading_html = f"""
    <style>
        #loading-screen {{
            position: fixed;
            top: 0; left: 0;
            width: 100vw; height: 100vh;
            background-color: #ffffff;
            z-index: 999999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            animation: hideScreen 3.5s forwards; /* 3.5초 후 화면 자체를 제거 */
        }}

        @keyframes hideScreen {{
            0% {{ opacity: 1; visibility: visible; }}
            85% {{ opacity: 1; visibility: visible; }} /* 3초 지점까지 100% 표시 */
            100% {{ opacity: 0; visibility: hidden; }} /* 마지막 0.5초 동안 투명화 및 클릭 통과 */
        }}

        #loading-logo {{
            width: 400px; /* 로고 사이즈 대폭 확대 (기존 250px) */
            height: auto;
            opacity: 0;
            mix-blend-mode: multiply; /* 흰색 배경 제거 효과 */
            animation: fadeInLogo 1s ease-in forwards;
            margin-bottom: 20px;
        }}

        @keyframes fadeInLogo {{
            0% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}

        #loading-bar-container {{
            width: 400px; /* 로고 사이즈에 맞춰 로딩바 길이 동기화 (기존 300px) */
            height: 8px;
            background-color: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            opacity: 0;
            animation: fadeInBarContainer 0.5s ease-in 0.8s forwards;
        }}

        @keyframes fadeInBarContainer {{
            0% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}

        #loading-bar {{
            width: 0%;
            height: 100%;
            background-color: #2563eb;
            border-radius: 4px;
            animation: fillBar 1.5s ease-in-out 1.2s forwards;
        }}

        @keyframes fillBar {{
            0% {{ width: 0%; }}
            100% {{ width: 100%; }}
        }}
    </style>

    <div id="loading-screen">
        <img id="loading-logo" src="data:image/png;base64,{encoded_string}" />
        <div id="loading-bar-container">
            <div id="loading-bar"></div>
        </div>
    </div>
    """
    st.markdown(loading_html, unsafe_allow_html=True)
    st.session_state["has_loaded"] = True

elif not st.session_state["has_loaded"] and not os.path.exists(LOGO_PATH):
    st.error(f"로딩 화면 구현 실패: 로고 파일을 찾을 수 없습니다. 경로를 확인하십시오: {LOGO_PATH}")
    st.session_state["has_loaded"] = True

# -------------------------------------------------------------------------
# [메인 화면 렌더링]
# 로딩 스크린이 상단에 오버레이되는 동안, 뒤에서는 시스템이 즉각적으로 렌더링 완료됨
# -------------------------------------------------------------------------

if modules_loaded:
    # 2. 사이드바 네비게이션
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