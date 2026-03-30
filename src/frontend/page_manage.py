import streamlit as st
import pandas as pd
import os
import altair as alt

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "00_data"))

# 하단 목록용 샘플 데이터
MOCK_DATA = pd.DataFrame({
    "Customer Name":   ["홍길동", "이순신", "강감찬", "유관순", "장보고"],
    "Tenure":          [12, 45, 2, 72, 5],
    "Contract":        ["Month-to-month", "One year", "Month-to-month", "Two year", "Month-to-month"],
    "Monthly Charges": [85.5, 45.0, 95.0, 25.0, 80.0],
    "Risk Status":     ["High Risk", "Safe", "High Risk", "Safe", "Warning"],
})


def _load_uploaded_data() -> pd.DataFrame | None:
    """00_data 폴더의 CSV 파일을 모두 읽어 하나로 합쳐 반환"""
    if not os.path.exists(DATA_DIR):
        return None
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    if not files:
        return None
    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_csv(os.path.join(DATA_DIR, f)))
        except Exception:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else None


def _get_col(df: pd.DataFrame, *candidates: str) -> str | None:
    """후보 컬럼명 중 df에 실제 존재하는 첫 번째를 반환"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _render_overview_dashboard(df: pd.DataFrame) -> None:
    churn_col    = _get_col(df, "Churn Label", "Risk Status")
    contract_col = _get_col(df, "Contract", "Contract type")
    charges_col  = _get_col(df, "Monthly Charges", "Monthly_Charges")
    tenure_col   = _get_col(df, "Tenure Months", "Tenure")

    total = len(df)

    # ── 메트릭 카드 ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 고객 수", f"{total:,}명")

    if churn_col == "Churn Label":
        n = int((df[churn_col] == "Yes").sum())
        c2.metric("이탈 고객", f"{n:,}명",
                  delta=f"{n/total*100:.1f}%", delta_color="inverse")
    elif churn_col == "Risk Status":
        n = int((df[churn_col] == "High Risk").sum())
        c2.metric("이탈 고위험", f"{n:,}명",
                  delta=f"{n/total*100:.1f}%", delta_color="inverse")
    else:
        c2.metric("이탈 고위험", "-")

    c3.metric("평균 가입 기간",
              f"{df[tenure_col].mean():.1f}개월" if tenure_col else "-")
    c4.metric("평균 월 요금",
              f"${df[charges_col].mean():,.1f}" if charges_col else "-")

    # ── 차트 2종 ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    # 1) 이탈 여부 비율 – 도넛 차트
    with col1:
        st.markdown("##### 이탈 고객 비율")
        if churn_col:
            is_churn_label = churn_col == "Churn Label"
            counts = (df[churn_col].value_counts()
                      .rename_axis("category").reset_index(name="count"))

            if is_churn_label:
                domain = ["Yes", "No"]
                range_ = ["#F04F4F", "#4CAF85"]
                label_map = {"Yes": "이탈", "No": "유지"}
            else:
                domain = list(counts["category"])
                range_ = ["#F04F4F", "#F5A623", "#4CAF85"][: len(domain)]
                label_map = {}

            if label_map:
                counts["category"] = counts["category"].map(
                    lambda v: label_map.get(v, v)
                )
                domain = [label_map.get(d, d) for d in domain]

            chart = (
                alt.Chart(counts)
                .mark_arc(innerRadius=80, outerRadius=150)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color(
                        "category:N",
                        scale=alt.Scale(domain=domain, range=range_),
                        legend=alt.Legend(
                            orient="bottom",
                            labelFontSize=13,
                            symbolSize=150,
                            labelLimit=300,
                        ),
                    ),
                    tooltip=["category:N", "count:Q"],
                )
                .properties(height=380, padding={"top": 30, "bottom": 10})
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("이탈 컬럼을 찾을 수 없습니다.")

    # 2) 계약 유형별 이탈율 – 가로 막대 차트
    with col2:
        st.markdown("##### 계약 유형별 이탈율")
        if churn_col and contract_col:
            churn_flag = (
                (df[churn_col] == "Yes") if churn_col == "Churn Label"
                else (df[churn_col] == "High Risk")
            )
            rate_df = (
                df.groupby(contract_col)
                .apply(lambda g: round(churn_flag.loc[g.index].sum() / len(g) * 100, 1))
                .rename_axis("contract")
                .reset_index(name="churn_rate")
                .sort_values("churn_rate", ascending=False)
            )

            chart = (
                alt.Chart(rate_df)
                .mark_bar()
                .encode(
                    y=alt.Y("contract:N", sort="-x", title=None,
                             axis=alt.Axis(labelFontSize=13)),
                    x=alt.X("churn_rate:Q", title="이탈율 (%)",
                             scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color(
                        "churn_rate:Q",
                        scale=alt.Scale(scheme="reds"),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("contract:N", title="계약 유형"),
                        alt.Tooltip("churn_rate:Q", title="이탈율 (%)"),
                    ],
                )
                .properties(height=380)
            )

            text = chart.mark_text(align="left", dx=4, fontSize=13).encode(
                text=alt.Text("churn_rate:Q", format=".1f")
            )
            st.altair_chart(
                (chart + text).properties(padding={"top": 30, "bottom": 10}),
                use_container_width=True,
            )
        else:
            st.info("계약 유형 또는 이탈 컬럼을 찾을 수 없습니다.")


def render():
    st.title("고객 데이터베이스 관리")
    st.markdown("대량의 고객 데이터를 업로드하고, 물리적 저장소(00_data)에 안전하게 적재합니다.")

    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"데이터 디렉토리 생성 실패. 관리자 권한을 확인하십시오: {e}")
            return

    # ── 상단 현황 대시보드 ───────────────────────────────────────────────────
    st.subheader("전반적 고객 현황")
    df_dash = _load_uploaded_data()
    if df_dash is not None:
        st.caption(f"00_data 기준 총 {len(df_dash):,}개 레코드")
        _render_overview_dashboard(df_dash)
    else:
        st.info("아직 업로드된 데이터가 없습니다. 아래에서 CSV를 업로드하면 현황이 자동으로 표시됩니다.")

    st.markdown("---")

    # ── 파일 업로드 ─────────────────────────────────────────────────────────
    st.subheader("신규 데이터 일괄 업로드 (CSV)")
    uploaded_file = st.file_uploader(
        "배치(Batch) 예측을 수행할 CSV 파일을 선택하십시오.", type=["csv"]
    )

    if uploaded_file is not None:
        file_path = os.path.join(DATA_DIR, uploaded_file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.info(f"파일이 성공적으로 서버에 적재되었습니다. [저장 경로: {file_path}]")

            df = pd.read_csv(file_path)
            st.markdown(f"**업로드 데이터 미리보기 (총 {len(df):,}행 감지됨)**")
            st.dataframe(df.head(), use_container_width=True)
            st.rerun()  # 상단 대시보드 즉시 갱신
        except Exception as e:
            st.error(f"파일 저장 및 읽기 중 치명적 오류가 발생했습니다: {e}")

    st.markdown("---")

    # ── 샘플 고객 목록 ──────────────────────────────────────────────────────
    st.subheader("현재 관리 중인 고객 목록")
    st.caption("아래는 샘플 데이터입니다.")
    st.data_editor(MOCK_DATA, use_container_width=True, num_rows="dynamic")
