# Deploy Checklist (Render-targeted) — Run 2

## Environment variables (all of them)

| Variable | Required | Example | Notes |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | **yes** | 50+ random chars | App **fails fast** without it — no insecure fallback |
| `DJANGO_DEBUG` | **yes** | `False` | Anything except `true/1/yes` is False |
| `DJANGO_ALLOWED_HOSTS` | **yes** | `vyayam.onrender.com,vyayam.app` | Comma-separated; empty + DEBUG=False = crash on first request |
| `DJANGO_CSRF_ORIGINS` | **yes** | `https://vyayam.onrender.com,https://vyayam.app` | Scheme required |
| `DATABASE_URL` | **yes (prod)** | `postgres://…` | Absent → SQLite (dev only). `ssl_require` is on when DEBUG=False |
| `DJANGO_SSL_REDIRECT` | yes | `1` | Enables redirect + secure cookies path |
| `DJANGO_TRUSTED_PROXY` | yes on Render | `1` | Lets the rate limiter trust `X-Forwarded-For` — set ONLY behind a real proxy |
| `DJANGO_EMAIL_BACKEND` | no | (default smtp in prod) | Console backend when DEBUG=True |
| `DJANGO_EMAIL_HOST` | **yes (for U1 reset emails)** | `smtp.sendgrid.net` | Password reset emails silently no-op without SMTP |
| `DJANGO_EMAIL_PORT` | no | `587` | |
| `DJANGO_EMAIL_HOST_USER` | yes (smtp) | `apikey` | |
| `DJANGO_EMAIL_HOST_PASSWORD` | yes (smtp) | *(secret)* | |
| `DJANGO_EMAIL_USE_TLS` | no | `True` | |
| `DJANGO_DEFAULT_FROM_EMAIL` | no | `VYAYAM <noreply@vyayam.app>` | |
| `SENTRY_DSN` | no | `https://<key>@o<org>.ingest.sentry.io/<project>` | Unset → Sentry completely off (dev/CI: sentry_sdk never imported). Set on Render (Environment → Add env var) to enable server + browser error monitoring. Clinical posture is hard-coded: `send_default_pii=False`, request bodies never sent, tracing 0 — pain values/notes/user data never leave the server |

## Render service config

- **Build command**: `./build.sh` — verified: `pip install -r requirements.txt`
  → `collectstatic --no-input` → `migrate`. Migration-on-deploy is the
  intended behaviour (all migrations are additive/safe this run: 0020–0021
  strength_app, 0004 therapist_app).
- **Start command**:
  `gunicorn vyayam_project.wsgi:application --workers 2 --threads 4 --timeout 60 --access-logfile -`
  - NOTE (health sweep A2): the rate limiter uses per-process LocMemCache —
    with 2 workers every documented limit is effectively doubled and counters
    reset on deploy. Acceptable for launch; move to Redis/DB cache to make
    limits exact.
  - NEVER run seed commands (seed_therapist_demo, seed_demo_patient — the
    latter plants a fixed 'demo1234' login) against a production database.
  - Starter/standard dyno (512MB–2GB): 2 workers × 4 threads is the safe
    default for this mostly-IO app. Bump workers to `(2×CPU)+1` on bigger
    instances. 60 s timeout covers PDF generation; nothing long-running
    happens in-request.
  - `--access-logfile -` gives path+status per request in Render logs —
    combined with Django's WARNING-level console logging this is enough to
    debug a live incident (request line → grep the stack trace next to it).
- **Health check path**: `/healthz/` — returns `{"status":"ok"}` 200, and
  503 if the database is unreachable. Unauthenticated by design.
- **Postgres**: enable Render's automated daily backups (instance setting,
  not code). Before risky deploys: `pg_dump $DATABASE_URL > pre_deploy.sql`.

## First-deploy / every-deploy gate

1. `python manage.py check --deploy` with prod env — expect no errors
   (warnings list documented below).
2. Fresh-DB migrate works: `migrate` on an empty database (verified this
   run — see SHIP_READY_REPORT.md gate results).
3. Full test suite green (`manage.py test`).
4. DEBUG=False smoke of major routes with collectstatic done (catches the
   Manifest staticfiles failure class — verified this run).
5. Create the superuser with a STRONG password; consider relocating
   `/admin/` in a future release (SECURITY_AUDIT.md #14).
6. Verify `/healthz/` 200 from outside.
7. Send yourself a password-reset email end-to-end (proves SMTP vars).

## Things that intentionally need a human

- SMTP account creation + the four email env vars.
- Filming verification of camera exercises (docs/FILMING_PROTOCOL.md).
- D3 data migration ONLY IF production patients exist with
  `absolute_stop=True` rows written before Run 1 (stores internal IDs).

8. (2026-07 exam, ledger D2/D5) The authoritative full-tree `pip-audit`
   must run INSIDE the Linux deploy image — mediapipe==0.10.33 has no
   macOS/py3.12 wheel, so dev-machine environments drift (0.10.14 locally).
   When touching requirements.txt, generate a hash-pinned lockfile
   (pip-compile) and pin at least: pillow>=12.2, protobuf>=5.29.6,
   fonttools>=4.60.2 (transitive CVEs, SECURITY_AUDIT rows 23-24).
