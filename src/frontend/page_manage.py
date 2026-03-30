import streamlit as st
import pandas as pd
import os
from ml_utils import load_ml_objects, create_engineered_features

# ✅ Fix 3: 상대경로
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

# 고객 목록 표시 컬럼 순서
DISPLAY_COLS = {
    'CustomerID':       '고객 ID',
    'Tenure Months':    '가입 기간(월)',
    'Contract':         '계약 형태',
    'Monthly Charges':  '월 요금($)',
    'Total Charges':    '총 요금($)',
    'Internet Service': '인터넷 서비스',
    '이탈 확률':        '이탈 확률',   # 예측 후 추가되는 컬럼
}


def predict_churn_proba(df: pd.DataFrame) -> pd.DataFrame:
    """배치 예측: 이탈 확률 컬럼을 추가한 DataFrame 반환"""
    model, encoder, scaler, model_columns, _ = load_ml_objects()
    if model is None:
        return df

    try:
        processed = create_engineered_features(df.copy(), model_columns=model_columns)
        processed = processed[model_columns]

        # 수치형 dtype 안정화
        for col in processed.columns:
            if processed[col].dtype != 'object':
                processed[col] = pd.to_numeric(processed[col], errors='coerce').fillna(0)

        encoded_data = encoder.transform(processed)

        encoder_out_cols = []
        for _, _, cols in encoder.transformers_:
            if isinstance(cols, list):
                encoder_out_cols.extend(cols)

        encoded_df   = pd.DataFrame(encoded_data, columns=encoder_out_cols).astype('float64')
        scaled_input = scaler.transform(encoded_df)
        proba        = model.predict_proba(scaled_input)[:, 1]

        result = df.copy()
        result['이탈 확률'] = (proba * 100).round(1)   # 퍼센트로 변환
        return result

    except Exception as e:
        st.warning(f"⚠️ 이탈 확률 예측 실패: {e}")
        return df


def load_latest_csv() -> pd.DataFrame | None:
    """00_data 폴더에서 가장 최근 저장된 CSV를 불러옴"""
    if not os.path.exists(DATA_DIR):
        return None
    csv_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')],
        key=lambda f: os.path.getmtime(os.path.join(DATA_DIR, f)),
        reverse=True
    )
    if not csv_files:
        return None
    return pd.read_csv(os.path.join(DATA_DIR, csv_files[0]))


def render_customer_table(df: pd.DataFrame):
    """이탈 확률 기준 정렬 + 위험도 강조 테이블 렌더링"""
    available = {k: v for k, v in DISPLAY_COLS.items() if k in df.columns}
    view_df = df[list(available.keys())].copy()
    view_df.rename(columns=available, inplace=True)

    # 월 요금 / 총 요금 소수점 2자리 포맷
    for col in ['월 요금($)', '총 요금($)']:
        if col in view_df.columns:
            view_df[col] = pd.to_numeric(view_df[col], errors='coerce').map('{:.2f}'.format)

    # 이탈 확률 내림차순 정렬
    if '이탈 확률' in view_df.columns:
        view_df = view_df.sort_values('이탈 확률', ascending=False).reset_index(drop=True)

        def highlight_risk(row):
            # 숫자형 상태에서 비교 (% 문자열 변환 전에 실행)
            prob = pd.to_numeric(row.get('이탈 확률', 0), errors='coerce') or 0
            if prob >= 70:
                return ['background-color: #fff0f0'] * len(row)
            elif prob >= 40:
                return ['background-color: #fffbea'] * len(row)
            return [''] * len(row)

        # style.apply(강조) 먼저 -> format으로 % 문자열 표시
        st.dataframe(
            view_df.style.apply(highlight_risk, axis=1)
                         .format({'이탈 확률': '{:.1f}%'}),
            use_container_width=True,
            height=460
        )
    else:
        st.dataframe(view_df, use_container_width=True, height=460)

    # 위험도 범례
    if '이탈 확률' in view_df.columns:
        c1, c2, c3 = st.columns(3)
        c1.markdown("🔴 **고위험** : 이탈 확률 70% 이상")
        c2.markdown("🟡 **중위험** : 이탈 확률 40~70%")
        c3.markdown("⚪ **안전**   : 이탈 확률 40% 미만")

    st.caption(f"총 {len(df):,}명 | 이탈 확률 높은 순 정렬")


def render():
    st.title("고객 데이터베이스 관리")
    st.markdown("CSV 파일을 업로드하면 이탈 확률을 자동 예측하여 고객 목록에 반영합니다.")

    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"데이터 디렉토리 생성 실패: {e}")
            return

    # ── 업로드 섹션 ──────────────────────────────────────────────
    st.subheader("신규 데이터 일괄 업로드 (CSV)")
    uploaded_file = st.file_uploader(
        "배치(Batch) 예측을 수행할 CSV 파일을 선택하십시오.", type=["csv"]
    )

    if uploaded_file is not None:
        file_path = os.path.join(DATA_DIR, uploaded_file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            df_uploaded = pd.read_csv(file_path)
            st.success(f"✅ **{uploaded_file.name}** 적재 완료 — {len(df_uploaded):,}행 감지")

            with st.expander("업로드 데이터 미리보기 (상위 5행)"):
                st.dataframe(df_uploaded.head(), use_container_width=True)

            # 배치 예측 실행
            with st.spinner("🔮 이탈 확률 예측 중..."):
                df_predicted = predict_churn_proba(df_uploaded)

            st.session_state["customer_df"] = df_predicted

        except Exception as e:
            st.error(f"파일 저장 중 오류: {e}")

    st.markdown("---")

    # ── 고객 목록 섹션 ───────────────────────────────────────────
    st.subheader("현재 관리 중인 고객 목록")

    # 우선순위: ① 방금 업로드(session) → ② 00_data 기존 파일
    if "customer_df" in st.session_state:
        render_customer_table(st.session_state["customer_df"])
    else:
        df_stored = load_latest_csv()
        if df_stored is not None:
            with st.spinner("🔮 저장된 데이터 이탈 확률 예측 중..."):
                df_predicted = predict_churn_proba(df_stored)
            render_customer_table(df_predicted)
        else:
            st.info("업로드된 고객 데이터가 없습니다. 위에서 CSV 파일을 업로드해 주세요.")