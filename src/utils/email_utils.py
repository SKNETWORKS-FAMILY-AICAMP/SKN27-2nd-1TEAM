import smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST     = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER     = os.environ.get('SMTP_USER',     '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
ALERT_TO      = os.environ.get('ALERT_TO',      '')

print(f"[email_utils] SMTP_USER={SMTP_USER}, SMTP_HOST={SMTP_HOST}:{SMTP_PORT}")


def send_alert_bulk(customers, to_email, sender_name='담당자', note=''):
    """여러 고객을 이메일 1개로 한번에 발송"""
    recipient = to_email or ALERT_TO
    if not all([SMTP_USER, SMTP_PASSWORD, recipient]):
        print("SMTP 설정 누락 — .env 파일을 확인하세요.")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'[이탈 위험] 위험 고객 {len(customers)}명 감지'
        msg['From']    = SMTP_USER
        msg['To']      = recipient

        rows_html = ''
        for c in customers:
            rows_html += f"""
            <tr>
                <td>{c['customer_id']}</td>
                <td style="color:#F44336;"><b>{c['churn_prob']*100:.1f}%</b></td>
                <td>{c.get('contract','')}</td>
                <td>${float(c.get('monthly_charges',0)):.2f}</td>
                <td>{int(c.get('tenure_months',0))}개월</td>
            </tr>"""

        note_section = f"<p><b>메모:</b> {note}</p>" if note else ""

        html = f"""
        <h2 style="color:#F44336;">⚠️ 이탈 위험 고객 {len(customers)}명 감지</h2>
        <p>발송자: {sender_name} | 감지 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        {note_section}
        <table border="1" cellpadding="8" style="border-collapse:collapse; width:100%;">
            <thead style="background:#F44336; color:white;">
                <tr>
                    <th>고객 ID</th>
                    <th>이탈 확률</th>
                    <th>계약 유형</th>
                    <th>월 요금</th>
                    <th>이용 기간</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        <p><b>권장 조치:</b> 즉시 장기 계약 전환 유도 연락</p>
        """
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            print(f"[SMTP] 로그인 시도: {SMTP_USER}")
            s.login(SMTP_USER, SMTP_PASSWORD)
            print(f"[SMTP] 로그인 성공")
            s.sendmail(SMTP_USER, recipient, msg.as_string())
            print(f"[SMTP] 일괄 발송 완료 → {recipient} ({len(customers)}명)")
        return True
    except Exception as e:
        print(f"[SMTP] 이메일 발송 실패: {e}")
        return False


def send_alert(customer_name, customer_id, churn_prob,
               contract, monthly_charges, tenure_months,
               to_email=None, note=''):
    recipient = to_email or ALERT_TO
    if not all([SMTP_USER, SMTP_PASSWORD, recipient]):
        print("SMTP 설정 누락 — .env 파일을 확인하세요.")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'[이탈 위험] {customer_name} — {churn_prob*100:.1f}%'
        msg['From']    = SMTP_USER
        msg['To']      = recipient
        note_row = f"<tr><td>메모</td><td><b>{note}</b></td></tr>" if note else ""
        html = f"""
        <h2 style="color:#F44336;">⚠️ 이탈 위험 고객 감지</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse;">
            <tr><td>고객명</td><td><b>{customer_name}</b></td></tr>
            <tr><td>고객 ID</td><td>{customer_id}</td></tr>
            <tr><td>이탈 확률</td><td style="color:#F44336;"><b>{churn_prob*100:.1f}%</b></td></tr>
            <tr><td>계약 유형</td><td>{contract}</td></tr>
            <tr><td>월 요금</td><td>${monthly_charges:.2f}</td></tr>
            <tr><td>이용 기간</td><td>{tenure_months}개월</td></tr>
            <tr><td>감지 시간</td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            {note_row}
        </table>
        <p><b>권장 조치:</b> 즉시 장기 계약 전환 유도 연락</p>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            print(f"[SMTP] 로그인 시도: {SMTP_USER}")
            s.login(SMTP_USER, SMTP_PASSWORD)
            print(f"[SMTP] 로그인 성공")
            s.sendmail(SMTP_USER, recipient, msg.as_string())
            print(f"[SMTP] 발송 완료 → {recipient}")
        return True
    except Exception as e:
        print(f"[SMTP] 이메일 발송 실패: {e}")
        return False