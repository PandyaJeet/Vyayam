# VYAYAM — Deploy Security Review (final build, post G0–F)
**Reviewed by chat-Claude, 2026-06-30 · against the uploaded snapshot · every claim below was verified by running the code, not by reading reports.**

## VERDICT
**Deploy-ready after ONE small fix** (F1 below, ~10 lines + a test). F2 is recommended hardening you can do the same session. F3 is a documented accept. Everything else passes.

---

## 1 · What I verified GREEN (evidence, not claims)

| Area | Result |
|---|---|
| Full test suite | **268/268 OK** (my earlier 55 "errors" were my own extraction dropping `staticfiles/` — after `collectstatic`, all green. Same manifest behavior GROUP2 hit; the suite correctly enforces it.) |
| `manage.py check` / `check --deploy` (prod env) | 0 issues (only W009 for my deliberately short test key — a real 50-char `DJANGO_SECRET_KEY` clears it) |
| Prod-mode smoke (`DEBUG=False`) | `/healthz` `/login` `/forgot-password` `/therapist/login` all 200; unknown URL → custom 404; **CSP-Report-Only + Referrer-Policy: same-origin + Permissions-Policy on every response** |
| Dependency audit | `pip-audit` on requirements.txt: **no known vulnerabilities** (Django pinned 4.2.30) |
| Settings | Fail-fast SECRET_KEY (no insecure fallback) · env-driven DEBUG/hosts · HSTS 1y + preload + subdomains · secure/HTTPOnly/SameSite=Lax cookies in prod · X-Frame DENY · nosniff · proxy-SSL header |
| AuthN | Both logins rate-limited (5/300s) + `session.flush()` before login (fixation-safe) · register 3/600 · change-password 5/300 + `cycle_key()` · forgot 5/300 · reset 10/300 |
| Password reset (U1) | `secrets.token_urlsafe(32)`, 1-hour expiry, single-use, **all other live tokens killed on success**, enumeration-safe identical response, same password rules as registration. Therapist temp-reset: `@therapist_required` + POST + link-ownership 404 + `secrets`-random temp + forced `must_change_password` |
| XSS | All 3 `|safe` uses are server-authored JSON/SVG (never user input) · builder `esc()` escapes `& < > " '` (attribute-safe) · **server pain guidance rendered via `textContent`, not innerHTML** · all 11 innerHTML sinks carry static markup only · `mark_safe` flash uses `escape()` on every interpolated value |
| CSRF | Both pain fetches + result saves send `X-CSRFToken`; zero `csrf_exempt` in the codebase |
| Secrets | No hardcoded keys/passwords in the tree; `.env*`/db.sqlite3 gitignored |
| healthz | Leaks nothing (status-only JSON), DB-touching as designed |

Phases G0–F all fingerprint in code: inline-JS harness test, severity≥8 type-blind stop on BOTH flows, notes input (`data-k="notes"`), opt-in `Show demo`, tempo chip with per-phase colors + single spoken cue, voice picker with `onvoiceschanged`. PITCH_SMOKE.md's steps match the code paths — it's accurate as written.

---

## 2 · Findings

### F1 — MEDIUM · fix before deploy: pain endpoint has no rate limit → alert flooding
`therapist_session_report_pain` is the only state-writing patient endpoint **without** `@rate_limit` (every comparable endpoint has one: save_exercise 60/60, quick_log 60/60, football_save 60/60). A patient session in a loop can create unbounded `PainEvent` + `TherapistMessage` + `Alert` rows — flooding the therapist inbox (clinical alarm fatigue: real 8/10 alerts drown), growing the DB, and polluting the future V2 training data with junk events. Authenticated-only, so severity is Medium not High — but it's exactly the kind of thing that misfires during a live demo.

### F2 — LOW-MEDIUM · recommended same-session: reset tokens stored in plaintext
`PasswordResetToken.token` stores the raw token; lookup is by exact value. If the DB or a backup ever leaks, unexpired tokens are directly usable. Standard practice: store `sha256(token)`, look up by hash — the email still carries the raw token, nothing else changes. Mitigated today by 1-hour expiry + single-use + kill-on-success, hence not a blocker.

### F3 — LOW · documented accept (no action): forgot-password timing side channel
On a phone match with an email, `send_mail` runs inline — SMTP latency (~0.5–2s) vs the instant no-match path weakly reveals which phones have accounts, despite the identical response body. With the 5/300s rate limit, mass enumeration is impractical. Accept and note in SECURITY_AUDIT.md; if it ever matters, move the send to a post-response hook or add `EMAIL_TIMEOUT = 5`.

### Note (not a security finding): Tailwind via CDN
Your screenshot's console warning — `cdn.tailwindcss.com should not be used in production` — still stands. It's a page-weight/reliability issue plus a third-party script dependency (already why CSP is Report-Only). Not a blocker; post-pitch, build Tailwind locally per the CSP middleware's own comment, then enforce CSP.

---

## 3 · PASTE THIS TO CLAUDE CODE (one short session, fixes F1 + F2)

> TITLE: security hardening — rate-limit pain endpoint + hash reset tokens
> CONTEXT: repo root, current branch. Two small fixes, one commit each, run `manage.py check` + full suite (268) after each. Verify every find-string matches exactly once first.
>
> FIX 1 (F1) — In `strength_app/v1_therapist_session_views.py`: import the same `rate_limit` decorator used in `strength_app/views.py`, and decorate `therapist_session_report_pain` with `@rate_limit(max_attempts=15, window_seconds=60, key_prefix='report_pain')` placed directly ABOVE the existing `@require_POST`. 15/min allows every legitimate use (a few reports per exercise) while killing loops. Then add alert dedupe inside `_record_pain`: before `Alert.objects.create(...)`, skip creation if an unreviewed Alert for the same `link` with `alert_type='pain'` was created in the last 10 minutes AND its message contains the same exercise_name (the PainEvent + message must still be created — only the duplicate Alert row is suppressed). Tests: (a) 16th POST in a minute → 429; (b) two severity-8 reports on the same exercise 1 minute apart → 2 PainEvents, 2 messages, **1** Alert; (c) different exercise → 2 Alerts.
>
> FIX 2 (F2) — Hash reset tokens at rest. In `strength_app/models.py` `PasswordResetToken`: rename semantics only — keep the field but store `hashlib.sha256(token.encode()).hexdigest()` (64 chars fits max_length=64 exactly). In `forgot_password`: create with the hash, email the raw token unchanged. In `reset_password`: look up by `token=sha256(url_token)`. Add a small helper `PasswordResetToken.hash_of(raw)` used by both views. No migration needed (same field/type); old plaintext rows simply become unusable — acceptable (1-hour lifetime). Update the two existing U1 tests to go through the email-extracted raw token path so they still pass end-to-end.
>
> Finish: append both fixes to SECURITY_AUDIT.md's findings table (F1 fixed, F2 fixed, F3 accepted with one-line rationale), run the full suite, commit, push.

---

## 4 · Pre-deploy env reminders (unchanged from DEPLOY_CHECKLIST.md — the ones people forget)
Real 50+ char `DJANGO_SECRET_KEY` · `DJANGO_ALLOWED_HOSTS` set explicitly (don't rely on the `.onrender.com` fallback) · `DJANGO_CSRF_ORIGINS` with your real https origin · `DJANGO_SSL_REDIRECT=True` · the 4 SMTP vars (reset emails silently no-op without them) · strong admin credentials · run `seed_therapist_demo` ONLY on demo databases, never production.
