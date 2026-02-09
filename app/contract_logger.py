import sqlite3
import hashlib
import json
import os
import tempfile
from datetime import datetime

class ContractLogger:
    def __init__(self, db_path='database/contract_qa.db'):
        # Railway or Streamlit Cloud - use temp directory
        if os.path.exists("/mount/src") or os.environ.get("RAILWAY_ENVIRONMENT"):
            self.db_path = os.path.join(tempfile.gettempdir(), "contract_qa.db")
        else:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create database tables - Multi-contract version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Questions log with contract_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions_log (
                question_id TEXT PRIMARY KEY,
                user_hash TEXT,
                contract_id TEXT,
                timestamp TEXT,
                question_text TEXT,
                answer_text TEXT,
                status TEXT,
                category TEXT,
                response_time_seconds REAL
            )
        ''')

        conn.commit()
        conn.close()

    def log_question(self, question_text, answer_text, status, contract_id, response_time=None):
        """Log a question with contract ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        question_id = f"q_{datetime.now().timestamp()}"
        user_hash = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]
        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO questions_log 
            (question_id, user_hash, contract_id, timestamp, question_text, 
             answer_text, status, response_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (question_id, user_hash, contract_id, timestamp, question_text,
              answer_text, status, response_time))

        conn.commit()
        conn.close()

# Test
if __name__ == "__main__":
    print("="*70)
    print("TESTING MULTI-CONTRACT LOGGER")
    print("="*70)

    logger = ContractLogger()
    print("✓ Database initialized")

    logger.log_question(
        question_text="Test question",
        answer_text="Test answer",
        status="CLEAR",
        contract_id="NAC",
        response_time=2.5
    )
    print("✓ Question logged successfully for NAC")