"""
Semantic Cache Manager for AskTheContract.

Turso-backed persistent cache with in-memory similarity search.
Extracted into its own module so admin.py can import it
without triggering main app UI code.
"""

import streamlit as st
import threading
import json
import os
import numpy as np


class SemanticCache:
    """Turso-backed persistent cache with in-memory similarity search.
    
    Uses Turso HTTP API — no extra packages needed.
    On startup: loads all cached Q&A from Turso into memory.
    On new answer: writes to both memory AND Turso.
    On restart/deploy: memory reloads from Turso — nothing lost.
    Falls back to memory-only if Turso is unavailable.
    Each entry is tagged with a category for selective clearing.
    """
    SIMILARITY_THRESHOLD = 0.93
    MAX_ENTRIES = 2000

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = {}
        self._turso_available = False
        turso_url = os.environ.get('TURSO_DATABASE_URL', '')
        self._turso_token = os.environ.get('TURSO_AUTH_TOKEN', '')
        # Convert libsql:// URL to https:// for HTTP API
        if turso_url and self._turso_token:
            self._http_url = turso_url.replace('libsql://', 'https://') + '/v3/pipeline'
            self._init_turso()
        else:
            self._http_url = ''
            print("[Cache] No Turso credentials — memory-only mode")

    def _turso_request(self, statements):
        """Send SQL statements to Turso via HTTP API."""
        import urllib.request
        import base64 as b64module
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
            print(f"[Cache] Turso HTTP {e.code}: {error_body[:200]}")
            return None
        except Exception as e:
            print(f"[Cache] Turso error: {e}")
            return None

    def _init_turso(self):
        """Initialize Turso table via HTTP API."""
        try:
            result = self._turso_request([
                """CREATE TABLE IF NOT EXISTS answer_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT,
                    response_time REAL,
                    embedding_b64 TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                "CREATE INDEX IF NOT EXISTS idx_cache_contract ON answer_cache(contract_id)",
                # Add columns if they don't exist (safe for existing databases)
                "ALTER TABLE answer_cache ADD COLUMN category TEXT DEFAULT ''",
                "ALTER TABLE answer_cache ADD COLUMN thumbs_down INTEGER DEFAULT 0",
                "ALTER TABLE answer_cache ADD COLUMN serve_count INTEGER DEFAULT 0",
                "ALTER TABLE answer_cache ADD COLUMN reviewed INTEGER DEFAULT 0",
                # Metadata table for tracking cache-invalidation keys (e.g. PAY_INCREASES)
                """CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                # Pilot feedback on cached answers (separate table — multiple comments per answer)
                """CREATE TABLE IF NOT EXISTS cache_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
            ])
            if result:
                self._turso_available = True
                self._load_from_turso()
                total = sum(len(v) for v in self._entries.values())
                print(f"[Cache] ✅ Turso connected — loaded {total} cached answers")
            else:
                print("[Cache] Turso init failed — memory-only mode")
        except Exception as e:
            print(f"[Cache] Turso init error: {e} — memory-only mode")

    def _load_from_turso(self):
        """Load all cached entries from Turso into memory."""
        if not self._turso_available:
            return
        import base64 as b64module
        try:
            result = self._turso_request([
                "SELECT contract_id, question, answer, status, response_time, embedding_b64, category FROM answer_cache ORDER BY created_at DESC"
            ])
            if not result or 'results' not in result:
                return
            # Parse response — results[0] is our SELECT
            select_result = result['results'][0]
            if select_result.get('type') != 'ok':
                return
            rows = select_result['response']['result'].get('rows', [])
            for row in rows:
                contract_id = row[0]['value']
                question = row[1]['value']
                answer = row[2]['value']
                status = row[3]['value'] if row[3]['type'] != 'null' else ''
                response_time = float(row[4]['value']) if row[4]['type'] != 'null' else 0.0
                emb_b64 = row[5]['value']
                category = row[6]['value'] if row[6]['type'] != 'null' else ''
                embedding = np.frombuffer(b64module.b64decode(emb_b64), dtype=np.float32)
                if contract_id not in self._entries:
                    self._entries[contract_id] = []
                if len(self._entries[contract_id]) < self.MAX_ENTRIES:
                    self._entries[contract_id].append((embedding, question, answer, status, response_time, category))
        except Exception as e:
            print(f"[Cache] Failed to load from Turso: {e}")

    def _save_to_turso(self, embedding, question, answer, status, response_time, contract_id, category):
        """Persist a new cache entry to Turso via HTTP API."""
        if not self._turso_available:
            return
        import base64 as b64module
        try:
            emb_b64 = b64module.b64encode(np.array(embedding, dtype=np.float32).tobytes()).decode('ascii')
            stmt = {
                "sql": "INSERT INTO answer_cache (contract_id, question, answer, status, response_time, embedding_b64, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                "args": [
                    {"type": "text", "value": contract_id},
                    {"type": "text", "value": question},
                    {"type": "text", "value": answer},
                    {"type": "text", "value": status or ""},
                    {"type": "float", "value": response_time},
                    {"type": "text", "value": emb_b64},
                    {"type": "text", "value": category or ""},
                ]
            }
            self._turso_request([stmt])
        except Exception as e:
            print(f"[Cache] Failed to save to Turso: {e}")

    def lookup(self, embedding, contract_id):
        embedding = np.array(embedding, dtype=np.float32)
        with self._lock:
            entries = self._entries.get(contract_id, [])
            best_score = 0
            best_result = None
            best_question = None
            for cached_emb, cached_q, cached_answer, cached_status, cached_time, cached_cat in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD and score > best_score:
                    best_score = score
                    best_result = (cached_answer, cached_status, cached_time)
                    best_question = cached_q
        # Increment serve_count in Turso (fire and forget)
        if best_result and best_question and self._turso_available:
            try:
                stmt = {
                    "sql": "UPDATE answer_cache SET serve_count = serve_count + 1 WHERE contract_id = ? AND question = ?",
                    "args": [
                        {"type": "text", "value": contract_id},
                        {"type": "text", "value": best_question},
                    ]
                }
                self._turso_request([stmt])
            except Exception:
                pass  # Non-critical — don't break cache hits
        return best_result

    def store(self, embedding, question, answer, status, response_time, contract_id, category=""):
        embedding = np.array(embedding, dtype=np.float32)
        with self._lock:
            if contract_id not in self._entries:
                self._entries[contract_id] = []
            entries = self._entries[contract_id]
            for cached_emb, _, _, _, _, _ in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD:
                    return
            if len(entries) >= self.MAX_ENTRIES:
                entries.pop(0)
            entries.append((embedding, question, answer, status, response_time, category))
        self._save_to_turso(embedding, question, answer, status, response_time, contract_id, category)

    def clear(self, contract_id=None):
        with self._lock:
            if contract_id:
                self._entries.pop(contract_id, None)
            else:
                self._entries = {}
        if self._turso_available:
            try:
                if contract_id:
                    stmt = {
                        "sql": "DELETE FROM answer_cache WHERE contract_id = ?",
                        "args": [{"type": "text", "value": contract_id}]
                    }
                else:
                    stmt = "DELETE FROM answer_cache"
                self._turso_request([stmt])
            except Exception as e:
                print(f"[Cache] Failed to clear Turso: {e}")

    def clear_category(self, contract_id, category):
        """Clear only entries matching a specific category for a contract."""
        with self._lock:
            entries = self._entries.get(contract_id, [])
            # Keep entries that DON'T match the category
            self._entries[contract_id] = [e for e in entries if e[5] != category]
            removed = len(entries) - len(self._entries[contract_id])
        if self._turso_available:
            try:
                stmt = {
                    "sql": "DELETE FROM answer_cache WHERE contract_id = ? AND category = ?",
                    "args": [
                        {"type": "text", "value": contract_id},
                        {"type": "text", "value": category},
                    ]
                }
                self._turso_request([stmt])
            except Exception as e:
                print(f"[Cache] Failed to clear category from Turso: {e}")
        print(f"[Cache] Cleared {removed} entries for {contract_id} / {category}")
        return removed

    def get_category_stats(self, contract_id=None):
        """Return dict of category -> count for a contract (or all contracts)."""
        with self._lock:
            stats = {}
            if contract_id:
                entries = self._entries.get(contract_id, [])
                for _, _, _, _, _, cat in entries:
                    label = cat if cat else "Uncategorized"
                    stats[label] = stats.get(label, 0) + 1
            else:
                for cid, entries in self._entries.items():
                    for _, _, _, _, _, cat in entries:
                        label = cat if cat else "Uncategorized"
                        stats[label] = stats.get(label, 0) + 1
            return stats

    def stats(self):
        total = sum(len(v) for v in self._entries.values())
        return {
            'total_entries': total,
            'turso_connected': self._turso_available,
            'contracts': {k: len(v) for k, v in self._entries.items()}
        }

    def get_all_entries(self, contract_id):
        """Return all cached entries for a contract from Turso with IDs for admin review.
        Returns list of dicts sorted by: flagged first, then highest serve_count.
        """
        if not self._turso_available:
            with self._lock:
                entries = self._entries.get(contract_id, [])
                return [
                    {'id': i, 'question': e[1], 'answer': e[2], 'status': e[3],
                     'category': e[5], 'created_at': 'unknown', 'thumbs_down': 0,
                     'serve_count': 0, 'reviewed': 0}
                    for i, e in enumerate(entries)
                ]
        try:
            stmt = {
                "sql": "SELECT id, question, answer, status, category, created_at, COALESCE(thumbs_down, 0), COALESCE(serve_count, 0), COALESCE(reviewed, 0) FROM answer_cache WHERE contract_id = ? ORDER BY thumbs_down DESC, serve_count DESC",
                "args": [{"type": "text", "value": contract_id}]
            }
            result = self._turso_request([stmt])
            if not result or 'results' not in result:
                return []
            select_result = result['results'][0]
            if select_result.get('type') != 'ok':
                return []
            rows = select_result['response']['result'].get('rows', [])
            entries = []
            for row in rows:
                entries.append({
                    'id': int(row[0]['value']),
                    'question': row[1]['value'],
                    'answer': row[2]['value'],
                    'status': row[3]['value'] if row[3]['type'] != 'null' else '',
                    'category': row[4]['value'] if row[4]['type'] != 'null' else '',
                    'created_at': row[5]['value'] if row[5]['type'] != 'null' else 'unknown',
                    'thumbs_down': int(row[6]['value']) if row[6]['type'] != 'null' else 0,
                    'serve_count': int(row[7]['value']) if row[7]['type'] != 'null' else 0,
                    'reviewed': int(row[8]['value']) if row[8]['type'] != 'null' else 0,
                })
            return entries
        except Exception as e:
            print(f"[Cache] Failed to get all entries: {e}")
            return []

    def delete_entry(self, entry_id, contract_id):
        """Delete a single cached entry by Turso ID. Also removes from memory."""
        # Remove from Turso
        if self._turso_available:
            try:
                # Get the question text first so we can remove from memory
                stmt_select = {
                    "sql": "SELECT question FROM answer_cache WHERE id = ?",
                    "args": [{"type": "integer", "value": str(entry_id)}]
                }
                result = self._turso_request([stmt_select])
                question_text = None
                if result and 'results' in result:
                    select_result = result['results'][0]
                    if select_result.get('type') == 'ok':
                        rows = select_result['response']['result'].get('rows', [])
                        if rows:
                            question_text = rows[0][0]['value']

                stmt_delete = {
                    "sql": "DELETE FROM answer_cache WHERE id = ?",
                    "args": [{"type": "integer", "value": str(entry_id)}]
                }
                self._turso_request([stmt_delete])

                # Remove from memory by matching question text
                if question_text:
                    with self._lock:
                        entries = self._entries.get(contract_id, [])
                        self._entries[contract_id] = [
                            e for e in entries if e[1] != question_text
                        ]
                print(f"[Cache] Deleted entry {entry_id}: {question_text[:50] if question_text else 'unknown'}...")
                return True
            except Exception as e:
                print(f"[Cache] Failed to delete entry {entry_id}: {e}")
                return False
        return False

    def record_thumbs_down(self, question_text, contract_id):
        """Increment thumbs_down counter on the cached answer matching this question.
        Called when a pilot clicks 👎. Uses fuzzy matching via embedding similarity
        but for simplicity we match on exact question text first."""
        if not self._turso_available:
            return False
        try:
            stmt = {
                "sql": "UPDATE answer_cache SET thumbs_down = thumbs_down + 1 WHERE contract_id = ? AND question = ?",
                "args": [
                    {"type": "text", "value": contract_id},
                    {"type": "text", "value": question_text},
                ]
            }
            result = self._turso_request([stmt])
            if result:
                print(f"[Cache] Thumbs down recorded for: {question_text[:50]}...")
                return True
        except Exception as e:
            print(f"[Cache] Failed to record thumbs down: {e}")
        return False

    def mark_reviewed(self, entry_id):
        """Mark a cached entry as reviewed by admin."""
        if not self._turso_available:
            return False
        try:
            stmt = {
                "sql": "UPDATE answer_cache SET reviewed = 1 WHERE id = ?",
                "args": [{"type": "integer", "value": str(entry_id)}]
            }
            self._turso_request([stmt])
            return True
        except Exception as e:
            print(f"[Cache] Failed to mark reviewed: {e}")
            return False

    def save_feedback(self, question_text, contract_id, comment):
        """Save a pilot's feedback comment about a cached answer."""
        if not self._turso_available or not comment.strip():
            return False
        try:
            stmt = {
                "sql": "INSERT INTO cache_feedback (contract_id, question, comment) VALUES (?, ?, ?)",
                "args": [
                    {"type": "text", "value": contract_id},
                    {"type": "text", "value": question_text},
                    {"type": "text", "value": comment.strip()},
                ]
            }
            self._turso_request([stmt])
            print(f"[Cache] Feedback saved for: {question_text[:50]}...")
            return True
        except Exception as e:
            print(f"[Cache] Failed to save feedback: {e}")
            return False

    def get_feedback(self, question_text, contract_id):
        """Get all pilot feedback comments for a specific cached question.
        Returns list of dicts: {comment, created_at}"""
        if not self._turso_available:
            return []
        try:
            stmt = {
                "sql": "SELECT comment, created_at FROM cache_feedback WHERE contract_id = ? AND question = ? ORDER BY created_at DESC",
                "args": [
                    {"type": "text", "value": contract_id},
                    {"type": "text", "value": question_text},
                ]
            }
            result = self._turso_request([stmt])
            if not result or 'results' not in result:
                return []
            select_result = result['results'][0]
            if select_result.get('type') != 'ok':
                return []
            rows = select_result['response']['result'].get('rows', [])
            return [
                {'comment': row[0]['value'], 'created_at': row[1]['value'] if row[1]['type'] != 'null' else ''}
                for row in rows
            ]
        except Exception as e:
            print(f"[Cache] Failed to get feedback: {e}")
            return []

    def get_meta(self, key):
        """Retrieve a metadata value from Turso. Returns None if not found."""
        if not self._turso_available:
            return None
        try:
            stmt = {
                "sql": "SELECT value FROM cache_metadata WHERE key = ?",
                "args": [{"type": "text", "value": key}]
            }
            result = self._turso_request([stmt])
            if not result or 'results' not in result:
                return None
            select_result = result['results'][0]
            if select_result.get('type') != 'ok':
                return None
            rows = select_result['response']['result'].get('rows', [])
            if rows:
                return rows[0][0]['value']
            return None
        except Exception as e:
            print(f"[Cache] Failed to get metadata '{key}': {e}")
            return None

    def set_meta(self, key, value):
        """Store a metadata value in Turso (upsert)."""
        if not self._turso_available:
            return
        try:
            stmt = {
                "sql": "INSERT INTO cache_metadata (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                "args": [
                    {"type": "text", "value": key},
                    {"type": "text", "value": str(value)},
                ]
            }
            self._turso_request([stmt])
        except Exception as e:
            print(f"[Cache] Failed to set metadata '{key}': {e}")


@st.cache_resource
def get_semantic_cache():
    """Shared cache instance — same object across all pages."""
    return SemanticCache()
