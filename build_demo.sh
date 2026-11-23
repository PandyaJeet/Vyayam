#!/usr/bin/env bash
# Render build for the free judges' demo (render.yaml). Real production keeps
# using build.sh on a paid instance (DEPLOY_CHECKLIST.md).
set -o errexit -o nounset -o pipefail

bash build.sh  # pip install -r requirements.txt, collectstatic, migrate

# mediapipe pulls in opencv-contrib-python, whose cv2 needs the system libGL
# at import; Render's native image does not promise it. The headless wheel of
# the same version gives the same cv2 module without GUI libraries.
# (mediapipe's own native library loads lazily and is never used server-side.)
cv_version="$(pip show opencv-contrib-python 2>/dev/null | sed -n 's/^Version: //p')"
if [ -n "$cv_version" ]; then
    pip uninstall --yes opencv-contrib-python
    # Both wheels share the cv2/ folder, so the uninstall can strip files a
    # cached headless install still claims: force-reinstall puts them back.
    pip install --force-reinstall --no-deps "opencv-contrib-python-headless==${cv_version}"
fi

# Fail the build, not a judge's first page, if the CV exercise registry
# (imported by the patient, athlete and therapist pages) cannot load.
DJANGO_SETTINGS_MODULE=vyayam_project.settings python -c "import django; django.setup(); from strength_app.exercise_system.exercise_registry_v2 import EXERCISE_METADATA; print('CV exercise registry OK:', len(EXERCISE_METADATA), 'exercises')"

# Precompile app bytecode so the 0.1-CPU free instance does not compile
# ~280 modules on the first request after every wake-up.
python -m compileall -q -f --invalidation-mode unchecked-hash strength_app therapist_app vyayam_project

# Demo logins for the judges (listed in render.yaml). The seeders are
# idempotent, so every deploy resets the demo accounts.
if [ "${VYAYAM_SEED_DEMO:-0}" = "1" ]; then
    python manage.py seed_food_database
    python manage.py seed_therapist_demo
    python manage.py seed_football_demo
    python manage.py seed_demo_patient
fi
