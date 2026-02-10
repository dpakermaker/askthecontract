import hashlib
import json
import os
import sqlite3
import tempfile
import urllib.request
from datetime import datetime


class ContractLogger:
    """Question logger with Turso persistence.
    
    Uses same Turso HTTP API as SemanticCache.
    On Railway: logs to Turso (persists across deploys).
    Locally: logs to SQLite file (for dev/testing).
    Falls back to local SQLite if Turso is unavailable.
    """

    def __init__(self, db_path='database/contract_qa.db'):
        self._turso_available = False
        self._http_url = ''
        self._turso_token = ''

        # Try Turso first
        turso_url = os.environ.get('TURSO_DATABASE_URL', '')
        self._turso_token = os.environ.get('TURSO_AUTH_TOKEN', '')
        if turso_url and self._turso_token:
            self._http_url = turso_url.replace('libsql://', 'https://') + '/v3/pipeline'
            self._init_turso()

        # Local SQLite fallback (always available for dev/testing)
        if os.path.exists("/mount/src") or os.environ.get("RAILWAY_ENVIRONMENT"):
            self.db_path = os.path.join(tempfile.gettempdir(), "contract_qa.db")
        else:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.db_path = db_path
        self._init_local_db()

    def _turso_request(self, statements):
        """Send SQL statements to Turso via HTTP API."""
        requests_body = []
        for stmt in statements:
            if isinstance(stmt, str):
                requests_body.append({"type": "execute", "stmt": {"sql": stmt}})
            elif isinstance(stmt, dict):
                requests_body.append({"type": "execute", "stmt": stmt})
        requests_body.append({"type": "close"})

        data = json.dumps({"requests": requests_body}).encode('utf-8')
        req = urllib.request.Request(
            self._http_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._turso_token}'
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.request.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else 'no body'
            print(f"[Logger] Turso HTTP {e.code}: {error_body[:200]}")
            return None
        except Exception as e:
            print(f"[Logger] Turso error: {e}")
            return None

    def _init_turso(self):
        """Create questions_log table in Turso."""
        try:
            result = self._turso_request([
                """CREATE TABLE IF NOT EXISTS questions_log (
                    question_id TEXT PRIMARY KEY,
                    user_hash TEXT,
                    contract_id TEXT,
                    timestamp TEXT,
                    question_text TEXT,
                    answer_text TEXT,
                    status TEXT,
                    category TEXT,
                    response_time_seconds REAL
                )""",
                "CREATE INDEX IF NOT EXISTS idx_questions_contract ON questions_log(contract_id)",
                "CREATE INDEX IF NOT EXISTS idx_questions_timestamp ON questions_log(timestamp)"
            ])
            if result:
                self._turso_available = True
                print("[Logger] ✅ Turso connected — questions persist across deploys")
            else:
                print("[Logger] Turso init failed — local SQLite only")
        except Exception as e:
            print(f"[Logger] Turso init error: {e} — local SQLite only")

    def _init_local_db(self):
        """Create local SQLite tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
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
        """Log a question to both Turso and local SQLite."""
        question_id = f"q_{datetime.now().timestamp()}"
        user_hash = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]
        timestamp = datetime.now().isoformat()

        # Write to Turso (persistent)
        if self._turso_available:
            try:
                self._turso_request([{
                    "sql": """INSERT OR IGNORE INTO questions_log 
                              (question_id, user_hash, contract_id, timestamp, 
                               question_text, answer_text, status, response_time_seconds)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    "args": [
                        {"type": "text", "value": question_id},
                        {"type": "text", "value": user_hash},
                        {"type": "text", "value": contract_id},
                        {"type": "text", "value": timestamp},
                        {"type": "text", "value": question_text},
                        {"type": "text", "value": answer_text},
                        {"type": "text", "value": status or ""},
                        {"type": "float", "value": str(response_time or 0)}
                    ]
                }])
            except Exception as e:
                print(f"[Logger] Turso write failed: {e}")

        # Always write to local SQLite too (for local analytics)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO questions_log 
                (question_id, user_hash, contract_id, timestamp, question_text, 
                 answer_text, status, response_time_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (question_id, user_hash, contract_id, timestamp, question_text,
                  answer_text, status, response_time))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Logger] Local SQLite write failed: {e}")

    def get_top_questions(self, limit=5):
        """Get most asked questions. Reads from Turso if available, else local."""
        if self._turso_available:
            try:
                result = self._turso_request([{
                    "sql": "SELECT question_text, COUNT(*) as cnt FROM questions_log GROUP BY question_text ORDER BY cnt DESC LIMIT ?",
                    "args": [{"type": "integer", "value": str(limit)}]
                }])
                if result and 'results' in result:
                    select_result = result['results'][0]
                    if select_result.get('type') == 'ok':
                        rows = select_result['response']['result'].get('rows', [])
                        return [(row[0]['value'], int(row[1]['value'])) for row in rows]
            except Exception as e:
                print(f"[Logger] Turso read failed: {e}")

        # Fallback to local
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT question_text, COUNT(*) as cnt FROM questions_log GROUP BY question_text ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []


# Test
if __name__ == "__main__":
    print("=" * 70)
    print("TESTING TURSO-BACKED LOGGER")
    print("=" * 70)

    logger = ContractLogger()
    print(f"✓ Database initialized (Turso: {logger._turso_available})")

    logger.log_question(
        question_text="Test question",
        answer_text="Test answer",
        status="CLEAR",
        contract_id="NAC",
        response_time=2.5
    )
    print("✓ Question logged")

    top = logger.get_top_questions(5)
    print(f"✓ Top questions: {top}")
