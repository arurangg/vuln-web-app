# Bcrypt Password Hashing Specification

**Version:** 1.0.0
**Last Updated:** July 1, 2026
**Parent Documents:** [PRD.md](../../docs/PRD.md), [TDD.md](../../docs/TDD.md), [app-foundation.md](./app-foundation.md)

---

## 1. Overview / Purpose

This document specifies the remediation of **Vulnerability #5 — Weak Password Storage**. The application currently hashes passwords with unsalted MD5 (`hashlib.md5(...).hexdigest()` in `backend/app/core/security.py`), which is fast, unsalted, and trivially reversible via rainbow tables. This change replaces MD5 with **bcrypt at a work factor of at least 12**, preserving the two public function signatures (`hash_password(password)` and `verify_password(plain, hashed)`) so callers do not change shape. Because bcrypt embeds a random salt in every hash, the same password produces a different hash each time, and a stored hash can no longer be matched *inside* the SQL query — so `auth_service.login()` is adjusted to fetch the user by username and verify the password in Python via `verify_password()`. This fix **closes vulnerability #5 only**; all other intentional lab vulnerabilities remain deliberately intact.

---

## 2. Scope & Non-Goals

### 2.1 In Scope (Vulnerability Being Fixed)

| # | Vulnerability | Status After This Change |
|---|---------------|--------------------------|
| 5 | Weak Password Storage (MD5, no salt) | **FIXED** — replaced with bcrypt, work factor ≥ 12, per-hash random salt |

### 2.2 Explicitly Out of Scope (Intentional Vulnerabilities That Remain Unfixed)

This task is surgical. The following seven vulnerabilities **must remain exploitable** and unchanged:

| # | Vulnerability | Status After This Change |
|---|---------------|--------------------------|
| 1 | SQL Injection (`auth_service.py`) | Unchanged — queries stay built by **string concatenation** (not parameterized) |
| 2 | Stored XSS (`{{username}}` in dashboard) | Unchanged — intentionally vulnerable |
| 3 | Reflected XSS (`/search`) | Unchanged — intentionally vulnerable |
| 4 | Session Hijacking (hardcoded secret) | Unchanged — intentionally vulnerable |
| 6 | Exposed DB (`/download/db`) | Unchanged — intentionally vulnerable |
| 7 | No Rate Limiting | Unchanged — intentionally vulnerable |
| 8 | CSRF (no tokens) | Unchanged — intentionally vulnerable |

**Non-Goals:**

- **No change to SQL query construction.** The SQL Injection flaw (VULN-1) is a separate task. Both `signup()` and `login()` continue to build their SQL by string concatenation. `login()` drops only the password predicate from the `WHERE` clause; the `username` value is still concatenated directly into the query (SQLi via the username field remains fully exploitable).
- **No parameterized queries, no ORM, no input sanitization.**
- **No password-strength rules, no account lockout, no rate limiting** (VULN-7 stays open).
- **No automatic MD5→bcrypt migration / rehash-on-login.** Legacy MD5 accounts simply can no longer authenticate and must re-register (see §9 migration note).
- **No change to session handling, secret key, or the `/download/db` endpoint.**

---

## 3. Affected Files

Exactly four files change. No frontend, template, route-handler, or database-layer file is modified.

| Path | Change |
|------|--------|
| `backend/app/core/security.py` | Replace MD5 implementation of `hash_password()` with bcrypt (work factor ≥ 12); reimplement `verify_password()` around `bcrypt.checkpw` wrapped in `try/except` returning `False` for non-bcrypt (legacy MD5) values. |
| `backend/app/services/auth_service.py` | In `login()`, remove the password predicate from the concatenated SQL, fetch the user row by `username`, and compare the submitted password against the stored hash with `verify_password()` in Python. `signup()` still calls `hash_password()` and still concatenates the resulting hash into its INSERT. |
| `backend/pyproject.toml` | Add `bcrypt` to `[project].dependencies`. |
| `pyproject.toml` (root) | Add `bcrypt` to `[project].dependencies`. |

No changes to `main.py`, `auth.py`, `db/session.py`, templates, or CSS.

---

## 4. Functional Requirements

- **FR-01: Bcrypt Hashing.** `hash_password(password: str) -> str` returns a bcrypt hash string generated with a randomly generated salt at a **cost/work factor of at least 12**. The returned value is the UTF-8 decoded bcrypt hash (begins with the `$2b$` prefix).

- **FR-02: Stable Public API.** The module keeps the same two public callables with the same signatures: `hash_password(password: str) -> str` and `verify_password(plain: str, hashed: str) -> bool`. Callers (`auth_service.signup()` and `auth_service.login()`) require no import changes.

- **FR-03: Safe Verification.** `verify_password(plain: str, hashed: str) -> bool` compares `plain` against `hashed` using `bcrypt.checkpw`. The call is wrapped in `try/except` so that a stored value which is **not** a valid bcrypt hash (e.g. a legacy 32-hex-char MD5 digest) causes the function to return `False` — never raise.

- **FR-04: Signup Stores Bcrypt.** `signup()` continues to call `hash_password(password)` and concatenate the resulting bcrypt string into its INSERT statement. New accounts are persisted with a `$2b$`-prefixed hash. (The INSERT remains string-concatenated — SQLi preserved.)

- **FR-05: Login Verifies in Python.** Because bcrypt salts each hash, the stored hash cannot be matched inside SQL. `login()` builds a concatenated `SELECT ... WHERE username = '<username>'` query (no password predicate), fetches the row, and — if a row exists — calls `verify_password(password, row["password"])`. Session is established **only** when verification returns `True`.

- **FR-06: Failed Login Contract Unchanged.** On no matching row, or when `verify_password()` returns `False`, `login()` returns the existing JSON error contract: `{"error": "Invalid username or password"}` with HTTP status **401**. No stack trace, no crash.

- **FR-07: Dependency Declaration.** `bcrypt` is declared as a runtime dependency in **both** `backend/pyproject.toml` and the root `pyproject.toml`.

---

## 5. Non-Functional Requirements

- **NFR-01: Work Factor.** Bcrypt cost is ≥ 12. Higher is acceptable if login latency stays within the PRD's performance envelope (≈200 ms average).

- **NFR-02: Per-Hash Salt.** Every call to `hash_password()` with identical input yields a distinct hash (bcrypt's built-in random salt). No salt is stored or managed separately.

- **NFR-03: Backward-Safe Reads.** Reading a legacy MD5 value from the database must never raise; it deterministically fails verification (returns `False`).

- **NFR-04: Surgical Change.** Only the four files in §3 change. No other vulnerability's code path is altered; the SQL is still assembled by string concatenation.

- **NFR-05: No New Attack Surface.** The fix introduces no new endpoints, no new session behavior, and no logging of plaintext passwords or hashes.

- **NFR-06: Encoding.** Passwords are encoded to bytes (UTF-8) for bcrypt; stored hashes are decoded to `str` for storage and comparison, consistent with the existing `str`-typed `password` column.

---

## 6. Success Paths

- **SP-01: New Registration Stores Bcrypt.** User registers via `POST /signup`. `hash_password()` returns a `$2b$`-prefixed hash, which is inserted into `users.password`. Server redirects to `/login`.

- **SP-02: Successful Login.** A user registered *after* this change logs in with the correct password. `login()` fetches the row by username, `verify_password()` returns `True`, the session (`user_id`, `username`, `email`) is set, and the JSON success/redirect response is returned.

- **SP-03: Distinct Salts.** Two different users register with the *same* password. Their stored hashes differ (different salts), yet both can log in successfully.

- **SP-04: Wrong Password Rejected.** A valid username with an incorrect password: the row is fetched, `verify_password()` returns `False`, and the server returns the 401 JSON error.

---

## 7. Edge Cases

- **EC-01: Legacy MD5 Row.** A user row created before this change holds a 32-char MD5 hex digest. On login attempt, `bcrypt.checkpw` treats the stored value as an invalid bcrypt hash; the `try/except` yields `False`; the server returns **401** without crashing. (The account must re-register — see §9.)

- **EC-02: Empty Credentials.** Empty username or password still short-circuits to the existing 401 JSON error before any hashing or DB access (unchanged behavior).

- **EC-03: Corrupted/Non-Bcrypt Stored Value.** Any stored `password` value that is not a parseable bcrypt hash (truncated, empty, arbitrary text) causes `verify_password()` to return `False`, never raise.

- **EC-04: SQL Injection Still Works via Username.** Because the username is still concatenated into the `SELECT`, an injection payload in the username field (e.g. `' OR '1'='1' --`) can still return a row. If such a row is returned, login now additionally requires `verify_password()` against that row's stored hash; the SQLi flaw itself (VULN-1) is unchanged and still demonstrable — this spec neither strengthens nor removes it.

- **EC-05: Unicode Password.** A password containing multibyte UTF-8 characters hashes and verifies correctly (encoded to bytes before bcrypt).

---

## 8. Acceptance Criteria

- **AC-01:** `backend/app/core/security.py` contains no `hashlib`/MD5 usage; `hash_password()` produces bcrypt hashes at work factor ≥ 12.
- **AC-02:** A newly registered account's stored `password` value begins with `$2b$`.
- **AC-03:** Two accounts created with the same password have **different** stored hashes, and both log in successfully.
- **AC-04:** Correct password logs in; wrong password returns HTTP 401 with `{"error": "Invalid username or password"}`.
- **AC-05:** A legacy MD5 row returns HTTP 401 on login **without** raising an exception or 500 error.
- **AC-06:** `login()` no longer includes the password in its SQL predicate; the SQL is still built by string concatenation (SQLi via username preserved).
- **AC-07:** `bcrypt` appears in the `dependencies` list of both `backend/pyproject.toml` and the root `pyproject.toml`.
- **AC-08:** The public signatures `hash_password(password)` and `verify_password(plain, hashed)` are unchanged.
- **AC-09:** Only the four files in §3 are modified; all other 7 vulnerabilities remain intact.

---

## 9. Migration Note (DB Reset / Re-Register)

Bcrypt cannot verify passwords stored as MD5, and this spec intentionally implements **no** rehash-on-login migration. Therefore existing accounts created under MD5 **cannot log in** after this change and will receive a 401 (EC-01).

Required operator action after deploying the change:

1. Stop the application.
2. Delete the SQLite database file at the project root: `vulnerable_app.db`.
3. Restart the application (the `users` table is recreated on startup by `init_db()`).
4. Re-register any needed accounts; new accounts are stored with bcrypt (`$2b$…`).

This is acceptable in the lab context, where the database holds only disposable educational test accounts.

---

## 10. Test Cases

| ID | Scenario | Precondition | Expected Result |
|----|----------|--------------|-----------------|
| TC-01 | New signup stores bcrypt | Fresh DB | `users.password` for the new row begins with `$2b$` |
| TC-02 | Successful login (post-fix account) | Account registered after change | 200 JSON `{"success": true, "redirect": "/welcome"}`, session set |
| TC-03 | Wrong password | Valid username, bad password | HTTP 401 JSON `{"error": "Invalid username or password"}` |
| TC-04 | Same password → different hashes | Two users registered with identical password | Stored hashes differ; both users can log in |
| TC-05 | Legacy MD5 row rejected safely | A row whose `password` is a 32-char MD5 digest | HTTP 401, no exception/500, app keeps running |
| TC-06 | `verify_password` on MD5 value | `verify_password("anything", "<32-char md5 hex>")` | Returns `False` (no raise) |
| TC-07 | `hash_password` prefix & cost | Call `hash_password("pass123")` | Returns `$2b$` string with cost ≥ 12 |
| TC-08 | Empty credentials | username="" or password="" | HTTP 401 before hashing/DB access |
| TC-09 | SQLi via username still works | Username `' OR '1'='1' --` | VULN-1 behavior unchanged (query still concatenated); login still gated by `verify_password()` on the returned row |
| TC-10 | No MD5 in source | Inspect `security.py` | No `hashlib`/`md5` references remain |
| TC-11 | Dependency present | Inspect both pyproject files | `bcrypt` listed in `dependencies` in each |

---

## 11. Verification Steps

1. **Install the new dependency** (from project root):

   ```bash
   uv sync
   ```

2. **Reset the database** (legacy MD5 accounts cannot authenticate — see §9):

   ```bash
   rm -f vulnerable_app.db
   ```

3. **Start the application** (from project root):

   ```bash
   uv run backend/app/main.py
   ```

   App serves at `http://localhost:3001`.

4. **Register a fresh account** — open <http://localhost:3001/signup>, create a user (e.g. `alice` / `pass123`), and confirm the redirect to `/login`.

5. **Confirm the stored hash is bcrypt (TC-01, TC-07):**

   ```bash
   python -c "import sqlite3; c=sqlite3.connect('vulnerable_app.db'); print(c.execute('SELECT username,password FROM users').fetchall())"
   ```

   Expected: `alice`'s password value begins with `$2b$`.

6. **Correct password logs in (TC-02):** at <http://localhost:3001/login>, log in as `alice` / `pass123` → redirected to `/welcome`.

7. **Wrong password rejected (TC-03):** log in as `alice` with a wrong password → inline error, HTTP 401 JSON `{"error": "Invalid username or password"}`.

8. **Same password → different hashes (TC-04):** register `bob` / `pass123`, then re-run the query from step 5. Expected: `alice` and `bob` have **different** `$2b$` hashes; both accounts log in successfully.

9. **Legacy MD5 row returns 401 without crashing (TC-05):** insert a legacy-style row and attempt login:

   ```bash
   python -c "import sqlite3,hashlib; c=sqlite3.connect('vulnerable_app.db'); c.execute(\"INSERT INTO users (username,email,password) VALUES ('legacy','legacy@test.com','\"+hashlib.md5(b'pass123').hexdigest()+\"')\"); c.commit()"
   ```

   Then log in as `legacy` / `pass123` at <http://localhost:3001/login>. Expected: HTTP 401 JSON error; the server does **not** return a 500 or crash.

10. **Confirm other vulnerabilities remain intact:**
    - **SQLi (VULN-1):** the login SQL is still string-concatenated on the username (verify by code inspection of `login()`); an injected username still forms a raw query.
    - **Reflected XSS:** <http://localhost:3001/search?q=%3Cscript%3Ealert(1)%3C/script%3E> still reflects unescaped.
    - **Exposed DB:** <http://localhost:3001/download/db> still serves the database with no auth.

11. **File-scope check:**

    ```bash
    git diff --name-only
    ```

    Expected: only `backend/app/core/security.py`, `backend/app/services/auth_service.py`, `backend/pyproject.toml`, and `pyproject.toml` (plus `uv.lock` if regenerated by `uv sync`).
