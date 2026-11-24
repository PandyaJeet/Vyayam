"""
VYAYAM — Pass Window (athlete). Scored Mind Lab game, demo scenarios.

Behind settings.MIND_LAB_ENABLED (default False: 404). Gated by
mind_lab_day_mode: only 'full' and 'shortened' days can play it. The server
rescores every trial and sets the next level; the browser's numbers are not
trusted. Does NOT import the exercise registry.
"""

import json

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .mind_lab import config
from .mind_lab import pass_window as pw
from .mind_lab.checkin import PLAN_TEXT
from .mind_lab.day_mode import mind_lab_day_mode
from .mind_lab.pass_window_data import GAME_ID, game_config, load_scenarios
from .models import GameSession
from .v1_athlete_views import _require_athlete

PLAYABLE_MODES = ('full', 'shortened')
MAX_TRIAL_MS = 600000


def _start_level(patient):
    last = GameSession.objects.filter(athlete=patient, game_id=GAME_ID).first()
    stored = (last.summary or {}).get('next_level') if last else None
    return pw.clamp_level(stored) if isinstance(stored, int) else pw.MIN_LEVEL


def pass_window_page(request):
    if not settings.MIND_LAB_ENABLED:
        raise Http404
    patient, err = _require_athlete(request)
    if err:
        return err
    mode = mind_lab_day_mode(patient)
    if mode not in PLAYABLE_MODES:
        return render(request, 'strength_app/mind_lab_pass_window.html',
                      {'blocked': True, 'plan_text': PLAN_TEXT[mode]}, status=403)
    cfg = game_config(_start_level(patient))
    cfg['save_url'] = request.path.rstrip('/') + '/save/'
    return render(request, 'strength_app/mind_lab_pass_window.html',
                  {'config_json': json.dumps(cfg)})


@require_POST
def pass_window_save(request):
    if not settings.MIND_LAB_ENABLED:
        raise Http404
    patient, err = _require_athlete(request)
    if err:
        return JsonResponse({'error': 'not signed in'}, status=403)
    mode = mind_lab_day_mode(patient)
    if mode not in PLAYABLE_MODES:
        return JsonResponse({'error': 'not playable today'}, status=403)
    try:
        data = json.loads(request.body or b'{}')
        raw = data['summary']['trials']
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'error': 'bad json'}, status=400)

    level = _start_level(patient)  # the client's level is ignored
    try:
        trials = pw.clean_trials(raw, load_scenarios(), config.PASS_WINDOW_TRIALS)
    except ValueError:
        return JsonResponse({'error': 'invalid field'}, status=400)
    result = pw.session_result(level, trials, load_scenarios(), hold=(mode == 'shortened'))

    gs = GameSession.objects.create(
        athlete=patient, game_id=GAME_ID, level=level,
        n_trials=result['n_trials'], accuracy=result['accuracy'],
        median_rt_ms=result['median_rt_ms'], slowmo_factor=pw.LEVEL_FACTORS[level],
        summary={'trials': trials, 'next_level': result['next_level'],
                 'timeouts': result['timeouts'], 'demo_scenarios': True,
                 'scenario_review': 'UNREVIEWED'})
    return JsonResponse({'status': 'ok', 'id': gs.id})
