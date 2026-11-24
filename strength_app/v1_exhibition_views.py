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
from .mind_lab import pass_window as pw
from .mind_lab.pass_window_data import game_config

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
    'qr_placeholder': 'QR code goes here',
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


def exhibition_games(request):
    """Pass Window (walk-up, 60 s) and Go / No-Go Pass. Own view: it must not
    use the Mind Lab visitor view, which checks the other flag. Stores nothing."""
    _require_flag()
    cfg = game_config(PW_LEVEL, visitor=True)
    cfg['visitor'] = True
    cfg['save_url'] = None
    cfg['max_s'] = PW_ROUND_START_CUTOFF_S
    cfg['order'] = pw.trial_order(cfg['scenarios'], PW_LEVEL, PW_ORDER_LEN)
    games_cfg = {
        'text': GAMES_TEXT,
        'pass_window': cfg,
        'idle_seconds': IDLE_SECONDS,
        'qr_src': settings.STATIC_URL + GAMES_QR_STATIC,
    }
    return render(request, 'strength_app/exhibition_games.html', {
        'g': GAMES_TEXT,
        'page_url': request.build_absolute_uri(request.path),
        'games_cfg_json': json.dumps(games_cfg),
    })
