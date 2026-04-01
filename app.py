import sys
import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from streamlit_option_menu import option_menu

current_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir   = os.path.join(current_dir, 'src', 'utils')

for team in ['common', 'analytics', 'marketing', 'sales', 'operations']:
    p = os.path.join(current_dir, 'src', 'frontend', team)
    if p not in sys.path:
        sys.path.append(p)

if utils_dir not in sys.path:
    sys.path.append(utils_dir)

try:
    # 공용
    import page_churn_reason
    import page_correlation
    import page_survival
    # 분석팀
    import page_metrics
    import page_segment
    # 마케팅팀
    import page_marketing
    import page_campaign
    import page_revenue
    # 영업팀
    import page_predict
    import page_profile
    import page_region
    import page_alert
    # 운영팀
    import page_dashboard
    import page_manage
    import page_customer_register
    import page_report
    import page_history
    from db_utils import init_db
    init_db()
    modules_loaded = True
except ImportError as e:
    st.error(f"모듈 로드 실패: {e}")
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
    with open(LOGO_PATH, "rb") as f:
        enc = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
        #loading-screen {{
            position:fixed; top:0; left:0; width:100vw; height:100vh;
            background:#fff; z-index:999999;
            display:flex; flex-direction:column;
            justify-content:center; align-items:center;
            animation:hideScreen 3.5s forwards;
        }}
        @keyframes hideScreen {{0%,85%{{opacity:1;visibility:visible;}}100%{{opacity:0;visibility:hidden;}}}}
        #loading-logo {{width:400px;opacity:0;mix-blend-mode:multiply;animation:fadeInLogo 1s ease-in forwards;margin-bottom:20px;}}
        @keyframes fadeInLogo {{0%{{opacity:0;}}100%{{opacity:1;}}}}
        #loading-bar-container {{width:400px;height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;opacity:0;animation:fadeInBar 0.5s ease-in 0.8s forwards;}}
        @keyframes fadeInBar {{0%{{opacity:0;}}100%{{opacity:1;}}}}
        #loading-bar {{width:0%;height:100%;background:#2563eb;border-radius:4px;animation:fillBar 1.5s ease-in-out 1.2s forwards;}}
        @keyframes fillBar {{0%{{width:0%;}}100%{{width:100%;}}}}
    </style>
    <div id="loading-screen">
        <img id="loading-logo" src="data:image/png;base64,{enc}" />
        <div id="loading-bar-container"><div id="loading-bar"></div></div>
    </div>
    """, unsafe_allow_html=True)

st.session_state["has_loaded"] = True

# ── 팀별 메뉴 정의 ────────────────────────────────
# 요청사항 반영:
# - 대시보드: 공용(맨위) + 운영팀(맨위)
# - 분석팀: 모델 관련만
# - 생존분석: 공용으로 이동
# - 고객 세그먼트: 분석팀에서 삭제
# - 운영팀 순서: 전체대시보드→배치예측→고객데이터관리→고객등록수정→리포트생성→알림이력삭제
# - 공용: 이탈사유/상관관계/생존분석
# - 영업팀: 고객상세프로필 맨위

TEAM_MENUS = {
    "🌐 공용 인사이트": {
        "menus": [
            "전체 대시보드",
            "이탈 사유 분석",
        ],
        "icons": [
            "speedometer2",
            "chat-left-text-fill",
            "link-45deg",
            "graph-up",
        ],
        "color": "#1E3A5F"
    },
    "📊 분석팀": {
        "menus": [
            "모델 성능 지표",
            "이탈 사유 분석",
            "상관관계 분석",
            "생존 분석",
            "전체 대시보드",
        ],
        "icons": [
            "bar-chart-line-fill",
            "chat-left-text-fill",
            "link-45deg",
            "graph-up",
            "speedometer2",
        ],
        "color": "#2563EB"
    },
    "📣 마케팅팀": {
        "menus": [
            "마케팅 액션 플랜",
            "캠페인 관리",
            "수익 분석",
            "이탈 사유 분석",
            "전체 대시보드",
        ],
        "icons": [
            "megaphone-fill",
            "bullseye",
            "currency-dollar",
            "chat-left-text-fill",
            "speedometer2",
        ],
        "color": "#16A34A"
    },
    "👤 영업팀": {
        "menus": [
            "고객 상세 프로필",
            "고객 세그먼트 분석",
            "이탈 위험 예측",
            "지역 분석",
            "알림 센터",
            "전체 대시보드",
        ],
        "icons": [
            "person-badge-fill",
            "lightning-charge-fill",
            "geo-alt-fill",
            "bell-fill",
            "speedometer2",
        ],
        "color": "#D97706"
    },
    "🔧 운영팀": {
        "menus": [
            "전체 대시보드",
            "배치 예측 실행",
            "고객 데이터 관리",
            "고객 등록/수정",
            "리포트 생성",
        ],
        "icons": [
            "speedometer2",
            "people-fill",
            "database-fill",
            "person-plus-fill",
            "file-earmark-bar-graph-fill",
        ],
        "color": "#7C3AED"
    },
}

PAGE_ROUTES = {
    "전체 대시보드"     : lambda: page_dashboard.render(),
    "이탈 사유 분석"    : lambda: page_churn_reason.render(),
    "상관관계 분석"     : lambda: page_correlation.render(),
    "생존 분석"         : lambda: page_survival.render(),
    "모델 성능 지표"    : lambda: page_metrics.render(),
    "마케팅 액션 플랜"  : lambda: page_marketing.render(),
    "캠페인 관리"       : lambda: page_campaign.render(),
    "수익 분석"         : lambda: page_revenue.render(),
    "고객 상세 프로필"  : lambda: page_profile.render(),
    "이탈 위험 예측"    : lambda: page_predict.render(),
    "지역 분석"         : lambda: page_region.render(),
    "알림 센터"         : lambda: page_alert.render(),
    "배치 예측 실행"    : lambda: page_history.render(),
    "고객 데이터 관리"  : lambda: page_manage.render(),
    "고객 세그먼트 분석": lambda: page_segment.render(),
    "고객 등록/수정"    : lambda: page_customer_register.render(),
    "리포트 생성"       : lambda: page_report.render(),
}

if modules_loaded:
    with st.sidebar:
        if os.path.exists(SIDEBAR_LOGO_PATH):
            import base64
            with open(SIDEBAR_LOGO_PATH, "rb") as f:
                enc2 = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style='display:flex;align-items:center;justify-content:center;padding:10px 0;'>
                <img src='data:image/png;base64,{enc2}'
                     style='width:35px;mix-blend-mode:multiply;margin-right:12px;'/>
                <h3 style='color:#1f77b4;margin:0;font-size:20px;font-weight:600;'>고객 분석 시스템</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                "<h3 style='text-align:center;color:#1f77b4;padding:10px 0;'>고객 분석 시스템</h3>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        selected_team = st.selectbox("👥 팀 선택", list(TEAM_MENUS.keys()))
        st.markdown("---")

        team_cfg = TEAM_MENUS[selected_team]
        menu = option_menu(
            menu_title=None,
            options=team_cfg["menus"],
            icons=team_cfg["icons"],
            default_index=0,
            styles={
                "container"        : {"padding":"0!important","background-color":"transparent"},
                "icon"             : {"color":"#4B5563","font-size":"15px"},
                "nav-link"         : {
                    "font-size":"13px","text-align":"left",
                    "margin":"2px 0","--hover-color":"#e2e8f0",
                    "color":"#374151","font-weight":"500"
                },
                "nav-link-selected": {
                    "background-color": team_cfg["color"],
                    "color":"white","font-weight":"bold"
                },
            }
        )

        st.markdown("---")
        st.caption("SKN27-2nd-1TEAM")
        st.caption("Model: Stacking (AUC 0.85)")

    if menu in PAGE_ROUTES:
        PAGE_ROUTES[menu]()