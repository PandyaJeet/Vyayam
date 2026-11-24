"""
/exhibition/progression/ : two live runs of the real prescription engine on a
demo history. STORES NOTHING.

Each request builds a demo persona with the real models inside
transaction.atomic(), runs generate_v1_session() (the same entry point the
patient session view uses), copies every result into plain dicts, and rolls
the transaction back. The page is rendered from the dicts after the rollback.
No seed command. No request data enters any query or any template script.

Every string shown on the page is unsigned: see docs/UNSIGNED_DEFAULTS.md,
"Exhibition pages".
"""
import re
import threading
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from .models import (
    ExerciseExecution, PainEvent, PatientFamilyCapability, PatientProfile,
    PeriodisationState, SessionFeedback, StrengthProfile, WorkoutSession,
)
from .v1_football_constants import LSI_THRESHOLDS
from .v1_onboarding_views import _compute_asymmetry_raw, _weaker_side
from .v1_prescription_engine import generate_v1_session
from .v1_progression_chains import V1_PROGRESSION_CHAINS
from .v1_safety_logic import check_progression_ready

# shortcut: one lock per process. With one gunicorn worker (render.yaml) it
# covers every request; with more workers the unique ids still prevent a key
# clash. Upgrade to a database advisory lock if workers are added.
_LOCK = threading.Lock()

WEEKS = 6                      # weeks of history
EARLY_WEEKS = 2                # weeks the "4 weeks ago" run knows about
SHIFT_DAYS = 7 * (WEEKS - EARLY_WEEKS)
DAYS_BACK = (1, 3, 5)          # days before the week's end: 3 sessions a week
LIGHT_WEEK = 2                 # weeks ago; its sets are lower
# Hand-set illustrative dosage per weeks-ago (sets, reps, rest seconds).
WEEK_DOSE = {5: (2, 10, 75), 4: (3, 8, 75), 3: (3, 8, 75),
             2: (2, 8, 60), 1: (3, 8, 75), 0: (3, 8, 75)}
# Session split used for the demo history: three patterns per session.
SESSION_PATTERNS = (('squat', 'hinge', 'lunge'), ('push', 'pull', 'rotate'),
                    ('lunge', 'hinge', 'carry'))
# Raw lunge reps (left, right). Left is the weaker leg in both tests.
LUNGE_EARLIER = (6, 12)        # LSI 50.0
LUNGE_NOW = (7, 11)            # LSI 63.6
# Hop distances in cm (left, right): page data only, never read by the engine.
HOP_EARLIER = (110, 141)
HOP_NOW = (125, 143)
# Same pattern levels in both runs, so the lunge symmetry result is the one input that
# differs. Lunge is the lowest score because of the weaker leg (the engine ranks the
# lowest pattern first, so it is trained every day).
SCORES_EARLIER = dict(squat=3, hinge=3, push=3, pull=3, rotate=3, lunge=2)
SCORES_NOW = SCORES_EARLIER
DAY_NAMES = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')

TEXT = {
    'title': 'How a plan changes',
    'hero_head': 'A training plan that progresses on its own.',
    'hero_sub': 'Same athlete, 4 weeks apart. New numbers in, new plan out.',
    'hero_balance': 'Leg balance',
    'hero_extra': 'Extra sets, weaker leg',
    'hero_level': 'Lunge level',
    'hero_level_note': 'next session',
    'hero_cue': 'How the plan decided',
    'persona': 'Demo athlete, 24, returned to training. Trained, not new to lifting. '
               'One leg is weaker (the left), the same leg in both tests. '
               'Training state set for this demo: the phase, the week count and the '
               'date of the last lighter week are set by hand so the rules do not '
               'call a deload.',
    'history_label': 'Illustrative demo data',
    'history_h': 'Last 6 weeks',
    'week_cols': ('Week', 'Sessions', 'Sets', 'Note'),
    'light_note': 'Lighter week',
    'days_h': 'Last 7 days',
    'day_cols': ('Day', 'Exercises', 'Rest', 'Pain'),
    'pain_none': 'No pain logged',
    'pain_some': 'Pain logged',
    'sym_h': 'Symmetry tests (weaker side as % of stronger side)',
    'sym_cols': ('Test', '4 weeks ago', 'Now', 'Benchmark'),
    'lunge': 'Lunge (used by the engine)',
    'hop': 'Hop distance (shown here only)',
    'hop_note': 'The hop result is not used by the plan. The lunge result is.',
    'bands': 'Bands used by the plan: 85 and above none, 70 to 84 mild, '
             '55 to 69 moderate, under 55 significant.',
    'proto_h': 'Two runs of the same rules on the demo history',
    'proto_label': 'Computed live by the engine on this request. '
                   'Not a replay of the earlier plan.',
    'run_a': '4 weeks ago',
    'run_b': 'Now',
    'diff_h': 'What changed',
    'diff_cols': ('Exercise', 'Sets', 'Reps', 'Level', 'Weaker-side sets', 'Why'),
    'no_ex': 'Not in this run',
    'same_side': 'same',
    'status_other': 'The engine returned this status instead of a plan:',
    'footer': 'Demo data and demo plans. Nothing is saved. '
              'The plans follow the same rules for every user.',
    'back': 'Back',
    'why_sym': 'Symmetry band {rule}: {extra} extra set(s) on the weaker side',
    'why_blocked': 'Progression blocked while the band is significant',
    'why_adv': 'Ready to progress: level {level} saved for the next session',
    'why_deload': 'Deload',
    'why_none': 'No rule changed this row',
}


def _require_flag():
    if not settings.EXHIBITION_MODE:
        raise Http404


# ---- persona -----------------------------------------------------------------

def _chain_ids(pattern, level):
    levels = V1_PROGRESSION_CHAINS[pattern]['levels']
    return list(levels[max(1, min(level, len(levels))) - 1]['exercises'])


def _make_patient(frag, suffix):
    pid = 'EXHDEMO_%s%s' % (frag, suffix)           # 8 + 8 + 1 = 17 <= 20
    return PatientProfile.objects.create(
        patient_id=pid, name='Demo athlete', phone='%s%s' % (frag, suffix),
        age=24, biological_sex='male', goals='Demo', goal_type='athletic',
        training_history='intermediate', training_age_months=18,    # onboarding maps 'intermediate' to 18
        sessions_per_week=3, session_duration_minutes=90,    # top of the onboarding slider (20-90)
        sleep_quality='good', stress_level='moderate',
        absolute_stop=False,
        # no FootballProfile, no InjuryEpisode, no athlete tier, no red flags
    )


def _profile(patient, scores, lunge_pair, number, days_ago, now):
    left, right = lunge_pair
    cls, _ = _compute_asymmetry_raw(left, right)
    sp = StrengthProfile.objects.create(
        patient=patient, assessment_number=number,
        squat_score=scores['squat'], hinge_score=scores['hinge'],
        push_score=scores['push'], pull_score=scores['pull'],
        rotate_score=scores['rotate'], lunge_score=scores['lunge'], core_score=3,
        hinge_left=10, hinge_right=10, rotate_left=10, rotate_right=10,
        lunge_left=left, lunge_right=right,
        lunge_asymmetry=cls, weaker_side_lunge=_weaker_side(left, right),
        hinge_asymmetry='none', rotate_asymmetry='none',
    )
    StrengthProfile.objects.filter(pk=sp.pk).update(
        assessed_at=now - timedelta(days=days_ago))
    return sp


def _history(patient, weeks_ago_list, shift, scores, now):
    """Create sessions, feedback and execution rows. Returns plain dicts."""
    sessions = []
    n = 0
    for k in sorted(weeks_ago_list, reverse=True):
        sets, reps, rest = WEEK_DOSE[k]
        for i, back in enumerate(DAYS_BACK):
            days_ago = back + 7 * k - shift
            ws = WorkoutSession.objects.create(
                patient=patient, week_number=WEEKS - k, patient_comfortable=True,
                total_exercises_completed=3)
            stamp = now - timedelta(days=days_ago)
            WorkoutSession.objects.filter(pk=ws.pk).update(session_date=stamp)
            fb = SessionFeedback.objects.create(
                session=ws, patient=patient, perceived_difficulty='just_right',
                sleep_last_night='7_to_8', energy_level='good', session_rpe=6)
            SessionFeedback.objects.filter(pk=fb.pk).update(created_at=stamp)
            exs = []
            for pattern in SESSION_PATTERNS[i]:
                ids = _chain_ids(pattern, scores.get(pattern, 2))
                ex_id = ids[(n + len(exs)) % min(2, len(ids))]
                ExerciseExecution.objects.create(
                    session=ws, exercise_id=ex_id, exercise_name=ex_id.replace('_', ' ').title(),
                    category='lower_body', prescribed_sets=sets, prescribed_reps=reps,
                    prescribed_rest=rest)
                exs.append(ex_id)
            n += 1
            sessions.append({'pk': ws.pk, 'days_ago': days_ago, 'week_k': k,
                             'sets': sets, 'reps': reps, 'rest': rest, 'ex': exs})
    return sessions


def _state(patient, *, phase, week, since_deload, deload_days_ago, total, today):
    PeriodisationState.objects.create(
        patient=patient, current_phase=phase, current_week=week,
        weeks_since_deload=since_deload, total_sessions_this_cycle=total,
        phase_start_date=today - timedelta(days=7 * week),
        last_deload_date=today - timedelta(days=deload_days_ago))


def _capabilities(patient, comfortable):
    for pattern, n in comfortable.items():
        PatientFamilyCapability.objects.create(
            patient=patient, family_id='%s_family' % pattern, family_name=pattern.title(),
            consecutive_comfortable_sessions=n)


def _persona_early(frag, now, today):
    p = _make_patient(frag, 'a')
    _profile(p, SCORES_EARLIER, LUNGE_EARLIER, 1, 7 * (WEEKS) + 1 - SHIFT_DAYS, now)
    sessions = _history(p, range(WEEKS - EARLY_WEEKS, WEEKS), SHIFT_DAYS, SCORES_EARLIER, now)
    _state(p, phase='hypertrophy', week=EARLY_WEEKS, since_deload=2,
           deload_days_ago=14, total=len(sessions), today=today)
    # Squat and lunge have 2 comfortable sessions in a row: lunge is still blocked by its band.
    _capabilities(p, {'squat': 2, 'lunge': 2, 'hinge': 1, 'push': 1, 'pull': 1, 'rotate': 1})
    return p, sessions


def _persona_now(frag, now, today):
    p = _make_patient(frag, 'b')
    _profile(p, SCORES_EARLIER, LUNGE_EARLIER, 1, 7 * WEEKS + 1, now)
    _profile(p, SCORES_NOW, LUNGE_NOW, 2, 3, now)
    sessions = _history(p, range(WEEKS), 0, SCORES_NOW, now)
    _state(p, phase='hypertrophy', week=WEEKS, since_deload=2,   # week = latest history week
           deload_days_ago=7 * LIGHT_WEEK + 4, total=len(sessions), today=today)
    _capabilities(p, {'squat': 2, 'lunge': 2, 'hinge': 1, 'push': 1, 'pull': 1, 'rotate': 1})
    return p, sessions


# ---- copying results into plain dicts ----------------------------------------

_ADV = re.compile(r'^(\w+) pattern advanced to level (\d)')
_BLOCK = re.compile(r'^(\w+) progression BLOCKED')


def _protocol(result, patient):
    """Plain dicts only. Reads rule results the engine returned."""
    notes = [str(n) for n in result.get('modifiers_applied', {}).get('notes', [])]
    advanced, blocked = {}, set()
    for n in notes:
        m = _ADV.match(n)
        if m:
            advanced[m.group(1).lower()] = int(m.group(2))
        m = _BLOCK.match(n)
        if m:
            blocked.add(m.group(1).lower())
    ready = {}
    for fc in patient.family_capabilities.all():
        ready[fc.family_id.split('_')[0]] = bool(check_progression_ready(fc))
    rows = []
    for ex in result.get('working_sets', []):
        asym = ex.get('asymmetry') or {}
        extra = int(asym.get('extra_sets_weak', 0) or 0)
        rows.append({
            'pattern': ex.get('movement_pattern', ''),
            'exercise_id': ex.get('exercise_id', ''),
            'name': str(ex.get('exercise_name', '')),
            'sets': ex.get('sets'),
            'reps': ex.get('reps'),
            'hold': ex.get('hold_duration') or 0,
            'rest': ex.get('rest_seconds'),
            'level': ex.get('capability_level'),
            'unilateral': bool(ex.get('is_unilateral')),
            'rule': asym.get('rule', 'none'),
            'extra': extra,
            'sets_weak': ex.get('sets_weak_side'),
            'is_new': bool(ex.get('is_new_exercise')),
        })
    return {
        'status': result.get('status', ''),
        'stop_reason': str(result.get('stop_reason', '')),
        'deload': result.get('status') == 'deload',
        'phase': (result.get('meta') or {}).get('periodisation_phase', ''),
        'notes': notes,
        'advanced': advanced,
        'blocked': sorted(blocked),
        'ready': ready,
        'rows': rows,
    }


def _why(row, proto):
    """Short generic labels from the engine's own rule results."""
    out = []
    if proto['deload']:
        out.append(TEXT['why_deload'])
    if row['extra']:
        out.append(TEXT['why_sym'].format(rule=row['rule'], extra=row['extra']))
    p = row['pattern']
    if p in proto['blocked']:
        out.append(TEXT['why_blocked'])
    elif p in proto['advanced']:
        out.append(TEXT['why_adv'].format(level=proto['advanced'][p]))
    return out


def _week_table(sessions):
    weeks = {}
    for s in sessions:
        w = weeks.setdefault(s['week_k'], {'n': 0, 'sets': 0})
        w['n'] += 1
        w['sets'] += s['sets'] * len(s['ex'])
    out = []
    for k in sorted(weeks, reverse=True):
        out.append({'label': 'Week %d%s' % (WEEKS - k, ' (latest)' if k == 0 else ''),
                    'sessions': weeks[k]['n'], 'sets': weeks[k]['sets'],
                    'note': TEXT['light_note'] if k == LIGHT_WEEK else ''})
    return out


def _day_strip(sessions, now):
    out = []
    for s in sorted(sessions, key=lambda x: -x['days_ago']):
        if s['days_ago'] > 7:
            continue
        pain = PainEvent.objects.filter(session_id=s['pk']).count()
        day = DAY_NAMES[(now - timedelta(days=s['days_ago'])).weekday()]
        out.append({
            'day': day,
            'exercises': ['%s: %d x %d' % (e.replace('_', ' '), s['sets'], s['reps'])
                          for e in s['ex']],
            'rest': s['rest'],
            'pain': TEXT['pain_some'] if pain else TEXT['pain_none'],
            'pain_n': pain,
        })
    return out


def _lsi(pair):
    return _compute_asymmetry_raw(pair[0], pair[1])[1]


def build_page():
    """Run the demo and return plain dicts. Nothing is kept in the database."""
    frag = uuid.uuid4().hex[:8]
    now = timezone.now()
    today = date.today()           # the engine reads date.today() too
    with transaction.atomic():
        try:
            pa, sess_a = _persona_early(frag, now, today)
            run_a = _protocol(generate_v1_session(pa), pa)
            pb, sess_b = _persona_now(frag, now, today)
            run_b = _protocol(generate_v1_session(pb), pb)
            weeks = _week_table(sess_b)
            days = _day_strip(sess_b, now)
        finally:
            transaction.set_rollback(True)
    return _assemble(run_a, run_b, weeks, days)


def _lunge_row(run):
    rows = [r for r in run['rows'] if r['pattern'] == 'lunge']
    uni = [r for r in rows if r['unilateral']]
    return (uni or rows or [None])[0]


def _hero(run_a, run_b, sym):
    """The three before/now numbers, read from this request's results. '-' if missing."""
    def pct(v):
        return '%d%%' % round(v) if v is not None else '-'

    def extra(run):
        r = _lunge_row(run)
        return '+%d' % r['extra'] if r else '-'

    def level(run, saved):
        r = _lunge_row(run)
        v = run['advanced'].get('lunge') if saved else None
        if v is None and r:
            v = r['level']
        return str(v) if v is not None else '-'
    return {
        'balance': (pct(sym['lunge'][0]), pct(sym['lunge'][1])),
        'extra': (extra(run_a), extra(run_b)),
        'level': (level(run_a, False), level(run_b, True)),
    }


def _assemble(run_a, run_b, weeks, days):
    for run in (run_a, run_b):
        for r in run['rows']:
            r['why'] = _why(r, run)
    diff = []
    by_a, by_b = {}, {}
    for r in run_a['rows']:
        by_a.setdefault(r['pattern'], []).append(r)
    for r in run_b['rows']:
        by_b.setdefault(r['pattern'], []).append(r)
    for pattern in list(by_b) + [p for p in by_a if p not in by_b]:
        a_rows, b_rows = by_a.get(pattern, []), by_b.get(pattern, [])
        for i in range(max(len(a_rows), len(b_rows))):
            a = a_rows[i] if i < len(a_rows) else None
            b = b_rows[i] if i < len(b_rows) else None
            why = (['%s: %s' % (TEXT['run_a'], w) for w in (a or {}).get('why', [])]
                   + ['%s: %s' % (TEXT['run_b'], w) for w in (b or {}).get('why', [])])
            diff.append({'pattern': pattern, 'a': a, 'b': b,
                         'why': why or [TEXT['why_none']]})
    hop_bench = LSI_THRESHOLDS['hop']
    sym = {'lunge': (_lsi(LUNGE_EARLIER), _lsi(LUNGE_NOW)),
           'hop': (_lsi(HOP_EARLIER), _lsi(HOP_NOW))}
    return {
        'hero': _hero(run_a, run_b, sym),
        't': TEXT, 'weeks': weeks, 'days': days, 'run_a': run_a, 'run_b': run_b,
        'diff': diff, 'hop_bench': hop_bench,
        'sym': sym,
    }


def exhibition_progression(request):
    _require_flag()
    with _LOCK:
        ctx = build_page()
    return render(request, 'strength_app/exhibition_progression.html', ctx)
