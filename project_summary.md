# 📊 프로젝트 요약 정리 (Telco Churn Analytics)

## 📁 프로젝트 폴더 구조

```text
c:\dev\project\SKN27-2nd-1TEAM\
├── app.py                  # Streamlit 애플리케이션의 메인 진입점
├── src/                    # 소스 코드
│   ├── frontend/           # 화면별 UI 모듈 및 화면 구성 요소 (.py)
│   │   ├── ml_utils.py
│   │   ├── page_dashboard.py, page_predict.py, page_profile.py 등 총 17개의 페이지별 파일
│   └── utils/              # 각종 유틸리티 파일
│       ├── db_utils.py     # 데이터베이스 연동 및 쿼리 관리 모듈
│       └── email_utils.py  # 알림 및 메일 발송 관련 모듈
├── assets/                 # 이미지 등 정적 리소스 파일
│   ├── loading_logo.png    # 로딩 애니메이션 화면용 로고
│   └── sub_logo.png        # 사이드바용 서브 로고
├── data/                   # 데이터셋 폴더
│   ├── Telco_churn.csv 등 원본 및 전처리된 결과 데이터
├── docs/                   # 기획서, 요구사항 정의서, WBS, EDA 요약 등 문서 파일
├── model/                  # 학습된 머신러닝 모델 저장 폴더
├── notebook/               # 주피터 노트북 (EDA, 전처리 과정 및 모델 학습 테스트 등)
├── init.sql/               # 데이터베이스 초기화용 SQL 스크립트
├── requirements.txt        # Python 패키지 의존성 파일
└── docker-compose.yml      # 도커 (Docker) 구성 파일
```

---

## 🖥 화면 구성 (UI Layout)

애플리케이션은 **Streamlit**을 기반으로 설계되었으며 크게 **시작(로딩) 화면**, **좌측 사이드바(Sidebar)**, **우측 메인 화면(Main Content)** 으로 구성됩니다.

### 1️⃣ 인트로 (로딩 애니메이션)
앱이 처음 실행될 때 `assets/loading_logo.png` 로고 이미지와 함께 자체 제작된 로딩 애니메이션이 화면 중앙에 나타났다가 서서히 사라집니다(Fade-Out).

### 2️⃣ 측면 사이드바 (Navigation)
사이드바는 사용자의 직무 특성을 고려해 **부서(팀)별 맞춤형 메뉴**를 제공하도록 구성되어 있습니다.
- **최상단**: 시스템 로고(`sub_logo.png`) 및 "고객 분석 시스템" 타이틀
- **👥 팀 선택(Dropdown)**: 
  - 선택한 팀에 따라 관련 메뉴만 하단에 필터링되어 나타납니다.
  - [📊 분석팀, 📣 마케팅팀, 👤 영업/CS팀, 🔧 운영팀, 🔍 전체 보기]를 지원합니다.
- **메뉴 진입점**: 팀 선택 결과에 연동된 세부 메뉴 리스트 (예: 대시보드, 마케팅 액션 플랜, 이탈 예측 등)
- **최하단**: 팀 명칭(SKN27-2nd-1TEAM) 및 적용된 모델 기술 지표 (Model: Stacking - AUC 0.85)가 노출됩니다.

### 3️⃣ 메인 콘텐츠 (Page Contents)
사이드바에서 사용자가 선택한 메뉴에 따라 `src/frontend` 디렉터리 내 개별 페이지 모듈(예: `page_predict.py`, `page_marketing.py` 등)이 호출되어 실시간으로 화면 중앙에 렌더링되는 방식입니다.

#### 주요 페이지 라우팅 내역 (17개)
1. **대시보드** (`page_dashboard.py`)
2. **실시간 이탈 위험 예측** (`page_predict.py`)
3. **고객 상세 프로필** (`page_profile.py`)
4. **고객 등록/수정** (`page_customer_register.py`)
5. **지역 분석** (`page_region.py`)
6. **생존 분석** (`page_survival.py`)
7. **고객 세그먼트** (`page_segment.py`)
8. **상관관계 분석** (`page_correlation.py`)
9. **이탈 사유 분석** (`page_churn_reason.py`)
10. **수익 분석** (`page_revenue.py`)
11. **마케팅 액션 플랜** (`page_marketing.py`)
12. **캠페인 관리** (`page_campaign.py`)
13. **알림 센터** (`page_alert.py`)
14. **예측 이력 조회** (`page_history.py`)
15. **리포트 생성** (`page_report.py`)
16. **고객 데이터 관리** (`page_manage.py`)
17. **모델 신뢰성 검증 지표** (`page_metrics.py`)

---

## 📌 주요 특징
- **역할 기반 화면 제공 (RBAC 유사)**: 분석팀부터 마케팅, 영업/CS팀까지 다양한 팀의 목적에 맞게 필요한 대시보드 지표 및 도구들만 효율적으로 보여줍니다.
- **모듈화 아키텍처**: 시스템 로직(`utils`), 화면 구성 로직(`frontend`), 메인 라우팅 로직(`app.py`)이 명확하게 분리되어 유지보수에 용이한 구조를 취하고 있습니다.
