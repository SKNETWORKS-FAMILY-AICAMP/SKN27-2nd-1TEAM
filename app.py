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

st.set_page_config(
    page_title="Telco Churn Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            background-color: #ffffff; z-index: 999999;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            animation: hideScreen 3.5s forwards;
        }}
        @keyframes hideScreen {{
            0%   {{ opacity: 1; visibility: visible; }}
            85%  {{ opacity: 1; visibility: visible; }}
            100% {{ opacity: 0; visibility: hidden;  }}
        }}
        #loading-logo {{
            width: 400px; height: auto; opacity: 0;
            mix-blend-mode: multiply;
            animation: fadeInLogo 1s ease-in forwards;
            margin-bottom: 20px;
        }}
        @keyframes fadeInLogo {{
            0%   {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
        #loading-bar-container {{
            width: 400px; height: 8px;
            background-color: #e5e7eb;
            border-radius: 4px; overflow: hidden; opacity: 0;
            animation: fadeInBarContainer 0.5s ease-in 0.8s forwards;
        }}
        @keyframes fadeInBarContainer {{
            0%   {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
        #loading-bar {{
            width: 0%; height: 100%;
            background-color: #2563eb; border-radius: 4px;
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