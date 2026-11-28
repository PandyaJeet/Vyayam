"""
VYAYAM stall pages. STORE NOTHING, no login.

Structural guarantee: no model import, no session write, no ORM call, no
write endpoint. tests/test_exhibition.py parses this file for that.
"""
import json
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render

from .cv_targets import get_cv_config
from .exercise_content import EXERCISE_CONTENT

SQUAT_KEY = 'full_squats'

# Every string below is athlete-facing and unsigned: listed in
# docs/UNSIGNED_DEFAULTS.md under "Exhibition pages".
SQUAT_TEXT = {
    'start': 'Start',
    # Wording follows the SQUAT cameraPosition data in v1_exercise_execute.html.
    'hint': 'Prop your phone at waist height, facing you. '
            'Step back so your whole body is on screen.',
    'unlock': 'Ready.',
    'fail_title': 'Camera not available',
    'fail_body': 'We could not start the camera. Watch the demo below.',
    'retry': 'Try again',
    # Line 1 is the camera page's own demo line (v1_exercise_execute.html startDemoSequence).
    'demo_line1': 'Watch me first. I will show you the movement.',
    'demo_line2': 'One more time.',
    'demo_again': 'Show demo',  # same label as the camera page's own button
}
CURL_KEY = 'bicep_curls'
# Same wording as SQUAT_TEXT except hint and fail_body (no clip, side view).
CURL_TEXT = {
    'start': 'Start',
    # Wording follows the CURL cameraPosition data in coach_dark.js (side view).
    'hint': 'Prop your phone at waist height, to your side. '
            'Stand side-on and step back so your whole body is on screen.',
    'unlock': 'Ready.',
    'fail_title': 'Camera not available',
    'fail_body': 'We could not start the camera.',
    'retry': 'Try again',
}
# Games page wording. Also unsigned: see docs/UNSIGNED_DEFAULTS.md.
GAMES_TEXT = {
    'title': 'Demo games',
    'sub': 'Tap a game to start.',
    'pw_title': 'Pass Window',
    'pw_sub': 'Pick the best pass. About 60 seconds.',
    'pw_demo': 'Demo scenarios',
    'gn_title': 'Go / No-Go Pass',
    'gn_sub': 'Tap teammates. Leave opponents. 45 seconds.',
    'gn_rules': 'Tap the blue circles. They are teammates. '
                'Do not tap the orange triangles. They are opponents. '
                'It gets a little faster when you get 3 right in a row.',
    'gn_go': 'Teammate: tap',
    'gn_nogo': 'Opponent: do not tap',
    'gn_legend': 'Blue circle: tap. Orange triangle: do not tap.',
    'gn_done': 'Round over',
    'get_ready': 'Get ready',
    'start': 'Start',
    'again': 'Play again',
    'back': 'Choose a game',
    'this_round': 'This round',
    'prev_round': 'Your previous round',
    'accuracy': 'Accuracy',
    'mean_rt': 'Mean response time',
    'no_prev': 'No earlier round yet',
    'none': '-',
    'no_rt': 'No taps counted',
    'own_only': 'Compared only with your own previous round on this page.',
    'demo_note': 'Demo games. Not a test of reaction time, ability or readiness. '
                 'Nothing is saved.',
    'pw_key': 'Circle: you. Squares: teammates. Triangles: defenders.',
    'qr_label': 'Scan to open this page, or type:',
    'qr_alt': 'QR code for this page',
}
GAMES_QR_STATIC = 'strength_app/exhibition/games_qr.png'
# Pass Window walk-up: the round is cut at the first scenario that starts after
# PW_ROUND_START_CUTOFF_S. A scenario takes at most 8 s (4000 ms / 0.5x at level 2)
# plus the 2 s reveal, so the whole round never runs past 60 s.
PW_ROUND_START_CUTOFF_S = 50
PW_LEVEL = 2
PW_ORDER_LEN = 40
IDLE_SECONDS = 60
NO_FRAME_SECONDS = 10
DEMO_TIMEOUT_SECONDS = 15  # both demo plays; after this the camera starts anyway


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
                       no_frame_seconds=NO_FRAME_SECONDS,
                       demo_timeout_seconds=DEMO_TIMEOUT_SECONDS)
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


def exhibition_bicep_curl(request):
    """Real camera page for bicep_curls, library mode (so it saves nothing),
    wrapped by exhibition_curl.html. No clip: Start runs the camera page's own
    showDemo(). Tempo is the registry's 2-1-2-0 (pinned by test_exhibition.py)."""
    _require_flag()
    content = EXERCISE_CONTENT[CURL_KEY]
    cfg = get_cv_config(CURL_KEY)
    exercise = {
        'exercise_id': CURL_KEY,
        'exercise_name': content['display_name'],
        'movement_pattern': content['movement_pattern'],
        'sets': 1,
        'reps': 5,
        'tempo': '2-1-2-0',
        'tempo_parts': ['2', '1', '2', '0'],
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
    wrapper_cfg = dict(CURL_TEXT, idle_seconds=IDLE_SECONDS,
                       no_frame_seconds=NO_FRAME_SECONDS)
    return render(request, 'strength_app/exhibition_curl.html', {
        'exercise': exercise,
        'exercise_index': 0,
        'total_exercises': 1,
        'is_last_exercise': True,
        'has_strength_profile': True,
        'library_mode': True,
        'library_return_url': '/exhibition/',
        'exh': CURL_TEXT,
        'exh_cfg_json': json.dumps(wrapper_cfg),
    })


MIND_GAMES_FILE = Path(__file__).resolve().parent / 'exhibition_pages' / 'mind_games.html'


def exhibition_games(request):
    """Pawan's mind-games.html, served byte for byte. Never goes through the
    template engine. Stores nothing."""
    _require_flag()
    try:
        body = MIND_GAMES_FILE.read_bytes()
    except OSError:
        raise Http404
    return HttpResponse(body, content_type='text/html; charset=utf-8')
