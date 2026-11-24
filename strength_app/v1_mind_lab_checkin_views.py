"""
VYAYAM — Check-In 4 (athlete). Four ratings that set the day's Mind Lab plan.

Behind settings.MIND_LAB_ENABLED (default False: the URL is a 404).
Does NOT import the exercise registry.
"""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from .mind_lab import checkin as ci
from .mind_lab import config
from .mind_lab.day_mode import pain_light_for, resolve_day_mode, s3_hold_active
from .models import MindLabCheckIn
from .v1_athlete_views import _require_athlete


def mind_lab_checkin(request):
    if not settings.MIND_LAB_ENABLED:
        raise Http404
    patient, err = _require_athlete(request)
    if err:
        return err
    if request.method == 'GET':
        return render(request, 'strength_app/mind_lab_checkin.html', {'patient': patient})
    if request.method != 'POST':
        return render(request, 'strength_app/mind_lab_checkin.html',
                      {'patient': patient}, status=405)

    try:
        answers = ci.clean_answers(
            request.POST.get('sleep'), request.POST.get('stress'),
            request.POST.get('energy'), request.POST.get('focus'))
    except ValueError:
        return render(request, 'strength_app/mind_lab_checkin.html',
                      {'patient': patient, 'error': 'Please answer all four questions.'},
                      status=400)

    pain_light = pain_light_for(patient)
    mode = resolve_day_mode(answers['sleep_bucket'], pain_light,
                            hold=s3_hold_active(patient))
    score = ci.checkin_score(answers['stress'], answers['energy'], answers['focus'])
    label = ci.day_label(score, mode)
    MindLabCheckIn.objects.create(
        athlete=patient, pain_light=pain_light, gate_applied=mode,
        day_label=label, **answers)

    youth = patient.age is not None and patient.age < config.YOUTH_AGE_CUTOFF
    support = None
    if ci.show_support_line(answers['stress'], answers['energy']):
        support = ci.SUPPORT_LINE_YOUTH if youth else ci.SUPPORT_LINE
    return render(request, 'strength_app/mind_lab_checkin_result.html', {
        'patient': patient,
        'label_text': ci.LABEL_TEXT[label],
        'plan_text': ci.PLAN_TEXT[mode],
        'support_line': support,
    })
