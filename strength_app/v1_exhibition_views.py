"""
VYAYAM stall pages. STORE NOTHING, no login.

Structural guarantee: no model import, no session write, no ORM call, no
write endpoint. tests/test_exhibition.py parses this file for that.
"""
import json

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from .cv_targets import get_cv_config
from .exercise_content import EXERCISE_CONTENT

SQUAT_KEY = 'full_squats'

# Every string below is athlete-facing and unsigned: listed in
# docs/UNSIGNED_DEFAULTS.md under "Exhibition pages".
SQUAT_TEXT = {
    'start': 'Start',
    'start_sub': 'Tap to turn on the camera and the voice.',
    # Wording follows the SQUAT cameraPosition data in v1_exercise_execute.html.
    'hint': 'Prop your phone at waist height, facing you. '
            'Step back so your whole body is on screen.',
    'unlock': 'Ready.',
    'fail_title': 'Camera not available',
    'fail_body': 'We could not start the camera. Watch the demo below.',
    'retry': 'Try again',
}
IDLE_SECONDS = 60
NO_FRAME_SECONDS = 10


def _require_flag():
    if not settings.EXHIBITION_MODE:
        raise Http404


def exhibition_index(request):
    _require_flag()
    return render(request, 'strength_app/exhibition_index.html')


def exhibition_squat(request):
    """Real camera page for full_squats, library mode (so it saves nothing),
    no qa_mode banner, wrapped by exhibition_squat.html."""
    _require_flag()
    content = EXERCISE_CONTENT[SQUAT_KEY]
    cfg = get_cv_config(SQUAT_KEY)
    exercise = {
        'exercise_id': SQUAT_KEY,
        'exercise_name': content['display_name'],
        'movement_pattern': content['movement_pattern'],
        'sets': 1,
        'reps': 5,
        'tempo': '3-1-2-0',
        'tempo_parts': ['3', '1', '2', '0'],
        'rest_seconds': 60,
        'prescribed_rest': 60,
        'is_unilateral': False,
        'mind_muscle_cue': content.get('mind_muscle_cue', {}),
        'form_cues': content.get('form_cues', []),
        'instructions': ' '.join(content.get('instructions', [])),
        'asymmetry': {},
        'capability_level': 2,
        'is_hold': bool(cfg.get('is_hold')),
    }
    wrapper_cfg = dict(SQUAT_TEXT, idle_seconds=IDLE_SECONDS,
                       no_frame_seconds=NO_FRAME_SECONDS)
    return render(request, 'strength_app/exhibition_squat.html', {
        'exercise': exercise,
        'exercise_index': 0,
        'total_exercises': 1,
        'is_last_exercise': True,
        'has_strength_profile': True,
        'library_mode': True,
        'library_return_url': '/exhibition/',
        'exh': SQUAT_TEXT,
        'exh_cfg_json': json.dumps(wrapper_cfg),
    })
