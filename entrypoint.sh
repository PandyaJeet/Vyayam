#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --no-input

# DEMO ONLY: seeds public logins with fixed passwords. Off unless DEMO_SEED=1.
# A seed failure is logged but must not stop the demo from starting.
if [ "${DEMO_SEED:-}" = "1" ]; then
    python manage.py seed_demo_patient || echo "WARN: seed_demo_patient failed"
    python manage.py seed_therapist_demo || echo "WARN: seed_therapist_demo failed"
fi

# ONE worker: the first logged-in page imports exercise_registry_v2 (lazy, per request),
# which costs ~490 MB more RSS and ~11 s (measured: docs/DEPLOY_DECISION.md). A second
# worker would double that.
exec gunicorn vyayam_project.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 1 --threads 4 \
    --preload \
    --timeout 120 \
    --access-logfile -
