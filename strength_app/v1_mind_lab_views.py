"""
VYAYAM — Mind Lab (scaffold). Game-agnostic runner page + session save.

The game loop is browser-side JS only. Nothing here knows about any specific
game: `game_id` is a slug and anything game-specific travels in `summary`.
Athlete track only (same gate as the athlete PWA). Deliberately does NOT
import the exercise registry (~449 MB, ~11 s on first use).
"""

import json
import re

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import GameSession
from .v1_athlete_views import _require_athlete

GAME_ID_RE = re.compile(r'^[a-z0-9_-]{1,50}$')
MAX_LEVEL = 100            # shortcut: sanity bound only, the real level range arrives with K5
MAX_TRIALS = 10000
MAX_SUMMARY_BYTES = 8192


def _clean_number(value, lo, hi):
    """Return a float in [lo, hi] or None. Rejects bools, NaN and inf."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value < lo or value > hi:
        return None
    return float(value)


def mind_lab_runner(request, game_id):
    patient, err = _require_athlete(request)
    if err:
        return err
    if not GAME_ID_RE.match(game_id):
        return JsonResponse({'error': 'bad game_id'}, status=404)
    last = GameSession.objects.filter(athlete=patient, game_id=game_id).first()
    config = {
        'game_id': game_id,
        'level': last.level if last else 1,
        'save_url': request.path.rstrip('/') + '/save/',
    }
    return render(request, 'strength_app/mind_lab_runner.html', {
        'config_json': json.dumps(config),
    })


@require_POST
def mind_lab_save(request, game_id):
    patient, err = _require_athlete(request)
    if err:
        return JsonResponse({'error': 'not signed in'}, status=403)
    if not GAME_ID_RE.match(game_id):
        return JsonResponse({'error': 'bad game_id'}, status=404)
    try:
        data = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'error': 'bad json'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'bad json'}, status=400)

    level = _clean_number(data.get('level', 1), 1, MAX_LEVEL)
    n_trials = _clean_number(data.get('n_trials', 0), 0, MAX_TRIALS)
    accuracy = data.get('accuracy')
    accuracy = None if accuracy is None else _clean_number(accuracy, 0, 1)
    rt = data.get('median_rt_ms')
    rt = None if rt is None else _clean_number(rt, 0, 600000)
    slowmo = _clean_number(data.get('slowmo_factor', 1.0), 0, 100)
    summary = data.get('summary', {})
    if (level is None or n_trials is None or slowmo is None
            or (data.get('accuracy') is not None and accuracy is None)
            or (data.get('median_rt_ms') is not None and rt is None)
            or not isinstance(summary, dict)
            or len(json.dumps(summary)) > MAX_SUMMARY_BYTES):
        return JsonResponse({'error': 'invalid field'}, status=400)

    gs = GameSession.objects.create(
        athlete=patient, game_id=game_id, level=int(level),
        n_trials=int(n_trials), accuracy=accuracy, median_rt_ms=rt,
        slowmo_factor=slowmo, summary=summary,
    )
    return JsonResponse({'status': 'ok', 'id': gs.id})
