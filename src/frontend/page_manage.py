import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
from ml_utils import load_ml_objects, predict_churn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def render():
    st.title('📂 고객 데이터 관리')
    st.caption('CSV 파일을 업로드하여 전체 고객 배치 예측을 수행합니다.')

    os.makedirs(DATA_DIR, exist_ok=True)

    uploaded = st.file_uploader('CSV 파일 업로드', type=['csv'])

    if uploaded:
        path = os.path.join(DATA_DIR, uploaded.name)
        with open(path, 'wb') as f:
            f.write(uploaded.getbuffer())
        st.success(f'업로드 완료: {uploaded.name}')

        df = pd.read_csv(path)
        st.markdown(f'**미리보기 (총 {len(df):,}행)**')
        st.dataframe(df.head(), use_container_width=True)

        if st.button('🚀 전체 고객 이탈 예측 실행', type='primary'):
            model, scaler, feature_cols = load_ml_objects()
            if model is None:
                st.error('모델 파일이 없습니다. 03_model.py를 먼저 실행하세요.')
                return

            results = []
            progress = st.progress(0)
            for i, (_, row) in enumerate(df.iterrows()):
                try:
                    inp = pd.DataFrame([row])
                    inp['Total Charges'] = pd.to_numeric(inp.get('Total Charges', 0), errors='coerce').fillna(0)
                    prob, is_churn = predict_churn(inp, model, scaler, feature_cols)
                    results.append({
                        'CustomerID'  : row.get('CustomerID', f'고객{i+1}'),
                        '이탈 확률(%)': round(prob*100,1),
                        '이탈 위험'   : '⚠️ 위험' if is_churn else '✅ 안전'
                    })
                except:
                    results.append({'CustomerID': row.get('CustomerID',f'고객{i+1}'),
                                    '이탈 확률(%)': '-','이탈 위험': '❓ 오류'})
                progress.progress((i+1)/len(df))

            rdf = pd.DataFrame(results)
            danger = rdf[rdf['이탈 위험']=='⚠️ 위험']

            c1,c2,c3 = st.columns(3)
            c1.metric('전체 고객',   f'{len(rdf):,}명')
            c2.metric('이탈 위험',   f'{len(danger):,}명')
            c3.metric('이탈률',      f'{len(danger)/len(rdf)*100:.1f}%')

            st.dataframe(rdf, use_container_width=True)
            csv = rdf.to_csv(index=False, encoding='utf-8-sig')
            st.download_button('📥 예측 결과 다운로드', csv, 'batch_result.csv', 'text/csv')

    st.markdown('---')
    st.subheader('현재 데이터 파일')
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if files:
        for f in files:
            size = os.path.getsize(os.path.join(DATA_DIR,f))/1024
            st.write(f'📄 `{f}` — {size:.1f} KB')
    else:
        st.info('data/ 폴더에 CSV 파일이 없습니다.')
