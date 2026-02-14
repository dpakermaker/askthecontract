"""
auth_manager.py — AskTheContract Authentication Module
=======================================================
Handles pilot registration, login, and session management.
Stores users in Turso Cloud SQLite alongside existing cache/logging tables.

Uses Turso HTTP API — same pattern as cache_manager.py.
No extra packages needed.

Privacy-first design:
- Passwords hashed with PBKDF2-SHA256 + unique salt per user
- No real names required (display_name is optional)
- User IDs are opaque UUIDs — no PII in the ID itself
- Email stored only for login + future password reset
"""

import hashlib
import secrets
import uuid
import os
import json
import urllib.request
from datetime import datetime


# ─────────────────────────────────────────────
# TURSO HTTP API CONNECTION
# Same pattern as cache_manager.py — no extra packages
# ─────────────────────────────────────────────

_turso_url = os.environ.get('TURSO_DATABASE_URL', '')
_turso_token = os.environ.get('TURSO_AUTH_TOKEN', '')

if _turso_url and _turso_token:
    _http_url = _turso_url.replace('libsql://', 'https://') + '/v3/pipeline'
    TURSO_AVAILABLE = True
else:
    _http_url = ''
    TURSO_AVAILABLE = False

# Local fallback for testing without Turso
LOCAL_USERS = {}  # email -> user dict (in-memory only, resets on restart)


def _turso_request(statements):
    """Send SQL statements to Turso via HTTP API.
    Identical pattern to SemanticCache._turso_request()."""
    if not TURSO_AVAILABLE:
        return None
    requests_body = []
    for stmt in statements:
        if isinstance(stmt, str):
            requests_body.append({"type": "execute", "stmt": {"sql": stmt}})
        elif isinstance(stmt, dict):
            requests_body.append({"type": "execute", "stmt": stmt})
    requests_body.append({"type": "close"})

    data = json.dumps({"requests": requests_body}).encode('utf-8')
    req = urllib.request.Request(
        _http_url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {_turso_token}'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.request.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else 'no body'
        print(f"[AUTH] Turso HTTP {e.code}: {error_body[:200]}")
        return None
    except Exception as e:
        print(f"[AUTH] Turso error: {e}")
        return None


# ─────────────────────────────────────────────
# TABLE INITIALIZATION
# ─────────────────────────────────────────────

def init_auth_tables():
    """
    Create users table if it doesn't exist.
    Call once at app startup.
    """
    if TURSO_AVAILABLE:
        result = _turso_request([
            """CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                last_login TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1
            )""",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)"
        ])
        if result:
            print("[AUTH] ✅ Users table ready.")
        else:
            print("[AUTH] Table creation failed — running in local mode.")
    else:
        print("[AUTH] No Turso credentials — local mode (users won't persist).")


# ─────────────────────────────────────────────
# PASSWORD HASHING
# PBKDF2-SHA256 with unique salt — standard library, no extra deps
# ─────────────────────────────────────────────

def _hash_password(password, salt=None):
    """
    Hash a password with PBKDF2-SHA256.
    Returns (hash_hex, salt_hex).
    """
    if salt is None:
        salt = secrets.token_hex(32)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000
    )
    return pw_hash.hex(), salt


def _verify_password(password, stored_hash, salt):
    """Check a password against stored hash + salt."""
    computed_hash, _ = _hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)


# ─────────────────────────────────────────────
# HELPER: parse Turso SELECT results
# ─────────────────────────────────────────────

def _get_rows(result, index=0):
    """Extract rows from a Turso HTTP API response.
    Returns list of rows (each row is a list of {type, value} dicts)."""
    if not result or 'results' not in result:
        return []
    select_result = result['results'][index]
    if select_result.get('type') != 'ok':
        return []
    return select_result['response']['result'].get('rows', [])


def _cell_value(cell, default=''):
    """Extract a value from a Turso cell, handling nulls."""
    if cell.get('type') == 'null':
        return default
    return cell.get('value', default)


# ─────────────────────────────────────────────
# USER REGISTRATION
# ─────────────────────────────────────────────

def register_user(email, password, display_name=""):
    """
    Register a new pilot account.

    Returns:
        {"success": True, "user_id": "...", "message": "..."} on success
        {"success": False, "message": "..."} on failure
    """
    email = email.strip().lower()

    # Basic validation
    if not email or "@" not in email:
        return {"success": False, "message": "Please enter a valid email address."}
    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}

    user_id = str(uuid.uuid4())
    pw_hash, salt = _hash_password(password)
    created_at = datetime.utcnow().isoformat()
    display_name = display_name.strip()

    if TURSO_AVAILABLE:
        try:
            # Check if email already exists
            check_stmt = {
                "sql": "SELECT id FROM users WHERE email = ?",
                "args": [{"type": "text", "value": email}]
            }
            result = _turso_request([check_stmt])
            rows = _get_rows(result)
            if rows:
                return {"success": False, "message": "An account with this email already exists."}

            # Insert new user
            insert_stmt = {
                "sql": "INSERT INTO users (id, email, password_hash, salt, display_name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                "args": [
                    {"type": "text", "value": user_id},
                    {"type": "text", "value": email},
                    {"type": "text", "value": pw_hash},
                    {"type": "text", "value": salt},
                    {"type": "text", "value": display_name},
                    {"type": "text", "value": created_at},
                ]
            }
            result = _turso_request([insert_stmt])
            if result:
                print(f"[AUTH] New user registered: {email}")
                return {"success": True, "user_id": user_id, "message": "Account created successfully!"}
            else:
                return {"success": False, "message": "Registration failed. Please try again."}
        except Exception as e:
            print(f"[AUTH] Registration error: {e}")
            return {"success": False, "message": "Registration failed. Please try again."}
    else:
        # Local fallback for testing
        if email in LOCAL_USERS:
            return {"success": False, "message": "An account with this email already exists."}
        LOCAL_USERS[email] = {
            "id": user_id,
            "email": email,
            "password_hash": pw_hash,
            "salt": salt,
            "display_name": display_name,
            "created_at": created_at
        }
        return {"success": True, "user_id": user_id, "message": "Account created! (Local mode — will not persist)"}


# ─────────────────────────────────────────────
# USER LOGIN
# ─────────────────────────────────────────────

def authenticate_user(email, password):
    """
    Authenticate a pilot.

    Returns:
        {"success": True, "user_id": "...", "display_name": "...", "message": "..."}
        {"success": False, "message": "..."}
    """
    email = email.strip().lower()

    if TURSO_AVAILABLE:
        try:
            stmt = {
                "sql": "SELECT id, password_hash, salt, display_name, is_active FROM users WHERE email = ?",
                "args": [{"type": "text", "value": email}]
            }
            result = _turso_request([stmt])
            rows = _get_rows(result)

            if not rows:
                return {"success": False, "message": "Invalid email or password."}

            row = rows[0]
            user_id = _cell_value(row[0])
            stored_hash = _cell_value(row[1])
            salt = _cell_value(row[2])
            display_name = _cell_value(row[3])
            is_active = int(_cell_value(row[4], '1'))

            if not is_active:
                return {"success": False, "message": "This account has been deactivated."}

            if not _verify_password(password, stored_hash, salt):
                return {"success": False, "message": "Invalid email or password."}

            # Update last login
            update_stmt = {
                "sql": "UPDATE users SET last_login = ? WHERE id = ?",
                "args": [
                    {"type": "text", "value": datetime.utcnow().isoformat()},
                    {"type": "text", "value": user_id},
                ]
            }
            _turso_request([update_stmt])

            return {
                "success": True,
                "user_id": user_id,
                "display_name": display_name or email.split("@")[0],
                "message": "Welcome back!"
            }
        except Exception as e:
            print(f"[AUTH] Login error: {e}")
            return {"success": False, "message": "Login failed. Please try again."}
    else:
        # Local fallback
        user = LOCAL_USERS.get(email)
        if not user:
            return {"success": False, "message": "Invalid email or password."}
        if not _verify_password(password, user["password_hash"], user["salt"]):
            return {"success": False, "message": "Invalid email or password."}
        return {
            "success": True,
            "user_id": user["id"],
            "display_name": user.get("display_name") or email.split("@")[0],
            "message": "Welcome back! (Local mode)"
        }


# ─────────────────────────────────────────────
# USER LOOKUP (for admin, future features)
# ─────────────────────────────────────────────

def get_user_count():
    """Return total registered users."""
    if TURSO_AVAILABLE:
        try:
            result = _turso_request(["SELECT COUNT(*) FROM users WHERE is_active = 1"])
            rows = _get_rows(result)
            if rows:
                return int(_cell_value(rows[0][0], '0'))
        except:
            pass
    return len(LOCAL_USERS)


def get_all_users():
    """Return list of users for admin dashboard. No passwords included."""
    if TURSO_AVAILABLE:
        try:
            result = _turso_request([
                "SELECT id, email, display_name, created_at, last_login FROM users WHERE is_active = 1 ORDER BY created_at DESC"
            ])
            rows = _get_rows(result)
            return [
                {
                    "id": _cell_value(r[0]),
                    "email": _cell_value(r[1]),
                    "display_name": _cell_value(r[2]),
                    "created_at": _cell_value(r[3]),
                    "last_login": _cell_value(r[4]),
                }
                for r in rows
            ]
        except:
            return []
    return list(LOCAL_USERS.values())
