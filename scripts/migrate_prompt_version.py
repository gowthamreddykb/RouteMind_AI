import pymysql
import sqlite3
import os

# 1. MySQL Migration
try:
    conn = pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='gowtham@69',
        database='routemind_db',
        autocommit=True
    )
    cur = conn.cursor()

    # communication_logs
    cur.execute("SHOW TABLES LIKE 'communication_logs';")
    if cur.fetchone():
        cur.execute("SHOW COLUMNS FROM communication_logs LIKE 'prompt_version';")
        if not cur.fetchone():
            cur.execute("ALTER TABLE communication_logs ADD COLUMN prompt_version VARCHAR(50) NOT NULL DEFAULT 'v1.0.0';")
            print("Added prompt_version to communication_logs in MySQL.")
        else:
            print("prompt_version already exists in communication_logs (MySQL).")

    # communications
    cur.execute("SHOW TABLES LIKE 'communications';")
    if not cur.fetchone():
        cur.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            communication_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            exception_id BIGINT NOT NULL,
            action_id BIGINT NULL,
            audience VARCHAR(30) NOT NULL DEFAULT 'CUSTOMER',
            communication_type VARCHAR(50) NOT NULL DEFAULT 'CUSTOMER_UPDATE',
            subject VARCHAR(255) NOT NULL,
            generated_draft TEXT NOT NULL,
            final_text TEXT NULL,
            ai_model_name VARCHAR(100) NULL DEFAULT 'RouteMind-GenAI-v1',
            prompt_version VARCHAR(50) NOT NULL DEFAULT 'v1.0.0',
            approval_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            created_by INT NULL,
            approved_by INT NULL,
            approved_at DATETIME NULL,
            delivery_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_comm_exception (exception_id),
            INDEX idx_comm_status (delivery_status)
        );
        """)
        print("Created communications table in MySQL with prompt_version.")
    else:
        cur.execute("SHOW COLUMNS FROM communications LIKE 'prompt_version';")
        if not cur.fetchone():
            cur.execute("ALTER TABLE communications ADD COLUMN prompt_version VARCHAR(50) NOT NULL DEFAULT 'v1.0.0';")
            print("Added prompt_version to communications table in MySQL.")
        else:
            print("prompt_version already exists in communications (MySQL).")
    conn.close()
except Exception as e:
    print("MySQL migration note:", e)

# 2. SQLite Migration
sqlite_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "routemind_control_tower.db"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "routemind.db"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_routemind.db"),
]

for p in sqlite_paths:
    if os.path.exists(p):
        try:
            s_conn = sqlite3.connect(p)
            s_cur = s_conn.cursor()
            # check communications
            s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='communications';")
            if s_cur.fetchone():
                s_cur.execute("PRAGMA table_info(communications);")
                cols = [c[1] for c in s_cur.fetchall()]
                if 'prompt_version' not in cols:
                    s_cur.execute("ALTER TABLE communications ADD COLUMN prompt_version TEXT NOT NULL DEFAULT 'v1.0.0';")
                    print(f"Added prompt_version to communications in {p}.")
            # check communication_logs
            s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='communication_logs';")
            if s_cur.fetchone():
                s_cur.execute("PRAGMA table_info(communication_logs);")
                cols = [c[1] for c in s_cur.fetchall()]
                if 'prompt_version' not in cols:
                    s_cur.execute("ALTER TABLE communication_logs ADD COLUMN prompt_version TEXT NOT NULL DEFAULT 'v1.0.0';")
                    print(f"Added prompt_version to communication_logs in {p}.")
            s_conn.commit()
            s_conn.close()
        except Exception as se:
            print(f"SQLite migration note for {p}:", se)

print("Database prompt_version migration completed successfully.")
