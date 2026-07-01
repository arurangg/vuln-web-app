# Bcrypt Password Hashing — Implementation Plan

**Version:** 1.0.0
**Last Updated:** July 1, 2026
**Parent Documents:** [bcrypt-password-hashing.md](./bcrypt-password-hashing.md), [app-foundation.md](./app-foundation.md), [PRD.md](../../docs/PRD.md), [TDD.md](../../docs/TDD.md)

---

## 0. Purpose & Ground Rules

This is the step-by-step build plan for the bcrypt remediation specified in [bcrypt-password-hashing.md](./bcrypt-password-hashing.md). It is a **plan only** — no source code is written in the step that produces this file.

**What this change does:** closes **Vulnerability #5 (Weak Password Storage)** by replacing unsalted MD5 with bcrypt (work factor ≥ 12), while keeping the public API (`hash_password`, `verify_password`) stable and adjusting `auth_service.login()` to verify the password in Python (bcrypt salts every hash, so the stored hash can no longer be matched inside the SQL predicate).

**Surgical / additive-preservation guarantee — the other 7 vulnerabilities stay intact:**

- **VULN-1 SQL Injection:** SQL is still assembled by **string concatenation** in both `signup()` and `login()`. `login()` only *drops the password predicate* from its `WHERE` clause; the `username` value remains concatenated raw (SQLi via username still exploitable). No parameterization, no ORM, no escaping.
- **VULN-2/3 XSS, VULN-4 Session, VULN-6 Exposed DB, VULN-7 Rate Limiting, VULN-8 CSRF:** untouched.

**Files touched (exactly four):**

| Phase | File | Nature of change |
|-------|------|------------------|
| 1 | `backend/pyproject.toml` | Add `bcrypt` to `[project].dependencies` |
| 1 | `pyproject.toml` (root) | Add `bcrypt` to `[project].dependencies` |
| 2 | `backend/app/core/security.py` | Replace MD5 with bcrypt; safe `verify_password` |
| 3 | `backend/app/services/auth_service.py` | `login()` fetch-by-username + Python verify |
| 4 | — | Migration (DB reset / re-register) — operator action, no file edit |
| 5 | — | Verification only (no edits) |

No changes to `main.py`, `auth.py`, `db/session.py`, templates, or CSS.

---

## Phase 1 — Add the bcrypt Dependency (both pyproject files)

Per spec FR-07 / AC-07, `bcrypt` must be declared in **both** manifests.

### 1.1 `backend/pyproject.toml`

**Before:**

```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "python-multipart>=0.0.6",
    "itsdangerous>=2.0.0",
]
```

**After:**

```toml
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "python-multipart>=0.0.6",
    "itsdangerous>=2.0.0",
    "bcrypt>=4.1.0",
]
```

### 1.2 `pyproject.toml` (root)

**Before:**

```toml
dependencies = [
    "fastapi>=0.136.3",
    "itsdangerous>=2.2.0",
    "python-multipart>=0.0.32",
    "uvicorn>=0.49.0",
]
```

**After:**

```toml
dependencies = [
    "fastapi>=0.136.3",
    "itsdangerous>=2.2.0",
    "python-multipart>=0.0.32",
    "uvicorn>=0.49.0",
    "bcrypt>=4.1.0",
]
```

> `bcrypt>=4.1.0` is a modern release with prebuilt wheels; any `>=4.x` is acceptable. The dependency is installed in Phase 5 via `uv sync` (not in this plan step).

---

## Phase 2 — Rewrite `backend/app/core/security.py` (MD5 → bcrypt)

Implements FR-01 (bcrypt, cost ≥ 12), FR-02 (stable signatures), FR-03 (safe verify), NFR-01/02/03/06.

**Before (current file, 9 lines):**

```python
import hashlib


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed
```

**After (exact target content):**

```python
import bcrypt

# Work factor for bcrypt. Spec NFR-01 requires >= 12.
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (per-hash random salt, cost = BCRYPT_ROUNDS).

    Returns the bcrypt hash as a str (begins with "$2b$"). Replaces the former
    unsalted MD5 implementation — closes Vulnerability #5.
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True iff `plain` matches the bcrypt `hashed` value.

    Wrapped in try/except so a stored value that is NOT a valid bcrypt hash
    (e.g. a legacy 32-char MD5 digest) returns False instead of raising.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
```

Design notes tied to the spec:
- **FR-01 / NFR-01:** `gensalt(rounds=12)` → cost factor 12; raise `BCRYPT_ROUNDS` later if latency budget allows.
- **FR-02 / AC-08:** signatures `hash_password(password: str) -> str` and `verify_password(plain: str, hashed: str) -> bool` are unchanged, so `auth_service` imports need no edit for `hash_password`.
- **FR-03 / EC-01 / EC-03 / AC-05:** `bcrypt.checkpw` raises `ValueError` on a malformed/non-bcrypt salt (legacy MD5, truncated, empty). Catching `ValueError`/`TypeError` returns `False` → legacy rows fail login with 401 instead of a 500.
- **NFR-02 / TC-04:** each `hash_password` call uses a fresh `gensalt()`, so identical passwords hash differently.
- **AC-01 / TC-10:** no `hashlib`/`md5` references remain.

---

## Phase 3 — Adjust `backend/app/services/auth_service.py` (`login()` verifies in Python)

Implements FR-04 (signup unchanged in shape), FR-05 (fetch-by-username + Python verify), FR-06 (401 contract), and preserves VULN-1 (string concatenation).

### 3.1 Import: add `verify_password`

**Before (line 7):**

```python
from app.core.security import hash_password
```

**After:**

```python
from app.core.security import hash_password, verify_password
```

### 3.2 `signup()` — no logic change

`signup()` keeps calling `hash_password(password)` and concatenating the result into its INSERT. The bcrypt output (`$2b$...`) contains `$`, `.`, `/` and base64 chars but **no single quote**, so the existing concatenated INSERT remains valid SQL. **Leave lines 10–38 exactly as-is** (INSERT still string-concatenated → VULN-1 preserved; FR-04).

### 3.3 `login()` — remove password predicate, verify in Python

Only the query string and the post-fetch check change. The query is **still built by string concatenation on `username`** (VULN-1 intact); the password is no longer part of the SQL.

**Before (lines 48–74):**

```python
    hashed = hash_password(password)

    # VULNERABILITY #1: SQL Injection via string concatenation
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + hashed + "'"

    conn = get_db()
    try:
        cursor = conn.execute(query)
        user = cursor.fetchone()
    except Exception:
        return JSONResponse(
            content={"error": "Invalid username or password"},
            status_code=401,
        )
    finally:
        conn.close()

    if user:
        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]
        request.session["email"] = user["email"]
        return JSONResponse(content={"success": True, "redirect": "/welcome"})
    else:
        return JSONResponse(
            content={"error": "Invalid username or password"},
            status_code=401,
        )
```

**After:**

```python
    # VULNERABILITY #1: SQL Injection via string concatenation (username still raw).
    # Password is NO LONGER matched in SQL — bcrypt hashes are salted, so the
    # stored hash cannot be compared with a single equality. We fetch by username
    # and verify the password in Python below.
    query = "SELECT * FROM users WHERE username = '" + username + "'"

    conn = get_db()
    try:
        cursor = conn.execute(query)
        user = cursor.fetchone()
    except Exception:
        return JSONResponse(
            content={"error": "Invalid username or password"},
            status_code=401,
        )
    finally:
        conn.close()

    if user and verify_password(password, user["password"]):
        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]
        request.session["email"] = user["email"]
        return JSONResponse(content={"success": True, "redirect": "/welcome"})
    else:
        return JSONResponse(
            content={"error": "Invalid username or password"},
            status_code=401,
        )
```

Key points:
- The `hashed = hash_password(password)` line is **removed** from `login()` (the hash is no longer needed there; hashing a candidate and string-comparing would never match a salted bcrypt hash).
- **VULN-1 preserved (AC-06 / TC-09):** `query` is still `"... WHERE username = '" + username + "'"` — raw concatenation. An injection payload in `username` (e.g. `' OR '1'='1' --`) still produces a rogue query and can return a row; login is now additionally gated by `verify_password()` on that row, but the injection itself is unchanged.
- **FR-05 / SP-02:** session set only when a row exists **and** `verify_password()` is `True`.
- **FR-06 / EC-01/EC-02/EC-03 / AC-04/AC-05:** empty creds still short-circuit (lines 42–46, unchanged); wrong password, no row, or a legacy MD5 row all fall through to the same 401 JSON. A legacy MD5 stored value makes `verify_password()` return `False` (never raise) → 401, no crash.
- **`if user:`** is deliberately combined into `if user and verify_password(...)` — `user["password"]` is only read when `user` is truthy, avoiding `None` indexing.

> **Migration consequence (documented in Phase 4):** any pre-existing MD5 account now fails `verify_password()` and cannot log in.

---

## Phase 4 — Migration Note (DB Reset / Re-Register)

This plan intentionally implements **no** rehash-on-login migration (spec §9). Consequently, accounts created under the old MD5 scheme can no longer authenticate (they return 401 via EC-01). After the code changes land, the operator must:

1. Stop the application.
2. Delete the SQLite database at the project root:
   ```bash
   rm -f vulnerable_app.db
   ```
3. Restart the app — `init_db()` recreates the `users` table on startup.
4. Re-register any needed accounts; new accounts are stored with bcrypt (`$2b$…`).

Acceptable in the lab context: the database holds only disposable educational test accounts. No data-preserving migration is required or wanted.

---

## Phase 5 — Verification (no code changes)

Mirrors spec §11 / §10 test cases.

### 5.1 Install the dependency (from project root)

```bash
uv sync
```

### 5.2 Reset the database (legacy MD5 accounts cannot authenticate)

```bash
rm -f vulnerable_app.db
```

### 5.3 Start the application (from project root)

```bash
uv run backend/app/main.py
```

App serves at `http://localhost:3001`.

### 5.4 Functional & security checks

| Check | Action | Pass condition | Spec ref |
|-------|--------|----------------|----------|
| New hash is bcrypt | Register `alice`/`pass123` at <http://localhost:3001/signup>, then inspect DB (below) | Stored `password` begins with `$2b$` | TC-01, TC-07 |
| Correct login | Log in `alice`/`pass123` at <http://localhost:3001/login> | Redirect to `/welcome`, session set | TC-02 |
| Wrong password | Log in `alice` with wrong password | HTTP 401 JSON `{"error": "Invalid username or password"}` | TC-03 |
| Distinct salts | Register `bob`/`pass123`; inspect DB | `alice` and `bob` hashes differ; both log in | TC-04 |
| Legacy MD5 → 401, no crash | Insert legacy MD5 row (below), log in `legacy`/`pass123` | HTTP 401, no 500/crash | TC-05, EC-01 |
| No MD5 in source | Inspect `security.py` | No `hashlib`/`md5` references | TC-10, AC-01 |
| Dependency present | Inspect both pyproject files | `bcrypt` in `dependencies` in each | TC-11, AC-07 |

**Inspect stored hashes:**

```bash
python -c "import sqlite3; c=sqlite3.connect('vulnerable_app.db'); print(c.execute('SELECT username,password FROM users').fetchall())"
```

**Insert a legacy MD5 row (for TC-05):**

```bash
python -c "import sqlite3,hashlib; c=sqlite3.connect('vulnerable_app.db'); c.execute(\"INSERT INTO users (username,email,password) VALUES ('legacy','legacy@test.com','\"+hashlib.md5(b'pass123').hexdigest()+\"')\"); c.commit()"
```

### 5.5 Confirm other vulnerabilities remain intact

| Vulnerability | Action | Pass condition |
|---------------|--------|----------------|
| SQLi (VULN-1) | Inspect `login()` source | `SELECT ... WHERE username = '" + username + "'"` still string-concatenated (username raw) |
| Reflected XSS (VULN-3) | Open <http://localhost:3001/search?q=%3Cscript%3Ealert(1)%3C/script%3E> | Payload reflected unescaped |
| Exposed DB (VULN-6) | Open <http://localhost:3001/download/db> | DB served, no auth |

### 5.6 File-scope check

```bash
git diff --name-only
```

Pass condition (AC-09): only these appear —

```
backend/app/core/security.py
backend/app/services/auth_service.py
backend/pyproject.toml
pyproject.toml
```

(plus `uv.lock` if regenerated by `uv sync`). No other backend file, template, or CSS is modified.

---

## 6. Risk & Rollback Notes

- **Lockout risk (expected):** all pre-existing MD5 accounts stop authenticating. This is by design; Phase 4's DB reset is mandatory after deploy. Communicate the re-register requirement.
- **Accidental over-fix risk:** the one thing that must NOT change is SQL construction. If a reviewer sees parameterized queries (`?` placeholders / `execute(query, params)`) in `login()` or `signup()`, VULN-1 was wrongly "fixed" — revert. The §5.5 SQLi check and TC-09 guard this.
- **`None` safety:** `login()` must read `user["password"]` only inside the `user and …` guard (Phase 3.3) to avoid a `TypeError` on failed lookups.
- **Dependency build:** `bcrypt>=4.x` ships wheels; if a source build is ever forced, ensure a C toolchain is present. `uv sync` handles resolution.
- **Rollback:** all changes are confined to four files on the current branch; `git checkout -- backend/ pyproject.toml` restores the MD5 implementation. The DB reset is not reversible, but the lab DB is disposable.
