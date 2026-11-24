"""
VYAYAM — Mind Lab exhibition visitor mode. STORES NOTHING.

Structural guarantee: this module imports no models, no session and no ORM,
and calls no write method. tests/test_mind_lab_checkin.py parses this file and
fails if that ever changes. Do not add storage here; use the athlete views.
"""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from .mind_lab import checkin as ci
from .mind_lab.day_mode import resolve_day_mode

TEMPLATE = 'strength_app/mind_lab_visitor.html'


def mind_lab_visitor(request):
    if not settings.MIND_LAB_ENABLED:
        raise Http404
    if request.method == 'GET':
        return render(request, TEMPLATE)
    if request.method != 'POST':
        return render(request, TEMPLATE, status=405)
    try:
        sleep = ci.clean_sleep(request.POST.get('sleep'))
        energy = ci.clean_rating(request.POST.get('energy'))
    except ValueError:
        return render(request, TEMPLATE,
                      {'error': 'Please answer both questions.'}, status=400)
    # No pain light for a visitor: green. Two answers only, no score.
    mode = resolve_day_mode(sleep, 'green')
    return render(request, TEMPLATE, {
        'done': True,
        'label_text': ci.LABEL_TEXT[ci.MODE_LABEL[mode]],
        'plan_text': ci.PLAN_TEXT[mode],
        'support_line': ci.SUPPORT_LINE if energy <= 1 else None,
    })
