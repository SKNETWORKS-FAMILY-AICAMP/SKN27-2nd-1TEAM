import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
import os

# 데이터가 저장될 절대 경로 엄격히 지정 (00_data로 변경됨)
DATA_DIR = r"C:\dev\SKN27-2nd-1TEAM\00_data"

def render():
    st.title("고객 데이터베이스 관리")
    st.markdown("대량의 고객 데이터를 업로드하고, 물리적 저장소(00_data)에 안전하게 적재합니다.")
    
    # 00_data 디렉토리 존재성 검증 및 강제 생성 방어 로직
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"데이터 디렉토리 생성 실패. 관리자 권한을 확인하십시오: {e}")
            return
            
    st.subheader("신규 데이터 일괄 업로드 (CSV)")
    uploaded_file = st.file_uploader("배치(Batch) 예측을 수행할 CSV 파일을 선택하십시오.", type=["csv"])
    
    if uploaded_file is not None:
        # 업로드된 파일을 00_data 폴더에 물리적으로 기록하는 I/O 로직
        file_path = os.path.join(DATA_DIR, uploaded_file.name)
        
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.info(f"파일이 성공적으로 서버에 적재되었습니다. [저장 경로: {file_path}]")
            
            # 저장된 데이터 정합성 검증을 위한 헤더(Head) 출력
            df = pd.read_csv(file_path)
            st.markdown(f"**업로드 데이터 미리보기 (총 {len(df)}행 감지됨)**")
            st.dataframe(df.head(), use_container_width=True)
            
        except Exception as e:
            st.error(f"파일 저장 및 읽기 중 치명적 오류가 발생했습니다: {e}")
            
    st.markdown("---")
    st.subheader("현재 관리 중인 고객 목록 (Sample View)")
    
    # 향후 00_data의 실제 데이터를 불러오는 로직으로 확장하기 위한 Placeholder
    mock_data = pd.DataFrame({
        "Customer Name": ["홍길동", "이순신", "강감찬", "유관순", "장보고"],
        "Tenure": [12, 45, 2, 72, 5],
        "Contract": ["Month-to-month", "One year", "Month-to-month", "Two year", "Month-to-month"],
        "Monthly Charges": [85.5, 45.0, 95.0, 25.0, 80.0],
        "Risk Status": ["High Risk", "Safe", "High Risk", "Safe", "Warning"]
    })
    
    st.data_editor(mock_data, use_container_width=True, num_rows="dynamic")