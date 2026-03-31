# =============================================================
# src/utils/db_utils.py — MySQL DB 연결 및 쿼리 유틸리티
# 모든 페이지에서 이 파일을 import해서 사용하세요.
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
    """MySQL 연결 반환 — 모든 페이지에서 공통으로 사용"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None


def init_db():
    """predictions 테이블 생성 (없으면 자동 생성)"""
    conn = get_conn()
    if not conn:
        return
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
        conn.commit()
    finally:
        conn.close()


def save_prediction(customer_id, customer_name, churn_prob, is_churn,
                    contract='', internet='', monthly_charges=0.0,
                    tenure_months=0, payment_method=''):
    """예측 결과 DB 저장"""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO predictions
                (customer_id, customer_name, churn_prob, is_churn,
                 contract, internet, monthly_charges, tenure_months,
                 payment_method, predicted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                customer_id, customer_name,
                round(float(churn_prob), 4),
                int(is_churn),
                contract, internet,
                float(monthly_charges),
                int(tenure_months),
                payment_method,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"저장 실패: {e}")
        return False
    finally:
        conn.close()


def load_predictions(limit=500) -> pd.DataFrame:
    """예측 이력 조회"""
    conn = get_conn()
    if not conn:
        return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT customer_id, customer_name,
                       ROUND(churn_prob*100,1) AS churn_pct,
                       is_churn, contract, internet,
                       monthly_charges, tenure_months,
                       payment_method, predicted_at
                FROM predictions
                ORDER BY id DESC
                LIMIT {limit}
            """)
            rows = cur.fetchall()
        if not rows:
            return pd.DataFrame()
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
        df['이탈 위험'] = df['is_churn'].apply(
            lambda x: '⚠️ 위험' if x == 1 else '✅ 안전'
        )
        df = df.drop(columns=['is_churn'])
        return df
    except Exception as e:
        print(f"조회 실패: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def load_predictions_raw(limit=500) -> pd.DataFrame:
    """예측 이력 원본 조회 (차트용)"""
    conn = get_conn()
    if not conn:
        return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT customer_id, customer_name, churn_prob,
                       is_churn, contract, internet,
                       monthly_charges, tenure_months,
                       payment_method, predicted_at
                FROM predictions
                ORDER BY id DESC
                LIMIT {limit}
            """)
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()


def get_stats() -> dict:
    """대시보드용 요약 통계"""
    conn = get_conn()
    if not conn:
        return {}
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
            'avg'    : round(avg * 100, 1),
            'today'  : today,
            'rate'   : round(churned / total * 100, 1) if total > 0 else 0
        }
    finally:
        conn.close()


def get_tables() -> list:
    """churn_db 테이블 목록 조회"""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            return [list(t.values())[0] for t in tables]
    finally:
        conn.close()


def load_table(table_name: str) -> pd.DataFrame:
    """특정 테이블 전체 조회"""
    conn = get_conn()
    if not conn:
        return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM `{table_name}`")
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    finally:
        conn.close()