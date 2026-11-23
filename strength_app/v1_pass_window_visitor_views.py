"""
VYAYAM — Pass Window exhibition visitor mode. STORES NOTHING.

3 trials at Level 2, fixed. Structural guarantee: this module imports no
models, no session and no ORM, and calls no write method. The page has no
save_url, so the browser sends nothing. tests/test_pass_window.py parses this
file and fails if that ever changes. Do not add storage here.
"""

import json

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from .mind_lab import config
from .mind_lab.pass_window_data import game_config


def pass_window_visitor(request):
    if not settings.MIND_LAB_ENABLED:
        raise Http404
    cfg = game_config(config.PASS_WINDOW_VISITOR_LEVEL, visitor=True)
    cfg['visitor'] = True
    cfg['save_url'] = None
    return render(request, 'strength_app/mind_lab_pass_window.html',
                  {'config_json': json.dumps(cfg), 'visitor': True})
