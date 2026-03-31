import smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST     = 'smtp.gmail.com'
SMTP_PORT     = 587
SMTP_USER     = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
ALERT_TO      = os.environ.get('ALERT_TO', '')


def send_alert(customer_name, customer_id, churn_prob,
               contract, monthly_charges, tenure_months, to_email=None):
    recipient = to_email or ALERT_TO
    if not all([SMTP_USER, SMTP_PASSWORD, recipient]):
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'[이탈 위험] {customer_name} — {churn_prob*100:.1f}%'
        msg['From']    = SMTP_USER
        msg['To']      = recipient
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
        </table>
        <p><b>권장 조치:</b> 즉시 리텐션 팀 연락 / 장기 계약 전환 유도</p>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, recipient, msg.as_string())
        return True
    except:
        return False
