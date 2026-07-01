# CLAUDE.md

## Project Context

This is an **intentionally vulnerable web application** for security education. It originally shipped with 8 OWASP Top 10 vulnerabilities through deliberate, exploitable flaws that students can attack, understand, and remediate. Vulnerability #5 (weak password storage) has since been **remediated with bcrypt** (see the Vulnerability Map below); **7 vulnerabilities remain active**.

**WARNING:** The remaining vulnerabilities are intentional. Do not "fix" them unless explicitly asked.

## Development Commands

```bash
# Install backend dependencies
cd backend && uv sync

# Run the application (from project root)
uv run backend/app/main.py

# Access at http://localhost:3001
```

## Architecture

Three-layer architecture: Presentation (HTML/CSS/JS) → Application (FastAPI) → Data (SQLite).

```
backend/app/
├── main.py              # Entry point, middleware, static mounts
├── core/security.py     # bcrypt password hashing (work factor 12) — VULN-5 remediated
├── db/session.py        # SQLite connection and init
├── services/auth_service.py  # Auth business logic (SQL injection here; login verifies via bcrypt in Python)
└── api/routes/auth.py   # HTTP route handlers

frontend/
├── templates/           # HTML templates (loaded from disk each request; light/dark theme toggle in header)
└── static/              # CSS and images (theme via CSS custom properties + [data-theme])
```

## Vulnerability Map

| # | Vulnerability | File | Mechanism |
|---|---------------|------|-----------|
| 1 | SQL Injection | `backend/app/services/auth_service.py` | String concatenation in SQL queries |
| 2 | Stored XSS | `backend/app/api/routes/auth.py` | Unescaped `{{username}}` in dashboard |
| 3 | Reflected XSS | `backend/app/api/routes/auth.py` | Unescaped query param in search |
| 4 | Session Hijacking | `backend/app/main.py` | Hardcoded secret `"super-secret-key-12345"` |
| 5 | ~~Weak Password~~ ✅ **Fixed** | `backend/app/core/security.py` | **Remediated:** bcrypt (work factor 12), no longer MD5; password verified in Python via `verify_password()` |
| 6 | Exposed DB | `backend/app/api/routes/auth.py` | No auth on `/download/db` |
| 7 | No Rate Limit | Global | No rate limiting middleware |
| 8 | CSRF | Global | No CSRF tokens |

## Frontend-Backend Integration

- **Login**: `fetch()` POST → JSON response → client-side redirect. `login()` fetches the user by username (still string-concatenated) and verifies the password with bcrypt in Python — the password is no longer part of the SQL.
- **Signup**: Standard form POST → server redirect. Password stored as a bcrypt hash (`$2b$…`).
- **Dashboard**: Server-side `str.replace('{{username}}', ...)` — no template engine
- **Theme toggle**: `data-theme` attribute on `<html>` + CSS custom properties. Preference persisted in `localStorage["theme"]`, restored in an inline `<head>` script before paint (no FOUC), falls back to `prefers-color-scheme`. Present on login, signup, and dashboard.

## Important Rules

- Never use parameterized queries in `auth_service.py` or `auth.py` (SQL is still string-concatenated — VULN-1 stays active)
- Never add CSRF tokens to forms
- Never change the session secret key
- Never add rate limiting middleware
- Password hashing uses **bcrypt** (work factor ≥ 12) in `security.py` — do **not** revert to MD5. `verify_password()` wraps `bcrypt.checkpw` in try/except so legacy MD5 rows return `False` (401) instead of crashing.
- The dark-mode toggle is additive/presentational — do not remove it or use it to alter/escape any vulnerability (e.g. the unescaped `{{username}}` must stay).

## Specification Hierarchy

1. `docs/PRD.md` — Product requirements
2. `docs/TDD.md` — Technical design
3. `.claude/specs/app-foundation.md` — Implementation specification
4. `.claude/specs/app-foundation-plan.md` — Implementation plan
5. `.claude/specs/dark-mode-toggle.md` / `dark-mode-toggle-plan.md` — Dark-mode feature spec & plan
6. `.claude/specs/bcrypt-password-hashing.md` / `bcrypt-password-hashing-plan.md` — bcrypt remediation spec & plan (VULN-5)
