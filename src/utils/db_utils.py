# =============================================================
# src/utils/db_utils.py
# 모든 DB 연결/조회/저장/수정 함수 통합 관리
# 각 페이지에서는 이 파일만 import해서 사용하세요
# =============================================================

import os
import pymysql
import pandas as pd
from datetime import datetime

DB_CONFIG = {
    'host'       : os.environ.get('DB_HOST',     '127.0.0.1'),
    'port'       : int(os.environ.get('DB_PORT', 3307)),
    'user'       : os.environ.get('DB_USER',     'root'),
    'password'   : os.environ.get('DB_PASSWORD', '1234'),
    'database'   : os.environ.get('DB_NAME',     'churn_db'),
    'charset'    : 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_conn():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None


def init_db():
    conn = get_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id               INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id      VARCHAR(50),
                    customer_name    VARCHAR(100),
                    churn_prob       FLOAT,
                    is_churn         TINYINT,
                    contract         VARCHAR(50),
                    internet         VARCHAR(50),
                    monthly_charges  FLOAT,
                    tenure_months    INT,
                    payment_method   VARCHAR(100),
                    predicted_at     DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id VARCHAR(50),
                    churn_prob  FLOAT,
                    alert_type  VARCHAR(50)  DEFAULT '이메일',
                    sent_to     VARCHAR(100),
                    is_sent     TINYINT      DEFAULT 0,
                    sent_by     VARCHAR(100) DEFAULT '담당자',
                    note        TEXT,
                    sent_at     DATETIME     DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS campaigns (
                    id            INT AUTO_INCREMENT PRIMARY KEY,
                    campaign_name VARCHAR(100),
                    campaign_type VARCHAR(100),
                    target_count  INT   DEFAULT 0,
                    discount_rate FLOAT DEFAULT 0,
                    cost_per      FLOAT DEFAULT 0,
                    status        VARCHAR(20) DEFAULT '진행중',
                    created_at    DATETIME    DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS campaign_targets (
                    id           INT AUTO_INCREMENT PRIMARY KEY,
                    campaign_id  INT,
                    customer_id  VARCHAR(50),
                    churn_prob   FLOAT,
                    action_taken VARCHAR(50) DEFAULT '미실행',
                    result       VARCHAR(50) DEFAULT '대기중',
                    updated_at   DATETIME    DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        conn.commit()
    finally:
        conn.close()


def get_tables() -> list:
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            return [list(t.values())[0] for t in cur.fetchall()]
    finally:
        conn.close()


def load_table(table_name: str) -> pd.DataFrame:
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM `{table_name}`")
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()


def save_prediction(customer_id, customer_name, churn_prob, is_churn,
                    contract='', internet='', monthly_charges=0.0,
                    tenure_months=0, payment_method='') -> bool:
    conn = get_conn()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO predictions
                (customer_id, customer_name, churn_prob, is_churn,
                 contract, internet, monthly_charges, tenure_months,
                 payment_method, predicted_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''', (customer_id, customer_name,
                  round(float(churn_prob), 4), int(is_churn),
                  contract, internet, float(monthly_charges),
                  int(tenure_months), payment_method,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except Exception as e:
        print(f"예측 저장 실패: {e}")
        return False
    finally:
        conn.close()


def load_predictions(limit=500) -> pd.DataFrame:
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT customer_id, customer_name,
                       ROUND(churn_prob*100,1) AS churn_pct,
                       is_churn, contract, internet,
                       monthly_charges, tenure_months,
                       payment_method, predicted_at
                FROM predictions ORDER BY id DESC LIMIT {limit}
            """)
            rows = cur.fetchall()
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df = df.rename(columns={
            'customer_id'    : '고객 ID',
            'customer_name'  : '고객명',
            'churn_pct'      : '이탈 확률(%)',
            'contract'       : '계약 유형',
            'internet'       : '인터넷',
            'monthly_charges': '월 요금($)',
            'tenure_months'  : '이용기간(월)',
            'payment_method' : '결제 방식',
            'predicted_at'   : '예측 시간',
        })
        df['이탈 위험'] = df['is_churn'].apply(lambda x: '⚠️ 위험' if x==1 else '✅ 안전')
        return df.drop(columns=['is_churn'])
    finally:
        conn.close()


def load_predictions_raw(limit=500) -> pd.DataFrame:
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT customer_id, customer_name, churn_prob,
                       is_churn, contract, internet,
                       monthly_charges, tenure_months,
                       payment_method, predicted_at
                FROM predictions ORDER BY id DESC LIMIT {limit}
            """)
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_conn()
    if not conn: return {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as v FROM predictions")
            total = cur.fetchone()['v']
            cur.execute("SELECT COUNT(*) as v FROM predictions WHERE is_churn=1")
            churned = cur.fetchone()['v']
            cur.execute("SELECT AVG(churn_prob) as v FROM predictions")
            avg = cur.fetchone()['v'] or 0
            cur.execute("SELECT COUNT(*) as v FROM predictions WHERE DATE(predicted_at)=CURDATE()")
            today = cur.fetchone()['v']
        return {
            'total'  : total,
            'churned': churned,
            'avg'    : round(avg*100, 1),
            'today'  : today,
            'rate'   : round(churned/total*100, 1) if total > 0 else 0
        }
    finally:
        conn.close()


def get_customer_predictions(customer_id: str) -> pd.DataFrame:
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT churn_prob, is_churn, contract, internet,
                       monthly_charges, tenure_months, payment_method, predicted_at
                FROM predictions WHERE customer_id=%s
                ORDER BY predicted_at DESC
            """, (customer_id,))
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()


def save_alert(customer_id, churn_prob, sent_to, is_sent,
               sent_by='담당자', note='') -> bool:
    conn = get_conn()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alerts
                (customer_id, churn_prob, alert_type, sent_to,
                 is_sent, sent_by, note, sent_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (customer_id, churn_prob, '이메일', sent_to,
                  1 if is_sent else 0, sent_by, note,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except Exception as e:
        print(f"알림 저장 실패: {e}")
        return False
    finally:
        conn.close()


def load_alerts(limit=200) -> pd.DataFrame:
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT customer_id, churn_prob, alert_type,
                       sent_to, is_sent, sent_by, note, sent_at
                FROM alerts ORDER BY sent_at DESC LIMIT {limit}
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


def create_campaign(name, ctype, target_count, discount_rate, cost_per) -> bool:
    conn = get_conn()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO campaigns
                (campaign_name, campaign_type, target_count,
                 discount_rate, cost_per, status, created_at)
                VALUES (%s,%s,%s,%s,%s,'진행중',%s)
            """, (name, ctype, target_count, discount_rate, cost_per,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except Exception as e:
        print(f"캠페인 저장 실패: {e}")
        return False
    finally:
        conn.close()


def load_campaigns() -> pd.DataFrame:
    conn = get_conn()
    if not conn: return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()


def update_campaign_status(campaign_id: int, status: str) -> bool:
    conn = get_conn()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE campaigns SET status=%s WHERE id=%s",
                        (status, campaign_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"캠페인 상태 업데이트 실패: {e}")
        return False
    finally:
        conn.close()


def insert_customer(data: dict, table_name: str) -> bool:
    conn = get_conn()
    if not conn: return False
    try:
        cols = ', '.join([f'`{k}`' for k in data.keys()])
        vals = ', '.join(['%s'] * len(data))
        with conn.cursor() as cur:
            cur.execute(f"INSERT INTO `{table_name}` ({cols}) VALUES ({vals})",
                        list(data.values()))
        conn.commit()
        return True
    except Exception as e:
        print(f"고객 등록 실패: {e}")
        return False
    finally:
        conn.close()


def update_customer(customer_id: str, data: dict,
                    table_name: str, id_col: str) -> bool:
    conn = get_conn()
    if not conn: return False
    try:
        set_clause = ', '.join([f'`{k}`=%s' for k in data.keys()])
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE `{table_name}` SET {set_clause} WHERE `{id_col}`=%s",
                list(data.values()) + [customer_id]
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"고객 수정 실패: {e}")
        return False
    finally:
        conn.close()