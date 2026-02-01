import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "app/storage/cases.db"))


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
              case_id TEXT PRIMARY KEY,
              order_id TEXT NOT NULL,
              reason TEXT NOT NULL,
              customer_message TEXT,
              wants_store_credit INTEGER NOT NULL DEFAULT 0,
              photos_required INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,

              ai_decision_json TEXT,
              ai_audit_json TEXT,
              policy_citations_json TEXT,
              order_facts_json TEXT,

              photo_urls_json TEXT,

              human_decision TEXT,
              human_notes TEXT,
              reviewed_at TEXT,

              final_customer_reply TEXT,
              next_actions_json TEXT
            );
            """
        )
        # Migration-safe add for existing DBs that predate next_actions_json
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN next_actions_json TEXT")
        except sqlite3.OperationalError:
            pass