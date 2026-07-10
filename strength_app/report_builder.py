"""
R2 — the session report engine.

``build_report(session_log) -> dict`` is a pure builder: it reads the
database rows hanging off one SessionLog and returns the complete report
dict, deterministically. No request objects, no rendering, no side effects.
``generate_session_report(session_log)`` persists that dict as an immutable
SessionReport snapshot exactly once (idempotent — an existing report is
returned untouched, locked decision 3).

Pain source of truth is PainEvent, NEVER SessionLogItem.pain (locked
decision 4) — silent below-threshold reports must appear. PainEvents are
tied to the session by patient + the session's time window (an explicit FK
was deliberately not added in R1; managed patients cannot run the athlete
flow, so the window is unambiguous).

NARRATIVE RULE TABLE (every sentence traceable to a rule; deterministic
templates, no free generation, no invention):
  S1 opener      — always. By status:
                   complete: "{name} completed {done} of {total} exercises
                   in {duration}."  (all done: "all {total} exercises")
                   ended_early_pain: "{name}'s session was stopped early
                   after a high pain report, {done} of {total} exercises in."
                   partial: "{name} completed {done} of {total} exercises
                   before the session ended without a finish."
  S2 positive    — when >=1 camera exercise has a form average: highest
                   form-average exercise: "Form was strongest on {ex}
                   ({pct}%)."
  S3 concern     — when the fatigue pattern fired: its evidence sentence.
                   Else, when some camera exercise averaged < 70%:
                   "Form on {ex} averaged {pct}% and is worth a look."
  S4 warm-in     — when the warm-in pattern fired (and S3 didn't): its
                   evidence sentence.
  S5 pain        — when >=1 PainEvent: the highest-severity event in one
                   plain sentence: "{name} reported {type} {sev}/10 at
                   rep R of set S of {ex}[, and N other pain report(s)]
                   — {inside their usual range — the session continued /
                   above their usual level — the exercise was skipped /
                   the session was stopped for safety}."
                   (rep/set clauses drop when null.)
  S6 trend close — when trends exist, first available of: completion
                   streak ("That makes {n} fully-completed sessions in a
                   row."), form delta ("Average form was {d}% {higher|
                   lower} than the previous session.").

PATTERN THRESHOLDS (all evidence-backed, neutral wording — both the
patient and the therapist read them):
  fatigue     — on >=1 exercise with >=2 camera sets: last-set form avg
                <= first-set * 0.85, OR avg rep duration slowed >= 15%
                first->last set; OR >=2 rest extensions in the session's
                second half (by exercise order).
  warm_in     — inverse form condition (last >= first * 1.15).
  asymmetry   — DORMANT: R1 capture has no per-side split (reps, form or
                pain side) on unilateral items yet; the rule is guarded and
                yields nothing until side-tagged data exists. Documented in
                the phase report — do not fabricate.
  perception  — exercise rated 'easy' whose camera form fell >= 20%
                first->last set.
  tempo       — >= 60% of tempo-scored reps missing in the same phase and
                direction: "tends to rush/extend the {phase} phase".

TEMPO ADHERENCE (locked): a rep phase is on-tempo within +/-40% of the
prescribed seconds or +/-0.7s, whichever is looser. adherence % = on-tempo
phases / scored phases. Zero-tempo prescriptions score nothing and the
section is omitted. Tempo NEVER colors form (R4 rule, recorded here).

P2 (spec only, not built): stale abandoned sessions get a 'partial' report
when the today page detects them; a reportlab PDF export button.
"""

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


# Fixed integrity disclaimer — locked decision 8; rendered on every report.
REPORT_FOOTER = (
    "This report is generated automatically from camera-based estimates and "
    "the patient's own reports. Single-camera tracking has accuracy limits, "
    "and guided exercises rely on self-reported counts. It is not a clinical "
    "assessment — the treating physiotherapist retains clinical judgment."
)

# cue_id -> what the coach actually says (R4b registry in coach_core.js —
# the report quotes the live phrasing; keep the two in sync).
CUE_TEXT = {
    'knee_valgus': 'Knees toward the camera',
    'knee_valgus_landing': 'Land with your knees wide',
    'soft_landing': 'Land soft and quiet',
    'hips_even': 'Hips level, like a tray',
    'stay_hinged': 'Push your hips back',
    'foot_forward': 'Front foot further forward',
    'chest_up': 'Chest proud',
    'hips_level': 'Keep your hips level',
    'stand_tall': 'Grow tall on the step',
    'feet_together': 'Glue your feet together',
    'hips_stacked': 'Stack your hips straight up',
    'orientation': 'Get into the starting position',
    'orientation_supine': 'Lie on your back',
    'orientation_prone': 'Lie face down',
    'orientation_sidelying': 'Lie on your side',
    'hold_position': 'Back into position',
    # 2026-07 dark coaches — keep in lockstep with coach_core.js CUES.
    'wall_sit_slide_down': 'Slide down — thighs level with the floor',
    'wall_sit_heels': 'Keep both heels on the floor',
    'plank_hips_sag': 'Lift your hips — straight line',
    'plank_hips_pike': 'Lower your hips — straight line',
    'side_plank_hip_drop': 'Push your hip up',
    'balance_foot_down': 'Lift your foot to restart the clock',
    'slr_knee_straight': 'Keep that knee locked straight',
    'prone_hips_flat': 'Keep your hips on the floor',
    'pelvis_still': 'Keep your pelvis still',
    'press_even': 'Press both arms up together',
    'row_sit_tall': 'Sit tall — pull with your back',
}

DIFFICULTY_LABEL = {
    'easy': 'easy', 'right': 'just right', 'hard': 'hard',
    'too_hard': 'too hard',
}

PHASE_LABEL = {'ecc': 'lowering', 'hold': 'hold', 'con': 'raising'}


def _cue_text(cue_id):
    if cue_id in CUE_TEXT:
        return CUE_TEXT[cue_id]
    if cue_id.startswith('cue_'):
        return cue_id[4:].replace('_', ' ').capitalize() + ' position cue'
    if cue_id.startswith('arrow_'):
        return 'Effort cue'
    return cue_id.replace('_', ' ')


def _mmss(seconds):
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _mean(values):
    values = [v for v in values if v is not None]
    return (sum(values) / len(values)) if values else None


def _parse_tempo(tempo):
    """'3-1-2-0' -> {'ecc': 3, 'hold': 1, 'con': 2}; junk/legacy -> {} of
    zeros (same normalization as the execute template)."""
    parts = str(tempo or '').replace('–', '-').replace('—', '-').split('-')
    while len(parts) < 4:
        parts.append('0')
    nums = []
    for p in parts[:4]:
        try:
            nums.append(max(0, int(float(p.strip() or 0))))
        except (TypeError, ValueError):
            nums.append(0)
    return {'ecc': nums[0], 'hold': nums[1], 'con': nums[2]}


def tempo_adherence(reps, prescribed):
    """Per-set tempo adherence from R1 phase_ms. Returns
    {'pct': int, 'misses': {(phase, direction): count}, 'scored': int} or
    None when nothing is scorable (no tempo / no phase data)."""
    prescribed = {k: v for k, v in (prescribed or {}).items() if v > 0}
    if not prescribed:
        return None
    scored = on_tempo = reps_scored = 0
    misses = {}
    deviations = {}
    for rep in reps or []:
        if not isinstance(rep, dict):
            continue
        phase_ms = rep.get('phase_ms')
        if not isinstance(phase_ms, dict):
            continue
        rep_counted = False
        for phase, target in prescribed.items():
            ms = phase_ms.get(phase)
            if not isinstance(ms, (int, float)) or ms <= 0:
                continue
            actual = ms / 1000.0
            tolerance = max(0.4 * target, 0.7)
            scored += 1
            rep_counted = True
            if abs(actual - target) <= tolerance:
                on_tempo += 1
            else:
                direction = 'fast' if actual < target else 'slow'
                misses[(phase, direction)] = misses.get((phase, direction), 0) + 1
                deviations.setdefault((phase, direction), []).append(actual)
        if rep_counted:
            reps_scored += 1
    if not scored:
        return None
    return {
        'pct': int(round(100.0 * on_tempo / scored)),
        'scored': scored,
        'reps_scored': reps_scored,
        'misses': misses,
        'deviations': deviations,
    }


def _pain_place(event):
    """'at rep 6 of set 2' / 'during set 3' / '' — honest to what we know."""
    if event.rep_number and event.set_number:
        return f"at rep {event.rep_number} of set {event.set_number}"
    if event.set_number:
        return f"during set {event.set_number}"
    return ""


def _pain_dict(event):
    place = _pain_place(event)
    text = f"{event.pain_type or 'unspecified'} {event.pain_severity}/10"
    if place:
        text += f" {place}"
    return {
        'severity': event.pain_severity,
        'type': event.pain_type or 'unspecified',
        'set_number': event.set_number,
        'rep_number': event.rep_number,
        'outcome': event.outcome,
        'text': text,
    }


def _exercise_block(presc_item, log_item, set_logs, rest_events, pain_events,
                    catalog_entry):
    """One exercises[] entry. Every read is defensive — a session with no
    camera data (or no set logs at all) still reports honestly."""
    tempo_parts = _parse_tempo(presc_item.tempo)
    has_tempo = any(v > 0 for v in tempo_parts.values())

    modes = {s.mode for s in set_logs}
    # A5 (2026-07 exam): plyo camera coaching is landing-check only (locked
    # rule) — the mode chip must say so rather than implying full-trajectory
    # form tracking. (Whether Form% should ALSO be suppressed for plyo sets
    # is with the physio mentor — MENTOR_REVIEW_QUEUE §2026-07.)
    is_plyo = (catalog_entry or {}).get('movement_pattern') == 'Plyometrics'
    camera_label = 'camera (landing checks)' if is_plyo else 'camera-tracked'
    if 'camera' in modes:
        mode_label = camera_label
    elif set_logs:
        mode_label = 'guided (self-reported)'
    else:
        mode_label = (camera_label
                      if (catalog_entry or {}).get('v2_ghost_supported')
                      else 'guided (self-reported)')

    sets_out = []
    all_reps = []
    working_seconds = 0
    for s in set_logs:
        reps = [r for r in (s.reps_json if isinstance(s.reps_json, list) else [])
                if isinstance(r, dict)]
        all_reps.extend(reps)
        form_avg = _mean([r.get('form_pct') for r in reps])
        depths = [r.get('bottom_angle') for r in reps
                  if r.get('bottom_angle') is not None]
        adherence = tempo_adherence(reps, tempo_parts) if has_tempo else None
        rep_durations = [
            sum(p.get('ms', 0) for p in r['phases_raw'] if isinstance(p, dict))
            for r in reps if isinstance(r.get('phases_raw'), list)
        ]
        avg_rep_ms = int(_mean(rep_durations)) if rep_durations else None
        if s.started_at and s.ended_at:
            working_seconds += (s.ended_at - s.started_at).total_seconds()

        set_rest = [e for e in rest_events if e.set_number == s.set_number]
        extensions = [e for e in set_rest
                      if e.context == 'between_sets' and not e.cut_short
                      and e.extra_seconds > 0]
        pauses = [e for e in set_rest if e.context == 'pause']
        sets_out.append({
            'set_number': s.set_number,
            'reps': s.reps_count,
            'hold_seconds': s.hold_seconds or 0,
            'self_reported': s.mode == 'guided',
            'form_avg': round(form_avg, 1) if form_avg is not None else None,
            'depth_best': min(depths) if depths else None,
            'depth_avg': round(_mean(depths), 1) if depths else None,
            'tempo_pct': adherence['pct'] if adherence else None,
            'avg_rep_ms': avg_rep_ms,
            'rest_extended_seconds': sum(e.extra_seconds for e in extensions),
            'rest_extension_count': len(extensions),
            'rest_cut_short': any(e.cut_short for e in set_rest),
            'pause_seconds': sum(e.extra_seconds for e in pauses),
        })

    # Cues aggregated across the exercise's reps.
    cue_counts = {}
    for rep in all_reps:
        for cue in rep.get('cues') or []:
            cid = cue.get('cue_id')
            if not cid:
                continue
            entry = cue_counts.setdefault(cid, {'fired': 0, 'corrected': 0})
            entry['fired'] += 1
            if cue.get('corrected'):
                entry['corrected'] += 1
    cues_out = []
    for cid in sorted(cue_counts):
        entry = cue_counts[cid]
        if entry['corrected'] == entry['fired']:
            note = 'corrected within a rep each time'
        elif entry['corrected'] > 0:
            note = f"corrected {entry['corrected']} of {entry['fired']} times"
        elif entry['fired'] >= 3:
            note = 'persisted after cueing — flagged for review'
        else:
            note = 'not corrected within the session'
        cues_out.append({
            'cue_id': cid,
            'text': _cue_text(cid),
            'fired': entry['fired'],
            'corrected': entry['corrected'],
            'note': note,
        })

    # Exercise-level tempo adherence (all reps together).
    exercise_adherence = (tempo_adherence(all_reps, tempo_parts)
                          if has_tempo else None)
    tempo_out = None
    if exercise_adherence:
        tempo_out = {'pct': exercise_adherence['pct']}
        if exercise_adherence['misses']:
            (phase, direction), count = max(
                exercise_adherence['misses'].items(), key=lambda kv: kv[1])
            avg_actual = _mean(exercise_adherence['deviations'][(phase, direction)])
            # share = reps missing this phase/direction over scored REPS
            # (the docstring rule) — one phase misses at most once per rep.
            tempo_out['dominant_miss'] = {
                'phase': PHASE_LABEL[phase],
                'direction': direction,
                'avg_actual': round(avg_actual, 1),
                'prescribed': tempo_parts[phase],
                'share': round(count / exercise_adherence['reps_scored'], 2),
            }

    # R1c times — per Pawan's R2 addition: BOTH clocks, clearly labeled.
    # elapsed = page entry -> exercise done (includes rest and pauses);
    # working = sum of the set clocks (R1 excludes rest/pause by design).
    elapsed_seconds = None
    if log_item is not None and log_item.started_at and log_item.completed_at:
        elapsed_seconds = (log_item.completed_at - log_item.started_at).total_seconds()
    time_out = {
        'elapsed_mmss': _mmss(elapsed_seconds) if elapsed_seconds is not None else None,
        'working_mmss': _mmss(working_seconds) if set_logs else None,
        'label': 'elapsed includes rest and pauses; working is time in the sets',
    }

    skip_events = [e for e in pain_events if e.outcome == 'exercise_skipped']
    skipped = None
    if skip_events:
        skipped = ('skipped after a pain report above the usual level '
                   f"({skip_events[0].pain_severity}/10)")
    elif log_item is not None and log_item.completed_at is None and not set_logs:
        skipped = 'not reached'

    difficulty = (DIFFICULTY_LABEL.get(log_item.difficulty, '')
                  if log_item is not None else '')

    return {
        'exercise_id': presc_item.exercise_id,
        'name': presc_item.exercise_name,
        'mode': mode_label,
        'prescribed': {
            'sets': presc_item.sets,
            'reps': presc_item.reps,
            'tempo': presc_item.tempo or '',
            'load': presc_item.load or '',
            'rest_seconds': presc_item.rest_seconds,
        },
        'achieved': {
            'sets': len(set_logs) or (log_item.sets_completed if log_item else 0),
            'reps_per_set': [s.reps_count for s in set_logs],
        },
        'time': time_out,
        'sets': sets_out,
        'cues': cues_out,
        'tempo': tempo_out,
        'pain': [_pain_dict(e) for e in pain_events],
        'feedback': difficulty,
        'skipped': skipped,
        'demo_viewed': any(s.demo_viewed for s in set_logs),
        'form_avg': (round(_mean([r.get('form_pct') for r in all_reps]), 1)
                     if any(r.get('form_pct') is not None for r in all_reps)
                     else None),
    }


def _find_patterns(exercise_blocks, total_exercises):
    """Pattern rules from the module docstring. Each hit is
    {'finding': ..., 'evidence': ...} in neutral, observational wording."""
    patterns = []

    def per_set_forms(block):
        return [(s['set_number'], s['form_avg']) for s in block['sets']
                if s['form_avg'] is not None]

    # Fatigue / warm-in from first->last set form (or rep speed for fatigue).
    for block in exercise_blocks:
        forms = per_set_forms(block)
        if len(forms) >= 2:
            first, last = forms[0][1], forms[-1][1]
            if first > 0 and last <= first * 0.85:
                patterns.append({
                    'finding': 'fatigue',
                    'evidence': (f"Form on {block['name']} fell from "
                                 f"{first:.0f}% (set {forms[0][0]}) to "
                                 f"{last:.0f}% (set {forms[-1][0]})."),
                })
                continue
            if first > 0 and last >= first * 1.15:
                patterns.append({
                    'finding': 'warm_in',
                    'evidence': (f"Form on {block['name']} improved from "
                                 f"{first:.0f}% to {last:.0f}% across the sets."),
                })
                continue
        speeds = [(s['set_number'], s['avg_rep_ms']) for s in block['sets']
                  if s.get('avg_rep_ms')]
        if len(speeds) >= 2 and speeds[-1][1] >= speeds[0][1] * 1.15:
            patterns.append({
                'finding': 'fatigue',
                'evidence': (f"Reps on {block['name']} slowed from "
                             f"{speeds[0][1] / 1000:.1f}s to "
                             f"{speeds[-1][1] / 1000:.1f}s between the first "
                             "and last set."),
            })

    # Fatigue from late rest extensions (second half of the protocol).
    half = max(1, total_exercises // 2)
    late_ext = sum(
        s['rest_extension_count']
        for i, block in enumerate(exercise_blocks) if i >= half
        for s in block['sets']
    )
    if late_ext >= 2 and not any(p['finding'] == 'fatigue' for p in patterns):
        patterns.append({
            'finding': 'fatigue',
            'evidence': (f"Rest was extended {late_ext} times in the second "
                         "half of the session."),
        })

    # Perception vs performance: rated easy while form fell >= 20%.
    for block in exercise_blocks:
        if block['feedback'] != 'easy':
            continue
        forms = per_set_forms(block)
        if len(forms) >= 2 and forms[0][1] > 0 and forms[-1][1] <= forms[0][1] * 0.8:
            patterns.append({
                'finding': 'perception_vs_performance',
                'evidence': (f"{block['name']} was rated easy while form "
                             f"fell from {forms[0][1]:.0f}% to "
                             f"{forms[-1][1]:.0f}%."),
            })

    # Tempo tendency: same phase+direction missing on >= 60% of scored phases.
    for block in exercise_blocks:
        tempo = block.get('tempo')
        if (tempo and tempo.get('dominant_miss')
                and tempo['dominant_miss'].get('share', 0) >= 0.6):
            miss = tempo['dominant_miss']
            verb = 'rushes' if miss['direction'] == 'fast' else 'extends'
            patterns.append({
                'finding': 'tempo_tendency',
                'evidence': (f"{verb.capitalize()} the {miss['phase']} phase "
                             f"on {block['name']}: about {miss['avg_actual']}s "
                             f"against {miss['prescribed']}s prescribed."),
            })

    # L/R asymmetry — DORMANT (no per-side capture yet; see docstring).
    return patterns


def _find_trends(exercise_blocks, session_form_avg, completion_pct,
                 pain_events, previous_reports):
    """Comparisons against up to 3 previous SessionReport snapshots."""
    trends = []
    if not previous_reports:
        return trends
    prev_jsons = [r.report_json or {} for r in previous_reports]

    # Average form delta vs the immediately previous session.
    prev_form = (prev_jsons[0].get('header') or {}).get('form_avg')
    if session_form_avg is not None and prev_form is not None:
        delta = round(session_form_avg - prev_form, 1)
        if abs(delta) >= 1:
            trends.append({
                'finding': 'form_delta',
                'evidence': (f"Average form {abs(delta):.0f}% "
                             f"{'higher' if delta > 0 else 'lower'} than the "
                             "previous session."),
            })

    # ROM delta per repeated camera exercise (lower bottom angle = deeper).
    for block in exercise_blocks:
        best = min((s['depth_best'] for s in block['sets']
                    if s['depth_best'] is not None), default=None)
        if best is None:
            continue
        prev_bests = []
        for pj in prev_jsons:
            for prev_block in pj.get('exercises', []):
                if prev_block.get('exercise_id') != block['exercise_id']:
                    continue
                pb = min((s.get('depth_best') for s in prev_block.get('sets', [])
                          if s.get('depth_best') is not None), default=None)
                if pb is not None:
                    prev_bests.append(pb)
        if prev_bests:
            delta = round(_mean(prev_bests) - best, 1)
            if abs(delta) >= 5:
                trends.append({
                    'finding': 'rom_delta',
                    'evidence': (f"{block['name']} depth "
                                 f"{'improved' if delta > 0 else 'reduced'} by "
                                 f"about {abs(delta):.0f}° vs recent sessions."),
                })

    # Pain recurrence: same exercise painful in consecutive prior reports.
    for block in exercise_blocks:
        if not block['pain']:
            continue
        streak = 1
        for pj in prev_jsons:
            hit = any(prev_block.get('exercise_id') == block['exercise_id']
                      and prev_block.get('pain')
                      for prev_block in pj.get('exercises', []))
            if hit:
                streak += 1
            else:
                break
        if streak >= 2:
            severities = sorted(p['severity'] for p in block['pain'])
            trends.append({
                'finding': 'pain_recurrence',
                'evidence': (f"{_ordinal(streak)} consecutive session with "
                             f"{block['pain'][0]['type']} pain during "
                             f"{block['name']} (severity {severities[0]}"
                             f"–{severities[-1]}/10 today)."),
            })

    # Completion streak (this session + consecutive previous at 100%).
    if completion_pct == 100:
        streak = 1
        for pj in prev_jsons:
            if (pj.get('header') or {}).get('completion_pct') == 100:
                streak += 1
            else:
                break
        if streak >= 2:
            trends.append({
                'finding': 'completion_streak',
                'evidence': f"{streak} fully-completed sessions in a row.",
            })
    return trends


def _ordinal(n):
    return {1: '1st', 2: '2nd', 3: '3rd'}.get(n, f'{n}th')


def _narrative(name, status, done, total, duration_mmss, exercise_blocks,
               patterns, pain_events, trends):
    """Deterministic sentence composition — rule table in the module
    docstring. 3–6 sentences depending on what the data supports."""
    sentences = []

    minutes = duration_mmss.split(':')[0]
    if status == 'complete' and done == total:
        sentences.append(f"{name} completed all {total} exercises in "
                         f"{minutes} minutes.")
    elif status == 'complete':
        sentences.append(f"{name} completed {done} of {total} exercises in "
                         f"{minutes} minutes.")
    elif status == 'ended_early_pain':
        sentences.append(f"{name}'s session was stopped early after a high "
                         f"pain report, {done} of {total} exercises in.")
    else:
        sentences.append(f"{name} completed {done} of {total} exercises "
                         "before the session ended without a finish.")

    with_form = [b for b in exercise_blocks if b['form_avg'] is not None]
    if with_form:
        best = max(with_form, key=lambda b: b['form_avg'])
        sentences.append(f"Form was strongest on {best['name']} "
                         f"({best['form_avg']:.0f}%).")

    fatigue = next((p for p in patterns if p['finding'] == 'fatigue'), None)
    if fatigue:
        sentences.append(fatigue['evidence'])
    else:
        weak = [b for b in with_form if b['form_avg'] < 70]
        if weak:
            worst = min(weak, key=lambda b: b['form_avg'])
            sentences.append(f"Form on {worst['name']} averaged "
                             f"{worst['form_avg']:.0f}% and is worth a look.")
        else:
            warm = next((p for p in patterns if p['finding'] == 'warm_in'), None)
            if warm:
                sentences.append(warm['evidence'])

    if pain_events:
        worst = max(pain_events, key=lambda e: e.pain_severity)
        place = _pain_place(worst)
        where = (f"{place} of {worst.exercise_name}" if place
                 else f"on {worst.exercise_name}")
        others = len(pain_events) - 1
        extra = (f", plus {others} other pain report"
                 f"{'s' if others > 1 else ''}") if others else ""
        outcome_text = {
            'continued': 'inside their usual range — the session continued',
            'exercise_skipped': 'above their usual level — the exercise was skipped',
            'session_paused': 'the session was stopped for safety',
        }.get(worst.outcome, 'noted for the therapist')  # D6: never KeyError
        sentences.append(f"{name} reported {worst.pain_type or 'unspecified'} "
                         f"{worst.pain_severity}/10 {where}{extra} — "
                         f"{outcome_text}.")

    if trends:
        streak = next((t for t in trends if t['finding'] == 'completion_streak'), None)
        form_d = next((t for t in trends if t['finding'] == 'form_delta'), None)
        close = streak or form_d
        if close:
            sentences.append(("That makes " + close['evidence'].lower())
                             if close is streak else close['evidence'])

    return ' '.join(sentences[:6])


def build_report(session_log):
    """Assemble the full report dict for one SessionLog. Pure: DB reads
    only, deterministic, defensive .get everywhere — a session with no
    camera data (or almost no data at all) still builds."""
    from therapist_app.exercise_catalog import EXERCISES_BY_ID
    from therapist_app.models import SessionReport
    from .models import PainEvent, PatientProfile

    link = session_log.link
    prescription = session_log.prescription
    profile = PatientProfile.objects.filter(user=link.patient).first()
    name = (profile.name if profile else '') or link.full_name or 'Patient'
    first_name = name.split()[0] if name else 'Patient'

    presc_items = list(prescription.items.all().order_by('order', 'id'))
    _items = list(session_log.items.all())  # B-N4: one query, two maps
    log_items = {li.prescription_item_id: li for li in _items}
    log_items_by_ex = {li.exercise_id: li for li in _items}
    set_logs_all = list(session_log.set_logs.all())
    rest_events_all = list(session_log.rest_events.all())

    window_start = session_log.started_at
    pain_events_all = list(
        PainEvent.objects.filter(
            patient=profile, created_at__gte=window_start,
        ).order_by('created_at')
    ) if profile else []

    pause_events = [e for e in pain_events_all
                    if e.outcome == 'session_paused']
    if session_log.completed_at:
        status = 'complete'
        window_end = session_log.completed_at
    elif pause_events:
        status = 'ended_early_pain'
        window_end = pause_events[0].created_at
    else:
        status = 'partial'
        candidates = ([s.ended_at for s in set_logs_all if s.ended_at]
                      + [e.created_at for e in pain_events_all]
                      + [window_start])
        window_end = max(candidates)
    # Constrain events to the session window (trailing slack for the last POST).
    cutoff = window_end + timedelta(seconds=90)
    pain_events = [e for e in pain_events_all if e.created_at <= cutoff]

    exercise_blocks = []
    for presc_item in presc_items:
        log_item = (log_items.get(presc_item.id)
                    or log_items_by_ex.get(presc_item.exercise_id))
        set_logs = sorted(
            (s for s in set_logs_all if s.exercise_id == presc_item.exercise_id),
            key=lambda s: s.set_number)
        rest = [e for e in rest_events_all
                if e.exercise_id == presc_item.exercise_id]
        pain = [e for e in pain_events
                if e.exercise_id == presc_item.exercise_id]
        exercise_blocks.append(_exercise_block(
            presc_item, log_item, set_logs, rest, pain,
            EXERCISES_BY_ID.get(presc_item.exercise_id)))

    total = len(presc_items)
    fully_done = sum(
        1 for b in exercise_blocks
        if b['achieved']['sets'] >= b['prescribed']['sets'] and not b['skipped'])
    completion_pct = int(round(100.0 * fully_done / total)) if total else 0
    duration_seconds = (window_end - window_start).total_seconds()
    session_form_avg = _mean([b['form_avg'] for b in exercise_blocks])
    if session_form_avg is not None:
        session_form_avg = round(session_form_avg, 1)

    # Safety FIRST (rendered first when non-empty; omitted when empty).
    safety = []
    for e in pain_events:
        if e.outcome == 'session_paused':
            safety.append({
                'kind': 'pause',
                'text': (f"Session stopped: {e.pain_type or 'unspecified'} "
                         f"pain {e.pain_severity}/10 on {e.exercise_name} "
                         f"{_pain_place(e)}".rstrip() + "."),
            })
        elif e.outcome == 'exercise_skipped':
            safety.append({
                'kind': 'skip',
                'text': (f"{e.exercise_name} skipped: {e.pain_type or 'unspecified'} "
                         f"pain {e.pain_severity}/10 crossed the usual level "
                         f"({e.threshold_applied}/10)."),
            })
    if status == 'partial':
        safety.append({'kind': 'incomplete',
                       'text': 'Session ended without the finish step.'})

    previous_reports = list(
        SessionReport.objects
        .filter(patient=profile, session_log__started_at__lt=window_start)
        .order_by('-session_log__started_at')[:3]
    ) if profile else []
    session_number = type(session_log).objects.filter(
        link=link, started_at__lte=window_start).count()

    patterns = _find_patterns(exercise_blocks, total)
    trends = _find_trends(exercise_blocks, session_form_avg, completion_pct,
                          pain_events, previous_reports)

    # Patient -> therapist messages inside the session window.
    messages = [
        {'time': timezone.localtime(m.sent_at).strftime('%I:%M %p').lstrip('0'),
         'body': m.body}
        for m in link.messages.filter(
            is_system=False, sender=link.patient,
            sent_at__gte=window_start, sent_at__lte=window_end,
        ).order_by('sent_at')
    ]

    # Review points: max 4 neutral flags — never advice, never diagnosis.
    review_points = []
    if any(s['kind'] == 'pause' for s in safety):
        review_points.append('High-pain stop during the session')
    for t in trends:
        if t['finding'] == 'pain_recurrence':
            review_points.append(t['evidence'])
    for b in exercise_blocks:
        for cue in b['cues']:
            if cue['fired'] >= 3 and cue['corrected'] == 0:
                review_points.append(
                    f"{b['name']}: form cue persisted after coaching "
                    f"({cue['text'].lower()})")
    for p in patterns:
        if p['finding'] == 'fatigue':
            review_points.append(p['evidence'])
            break
    review_points = review_points[:4]

    local_date = timezone.localtime(window_start)
    header = {
        'patient_name': name,
        'date': local_date.strftime('%d %b %Y'),
        'week_number': prescription.week_number,
        'session_number': session_number,
        'status': status,
        'duration_mmss': _mmss(duration_seconds),
        'completion_pct': completion_pct,
        'exercises_done': fully_done,
        'exercises_total': total,
        'form_avg': session_form_avg,
    }

    return {
        'version': 1,
        'header': header,
        'safety': safety,
        'narrative': _narrative(first_name, status, fully_done, total,
                                _mmss(duration_seconds), exercise_blocks,
                                patterns, pain_events, trends),
        'exercises': exercise_blocks,
        'patterns': patterns,
        'trends': trends,
        'messages': messages,
        'review_points': review_points,
        'footer': REPORT_FOOTER,
    }


def generate_session_report(session_log):
    """Idempotent persist: an existing report is returned untouched
    (locked decision 3 — the snapshot is immutable). Callers wrap this in
    try/except; a report failure must NEVER block the patient's flow."""
    from django.db import IntegrityError
    from therapist_app.models import SessionReport
    from .models import PatientProfile

    existing = SessionReport.objects.filter(session_log=session_log).first()
    if existing:
        return existing

    data = build_report(session_log)
    profile = PatientProfile.objects.filter(user=session_log.link.patient).first()
    # B-D2 (2026-07 exam): a None profile used to raise NOT-NULL
    # IntegrityError, which the race handler below misread — the report was
    # silently never generated and every retry failed identically.
    if profile is None:
        logger.error(
            'report NOT generated: no PatientProfile for link user %s '
            '(session_log=%s)', session_log.link.patient_id, session_log.id)
        return None
    try:
        return SessionReport.objects.create(
            link=session_log.link,
            session_log=session_log,
            patient=profile,
            report_date=timezone.localtime(session_log.started_at).date(),
            status=data['header']['status'],
            report_json=data,
        )
    except IntegrityError:
        # Concurrent trigger won the race — theirs is the snapshot.
        return SessionReport.objects.filter(session_log=session_log).first()
