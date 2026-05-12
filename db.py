import sqlite3
import datetime

DB_NAME = "audit.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            invoice_no TEXT,
            client_name TEXT,
            amount_due REAL,
            days_overdue INTEGER,
            followup_count INTEGER,
            tone_stage INTEGER,
            subject TEXT,
            body_preview TEXT,
            send_status TEXT,
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_email(invoice_no: str, client_name: str, amount_due: float, days_overdue: int, followup_count: int, tone_stage: int, subject: str, body_preview: str, send_status: str, error_message: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO email_audit (timestamp, invoice_no, client_name, amount_due, days_overdue, followup_count, tone_stage, subject, body_preview, send_status, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (timestamp, invoice_no, client_name, amount_due, days_overdue, followup_count, tone_stage, subject, body_preview, send_status, error_message)
    )
    conn.commit()
    conn.close()
