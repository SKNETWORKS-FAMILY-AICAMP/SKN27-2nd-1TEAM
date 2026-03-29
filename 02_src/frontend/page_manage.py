import streamlit as st
import pandas as pd
import os

# ✅ Fix 3: Windows 절대경로 하드코딩 제거 → 상대경로로 변경
# 이 파일 위치: 02_src/frontend/page_manage.py
# 00_data 위치: 프로젝트 루트/00_data/
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "00_data"))

def render():
    st.title("고객 데이터베이스 관리")
    st.markdown("대량의 고객 데이터를 업로드하고, 물리적 저장소(00_data)에 안전하게 적재합니다.")

    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"데이터 디렉토리 생성 실패. 관리자 권한을 확인하십시오: {e}")
            return

    st.subheader("신규 데이터 일괄 업로드 (CSV)")
    uploaded_file = st.file_uploader("배치(Batch) 예측을 수행할 CSV 파일을 선택하십시오.", type=["csv"])

    if uploaded_file is not None:
        file_path = os.path.join(DATA_DIR, uploaded_file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.info(f"파일이 성공적으로 서버에 적재되었습니다. [저장 경로: {file_path}]")

            df = pd.read_csv(file_path)
            st.markdown(f"**업로드 데이터 미리보기 (총 {len(df)}행 감지됨)**")
            st.dataframe(df.head(), use_container_width=True)

        except Exception as e:
            st.error(f"파일 저장 및 읽기 중 치명적 오류가 발생했습니다: {e}")

    st.markdown("---")
    st.subheader("현재 관리 중인 고객 목록")

    mock_data = pd.DataFrame({
        "Customer Name":  ["홍길동", "이순신", "강감찬", "유관순", "장보고"],
        "Tenure":         [12, 45, 2, 72, 5],
        "Contract":       ["Month-to-month", "One year", "Month-to-month", "Two year", "Month-to-month"],
        "Monthly Charges":[85.5, 45.0, 95.0, 25.0, 80.0],
        "Risk Status":    ["High Risk", "Safe", "High Risk", "Safe", "Warning"]
    })

    st.data_editor(mock_data, use_container_width=True, num_rows="dynamic")