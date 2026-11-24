# VYAYAM exhibition host decision (K1, 2026-11-17)

Deadline: stall setup Wed 25 Nov. Base: `main` 0208e84. Hugging Face is out (its API refused free Docker Spaces: PRO required).

## Verdict

- **Render free: NO.** The serving worker reaches 499–513 MB RSS after the first logged-in page. The free tier has 512 MB total. Render Starter ($7) is also 512 MB, so it fails too.
- **Recommendation: Fly.io, `shared-cpu-1x` with 1 GB RAM, $6.70 per 30 days, always on (never sleeps).** Fits with ~2x headroom over the measured 513 MB. If the Linux build measures higher, one command raises it to 2 GB at $12.70.
- **Database: Neon free Postgres** (no card, 1 GB, no time limit). SQLite is acceptable only because the demo holds `DEMO_SEED` data and nothing real.

Price sources, checked 2026-11-17: [Fly.io pricing page](https://fly.io/pricing/) (RAM $6.00 per extra GB/month), [Fly.io always-on cost guide](https://fly.io/learn/always-on-agent-hosting-cost/) (1 GB shared-cpu-1x $6.70, 2 GB $12.70 per 30 days), [Fly.io Oct 2026 price change write-up](https://dev.to/pavel-hostim/flyio-pricing-2026-what-changed-on-1-october-and-what-it-costs-in-europe-1pjl). Render: [Render compute plans](https://render.com/docs/compute-plans) and a third-party summary giving Starter $7 / 512 MB and Standard $25 / 2 GB (I could not read Render's own pricing page: it returned no text). Neon: [free plan limits](https://neon.com/faqs/free-plan-limits-and-quotas). Prices change; re-check on the day.

Cheapest Render option that fits is Standard, 2 GB, $25/month. Fly 1 GB is $18.30 cheaper.

## How it was measured

Machine: this Mac (macOS, Python 3.12.3, **mediapipe 0.10.14 installed locally, not the pinned 0.10.33**), host already loaded. Gunicorn 25.3.0 started as `entrypoint.sh` starts it: `--workers 1 --threads 4 --preload --timeout 120`, `DJANGO_DEBUG=False`, fresh SQLite, `seed_football_test` + `seed_football_demo` run first. A thin wrapper (`scripts/measure/measure_wsgi.py`) serves `/__mods__` from inside the worker; it changes no app code. Driver: `scripts/measure/run_measure.py`. RSS is read with `proc_pidinfo` (same number as `ps -o rss=`; `ps` is blocked in this sandbox) every 0.2 s. Raw runs: `docs/deploy_measure/run1.txt`, `run2.txt` (the long module list is trimmed).

### 1. Idle RSS (one worker, 30 s after the first response)

```
master_pid=12127 worker_pid=12128
IDLE_RSS_MB after 30s settle: master=44 worker=23
```
Run 1 gave the same: master 44, worker 23. **Idle is 23 MB because the heavy import has not happened yet.**

### 2. RSS during the football assessment walk

Logged in as `9100000001` (seeded athlete), then hit: `POST /login/`, `/athlete/today/`, `/football/sport-select/`, `/football/assessment/`, `/football/assessment/0..7/` (bilateral tests 0, 4, 5 with `?side=left` and `?side=right`), `POST /football/save-test-result/` after each test, `/football/results/`, `/football/matches/`, `/athlete/progress/`. Every request returned 200 (login 302).

```
('GET', '/login/', 200, None, '0.08s', 'rss_after=27MB')
('POST', '/login/', 302, '/athlete/today/', '0.49s', 'rss_after=31MB')
('GET', '/athlete/today/', 200, None, '11.06s', 'rss_after=512MB')
('GET', '/football/sport-select/', 200, None, '0.01s', 'rss_after=512MB')
('GET', '/football/assessment/', 200, None, '0.01s', 'rss_after=512MB')
...every assessment page and save: 0.01s, rss_after=512MB...
('GET', '/athlete/progress/', 200, None, '0.02s', 'rss_after=513MB')
PEAK_RSS_MB worker during walk: 513
END_RSS_MB worker: 513
```
Run 1: peak 499 MB. **Peak 499–513 MB.** The jump from 31 MB to 512 MB happens on one request, `/athlete/today/`, which loads the exercise registry. The assessment pages themselves add nothing. Gunicorn's own `/__mods__` reading at the end: `rss_kb=524892` (513 MB).

### 3. Cold start

```
Run 1: COLD_START first_http_response_s=1.0 status=200   (GET /healthz/)
Run 2: COLD_START first_http_response_s=1.1 status=200
```
Two numbers matter, not one:
- Launch to first response: **1.0–1.1 s** (the app boots light).
- First logged-in page after boot: **11.06 s** (run 2), which carries the whole 490 MB import. Run 1 did not time it per request; the TensorFlow banner appeared 38 s after launch, about 8 s into the walk.

The earlier 55 s figure was a cold-disk import measured on a different host; this Mac had warm caches. Expect worse on a 1 shared CPU VM. Not measured there.

### 4. Does the web process import mediapipe? **YES.**

From inside the worker, after boot:
```
pid=12128 rss_kb=24300
matching_modules=0 top_level=[]
```
After the football walk:
```
pid=12128 rss_kb=524892
matching_modules=1953 top_level=['cv2', 'mediapipe', 'tensorflow']
```
Stderr of gunicorn also shows the TensorFlow banner (`cpu_feature_guard.cc ... optimized to use available CPU instructions`). So the server carries mediapipe, cv2 and tensorflow in memory for a camera that runs in the browser. The trigger is a lazy import: `strength_app/views.py:1018` and ten other call sites do `from .exercise_system.exercise_registry_v2 import EXERCISE_METADATA` inside functions (e.g. `v1_prescription_engine.py:105`, `v1_session_views.py:1321`). Corrected from the earlier note: this does NOT happen at boot, it happens on the first request that needs the registry. Not fixed here (CLAUDE.md: do not make the imports lazy or drop mediapipe without a mediapipe-free venv proof).

## Render free: why it fails

| Item | Measured | Render free |
|---|---|---|
| RAM after first athlete page | 499–513 MB (worker) + 44 MB master | 512 MB |
| Sleep | n/a | after 15 min idle |
| Wake cost | ~1 s boot + ~11 s first athlete page here | worse on 0.1 CPU, not measured |

The worker alone is at the cap before Django's other memory, DB drivers or any second request. Expect an OOM kill. Sleep makes it worse: a visitor at the stall who arrives after 15 quiet minutes waits for the platform wake plus the import. A wake-ping cron would not help, because an OOM kill still happens. Fly with `auto_stop_machines = "off"` never sleeps, so the import runs once.

## Database

- Demo: `DATABASE_URL` unset gives SQLite inside the container. Fine **only** because the data is `DEMO_SEED` and wiped on every restart/deploy, then re-seeded by `entrypoint.sh`. The seeded logins are public (`9000000005 / athlete`, `9100000001 / athletepass123`, therapist demo accounts): no real person's data may be entered on this app.
- If you want Postgres anyway (or the demo keeps data between restarts): **Neon free**. No card, no time limit, 1 GB, 100 CU-hours/month, compute suspends after 5 minutes idle and wakes in a few hundred ms. Settings already read `DATABASE_URL` and force SSL when `DEBUG=False`. Chosen over Supabase free because Neon needs no card and the DB wake is sub-second.
- Real patient data: not on this host. Needs a paid Postgres with backups first.

## Runbook (what remains)

Steps marked **CARD** need Pawan's card or an account only he can open. I created nothing.

1. Open the Fly.io account and add a card. **CARD**
2. Install flyctl: `brew install flyctl` (ask before installing). Then `fly auth login`. **needs Pawan, no card**
3. From a checkout of branch `deploy-host-decision`: `fly launch --no-deploy --copy-config` (pick the name; update `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_ORIGINS` in `fly.toml` to `<name>.fly.dev`). **no card**
4. `fly secrets set DJANGO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(60))')"`. **no card**
5. Optional Postgres: create a Neon project (free, no card), then `fly secrets set DATABASE_URL='<neon pooled url>'`. Skip it to use container SQLite. **no card**
6. `fly deploy`. First deploy builds the image (several minutes: mediapipe wheels). **CARD (billing starts)**
7. Check `curl https://<name>.fly.dev/healthz/` returns `{"status":"ok"}`. **no card**
8. **Warm the worker:** log in once as the seeded athlete (`9000000005 / athlete`) and open `/athlete/today/`. This pays the ~11+ s import so no visitor does. Repeat after every deploy or restart. **no card**
9. Check memory: `fly machine status` / `fly logs`. If any OOM line appears: `fly scale memory 2048` ($12.70 per 30 days). **CARD**
10. Run the phone acceptance walk: `MASTER_TEST_DAY.md` Part M. **no card**
11. Day after the exhibition: `fly apps destroy <name>` to stop billing (Fly bills per use). **no card**

Estimated cost for a 10-day run on 1 GB: about $2.2 (10/30 of $6.70), plus a few cents egress.

## Files in this branch

`Dockerfile`, `entrypoint.sh`, `.dockerignore` (copied from `deploy@887e3a0`, comment in `entrypoint.sh` corrected), `fly.toml` (new), `scripts/measure/*`, `docs/deploy_measure/*`.

## UNVERIFIED

- Linux/Fly RSS: measured on macOS with mediapipe 0.10.14. The pinned 0.10.33 on Linux may differ by tens of MB either way. The 1 GB choice has ~2x headroom; step 9 is the safety net.
- Docker image build and `fly.toml` have never run (no Docker or flyctl here). Port 7860, `/healthz/` and the grace period are inferred.
- Cold start on a 1 shared-CPU VM and on Render free (0.1 CPU): not measured; only this Mac.
- Peak under concurrent users: one client only. Four threads share one worker, so extra visitors should add MB, not 500 MB each, but not measured.
- Only the athlete assessment path was walked, not the camera exercise page or PDF report generation.
- Render's own pricing page was unreadable; Starter/Standard numbers come from a third-party summary and the compute-plans doc snippet.
- Fly price: checked 2026-11-17 against search results quoting Fly's pages, not the live billing console.
