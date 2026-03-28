import streamlit as st
import pandas as pd

def render():
    st.title("고객 데이터베이스 관리")
    st.markdown("대량의 고객 데이터를 업로드하고, 기존 데이터를 관리 및 필터링할 수 있습니다.")
    
    st.subheader("신규 데이터 일괄 업로드 (CSV)")
    uploaded_file = st.file_uploader("업로드할 CSV 파일을 선택하십시오.", type=["csv"])
    if uploaded_file is not None:
        st.info("파일이 성공적으로 업로드되었습니다. 배치 예측을 수행할 수 있습니다.")
        
    st.markdown("---")
    st.subheader("현재 관리 중인 고객 목록 (Sample View)")
    
    mock_data = pd.DataFrame({
        "Customer Name": ["홍길동", "이순신", "강감찬", "유관순", "장보고"],
        "Tenure": [12, 45, 2, 72, 5],
        "Contract": ["Month-to-month", "One year", "Month-to-month", "Two year", "Month-to-month"],
        "Monthly Charges": [85.5, 45.0, 95.0, 25.0, 80.0],
        "Risk Status": ["High Risk", "Safe", "High Risk", "Safe", "Warning"]
    })
    st.data_editor(mock_data, use_container_width=True, num_rows="dynamic")