import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import get_conn, load_predictions_raw
from email_utils import send_alert

def get_alerts():
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT customer_id, churn_prob, alert_type,
                       sent_to, is_sent, sent_by, note, sent_at
                FROM alerts
                ORDER BY sent_at DESC
                LIMIT 200
            """)
            rows = cur.fetchall()
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df = df.rename(columns={
            'customer_id': '고객 ID',
            'churn_prob' : '이탈 확률',
            'alert_type' : '알림 유형',
            'sent_to'    : '수신자',
            'is_sent'    : '발송 성공',
            'sent_by'    : '발송자',
            'note'       : '메모',
            'sent_at'    : '발송 시간',
        })
        df['이탈 확률'] = (df['이탈 확률']*100).round(1).astype(str) + '%'
        df['발송 성공'] = df['발송 성공'].apply(lambda x: '✅ 성공' if x==1 else '❌ 실패')
        return df
    finally:
        conn.close()

def save_alert(customer_id, churn_prob, sent_to, is_sent, sent_by, note=''):
    conn = get_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alerts
                (customer_id, churn_prob, alert_type, sent_to, is_sent, sent_by, note, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (customer_id, churn_prob, '이메일', sent_to,
                  1 if is_sent else 0, sent_by, note,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    finally:
        conn.close()

def render():
    st.title("🔔 알림 센터")
    st.caption("이탈 위험 고객 알림 발송 및 이메일 발송 이력을 관리합니다.")

    tab1, tab2 = st.tabs(["⚠️ 위험 고객 알림 발송", "📧 이메일 발송 이력"])

    # ── TAB 1: 알림 발송 ──────────────────────────
    with tab1:
        st.subheader("이탈 위험 고객 목록")

        df_raw = load_predictions_raw(limit=500)
        if df_raw.empty:
            st.info("예측 이력이 없습니다. 실시간 예측 페이지에서 먼저 분석하세요.")
            return

        df_raw['churn_prob'] = df_raw['churn_prob'].astype(float)
        df_high = df_raw[df_raw['churn_prob'] >= 0.5].sort_values('churn_prob', ascending=False)

        if df_high.empty:
            st.success("현재 이탈 위험 고객이 없습니다.")
            return

        st.markdown(f"**총 {len(df_high):,}명의 이탈 위험 고객**")

        # 알림 설정
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1: recv_email = st.text_input("수신자 이메일", placeholder="manager@company.com")
        with col2: sender_name = st.text_input("발송자 이름", placeholder="홍길동")
        with col3: threshold  = st.slider("알림 기준 이탈 확률(%)", 50, 90, 70)

        df_target = df_high[df_high['churn_prob'] >= threshold/100]
        st.info(f"기준 적용 시 대상 고객: **{len(df_target):,}명**")

        # 고객 목록 표시
        df_show = df_target[['customer_id','churn_prob','contract','internet','monthly_charges']].copy()
        df_show['churn_prob'] = (df_show['churn_prob']*100).round(1).astype(str) + '%'
        df_show.columns = ['고객 ID','이탈 확률','계약 유형','인터넷','월 요금($)']
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("📧 전체 알림 일괄 발송", type="primary", use_container_width=True):
                if not recv_email:
                    st.error("수신자 이메일을 입력하세요.")
                else:
                    success = 0
                    with st.spinner(f"{len(df_target)}명 알림 발송 중..."):
                        for _, row in df_target.iterrows():
                            ok = send_alert(
                                customer_name=row['customer_id'],
                                customer_id=row['customer_id'],
                                churn_prob=float(row['churn_prob']),
                                contract=row.get('contract',''),
                                monthly_charges=float(row.get('monthly_charges',0)),
                                tenure_months=int(row.get('tenure_months',0)),
                                to_email=recv_email
                            )
                            save_alert(
                                customer_id=row['customer_id'],
                                churn_prob=float(row['churn_prob']),
                                sent_to=recv_email,
                                is_sent=ok,
                                sent_by=sender_name or '담당자'
                            )
                            if ok: success += 1
                    st.success(f"✅ {success}/{len(df_target)}건 발송 완료!")

        with col_b:
            note = st.text_input("메모 (선택)", placeholder="긴급 리텐션 캠페인 대상")
            if st.button("📋 발송 없이 이력만 기록", use_container_width=True):
                for _, row in df_target.iterrows():
                    save_alert(
                        customer_id=row['customer_id'],
                        churn_prob=float(row['churn_prob']),
                        sent_to=recv_email or '-',
                        is_sent=False,
                        sent_by=sender_name or '담당자',
                        note=note
                    )
                st.success("✅ 이력이 기록되었습니다.")

    # ── TAB 2: 발송 이력 ──────────────────────────
    with tab2:
        st.subheader("이메일 발송 이력")

        df_alerts = get_alerts()
        if df_alerts.empty:
            st.info("발송 이력이 없습니다.")
            return

        total    = len(df_alerts)
        success  = len(df_alerts[df_alerts['발송 성공'] == '✅ 성공'])
        fail     = total - success

        c1, c2, c3 = st.columns(3)
        c1.metric("총 발송 건수", f"{total:,}건")
        c2.metric("발송 성공",   f"{success:,}건")
        c3.metric("발송 실패",   f"{fail:,}건", delta=f"{fail}건 재확인 필요" if fail > 0 else None, delta_color='inverse')

        st.markdown("---")

        # 필터
        col_f1, col_f2 = st.columns(2)
        with col_f1: status_f = st.selectbox("발송 상태", ["전체", "✅ 성공만", "❌ 실패만"])
        with col_f2: search   = st.text_input("고객 ID 검색")

        df_show = df_alerts.copy()
        if status_f == "✅ 성공만": df_show = df_show[df_show['발송 성공'] == '✅ 성공']
        elif status_f == "❌ 실패만": df_show = df_show[df_show['발송 성공'] == '❌ 실패']
        if search: df_show = df_show[df_show['고객 ID'].astype(str).str.contains(search, na=False)]

        st.dataframe(df_show, use_container_width=True, hide_index=True)

        csv = df_show.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 발송 이력 다운로드", csv, "alert_history.csv", "text/csv")
