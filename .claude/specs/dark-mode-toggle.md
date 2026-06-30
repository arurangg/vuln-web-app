# Dark Mode Toggle Specification

**Version:** 1.0.0
**Last Updated:** June 30, 2026
**Parent Documents:** [PRD.md](../../docs/PRD.md), [TDD.md](../../docs/TDD.md), [app-foundation.md](./app-foundation.md)

---

## 1. Overview / Purpose

This document specifies a **light/dark theme toggle** for the Vulnerable Web Application's three pages (login, signup, dashboard). The toggle lets a user switch between a light and a dark visual theme. The chosen theme is persisted in browser `localStorage` under the key `"theme"` and restored **before first paint** to avoid a flash of the wrong theme (FOUC). When no saved value exists, the theme falls back to the operating system preference via the `prefers-color-scheme` media query. The feature is implemented purely with **CSS custom properties** and a `data-theme` attribute on the `<html>` element — no JavaScript framework, no build step, no server involvement.

This task is **purely additive and presentational**. It changes only how the existing pages look; it does not alter authentication, routing, data handling, or any vulnerability. It introduces no new endpoints and touches no backend file.

---

## 2. Scope & Non-Goals

### 2.1 In Scope

- A theme toggle control rendered in the shared header on the login, signup, and dashboard pages.
- A light theme (the current default appearance) and a new dark theme.
- Theme persistence in `localStorage["theme"]` with values `"light"` or `"dark"`.
- System-preference fallback (`prefers-color-scheme: dark`) when no saved value exists.
- Pre-render theme restoration to prevent a flash of the wrong theme.
- Keyboard accessibility and an `aria-label` that reflects the **current action** (i.e., the theme the toggle will switch to).
- CSS refactor of `frontend/static/css/styles.css` to drive colors from CSS custom properties so both themes share one stylesheet.

### 2.2 Explicitly Out of Scope (Vulnerabilities That Intentionally Remain Unfixed)

This feature **must not** add, remove, weaken, or remediate any of the 8 lab vulnerabilities. All of the following remain intentionally present and unchanged:

| # | Vulnerability | Status After This Feature |
|---|---------------|----------------------------|
| 1 | SQL Injection (`auth_service.py`) | Unchanged — intentionally vulnerable |
| 2 | Stored XSS (`{{username}}` in dashboard) | Unchanged — intentionally vulnerable |
| 3 | Reflected XSS (`/search`) | Unchanged — intentionally vulnerable |
| 4 | Session Hijacking (hardcoded secret) | Unchanged — intentionally vulnerable |
| 5 | Weak Password (MD5, no salt) | Unchanged — intentionally vulnerable |
| 6 | Exposed DB (`/download/db`) | Unchanged — intentionally vulnerable |
| 7 | No Rate Limiting | Unchanged — intentionally vulnerable |
| 8 | CSRF (no tokens) | Unchanged — intentionally vulnerable |

**Non-Goals:**

- No theme preference is stored server-side or in the session — persistence is client-only (`localStorage`).
- No theming of error states' semantic meaning (error red stays recognizably red in both themes).
- No new dependencies, template engine, or framework.
- No change to the `{{username}}` placeholder, the `str.replace()` substitution, or any escaping behavior. The dashboard must continue to render the username **unescaped**.
- No CSRF token, no rate limiter, no secret-key change, no parameterized queries, no password-hash change.

---

## 3. Affected Files

Exactly four existing files are modified. **No** new source files, no backend changes.

| Path | Change |
|------|--------|
| `frontend/static/css/styles.css` | Add `:root` light custom properties, `[data-theme="dark"]` overrides, and `.theme-toggle` control styles; replace hardcoded colors with `var(--…)` references. |
| `frontend/templates/login.html` | Add pre-render restore script in `<head>`; add toggle button in `.header`; add toggle-handler script. |
| `frontend/templates/signup.html` | Same three additions as login. |
| `frontend/templates/dashboard.html` | Same three additions as login. The `{{username}}` placeholder is left exactly as-is. |

The pre-render restore script and the toggle markup/handler are **identical** across the three templates so behavior is consistent.

---

## 4. Functional Requirements

- **FR-01: Toggle Control.** Each of the three pages renders a single theme-toggle control inside the shared `.header`, to the left of the organizational logos. The control is a `<button>` element so it is natively focusable and keyboard-operable.

- **FR-02: Theme Application.** The active theme is expressed by a `data-theme` attribute on the root `<html>` element. `data-theme="light"` (or absence of the attribute) yields the light theme; `data-theme="dark"` yields the dark theme. All themed colors derive from CSS custom properties whose values change with this attribute.

- **FR-03: Persistence.** When the user activates the toggle, the new theme (`"light"` or `"dark"`) is written to `localStorage` under the key `"theme"`. The value persists across reloads and across the three pages within the same origin.

- **FR-04: Restore Before Render.** A small inline script placed in `<head>` (before the stylesheet `<link>` and before `<body>`) reads `localStorage["theme"]` and sets `data-theme` on `<html>` **before first paint**, eliminating any flash of the wrong theme.

- **FR-05: System-Preference Fallback.** When `localStorage["theme"]` is absent (or not one of `"light"`/`"dark"`), the restore script consults `window.matchMedia('(prefers-color-scheme: dark)')`. If it matches, the dark theme is applied; otherwise light. This fallback does **not** write to `localStorage` — only an explicit user toggle persists a value.

- **FR-06: Accessible Label.** The toggle exposes an `aria-label` describing the **action it will perform** given the current state — e.g., while light is active the label reads "Switch to dark theme", and while dark is active it reads "Switch to light theme". The label is updated whenever the theme changes.

- **FR-07: Keyboard Operability.** The toggle is reachable in tab order and activatable with both Enter and Space (native `<button>` behavior). A visible focus indicator is present in both themes.

- **FR-08: Vulnerability Preservation.** No change in these files alters authentication, routing, escaping, or any of the 8 vulnerabilities. The dashboard continues to inject `{{username}}` via the existing server-side `str.replace()` with no escaping.

---

## 5. Non-Functional Requirements

- **NFR-01: No Framework.** Implemented with vanilla CSS custom properties and a few lines of inline vanilla JavaScript. No external scripts, no package additions.

- **NFR-02: No Flash (FOUC).** Theme restoration must run synchronously in `<head>` before render. Deferred or end-of-body scripts are not acceptable for restoration.

- **NFR-03: Single Stylesheet.** Both themes are served by the one existing `styles.css`. No second stylesheet, no inline color blocks in templates.

- **NFR-04: Visual Parity.** The light theme is visually identical to the current (pre-feature) appearance. Refactoring hardcoded hex values to custom properties must not change the rendered light-theme colors.

- **NFR-05: Contrast.** Dark-theme foreground/background pairings should remain legible (target WCAG AA for body text). Brand indigo accents are adjusted as needed for contrast on dark surfaces.

- **NFR-06: Statelessness.** The feature adds no server state, no cookie, and no session key. Persistence is confined to client `localStorage`.

- **NFR-07: Template Hot-Reload Compatibility.** Because templates are read from disk on every request (see app-foundation §2.3), edits remain visible on next request without restart; the feature must not depend on any caching or build artifact.

---

## 6. Success Paths

- **SP-01: First Visit, Light System.** A visitor with no saved theme and a light OS preference loads `/login`. Restore script finds no `localStorage` value, `prefers-color-scheme` does not match dark → light theme renders with no flash.

- **SP-02: First Visit, Dark System.** A visitor with no saved theme and a dark OS preference loads `/login`. Restore script applies dark theme before paint → dark theme renders with no flash; nothing is written to `localStorage`.

- **SP-03: Toggle to Dark.** On a light page the user activates the toggle → `data-theme="dark"` set on `<html>`, colors update instantly, `localStorage["theme"] = "dark"`, and the `aria-label` updates to "Switch to light theme".

- **SP-04: Persistence Across Pages.** After choosing dark on `/login`, the user navigates to `/signup` and `/welcome`. Each page's restore script reads `"dark"` and renders dark before paint.

- **SP-05: Persistence Across Reload.** After choosing dark, the user reloads the page → dark theme is restored with no flash.

- **SP-06: Toggle Back to Light.** On a dark page the user activates the toggle → `data-theme="light"`, `localStorage["theme"] = "light"`, `aria-label` updates to "Switch to dark theme".

- **SP-07: Keyboard Activation.** The user tabs to the toggle and presses Space/Enter → theme switches exactly as a click would.

---

## 7. Edge Cases

- **EC-01: localStorage Unavailable.** If `localStorage` access throws (e.g., privacy mode), the restore script falls back to `prefers-color-scheme`, and the toggle still flips `data-theme` in-memory for the current page. No uncaught exception is allowed to break page rendering.

- **EC-02: Invalid Stored Value.** If `localStorage["theme"]` holds a value other than `"light"`/`"dark"`, it is treated as absent and the system-preference fallback applies.

- **EC-03: No `matchMedia` Support.** If `window.matchMedia` is unavailable, the fallback defaults to the light theme.

- **EC-04: Rapid Repeated Toggling.** Multiple quick activations leave `localStorage["theme"]` consistent with the final visible state; no intermediate corruption.

- **EC-05: Dashboard XSS Payload Present.** If a username containing a `<script>` payload is rendered on the dashboard, theming does not escape, neutralize, or alter it — the Stored XSS remains exploitable (see TC-07).

- **EC-06: Direct Deep Link.** Loading `/signup` or `/welcome` directly (not via `/login`) still restores the saved theme before paint, because each template carries its own restore script.

- **EC-07: Two Tabs Open.** A theme change in one tab updates `localStorage`; other open tabs are not required to update live, but will reflect the saved theme on their next load.

---

## 8. Acceptance Criteria

- **AC-01:** Each of `/login`, `/signup`, `/welcome` shows a keyboard-focusable theme toggle in the header.
- **AC-02:** Activating the toggle switches the page between light and dark instantly via `data-theme` on `<html>`.
- **AC-03:** The chosen theme is written to `localStorage["theme"]` and survives reloads and cross-page navigation within the origin.
- **AC-04:** With no saved value, the theme matches `prefers-color-scheme`, and no value is written until the user explicitly toggles.
- **AC-05:** No flash of the wrong theme occurs on load for a saved dark preference (restore runs in `<head>`).
- **AC-06:** The toggle's `aria-label` always names the action it will perform next, updating on each switch.
- **AC-07:** The light theme is pixel-equivalent to the pre-feature appearance.
- **AC-08:** All 8 vulnerabilities remain intact; in particular the dashboard still renders the `{{username}}` value unescaped, so a `<script>` username still executes.
- **AC-09:** Only the four files in §3 are modified; no backend file changes.

---

## 9. Test Cases

| ID | Scenario | Precondition | Expected Result |
|----|----------|--------------|-----------------|
| TC-01 | Toggle present | Load `/login` | A focusable theme-toggle button appears in the header on all three pages |
| TC-02 | Toggle to dark | Light theme active | `<html data-theme="dark">`, colors update, `localStorage.theme === "dark"` |
| TC-03 | Toggle to light | Dark theme active | `<html data-theme="light">`, colors update, `localStorage.theme === "light"` |
| TC-04 | Persistence across reload | `localStorage.theme === "dark"` | After reload, page renders dark with no flash |
| TC-05 | Persistence across pages | Dark chosen on `/login` | `/signup` and `/welcome` render dark before paint |
| TC-06 | System fallback (dark) | `localStorage.theme` unset, OS prefers dark | Dark theme renders; `localStorage.theme` remains unset |
| TC-07 | Vulnerability intact — Stored XSS | Username is `<script>alert(1)</script>`; user logged in | Dashboard renders the raw `<script>` unescaped and it executes; theming did not sanitize it |
| TC-08 | Vulnerability intact — Reflected XSS | n/a | `GET /search?q=<script>alert(1)</script>` still reflects payload unescaped |
| TC-09 | No-flash restore | `localStorage.theme === "dark"` | No visible light-to-dark flash on initial paint |
| TC-10 | Accessible label updates | Light active | `aria-label` reads "Switch to dark theme"; after toggling, reads "Switch to light theme" |
| TC-11 | Keyboard activation | Toggle focused | Pressing Space or Enter switches the theme identically to a click |
| TC-12 | localStorage blocked | Storage access throws | Page still renders; fallback theme applied; toggle still flips current page; no uncaught error |
| TC-13 | Invalid stored value | `localStorage.theme === "blue"` | Treated as unset; system-preference fallback applies |
| TC-14 | Light parity | Light theme active | Header, auth panels, dashboard cards, tags match pre-feature colors |
| TC-15 | Files unchanged | Inspect diff | Only `styles.css` and the three templates changed; no backend file touched |

---

## 10. Verification Steps

1. **Start the application** from the project root:

   ```bash
   uv run backend/app/main.py
   ```

2. **Light/dark toggle on auth pages** — open <http://localhost:3001/login> and <http://localhost:3001/signup>:
   - Confirm the header shows a theme toggle (TC-01).
   - Click it; confirm the page switches to dark and back, and that DevTools → Application → Local Storage shows `theme` updating (TC-02, TC-03).
   - Tab to the toggle and press Space/Enter; confirm it switches (TC-11).
   - Inspect the toggle's `aria-label` before and after switching (TC-10).

3. **Persistence** — with dark selected, reload the page and navigate between `/login`, `/signup`, and (after logging in) <http://localhost:3001/welcome>. Confirm dark persists with no flash (TC-04, TC-05, TC-09).

4. **System fallback** — clear `localStorage.theme` in DevTools, set the OS/browser to prefer dark, and reload `/login`. Confirm dark renders and `localStorage.theme` stays unset (TC-06). Set `localStorage.theme` to `"blue"` and reload to confirm fallback (TC-13).

5. **Vulnerabilities still intact (must remain exploitable):**
   - Register a user whose username is `<script>alert(1)</script>` at <http://localhost:3001/signup>, log in, and load <http://localhost:3001/welcome>. Confirm the script executes — the Stored XSS is unaffected by theming (TC-07).
   - Open <http://localhost:3001/search?q=%3Cscript%3Ealert(1)%3C/script%3E> and confirm the payload is reflected unescaped (TC-08).
   - Confirm <http://localhost:3001/download/db> still serves the database with no authentication.

6. **Diff check** — run `git diff --name-only` and confirm only `frontend/static/css/styles.css`, `frontend/templates/login.html`, `frontend/templates/signup.html`, and `frontend/templates/dashboard.html` appear (TC-15).
