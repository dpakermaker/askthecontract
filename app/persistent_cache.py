import sqlite3
import json
import time
import numpy as np
from pathlib import Path

def _cosine(a, b):
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

class PersistentSemanticCache:
    def __init__(self, db_path, similarity_threshold=0.96, max_rows_per_key=2000):
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        self.max_rows_per_key = max_rows_per_key
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    question TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL NOT NULL
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON semantic_cache(cache_key)")

    def lookup(self, embedding, cache_key):
        emb = np.array(embedding, dtype=np.float32)

        with self._connect() as con:
            rows = con.execute("""
                SELECT embedding_json, answer, status, response_time
                FROM semantic_cache
                WHERE cache_key = ?
                ORDER BY id DESC
                LIMIT 250
            """, (cache_key,)).fetchall()

        best = None
        best_score = 0.0

        for emb_json, answer, status, response_time in rows:
            try:
                cached_emb = np.array(json.loads(emb_json), dtype=np.float32)
                score = _cosine(emb, cached_emb)
                if score > best_score:
                    best_score = score
                    best = (answer, status, response_time)
            except Exception:
                continue

        if best and best_score >= self.similarity_threshold:
            return best
        return None

    def store(self, embedding, question, answer, status, response_time, cache_key):
        with self._connect() as con:
            con.execute("""
                INSERT INTO semantic_cache
                (cache_key, created_at, question, embedding_json, answer, status, response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                time.time(),
                question,
                json.dumps(embedding),
                answer,
                status,
                float(response_time),
            ))
