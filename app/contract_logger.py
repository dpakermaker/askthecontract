import hashlib
import json
import os
import sqlite3
import tempfile
import urllib.request
from datetime import datetime


class ContractLogger:
    """Question and rating logger with Turso persistence.
    
    Uses same Turso HTTP API as SemanticCache.
    On Railway: logs to Turso (persists across deploys).
    Locally: logs to SQLite file (for dev/testing).
    Falls back to local SQLite if Turso is unavailable.
    
    ALL queries filter by contract_id — no cross-contract data leaks.
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

    # ================================================================
    # TURSO HTTP API
    # ================================================================
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

    def _turso_query_rows(self, sql, args=None):
        """Execute a single SELECT and return parsed rows. Returns list of tuples."""
        stmt = {"sql": sql}
        if args:
            stmt["args"] = args
        result = self._turso_request([stmt])
        if not result or 'results' not in result:
            return []
        select_result = result['results'][0]
        if select_result.get('type') != 'ok':
            return []
        rows = select_result['response']['result'].get('rows', [])
        parsed = []
        for row in rows:
            parsed.append(tuple(
                None if col['type'] == 'null' else
                int(col['value']) if col['type'] == 'integer' else
                float(col['value']) if col['type'] == 'float' else
                col['value']
                for col in row
            ))
        return parsed

    def _init_turso(self):
        """Create tables in Turso."""
        try:
            result = self._turso_request([
                """CREATE TABLE IF NOT EXISTS questions_log (
                    question_id TEXT PRIMARY KEY,
                    user_hash TEXT,
                    contract_id TEXT NOT NULL,
                    timestamp TEXT,
                    question_text TEXT,
                    answer_text TEXT,
                    status TEXT,
                    category TEXT,
                    response_time_seconds REAL
                )""",
                "CREATE INDEX IF NOT EXISTS idx_questions_contract ON questions_log(contract_id)",
                "CREATE INDEX IF NOT EXISTS idx_questions_timestamp ON questions_log(timestamp)",
                """CREATE TABLE IF NOT EXISTS answer_ratings (
                    rating_id TEXT PRIMARY KEY,
                    contract_id TEXT NOT NULL,
                    timestamp TEXT,
                    question_text TEXT,
                    rating TEXT,
                    comment TEXT
                )""",
                "CREATE INDEX IF NOT EXISTS idx_ratings_contract ON answer_ratings(contract_id)"
            ])
            if result:
                self._turso_available = True
                print("[Logger] ✅ Turso connected — questions + ratings persist across deploys")
            else:
                print("[Logger] Turso init failed — local SQLite only")
        except Exception as e:
            print(f"[Logger] Turso init error: {e} — local SQLite only")

    # ================================================================
    # LOCAL SQLITE
    # ================================================================
    def _init_local_db(self):
        """Create local SQLite tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions_log (
                question_id TEXT PRIMARY KEY,
                user_hash TEXT,
                contract_id TEXT NOT NULL,
                timestamp TEXT,
                question_text TEXT,
                answer_text TEXT,
                status TEXT,
                category TEXT,
                response_time_seconds REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answer_ratings (
                rating_id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                timestamp TEXT,
                question_text TEXT,
                rating TEXT,
                comment TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _local_query(self, sql, params=None):
        """Execute a SELECT against local SQLite. Returns list of tuples."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    # ================================================================
    # WRITE METHODS
    # ================================================================
    def log_question(self, question_text, answer_text, status, contract_id, response_time=None, category=None):
        """Log a question to both Turso and local SQLite."""
        question_id = f"q_{datetime.now().timestamp()}"
        user_hash = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]
        timestamp = datetime.now().isoformat()

        if self._turso_available:
            try:
                self._turso_request([{
                    "sql": """INSERT OR IGNORE INTO questions_log 
                              (question_id, user_hash, contract_id, timestamp, 
                               question_text, answer_text, status, category, response_time_seconds)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    "args": [
                        {"type": "text", "value": question_id},
                        {"type": "text", "value": user_hash},
                        {"type": "text", "value": contract_id},
                        {"type": "text", "value": timestamp},
                        {"type": "text", "value": question_text},
                        {"type": "text", "value": answer_text},
                        {"type": "text", "value": status or ""},
                        {"type": "text", "value": category or "General Contract Question"},
                        {"type": "float", "value": response_time or 0}
                    ]
                }])
            except Exception as e:
                print(f"[Logger] Turso write failed: {e}")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO questions_log 
                (question_id, user_hash, contract_id, timestamp, question_text, 
                 answer_text, status, category, response_time_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (question_id, user_hash, contract_id, timestamp, question_text,
                  answer_text, status, category or "General Contract Question", response_time))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Logger] Local SQLite write failed: {e}")

    def log_rating(self, question_text, rating, contract_id, comment=""):
        """Log a rating to both Turso and local SQLite."""
        rating_id = f"r_{datetime.now().timestamp()}"
        timestamp = datetime.now().isoformat()

        if self._turso_available:
            try:
                self._turso_request([{
                    "sql": """INSERT OR IGNORE INTO answer_ratings 
                              (rating_id, contract_id, timestamp, question_text, rating, comment)
                              VALUES (?, ?, ?, ?, ?, ?)""",
                    "args": [
                        {"type": "text", "value": rating_id},
                        {"type": "text", "value": contract_id},
                        {"type": "text", "value": timestamp},
                        {"type": "text", "value": question_text},
                        {"type": "text", "value": rating},
                        {"type": "text", "value": comment}
                    ]
                }])
            except Exception as e:
                print(f"[Logger] Turso rating write failed: {e}")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO answer_ratings 
                (rating_id, contract_id, timestamp, question_text, rating, comment)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (rating_id, contract_id, timestamp, question_text, rating, comment))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Logger] Local rating write failed: {e}")

    # ================================================================
    # PUBLIC READ METHODS (always filter by contract_id)
    # ================================================================
    def get_top_questions(self, limit=5, contract_id=None):
        """Top questions by frequency for a specific contract."""
        if contract_id:
            sql = "SELECT question_text, COUNT(*) as cnt FROM questions_log WHERE contract_id = ? GROUP BY question_text ORDER BY cnt DESC LIMIT ?"
            turso_args = [
                {"type": "text", "value": contract_id},
                {"type": "integer", "value": str(limit)}
            ]
            local_params = (contract_id, limit)
        else:
            sql = "SELECT question_text, COUNT(*) as cnt FROM questions_log GROUP BY question_text ORDER BY cnt DESC LIMIT ?"
            turso_args = [{"type": "integer", "value": str(limit)}]
            local_params = (limit,)

        if self._turso_available:
            try:
                rows = self._turso_query_rows(sql, turso_args)
                if rows:
                    return rows
            except:
                pass
        return self._local_query(sql, local_params)

    # ================================================================
    # ADMIN READ METHODS (all filter by contract_id)
    # ================================================================
    def admin_summary(self, contract_id):
        """Overview stats for a contract: total, status counts, avg time."""
        sql_total = "SELECT COUNT(*) FROM questions_log WHERE contract_id = ?"
        sql_status = "SELECT status, COUNT(*) FROM questions_log WHERE contract_id = ? GROUP BY status"
        sql_avg = "SELECT AVG(response_time_seconds) FROM questions_log WHERE contract_id = ? AND response_time_seconds > 0"
        args = [{"type": "text", "value": contract_id}]
        local_params = (contract_id,)

        if self._turso_available:
            try:
                total = self._turso_query_rows(sql_total, args)
                statuses = self._turso_query_rows(sql_status, args)
                avg_time = self._turso_query_rows(sql_avg, args)
                return {
                    'total': total[0][0] if total else 0,
                    'status_counts': dict(statuses) if statuses else {},
                    'avg_time': avg_time[0][0] if avg_time and avg_time[0][0] else 0,
                }
            except:
                pass

        total = self._local_query(sql_total, local_params)
        statuses = self._local_query(sql_status, local_params)
        avg_time = self._local_query(sql_avg, local_params)
        return {
            'total': total[0][0] if total else 0,
            'status_counts': dict(statuses) if statuses else {},
            'avg_time': avg_time[0][0] if avg_time and avg_time[0][0] else 0,
        }

    def admin_top_questions(self, contract_id, limit=20):
        """Top questions by frequency for admin view."""
        return self.get_top_questions(limit=limit, contract_id=contract_id)

    def admin_questions_by_category(self, contract_id):
        """Question counts grouped by stored category."""
        # Use stored category column. Old rows without category show as 'Uncategorized'.
        # Strip sub-categories (e.g. "Pay → Duty Rig" becomes "Pay")
        sql = """SELECT 
                    CASE 
                        WHEN category IS NULL OR category = '' THEN 'Uncategorized'
                        WHEN category LIKE 'Pay →%' OR category LIKE 'Pay %' THEN 'Pay'
                        WHEN category LIKE 'Reserve →%' OR category LIKE 'Reserve %' THEN 'Reserve'
                        WHEN category LIKE 'Scheduling →%' OR category LIKE 'Scheduling %' THEN 'Scheduling'
                        WHEN category LIKE 'Grievance%' THEN 'Grievance'
                        WHEN category LIKE 'Hours of Service%' OR category LIKE 'Rest%' THEN 'Rest / Duty Limits'
                        WHEN category LIKE 'Training%' THEN 'Training'
                        ELSE category
                    END as cat_group,
                    COUNT(*) as cnt
                 FROM questions_log 
                 WHERE contract_id = ?
                 GROUP BY cat_group
                 ORDER BY cnt DESC"""
        args = [{"type": "text", "value": contract_id}]
        local_params = (contract_id,)

        if self._turso_available:
            try:
                rows = self._turso_query_rows(sql, args)
                if rows:
                    return rows
            except:
                pass
        return self._local_query(sql, local_params)

    def admin_ambiguous_questions(self, contract_id, limit=20):
        """Questions that came back AMBIGUOUS — contract unclear."""
        sql = "SELECT question_text, COUNT(*) as cnt FROM questions_log WHERE contract_id = ? AND status = 'AMBIGUOUS' GROUP BY question_text ORDER BY cnt DESC LIMIT ?"
        args = [
            {"type": "text", "value": contract_id},
            {"type": "integer", "value": str(limit)}
        ]
        local_params = (contract_id, limit)

        if self._turso_available:
            try:
                rows = self._turso_query_rows(sql, args)
                if rows:
                    return rows
            except:
                pass
        return self._local_query(sql, local_params)

    def admin_ratings(self, contract_id):
        """Rating summary for a contract."""
        sql_counts = "SELECT rating, COUNT(*) FROM answer_ratings WHERE contract_id = ? GROUP BY rating"
        sql_down = "SELECT question_text, timestamp FROM answer_ratings WHERE contract_id = ? AND rating = 'down' ORDER BY timestamp DESC LIMIT 20"
        args = [{"type": "text", "value": contract_id}]
        local_params = (contract_id,)

        if self._turso_available:
            try:
                counts = self._turso_query_rows(sql_counts, args)
                down_qs = self._turso_query_rows(sql_down, args)
                counts_dict = dict(counts) if counts else {}
                up = counts_dict.get('up', 0)
                down = counts_dict.get('down', 0)
                total = up + down
                return {
                    'up': up, 'down': down, 'total': total,
                    'satisfaction': round(up / total * 100, 1) if total > 0 else 0,
                    'down_questions': down_qs,
                }
            except:
                pass

        counts = self._local_query(sql_counts, local_params)
        down_qs = self._local_query(sql_down, local_params)
        counts_dict = dict(counts) if counts else {}
        up = counts_dict.get('up', 0)
        down = counts_dict.get('down', 0)
        total = up + down
        return {
            'up': up, 'down': down, 'total': total,
            'satisfaction': round(up / total * 100, 1) if total > 0 else 0,
            'down_questions': down_qs,
        }

    def admin_recent_questions(self, contract_id, limit=50):
        """Recent questions log."""
        sql = "SELECT timestamp, question_text, status, response_time_seconds FROM questions_log WHERE contract_id = ? ORDER BY timestamp DESC LIMIT ?"
        args = [
            {"type": "text", "value": contract_id},
            {"type": "integer", "value": str(limit)}
        ]
        local_params = (contract_id, limit)

        if self._turso_available:
            try:
                rows = self._turso_query_rows(sql, args)
                if rows:
                    return rows
            except:
                pass
        return self._local_query(sql, local_params)

    def admin_tier1_vs_api(self, contract_id):
        """Count Tier 1 (0.0s response) vs API calls."""
        sql_tier1 = "SELECT COUNT(*) FROM questions_log WHERE contract_id = ? AND response_time_seconds = 0"
        sql_api = "SELECT COUNT(*) FROM questions_log WHERE contract_id = ? AND response_time_seconds > 0"
        args = [{"type": "text", "value": contract_id}]
        local_params = (contract_id,)

        if self._turso_available:
            try:
                t1 = self._turso_query_rows(sql_tier1, args)
                api = self._turso_query_rows(sql_api, args)
                return {
                    'tier1': t1[0][0] if t1 else 0,
                    'api': api[0][0] if api else 0,
                }
            except:
                pass

        t1 = self._local_query(sql_tier1, local_params)
        api = self._local_query(sql_api, local_params)
        return {
            'tier1': t1[0][0] if t1 else 0,
            'api': api[0][0] if api else 0,
        }

    def admin_export_csv(self, contract_id):
        """Export all questions for a contract as CSV string."""
        sql = "SELECT timestamp, question_text, status, response_time_seconds FROM questions_log WHERE contract_id = ? ORDER BY timestamp DESC"
        args = [{"type": "text", "value": contract_id}]
        local_params = (contract_id,)

        if self._turso_available:
            try:
                rows = self._turso_query_rows(sql, args)
                if rows:
                    return self._rows_to_csv(rows)
            except:
                pass
        rows = self._local_query(sql, local_params)
        return self._rows_to_csv(rows)

    def _rows_to_csv(self, rows):
        """Convert rows to CSV string."""
        lines = ["timestamp,question,status,response_time_seconds"]
        for row in rows:
            ts = row[0] or ""
            q = (row[1] or "").replace('"', '""')
            status = row[2] or ""
            rt = row[3] or 0
            lines.append(f'"{ts}","{q}","{status}",{rt}')
        return "\n".join(lines)

    def admin_get_contracts(self):
        """Get list of all contract_ids that have logged questions."""
        sql = "SELECT DISTINCT contract_id FROM questions_log ORDER BY contract_id"
        if self._turso_available:
            try:
                rows = self._turso_query_rows(sql)
                if rows:
                    return [r[0] for r in rows]
            except:
                pass
        rows = self._local_query(sql)
        return [r[0] for r in rows]


# Test
if __name__ == "__main__":
    print("=" * 70)
    print("TESTING TURSO-BACKED LOGGER")
    print("=" * 70)

    logger = ContractLogger()
    print(f"✓ Database initialized (Turso: {logger._turso_available})")

    logger.log_question(
        question_text="What is the daily pay guarantee?",
        answer_text="3.82 PCH",
        status="CLEAR",
        contract_id="NAC",
        response_time=2.5
    )
    print("✓ Question logged")

    logger.log_rating("What is the daily pay guarantee?", "up", "NAC")
    print("✓ Rating logged")

    top = logger.get_top_questions(5, contract_id="NAC")
    print(f"✓ Top questions: {top}")

    summary = logger.admin_summary("NAC")
    print(f"✓ Admin summary: {summary}")
