import sys
import os
import streamlit as st
from streamlit_option_menu import option_menu

current_dir  = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, 'src', 'frontend')
utils_dir    = os.path.join(current_dir, 'src', 'utils')

for path in [frontend_dir, utils_dir]:
    if path not in sys.path:
        sys.path.append(path)

try:
    import page_predict
    import page_manage
    import page_metrics
    import page_dashboard
    import page_history
    import page_marketing
    import page_profile
    import page_alert
    import page_campaign
    import page_report
    import page_region
    import page_customer_register
    import page_survival
    import page_segment
    import page_correlation
    import page_churn_reason
    import page_revenue
    modules_loaded = True
except ImportError as e:
    st.error(f"하위 모듈 로드 실패. 경로를 점검하십시오: {e}")
    modules_loaded = False

<<<<<<< HEAD
st.set_page_config(
    page_title="Telco Churn Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)
=======
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
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a

LOGO_PATH         = os.path.join(current_dir, 'assets', 'loading_logo.png')
SIDEBAR_LOGO_PATH = os.path.join(current_dir, 'assets', 'sub_logo.png')

if "has_loaded" not in st.session_state:
    st.session_state["has_loaded"] = False

if not st.session_state["has_loaded"] and modules_loaded and os.path.exists(LOGO_PATH):
    import base64
    with open(LOGO_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    loading_html = f"""
    <style>
        #loading-screen {{
            position: fixed; top: 0; left: 0;
            width: 100vw; height: 100vh;
<<<<<<< HEAD
            background-color: #ffffff; z-index: 999999;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            animation: hideScreen 3.5s forwards;
=======
            background-color: #0f172a; /* 다크모드 메인 배경색으로 변경 */
            z-index: 999999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            animation: hideScreen 3.5s forwards; /* 3.5초 후 화면 자체를 제거 */
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
        }}
        @keyframes hideScreen {{
            0%   {{ opacity: 1; visibility: visible; }}
            85%  {{ opacity: 1; visibility: visible; }}
            100% {{ opacity: 0; visibility: hidden;  }}
        }}
        #loading-logo {{
<<<<<<< HEAD
            width: 400px; height: auto; opacity: 0;
            mix-blend-mode: multiply;
=======
            width: 400px; /* 로고 사이즈 대폭 확대 (기존 250px) */
            height: auto;
            opacity: 0;
            /* mix-blend-mode: multiply; 다크모드 배경에서는 이미지가 까맣게 될 수 있으므로 제거 */
            background-color: transparent;
            border-radius: 12px;
            padding: 10px;
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
            animation: fadeInLogo 1s ease-in forwards;
            margin-bottom: 20px;
        }}
        @keyframes fadeInLogo {{
            0%   {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
        #loading-bar-container {{
<<<<<<< HEAD
            width: 400px; height: 8px;
            background-color: #e5e7eb;
            border-radius: 4px; overflow: hidden; opacity: 0;
=======
            width: 400px; /* 로고 사이즈에 맞춰 로딩바 길이 동기화 (기존 300px) */
            height: 8px;
            background-color: #1e293b; /* 다크 빈 로딩바 */
            border-radius: 4px;
            overflow: hidden;
            opacity: 0;
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
            animation: fadeInBarContainer 0.5s ease-in 0.8s forwards;
        }}
        @keyframes fadeInBarContainer {{
            0%   {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
        #loading-bar {{
<<<<<<< HEAD
            width: 0%; height: 100%;
            background-color: #2563eb; border-radius: 4px;
=======
            width: 0%;
            height: 100%;
            background-color: #3b82f6; /* 파란색 활성 로딩바 */
            border-radius: 4px;
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
            animation: fillBar 1.5s ease-in-out 1.2s forwards;
        }}
        @keyframes fillBar {{
            0%   {{ width: 0%;   }}
            100% {{ width: 100%; }}
        }}
    </style>
    <div id="loading-screen">
        <img id="loading-logo" src="data:image/png;base64,{encoded_string}" />
        <div id="loading-bar-container"><div id="loading-bar"></div></div>
    </div>
    """
    st.markdown(loading_html, unsafe_allow_html=True)

st.session_state["has_loaded"] = True

# ── 팀별 메뉴 정의 ────────────────────────────────
TEAM_MENUS = {
    "📊 분석팀": {
        "menus": [
            "대시보드",
            "생존 분석",
            "상관관계 분석",
            "고객 세그먼트",
            "이탈 사유 분석",
            "지역 분석",
            "모델 신뢰성 검증 지표",
        ],
        "icons": [
            'speedometer2',
            'graph-up',
            'link-45deg',
            'diagram-3-fill',
            'chat-left-text-fill',
            'geo-alt-fill',
            'bar-chart-line-fill',
        ],
        "color": "#2563eb"
    },
    "📣 마케팅팀": {
        "menus": [
            "대시보드",
            "마케팅 액션 플랜",
            "캠페인 관리",
            "알림 센터",
            "수익 분석",
            "리포트 생성",
        ],
        "icons": [
            'speedometer2',
            'megaphone-fill',
            'bullseye',
            'bell-fill',
            'currency-dollar',
            'file-earmark-bar-graph-fill',
        ],
        "color": "#16a34a"
    },
    "👤 영업/CS팀": {
        "menus": [
            "대시보드",
            "실시간 이탈 위험 예측",
            "고객 상세 프로필",
            "고객 등록/수정",
            "지역 분석",
            "예측 이력 조회",
        ],
        "icons": [
            'speedometer2',
            'lightning-charge-fill',
            'person-badge-fill',
            'person-plus-fill',
            'geo-alt-fill',
            'clock-history',
        ],
        "color": "#d97706"
    },
    "🔧 운영팀": {
        "menus": [
            "대시보드",
            "고객 데이터 관리",
            "예측 이력 조회",
            "알림 센터",
            "리포트 생성",
        ],
        "icons": [
            'speedometer2',
            'people-fill',
            'clock-history',
            'bell-fill',
            'file-earmark-bar-graph-fill',
        ],
        "color": "#7c3aed"
    },
    "🔍 전체 보기": {
        "menus": [
            "대시보드",
            "실시간 이탈 위험 예측",
            "고객 상세 프로필",
            "고객 등록/수정",
            "지역 분석",
            "생존 분석",
            "고객 세그먼트",
            "상관관계 분석",
            "이탈 사유 분석",
            "수익 분석",
            "마케팅 액션 플랜",
            "캠페인 관리",
            "알림 센터",
            "예측 이력 조회",
            "리포트 생성",
            "고객 데이터 관리",
            "모델 신뢰성 검증 지표",
        ],
        "icons": [
            'speedometer2',
            'lightning-charge-fill',
            'person-badge-fill',
            'person-plus-fill',
            'geo-alt-fill',
            'graph-up',
            'diagram-3-fill',
            'link-45deg',
            'chat-left-text-fill',
            'currency-dollar',
            'megaphone-fill',
            'bullseye',
            'bell-fill',
            'clock-history',
            'file-earmark-bar-graph-fill',
            'people-fill',
            'bar-chart-line-fill',
        ],
        "color": "#1f77b4"
    }
}

# 페이지 라우팅 딕셔너리
PAGE_ROUTES = {
    "대시보드"            : lambda: page_dashboard.render(),
    "실시간 이탈 위험 예측": lambda: page_predict.render(),
    "고객 상세 프로필"    : lambda: page_profile.render(),
    "고객 등록/수정"      : lambda: page_customer_register.render(),
    "지역 분석"           : lambda: page_region.render(),
    "생존 분석"           : lambda: page_survival.render(),
    "고객 세그먼트"       : lambda: page_segment.render(),
    "상관관계 분석"       : lambda: page_correlation.render(),
    "이탈 사유 분석"      : lambda: page_churn_reason.render(),
    "수익 분석"           : lambda: page_revenue.render(),
    "마케팅 액션 플랜"    : lambda: page_marketing.render(),
    "캠페인 관리"         : lambda: page_campaign.render(),
    "알림 센터"           : lambda: page_alert.render(),
    "예측 이력 조회"      : lambda: page_history.render(),
    "리포트 생성"         : lambda: page_report.render(),
    "고객 데이터 관리"    : lambda: page_manage.render(),
    "모델 신뢰성 검증 지표": lambda: page_metrics.render(),
}

if modules_loaded:
<<<<<<< HEAD
    with st.sidebar:
        if os.path.exists(SIDEBAR_LOGO_PATH):
            import base64
            with open(SIDEBAR_LOGO_PATH, "rb") as image_file:
                sidebar_logo_encoded = base64.b64encode(image_file.read()).decode()
            st.markdown(f"""
            <div style='display: flex; flex-direction: row; align-items: center;
                        justify-content: center; padding: 10px 0;'>
                <img src='data:image/png;base64,{sidebar_logo_encoded}'
                     style='width: 35px; mix-blend-mode: multiply; margin-right: 12px;' />
                <h3 style='color: #1f77b4; margin: 0; font-size: 20px; font-weight: 600;'>고객 분석 시스템</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                "<h3 style='text-align:center; color:#1f77b4; padding:10px 0;'>고객 분석 시스템</h3>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        # 팀 선택
        selected_team = st.selectbox(
            "👥 팀 선택",
            list(TEAM_MENUS.keys()),
            index=0
        )

        st.markdown("---")

        team_config = TEAM_MENUS[selected_team]

        menu = option_menu(
            menu_title=None,
            options=team_config["menus"],
            icons=team_config["icons"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container"        : {"padding": "0!important", "background-color": "transparent"},
                "icon"             : {"color": "#4B5563", "font-size": "15px"},
                "nav-link"         : {
                    "font-size": "13px", "text-align": "left",
                    "margin": "2px 0px", "--hover-color": "#e2e8f0",
                    "color": "#374151", "font-weight": "500"
                },
                "nav-link-selected": {
                    "background-color": team_config["color"],
                    "color": "white", "font-weight": "bold"
                },
            }
        )

        st.markdown("---")
        st.caption("SKN27-2nd-1TEAM")
        st.caption("Model: Stacking (AUC 0.85)")

    # 페이지 렌더링
    if menu in PAGE_ROUTES:
        PAGE_ROUTES[menu]()
=======
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
>>>>>>> b2494bf5580f5d8cdc87c861fb185de08065f56a
