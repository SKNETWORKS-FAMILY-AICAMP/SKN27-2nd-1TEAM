import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'utils'))

import streamlit as st
from db_utils import get_stats, load_predictions


def render():
    st.title("📋 예측 이력 조회")
    st.caption("저장된 예측 결과를 조회하고 분석합니다.")

    stats = get_stats()

    if not stats or stats['total'] == 0:
        st.info("아직 예측 이력이 없습니다. 실시간 예측 페이지에서 고객을 분석해보세요!")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 예측 수",     f"{stats['total']:,}건")
    c2.metric("이탈 위험 감지", f"{stats['churned']:,}명")
    c3.metric("이탈 감지율",    f"{stats['rate']}%")
    c4.metric("오늘 예측",      f"{stats['today']:,}건")

    st.markdown("---")
    st.subheader("🔍 필터")

    col1, col2, col3 = st.columns(3)
    with col1: risk_f = st.selectbox("위험 상태", ["전체", "⚠️ 위험만", "✅ 안전만"])
    with col2: prob_r = st.slider("이탈 확률 범위(%)", 0, 100, (0, 100))
    with col3: search = st.text_input("고객 ID / 고객명 검색")

    df = load_predictions(limit=1000)
    if df.empty:
        st.warning("조회된 데이터가 없습니다.")
        return

    df_show = df.copy()
    if risk_f == "⚠️ 위험만":  df_show = df_show[df_show["이탈 위험"] == "⚠️ 위험"]
    elif risk_f == "✅ 안전만": df_show = df_show[df_show["이탈 위험"] == "✅ 안전"]
    df_show = df_show[df_show["이탈 확률(%)"].between(*prob_r)]
    if search:
        mask = (df_show["고객 ID"].astype(str).str.contains(search, na=False) |
                df_show["고객명"].astype(str).str.contains(search, na=False))
        df_show = df_show[mask]

    st.markdown(f"**검색 결과: {len(df_show):,}건**")
    st.dataframe(df_show, use_container_width=True)

    csv = df_show.to_csv(index=False, encoding='utf-8-sig')
    st.download_button("📥 이력 다운로드 (CSV)", csv, "prediction_history.csv", "text/csv")
