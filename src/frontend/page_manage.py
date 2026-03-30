import streamlit as st
import pandas as pd
import numpy as np
import os
from ml_utils import load_ml_objects, create_engineered_features

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "00_data"))

@st.cache_data(show_spinner=False)
def get_batch_predictions(file_path):
    df = pd.read_csv(file_path)
    model, encoder, scaler, model_columns, optimal_threshold = load_ml_objects()
    if model is None:
        return None
        
    id_col = None
    for c in df.columns:
        if c.lower() == 'customerid':
            id_col = c
            break
            
    if id_col is None:
        st.error("데이터에 'CustomerID' 형식의 컬럼이 없습니다.")
        return None
        
    processed_df = create_engineered_features(df, model_columns=model_columns)
    processed_df = processed_df[model_columns]
    encoded_data = encoder.transform(processed_df).astype('float64')
    scaled_input = scaler.transform(encoded_data)
    probs = model.predict_proba(scaled_input)[:, 1]
    
    res_df = df[[id_col]].copy()
    res_df.rename(columns={id_col: 'Customer ID'}, inplace=True)
    
    if 'Tenure Months' in df.columns:
        res_df['Tenure Months'] = df['Tenure Months']
    if 'Contract' in df.columns:
        res_df['Contract'] = df['Contract']
    if 'Monthly Charges' in df.columns:
        res_df['Monthly Charges'] = df['Monthly Charges']
        
    res_df['Churn Probability (%)'] = np.round(probs * 100, 2)
    
    def prioritize_risk(p):
        if p >= 0.70:
            return "High Risk"
        elif p >= optimal_threshold:  # 0.3906 근방
            return "Warning"
        else:
            return "Safe"
            
    res_df['Risk Status'] = [prioritize_risk(p) for p in probs]
    return res_df

def render():
    st.title("고객 데이터베이스 관리")
    st.markdown("신규 고객 데이터를 업로드하거나, 현재 관리 중인 고객 목록의 위험률을 일괄 분석합니다.")
    
    # 차트를 최하단으로 이동
    
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except Exception as e:
            st.error(f"데이터 디렉토리 생성 실패: {e}")
            return
            
    st.subheader("신규 데이터 일괄 업로드 (CSV)")
    uploaded_file = st.file_uploader("배치(Batch) 예측을 수행할 CSV 파일을 선택하십시오.", type=["csv"])
    
    newly_uploaded_path = None
    
    if uploaded_file is not None:
        file_path = os.path.join(DATA_DIR, uploaded_file.name)
        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"파일이 성공적으로 서버에 적재되었습니다: {uploaded_file.name}")
            newly_uploaded_path = file_path
        except Exception as e:
            st.error(f"파일 저장 오류: {e}")
            
    st.markdown("---")
    st.subheader("현재 관리 중인 고객 목록")
    
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []
    
    default_idx = 0
    if newly_uploaded_path:
        uploaded_name = os.path.basename(newly_uploaded_path)
        if uploaded_name in csv_files:
            default_idx = csv_files.index(uploaded_name)
    
    selected_file = None
    if csv_files:
        st.markdown("로컬 스토리지에 적재된 데이터를 불러옵니다. (CSV 업로드 시 자동으로 해당 데이터가 선택됩니다.)")
        selected_file = st.selectbox("조회할 데이터셋 선택", ["가짜 고객 데이터 (Mock)"] + csv_files, index=0 if not newly_uploaded_path else default_idx + 1)
    else:
        st.info("업로드된 CSV 파일이 없습니다. 데모용(Mock) 가짜 고객 데이터를 표시합니다.")
        selected_file = "가짜 고객 데이터 (Mock)"
        
    def render_pie_chart(df):
        if df.empty: return
        import matplotlib.pyplot as plt
        import platform
        if platform.system() == 'Windows':
            plt.rc('font', family='Malgun Gothic')
        elif platform.system() == 'Darwin':
            plt.rc('font', family='AppleGothic')
        else:
            plt.rc('font', family='NanumGothic')
            
        risk_counts = df['Risk Status'].value_counts()
        color_map = {
            "High Risk": "#ff4b4b",
            "Warning": "#ffcc00",
            "Safe": "#2ecc71"
        }
        colors = [color_map.get(k, '#999999') for k in risk_counts.index]
        
        st.markdown("### 📈 전체 현황 요약 (현재 필터 반영)")
        c1, c2 = st.columns([1, 2])
        with c1:
            fig, ax = plt.subplots(figsize=(4, 4))
            ax.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%', 
                   colors=colors, startangle=90, pctdistance=0.75, textprops={'fontsize': 10, 'weight': 'bold'},
                   wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
            
            centre_circle = plt.Circle((0,0), 0.55, fc='white')
            fig.gca().add_artist(centre_circle)
            ax.axis('equal')
            fig.patch.set_alpha(0.0) 
            st.pyplot(fig)
            
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.info("좌측 차트는 상단에 설정된 데이터셋 및 필터 기준에 부합하는 고객들의 전체적인 **리스크 그룹 상태**를 시각화합니다.")
            st.write(f"- 집계 대상: **총 {len(df):,}명**")
            for k, v in risk_counts.items():
                st.write(f"  - **{k}**: {v:,}명")
        
        st.markdown("---")

    if selected_file == "가짜 고객 데이터 (Mock)" or not selected_file:
        mock_data = pd.DataFrame({
            "Customer ID": ["MOCK-0001", "MOCK-0002", "MOCK-0003", "MOCK-0004", "MOCK-0005"],
            "Tenure Months": [12, 45, 2, 72, 5],
            "Contract": ["Month-to-month", "One year", "Month-to-month", "Two year", "Month-to-month"],
            "Monthly Charges": [85.5, 45.0, 95.0, 25.0, 80.0],
            "Churn Probability (%)": [88.5, 12.0, 65.2, 5.5, 59.0],
            "Risk Status": ["High Risk", "Safe", "Warning", "Safe", "Warning"]
        })
        
        col_search, col_filter = st.columns(2)
        with col_search:
            search_id = st.text_input("🔍 Customer ID 검색", placeholder="예: MOCK-0001", key="mock_search")
        with col_filter:
            status_filter = st.multiselect("📊 위험 여부(Risk Status)", ["High Risk", "Warning", "Safe"], default=["High Risk", "Warning", "Safe"], key="mock_filter")
            
        filtered_mock = mock_data.copy()
        if search_id.strip():
            filtered_mock = filtered_mock[filtered_mock["Customer ID"].str.contains(search_id.strip(), case=False, na=False)]
        if status_filter:
            filtered_mock = filtered_mock[filtered_mock["Risk Status"].isin(status_filter)]
            
        # 차트는 하단에서 렌더링
            
        def color_risk_status(val):
            if val == "High Risk":
                return 'background-color: rgba(255, 75, 75, 0.2); color: #8B0000; font-weight: bold;'
            elif val == "Warning":
                return 'background-color: rgba(255, 204, 0, 0.2); color: #8B6508; font-weight: bold;'
            elif val == "Safe":
                return 'background-color: rgba(46, 204, 113, 0.2); color: #006400; font-weight: bold;'
            return ''
            
        styled_mock = filtered_mock.style.map(color_risk_status, subset=['Risk Status']) if hasattr(filtered_mock.style, 'map') else filtered_mock.style.applymap(color_risk_status, subset=['Risk Status'])
        st.dataframe(styled_mock, use_container_width=True)
        
        # 하단에 차트 삽입
        render_pie_chart(filtered_mock)
    else:
        target_path = os.path.join(DATA_DIR, selected_file)
        with st.spinner("빅데이터 기반 일괄 위험 여부 판별 중입니다. 잠시만 기다려주세요..."):
            ans_df = get_batch_predictions(target_path)
            
        if ans_df is not None:
            col_s, col_f = st.columns(2)
            with col_s:
                search_id = st.text_input("🔍 Customer ID 검색", placeholder="예: 3668-QPYBK", key="real_search")
            with col_f:
                status_filter = st.multiselect("📊 위험 여부(Risk Status)", ["High Risk", "Warning", "Safe"], default=["High Risk", "Warning", "Safe"], key="real_filter")
                
            disp_df = ans_df.copy()
            if search_id.strip():
                disp_df = disp_df[disp_df["Customer ID"].str.contains(search_id.strip(), case=False, na=False)]
            if status_filter:
                disp_df = disp_df[disp_df["Risk Status"].isin(status_filter)]
                
            st.success(f"**{selected_file}** 파일의 {len(ans_df):,}명 고객 위험도 생성이 완료되었습니다.")
            
            # 차트는 하단에서 렌더링
            
            def color_risk_status(val):
                if val == "High Risk":
                    return 'background-color: rgba(255, 75, 75, 0.2); color: #8B0000; font-weight: bold;'
                elif val == "Warning":
                    return 'background-color: rgba(255, 204, 0, 0.2); color: #8B6508; font-weight: bold;'
                elif val == "Safe":
                    return 'background-color: rgba(46, 204, 113, 0.2); color: #006400; font-weight: bold;'
                return ''
                
            styled_disp = disp_df.style.map(color_risk_status, subset=['Risk Status']) if hasattr(disp_df.style, 'map') else disp_df.style.applymap(color_risk_status, subset=['Risk Status'])
            st.dataframe(styled_disp, use_container_width=True)
            
            # 하단에 차트 삽입
            render_pie_chart(disp_df)