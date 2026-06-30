# Dark Mode Toggle — Implementation Plan

**Version:** 1.0.0
**Last Updated:** June 30, 2026
**Parent Documents:** [dark-mode-toggle.md](./dark-mode-toggle.md), [app-foundation.md](./app-foundation.md), [PRD.md](../../docs/PRD.md), [TDD.md](../../docs/TDD.md)

---

## 0. Purpose & Ground Rules

This document is the step-by-step build plan for the light/dark theme toggle specified in [dark-mode-toggle.md](./dark-mode-toggle.md). It is a **plan only** — no source code is written in the step that produces this file.

**Additive-only guarantee.** Every edit below is purely presentational. The plan does **not** remove, weaken, or remediate any of the 8 intentional vulnerabilities (SQL Injection, Stored XSS, Reflected XSS, Session Hijacking, MD5 password storage, Exposed DB, No Rate Limiting, CSRF). In particular:

- The dashboard's `{{username}}` placeholder and the server-side `html.replace('{{username}}', username)` substitution are **left exactly as-is** — the Stored XSS stays exploitable.
- No backend file is touched (`main.py`, `auth.py`, `auth_service.py`, `security.py`, `session.py` are all untouched).
- No CSRF token, no `SameSite`/escaping change, no rate limiter, no secret-key change.

**Files touched (exactly four, all frontend):**

| Phase | File | Nature of change |
|-------|------|------------------|
| 1 | `frontend/static/css/styles.css` | Add theme custom properties + dark overrides + toggle styles; swap hardcoded hex for `var(--…)` |
| 2 | `frontend/templates/login.html` | `<head>` restore script + header toggle button + handler script |
| 3 | `frontend/templates/signup.html` | Same three additions |
| 4 | `frontend/templates/dashboard.html` | Same three additions (placeholder untouched) |
| 5 | — | Verification only (no edits) |

The `<head>` restore script, the toggle button markup, and the handler script are **byte-for-byte identical** across the three templates.

---

## Phase 1 — CSS: Theme Tokens, Dark Overrides, Toggle Styles

**File:** `frontend/static/css/styles.css`

### 1.1 Add the light-theme token block at the very top of the file

Insert a `:root` block **above** the existing `Global Reset` comment (line 1). These tokens capture the *current* palette so the light theme is pixel-identical to today (NFR-04 / AC-07).

**Before (current top of file):**

```css
/* ============================
   Global Reset & Base Styles
   ============================ */
*, *::before, *::after {
```

**After:**

```css
/* ============================
   Theme Tokens (light = default)
   ============================ */
:root {
    color-scheme: light;

    /* Surfaces */
    --bg-body: #eef1f8;            /* dashboard body bg */
    --bg-surface: #ffffff;        /* header, form panels, cards */
    --bg-input: #f8f9ff;          /* form inputs */

    /* Text */
    --text-primary: #1e293b;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --text-on-brand: #ffffff;

    /* Brand / accents */
    --brand: #1a237e;
    --brand-2: #3949ab;
    --brand-3: #283593;
    --brand-deep: #0d1b5e;

    /* Borders & lines */
    --border: #c5cae9;            /* input border */
    --border-subtle: #e2e8f0;     /* header/card border */

    /* Shadows */
    --shadow-header: 0 2px 10px rgba(26, 35, 126, 0.08);
    --shadow-card-hover: 0 4px 16px rgba(26, 35, 126, 0.10);
    --focus-glow: 0 0 0 3px rgba(57, 73, 171, 0.12);

    /* Gradients */
    --auth-gradient: linear-gradient(135deg, #0d1b5e 0%, #1a237e 50%, #283593 100%);
    --hero-gradient: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);

    /* Error palette (kept recognizably red in both themes) */
    --error-bg: #fef2f2;
    --error-border: #fecaca;
    --error-text: #991b1b;

    /* Toggle control */
    --toggle-bg: rgba(26, 35, 126, 0.08);
    --toggle-fg: #1a237e;
    --toggle-border: #c5cae9;
}

/* ============================
   Global Reset & Base Styles
   ============================ */
*, *::before, *::after {
```

### 1.2 Add the dark-theme override block immediately after `:root`

Only the values that must change for dark are overridden; gradients and brand hues are darkened for contrast (NFR-05). Insert directly below the closing `}` of `:root`:

```css
/* ============================
   Dark Theme Overrides
   ============================ */
[data-theme="dark"] {
    color-scheme: dark;

    --bg-body: #0f172a;
    --bg-surface: #1e293b;
    --bg-input: #0f172a;

    --text-primary: #e2e8f0;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --text-on-brand: #ffffff;

    --brand: #7986cb;             /* lighter indigo reads on dark surfaces */
    --brand-2: #9fa8da;
    --brand-3: #5c6bc0;
    --brand-deep: #1a237e;

    --border: #334155;
    --border-subtle: #334155;

    --shadow-header: 0 2px 10px rgba(0, 0, 0, 0.45);
    --shadow-card-hover: 0 4px 16px rgba(0, 0, 0, 0.55);
    --focus-glow: 0 0 0 3px rgba(159, 168, 218, 0.25);

    --auth-gradient: linear-gradient(135deg, #060b2e 0%, #11164a 50%, #1a237e 100%);
    --hero-gradient: linear-gradient(135deg, #11164a 0%, #283593 100%);

    --error-bg: #3b1518;
    --error-border: #7f1d1d;
    --error-text: #fca5a5;

    --toggle-bg: rgba(255, 255, 255, 0.10);
    --toggle-fg: #e2e8f0;
    --toggle-border: #334155;
}
```

### 1.3 Replace hardcoded colors with token references

Swap the existing literal values for `var(--…)`. This is a mechanical refactor — **no rule is added or removed**, only the right-hand color values change to variables. Key replacements (full list applied across the file):

| Selector | Property | Before | After |
|----------|----------|--------|-------|
| `body` | `color` | `#1e293b` | `var(--text-primary)` |
| `a`, `.form-link a` | `color` | `#1a237e` | `var(--brand)` |
| `.header` | `background` | `#ffffff` | `var(--bg-surface)` |
| `.header` | `border-bottom` | `1px solid #e2e8f0` | `1px solid var(--border-subtle)` |
| `.header` | `box-shadow` | `0 2px 10px rgba(...)` | `var(--shadow-header)` |
| `.header-title` | `color` | `#1a237e` | `var(--brand)` |
| `.auth-left` | `background` | `linear-gradient(...)` | `var(--auth-gradient)` |
| `.auth-right` | `background` | `#ffffff` | `var(--bg-surface)` |
| `.form-title` | `color` | `#1e293b` | `var(--text-primary)` |
| `.form-subtitle` | `color` | `#64748b` | `var(--text-muted)` |
| `.form-label` | `color` | `#475569` | `var(--text-secondary)` |
| `.form-input` | `background` | `#f8f9ff` | `var(--bg-input)` |
| `.form-input` | `border` | `1.5px solid #c5cae9` | `1.5px solid var(--border)` |
| `.form-input` | `color` | `#1e293b` | `var(--text-primary)` |
| `.form-input:focus` | `border-color` | `#3949ab` | `var(--brand-2)` |
| `.form-input:focus` | `box-shadow` | `0 0 0 3px rgba(...)` | `var(--focus-glow)` |
| `.btn-primary` | `background` | `#1a237e` | `var(--brand)` |
| `.btn-primary:hover` | `background` | `#283593` | `var(--brand-3)` |
| `.error-message` | `background`/`border`/`color` | red literals | `var(--error-bg)` / `var(--error-border)` / `var(--error-text)` |
| `.dashboard-body` | `background` | `#eef1f8` | `var(--bg-body)` |
| `.hero-banner` | `background` | `linear-gradient(...)` | `var(--hero-gradient)` |
| `.mission-card`, `.vuln-card` | `background` | `#ffffff` | `var(--bg-surface)` |
| `.mission-card`, `.vuln-card` | `border` | `1px solid #e2e8f0` | `1px solid var(--border-subtle)` |
| `.vuln-card:hover` | `box-shadow` | `0 4px 16px rgba(...)` | `var(--shadow-card-hover)` |
| `.section-title`, `.card-title` | `color` | `#1e293b` | `var(--text-primary)` |
| `.mission-description`, `.card-description` | `color` | `#475569` | `var(--text-secondary)` |
| `.vuln-header` | `color` | `#64748b` | `var(--text-muted)` |
| `.step-card` | `background` | `#1a237e` | `var(--brand)` |

Notes:
- The colored `.tag-*` vulnerability pills, the decorative `.circle` overlays, and white-on-gradient text inside `.auth-left` / `.hero-*` / `.step-card` keep their existing literal values (they already sit on dark gradient surfaces and read in both themes). Leaving the tag colors fixed also preserves the dashboard's documented tag-color mapping.
- Add a smooth transition once, on `body`:

  **Before:** `body { font-family: ...; ... line-height: 1.6; }`
  **After:** append `background-color: var(--bg-body); transition: background-color 0.2s ease, color 0.2s ease;` to the `body` rule. (Auth pages have no `dashboard-body` class, so giving `body` the token background is harmless — it's covered by panels — and gives the dark theme a correct base canvas.)

### 1.4 Add the toggle control styles

Append a new section at the **end** of the file, before nothing else is needed (after the existing `@media` block is fine — the rules are not media-scoped):

```css
/* ============================
   Theme Toggle Control
   ============================ */
.theme-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    margin-right: 12px;
    font-size: 1.1rem;
    line-height: 1;
    background: var(--toggle-bg);
    color: var(--toggle-fg);
    border: 1px solid var(--toggle-border);
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s, border-color 0.2s;
}

.theme-toggle:hover {
    background: var(--brand-2);
    color: var(--text-on-brand);
}

.theme-toggle:focus-visible {
    outline: none;
    box-shadow: var(--focus-glow);
}

/* Show the correct glyph per active theme */
.theme-toggle .icon-dark { display: inline; }
.theme-toggle .icon-light { display: none; }
[data-theme="dark"] .theme-toggle .icon-dark { display: none; }
[data-theme="dark"] .theme-toggle .icon-light { display: inline; }
```

The two-glyph approach lets CSS alone swap the moon/sun icon based on `data-theme`, so the JS handler only flips the attribute, label, and storage.

---

## Phase 2 — `login.html`: Restore Script, Toggle Button, Handler

**File:** `frontend/templates/login.html`

### 2.1 Pre-render restore script in `<head>` (FOUC prevention — FR-04, NFR-02)

Insert as the **first child of `<head>`**, before the `<title>` and the stylesheet `<link>`, so `data-theme` is set before any paint.

**Before:**

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Security Vulnerability Lab</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
```

**After:**

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script>
        // Restore theme before first paint (no flash). See dark-mode-toggle spec FR-04/FR-05.
        (function () {
            try {
                var saved = localStorage.getItem('theme');
                if (saved !== 'light' && saved !== 'dark') {
                    saved = (window.matchMedia &&
                             window.matchMedia('(prefers-color-scheme: dark)').matches)
                            ? 'dark' : 'light';
                }
                document.documentElement.setAttribute('data-theme', saved);
            } catch (e) {
                document.documentElement.setAttribute('data-theme', 'light');
            }
        })();
    </script>
    <title>Login - Security Vulnerability Lab</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
```

Behavior covered: invalid/missing value → system fallback (EC-02, EC-13), `matchMedia` absent → light (EC-03), storage throws → light, no crash (EC-01/TC-12). The fallback path does **not** write to storage (FR-05 / TC-06).

### 2.2 Toggle button in the header (FR-01, FR-06, FR-07)

Add the button as the **first child of `.header-logos`** (places it left of the three logos). `aria-label` starts as the light-state action; the handler keeps it in sync.

**Before:**

```html
        <div class="header-logos">
            <img src="/static/images/PUCIT_Logo.png" alt="PUCIT" class="header-logo">
```

**After:**

```html
        <div class="header-logos">
            <button type="button" id="theme-toggle" class="theme-toggle"
                    aria-label="Switch to dark theme">
                <span class="icon-dark" aria-hidden="true">🌙</span>
                <span class="icon-light" aria-hidden="true">☀️</span>
            </button>
            <img src="/static/images/PUCIT_Logo.png" alt="PUCIT" class="header-logo">
```

`type="button"` prevents any accidental form submission. The element is a native `<button>`, so it is tab-reachable and Enter/Space-activatable (FR-07 / TC-11).

### 2.3 Toggle handler script

Add just before the existing `</script>`-bearing block's closing — simplest is to **append a new `<script>` right before `</body>`**, after the existing login `<script>`:

```html
    <script>
        // Theme toggle: flip data-theme, persist, and keep aria-label = next action.
        (function () {
            var btn = document.getElementById('theme-toggle');
            if (!btn) return;
            function syncLabel() {
                var dark = document.documentElement.getAttribute('data-theme') === 'dark';
                btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
            }
            syncLabel();
            btn.addEventListener('click', function () {
                var dark = document.documentElement.getAttribute('data-theme') === 'dark';
                var next = dark ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                try { localStorage.setItem('theme', next); } catch (e) { /* EC-01: ignore */ }
                syncLabel();
            });
        })();
    </script>
```

`syncLabel()` runs once on load so the label is correct even when the restore script applied a system-preference dark theme (FR-06 / TC-10). The `try/catch` around `setItem` keeps the in-page toggle working when storage is blocked (EC-01 / TC-12).

> **Vulnerability note:** `login.html`'s existing fetch-based login `<script>` (lines 64–86) is **unchanged**. No CSRF token is added to the login flow.

---

## Phase 3 — `signup.html`: Restore Script, Toggle Button, Handler

**File:** `frontend/templates/signup.html`

Apply the **identical** three edits from Phase 2:

1. **2.1 restore script** → insert as first child of `<head>` (before `<title>Sign Up - …</title>`). Byte-for-byte identical to Phase 2.1.
2. **2.2 toggle button** → insert as first child of `.header-logos` (identical markup).
3. **2.3 handler script** → append a new `<script>` immediately before `</body>`, after the existing signup confirm-password `<script>` (lines 71–86).

> **Vulnerability note:** The existing client-side `password !== confirm` validation script is **unchanged**. The signup `<form action="/signup" method="POST">` keeps **no CSRF token** (VULN-8 intact). Username input remains unsanitized, preserving Stored XSS (VULN-2).

---

## Phase 4 — `dashboard.html`: Restore Script, Toggle Button, Handler

**File:** `frontend/templates/dashboard.html`

Apply the same three edits:

1. **2.1 restore script** → first child of `<head>` (before `<title>Dashboard - …</title>`).
2. **2.2 toggle button** → first child of `.header-logos`.
3. **2.3 handler script** → append a new `<script>` immediately before `</body>` (dashboard currently has no script block, so this is the only `<script>` on the page).

> **Critical vulnerability preservation (AC-08 / TC-07):** The hero line
> `<span class="hero-username">Logged in as <strong>{{username}}</strong></span>` (line 27) is **left exactly as written**. The `{{username}}` token must remain so the backend's `html.replace('{{username}}', username)` continues to inject the username **unescaped**. Do not wrap, escape, or relocate it. The Stored XSS must still fire on dashboard load.

---

## Phase 5 — Verification (no code changes)

Run the app and execute the spec's verification steps ([dark-mode-toggle.md §10](./dark-mode-toggle.md)).

### 5.1 Start the application (from project root)

```bash
uv run backend/app/main.py
```

App serves at `http://localhost:3001`.

### 5.2 Toggle, persistence, accessibility

| Check | Action | Pass condition | Spec ref |
|-------|--------|----------------|----------|
| Toggle present | Open `http://localhost:3001/login` and `/signup` | Focusable toggle button in header | TC-01 |
| Toggle to dark/light | Click toggle | Page flips theme; DevTools → Application → Local Storage shows `theme` updating | TC-02, TC-03 |
| Keyboard | Tab to toggle, press Space/Enter | Theme switches like a click | TC-11 |
| aria-label | Inspect before/after switching | Reads "Switch to dark theme" in light, "Switch to light theme" in dark | TC-10 |
| Persist on reload | Select dark, reload | Dark restored, no flash | TC-04, TC-09 |
| Persist across pages | With dark set, navigate `/login` → `/signup` → (login) → `/welcome` | All render dark before paint | TC-05 |
| System fallback | Clear `localStorage.theme`, set OS to dark, reload `/login` | Dark renders; `theme` stays unset | TC-06 |
| Invalid value | Set `localStorage.theme = "blue"`, reload | Falls back to system preference | TC-13 |
| Storage blocked | Block storage (privacy mode), load + click toggle | Page renders; toggle still flips current page; no console error | TC-12 |
| Light parity | View light theme | Header, panels, cards, tags match pre-feature colors | TC-14 |

### 5.3 Vulnerabilities still intact (must remain exploitable)

| Check | Action | Pass condition | Spec ref |
|-------|--------|----------------|----------|
| Stored XSS | Sign up username `<script>alert(1)</script>`, log in, open `/welcome` | Script executes — theming did not escape `{{username}}` | TC-07 / AC-08 |
| Reflected XSS | Open `http://localhost:3001/search?q=%3Cscript%3Ealert(1)%3C/script%3E` | Payload reflected unescaped | TC-08 |
| Exposed DB | Open `http://localhost:3001/download/db` | DB served, no auth | PRD VULN-6 |
| CSRF | Inspect `/signup` form and `/login` flow | No CSRF token added | PRD VULN-8 |

### 5.4 File-scope check

```bash
git diff --name-only
```

Pass condition (TC-15 / AC-09): output is exactly

```
frontend/static/css/styles.css
frontend/templates/dashboard.html
frontend/templates/login.html
frontend/templates/signup.html
```

No backend file (`backend/app/**`) appears.

---

## 6. Risk & Rollback Notes

- **Visual regression risk (light theme):** mitigated by sourcing every light token from the current literal value (§1.1); verify with TC-14 before committing.
- **FOUC risk:** the restore script must stay in `<head>` *before* the stylesheet `<link>`; if moved to end-of-body the dark theme will flash. Re-check TC-09 after any template reordering.
- **Accidental vulnerability "fix" risk:** the only forbidden change is altering `{{username}}` or adding tokens/escaping to forms. Phase 4's note and the §5.3 checks guard this; a failing TC-07 means the feature broke the lab and must be reverted.
- **Rollback:** all changes live in four frontend files on `feature/dark-mode-toggle`; `git checkout -- frontend/` restores the pre-feature state with no backend or DB impact.
