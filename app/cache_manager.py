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
                # Add category column if it doesn't exist (safe for existing databases)
                "ALTER TABLE answer_cache ADD COLUMN category TEXT DEFAULT ''",
                # Metadata table for tracking cache-invalidation keys (e.g. PAY_INCREASES)
                """CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            for cached_emb, cached_q, cached_answer, cached_status, cached_time, cached_cat in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD and score > best_score:
                    best_score = score
                    best_result = (cached_answer, cached_status, cached_time)
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
