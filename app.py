import sys
import os
import streamlit as st
from streamlit_option_menu import option_menu

# [핵심 아키텍처] 하위 모듈 경로 강제 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, 'src', 'frontend')

if frontend_dir not in sys.path:
    sys.path.append(frontend_dir)

# 경로 주입 완료 후 하위 모듈 호출
# 예외 처리: 파일이 없을 경우 로딩 화면 이후 에러 메시지 표시
try:
    import page_predict
    import page_manage
    import page_metrics
    modules_loaded = True
except ImportError as e:
    st.error(f"하위 모듈 로드 실패. 경로를 점검하십시오: {e}")
    modules_loaded = False

st.set_page_config(page_title="Telco Churn Analytics", layout="wide", initial_sidebar_state="collapsed")

# -------------------------------------------------------------------------
# [전역 UI 여백 및 레이아웃 강제 최적화]
# -------------------------------------------------------------------------
st.markdown("""
<style>
    /* 메인 컨테이너의 스트림릿 기본 상단 여백(약 6rem) 대폭 제거 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 95% !important; /* 좌우 여백도 살짝 줄여서 와이드하게 */
    }
    
    /* 기본 헤더(우측 상단 Deploy 버튼 등) 완전 숨김 처리 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# [로딩 화면 애니메이션 구현 - 100% Pure CSS 무결점 아키텍처 적용]
# JS 차단 이슈 해결 및 파이썬 sleep() 병목 제거
# -------------------------------------------------------------------------

# 로고 경로 (루트/assets/)
LOGO_PATH         = os.path.join(current_dir, 'assets', 'loading_logo.png')
SIDEBAR_LOGO_PATH = os.path.join(current_dir, 'assets', 'sub_logo.png')

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
            background-color: #0f172a; /* 다크모드 메인 배경색으로 변경 */
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
            /* mix-blend-mode: multiply; 다크모드 배경에서는 이미지가 까맣게 될 수 있으므로 제거 */
            background-color: transparent;
            border-radius: 12px;
            padding: 10px;
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
            background-color: #1e293b; /* 다크 빈 로딩바 */
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
            background-color: #3b82f6; /* 파란색 활성 로딩바 */
            border-radius: 4px;
            animation: fillBar 1.5s ease-in-out 1.2s forwards;
        }}

        @keyframes fillBar {{
            0% {{ width: 0%; }}
            100% {{ width: 100%; }}
        }}
        
        /* 메인 페이지가 렌더링되면서 잠깐 깜빡이는 현상(FOUC) 방지 및 자연스러운 등장 */
        /* block-container 전체에 opacity:0을 주면 내부의 loading-screen까지 안보이게 되므로 삭제함 */
        /* loading-screen 자체가 z-index 999999에 백그라운드를 덮고 있으므로 서서히 사라질 때 아래 앱이 자연스럽게 나타납니다. */
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
    import sys
    import types
    import numpy as np
    
    # Numpy 2.x 하위 호환성 패치 (hydralit_components가 numpy.lib.arraysetops를 사용)
    if 'numpy.lib.arraysetops' not in sys.modules:
        mock_arraysetops = types.ModuleType('numpy.lib.arraysetops')
        mock_arraysetops.isin = np.isin
        sys.modules['numpy.lib.arraysetops'] = mock_arraysetops
        
    import hydralit_components as hc

    # 상단 헤더: 네비게이션 바 위쪽에 서브 로고와 메인 타이틀 배치
    if os.path.exists(SIDEBAR_LOGO_PATH):
        import base64
        with open(SIDEBAR_LOGO_PATH, "rb") as image_file:
            sidebar_logo_encoded = base64.b64encode(image_file.read()).decode()
        header_html = f"""
        <div style='display: flex; flex-direction: row; align-items: center; justify-content: flex-start; padding-top: 10px; padding-bottom: 20px; padding-left: 5px;'>
            <img src='data:image/png;base64,{sidebar_logo_encoded}' style='width: 45px; margin-right: 15px; border-radius: 8px;' />
            <h2 style='color: #f8fafc; margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.5px;'>Telco Churn Analytics</h2>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='color: #f8fafc; padding-top: 10px; padding-bottom: 20px; font-weight: 800;'>Telco Churn Analytics</h2>", unsafe_allow_html=True)

    # 2. 프리미엄 디자인 상단 네비게이션 바
    menu_data = [
        {'icon': "fas fa-satellite-dish", 'label': "✨ Analytics AI (실시간 이탈 예측)"},
        {'icon': "fas fa-id-card", 'label': "고객 데이터 관리"},
        {'icon': "fas fa-tachometer-alt", 'label': "모델 신뢰성 검증 지표"}
    ]

    # CSS 파싱 오류를 방지하기 위해 그라데이션 대신 프리미엄 단색(Hex) 컬러 적용
    over_theme = {
        'menu_background': '#1e293b', # 깊은 슬레이트 다크 (프리미엄 SaaS 느낌)
        'txc_inactive': '#94a3b8',    # 연한 회색 (선택 안된 텍스트)
        'txc_active': '#3b82f6',      # 선명한 블루 (선택된 텍스트 색상만 강조)
        'option_active': 'transparent' # 활성화된 메뉴의 말풍선(버블) 모양 배경을 투명하게 없애버림
    }

    menu = hc.nav_bar(
        menu_definition=menu_data,
        override_theme=over_theme,
        home_name=None,  # '✨ Analytics AI'와 기존 예측 탭을 하나로 합치기 위해 Home 버튼 비활성화
        login_name=None,
        hide_streamlit_markers=True, # 스트림릿 기본 햄버거 메뉴 및 헤더를 숨겨 실제 앱처럼 보이게 함
        sticky_nav=True,
        sticky_mode='pinned'
    )

    # 사이드바에는 최소한의 시스템 정보만 남김 (기본은 collapsed 됨)
    with st.sidebar:
        st.markdown("<h4 style='text-align: center; color: #f8fafc; padding-top: 10px; padding-bottom: 20px;'>시스템 로그</h4>", unsafe_allow_html=True)
        st.caption("System Version: 1.5.0 (Dark Mode & Top Logo)")
        st.caption("Model Updated: 2026-03-27")

    # 3. 모듈 라우팅
    if menu == "✨ Analytics AI (실시간 이탈 예측)":
        page_predict.render()
    elif menu == "고객 데이터 관리":
        page_manage.render()
    elif menu == "모델 신뢰성 검증 지표":
        page_metrics.render()