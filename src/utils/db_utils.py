import os
import sqlite3
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'churn_predictions.db')


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id      TEXT,
            customer_name    TEXT,
            churn_prob       REAL,
            is_churn         INTEGER,
            contract         TEXT,
            internet         TEXT,
            monthly_charges  REAL,
            tenure_months    INTEGER,
            payment_method   TEXT,
            predicted_at     TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_prediction(customer_id, customer_name, churn_prob, is_churn,
                    contract='', internet='', monthly_charges=0.0,
                    tenure_months=0, payment_method=''):
    init_db()
    conn = get_conn()
    conn.execute('''
        INSERT INTO predictions
        (customer_id, customer_name, churn_prob, is_churn,
         contract, internet, monthly_charges, tenure_months,
         payment_method, predicted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (customer_id, customer_name, round(churn_prob,4), int(is_churn),
          contract, internet, monthly_charges, tenure_months, payment_method,
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()


def load_predictions(limit=500):
    init_db()
    conn = get_conn()
    df = pd.read_sql(f'''
        SELECT id,
            customer_id     AS "고객 ID",
            customer_name   AS "고객명",
            ROUND(churn_prob*100,1) AS "이탈 확률(%)",
            CASE WHEN is_churn=1 THEN "⚠️ 위험" ELSE "✅ 안전" END AS "이탈 위험",
            contract        AS "계약 유형",
            internet        AS "인터넷",
            monthly_charges AS "월 요금($)",
            tenure_months   AS "이용기간(월)",
            payment_method  AS "결제 방식",
            predicted_at    AS "예측 시간"
        FROM predictions ORDER BY id DESC LIMIT {limit}
    ''', conn)
    conn.close()
    return df


def get_stats():
    init_db()
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM predictions')
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM predictions WHERE is_churn=1')
    churned = cur.fetchone()[0]
    cur.execute('SELECT AVG(churn_prob) FROM predictions')
    avg = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM predictions WHERE predicted_at >= datetime('now','-1 day','localtime')")
    today = cur.fetchone()[0]
    conn.close()
    return {
        'total': total, 'churned': churned,
        'avg_prob': round(avg*100,1), 'today': today,
        'churn_rate': round(churned/total*100,1) if total > 0 else 0
    }
