"""DA-H2 — Ideal-trajectory generator for exercise modules.

For every exercise registered in EXERCISE_METADATA, synthesizes the
*ideal* angle trajectory implied by the module's own get_target_poses()
phase sequence (interpolating phase→phase, ~20 frames per transition,
neutral stability and tempo) and drives the module's real scoring and
rep-counting code with it.

Invariants asserted by the caller (see tests/test_deep_audit.py):
  (a) no exception through full cycles
  (b) ≥1 rep (or practice rep / side rep) counted for rep exercises
  (c) mean real-time form score ≥ 85

A module failing (c) has a C3-class target bug — fix the module, never
the harness.
"""

FRAMES_PER_TRANSITION = 20
CYCLES = 5

# Neutral, perfectly stable synthetic skeleton (pixel coords).
NEUTRAL_JOINTS = {
    'lh': (300, 400), 'lk': (300, 500), 'la': (300, 600),
    'rh': (340, 400), 'rk': (340, 500), 'ra': (340, 600),
    'ls': (300, 250), 'rs': (340, 250),
    'le': (290, 320), 'lw': (285, 390),
    're': (350, 320), 'rw': (355, 390),
    'nose': (320, 200),
}


def _scalar(value):
    """Reduce a target value to a representative scalar.

    Band targets (lo, hi) → midpoint. Bool/str hints → None (skip).
    """
    if isinstance(value, bool) or isinstance(value, str):
        return None
    if isinstance(value, (tuple, list)):
        if not value:
            return None
        try:
            return (min(value) + max(value)) / 2.0
        except TypeError:
            return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_ideal_trajectory(target_poses):
    """Return a list of angle dicts tracing one ideal cycle.

    The cycle visits phases in dict insertion order, then returns to the
    first phase (so rep state machines that complete on returning to the
    start can fire). Angles interpolate linearly between phase targets;
    keys missing from a phase carry their previous value.
    """
    phase_names = list(target_poses.keys())
    if not phase_names:
        return []

    # Collect every numeric key with per-phase scalar values
    keys = []
    for ph in phase_names:
        for k, v in target_poses[ph].items():
            if k == 'tolerance':
                continue
            if _scalar(v) is not None and k not in keys:
                keys.append(k)
    if not keys:
        return []

    # Per-phase scalar map with carry-forward for missing keys
    waypoints = []
    last = {}
    for ph in phase_names:
        point = {}
        for k in keys:
            v = _scalar(target_poses[ph].get(k))
            if v is None:
                v = last.get(k)
            point[k] = v
            last[k] = v
        waypoints.append(point)
    # Backfill any leading Nones from the first defined value
    for k in keys:
        first_defined = next((wp[k] for wp in waypoints if wp[k] is not None), 0.0)
        for wp in waypoints:
            if wp[k] is None:
                wp[k] = first_defined

    # Close the loop back to the first phase
    cycle = waypoints + [waypoints[0]]

    frames = []
    for a, b in zip(cycle, cycle[1:]):
        for i in range(FRAMES_PER_TRANSITION):
            t = i / float(FRAMES_PER_TRANSITION - 1)
            frames.append(DefaultAngles(
                {k: a[k] + (b[k] - a[k]) * t for k in keys}
            ))
    return frames


class DefaultAngles(dict):
    """Angles dict that returns 0.0 for keys the trajectory cannot know.

    Production calculate_angles() provides measured-only keys (e.g.
    hip_symmetry) that never appear in get_target_poses(); modules may
    read them in validate_form/update_rep_counter. They don't affect the
    score (FormCalculator iterates TARGET keys only), so defaulting to
    0.0 avoids false-positive KeyErrors without masking real phase-key
    bugs (those are lookups on the TARGETS dict, not this one).
    """
    def __missing__(self, key):
        return 0.0


def _call_update_rep_counter(exercise, angles, feedback, voice):
    """Mirror headless_runner's dispatch: scalar primary angle for the
    ~190 'angle' modules, full dict for the ~30 'angles' modules."""
    import inspect
    try:
        params = list(inspect.signature(exercise.update_rep_counter).parameters)
    except (TypeError, ValueError):
        params = []
    wants_dict = bool(params) and params[0] in ('angles', 'angle_dict')
    primary = next((v for v in angles.values() if isinstance(v, (int, float))), 0.0)
    first_arg = angles if wants_dict else primary
    if len(params) >= 3:
        return exercise.update_rep_counter(first_arg, feedback, voice)
    return exercise.update_rep_counter(first_arg, feedback)


def _count_reps(exercise):
    """Best-effort total of counted + practice + per-side reps."""
    total = 0
    for attr in ('rep_count', 'practice_reps_completed', 'left_count',
                 'right_count', 'left_reps', 'right_reps', 'hold_count',
                 'step_count', 'set_count'):
        v = getattr(exercise, attr, 0)
        if isinstance(v, (int, float)):
            total += v
    return total


def run_ideal_trajectory(exercise_id, exercise_cls):
    """Run one module against its own ideal trajectory.

    Returns a result dict:
      {id, status: ok|no_targets|no_scoring|error,
       error, mean_score, min_score, reps, frames}
    """
    result = {'id': exercise_id, 'status': 'ok', 'error': '',
              'mean_score': None, 'min_score': None, 'reps': 0, 'frames': 0}
    try:
        ex = exercise_cls()
    except Exception as exc:  # noqa: BLE001 — harness must keep going
        result['status'] = 'error'
        result['error'] = f'instantiation: {type(exc).__name__}: {exc}'
        return result

    get_targets = getattr(ex, 'get_target_poses', None)
    if get_targets is None:
        result['status'] = 'no_targets'
        return result

    try:
        frames = build_ideal_trajectory(get_targets())
    except Exception as exc:  # noqa: BLE001
        result['status'] = 'error'
        result['error'] = f'get_target_poses: {type(exc).__name__}: {exc}'
        return result

    if not frames:
        result['status'] = 'no_targets'
        return result

    scorer = getattr(ex, 'calculate_real_time_form_score', None)
    updater = getattr(ex, 'update_rep_counter', None)
    voice = getattr(ex, 'voice', None)

    scores = []
    try:
        for _ in range(CYCLES):
            for angles in frames:
                result['frames'] += 1
                if scorer is not None:
                    score = scorer(angles, dict(NEUTRAL_JOINTS))
                    if isinstance(score, (int, float)):
                        scores.append(float(score))
                if updater is not None:
                    feedback = {}
                    validate = getattr(ex, 'validate_form', None)
                    if validate is not None:
                        try:
                            feedback = validate(angles, getattr(ex, 'phase', None)) or {}
                        except TypeError:
                            try:
                                feedback = validate(angles) or {}
                            except Exception:  # noqa: BLE001
                                raise
                    _call_update_rep_counter(ex, angles, feedback, voice)
    except Exception as exc:  # noqa: BLE001
        result['status'] = 'error'
        result['error'] = f'{type(exc).__name__}: {exc}'
        return result

    if scores:
        result['mean_score'] = round(sum(scores) / len(scores), 1)
        result['min_score'] = round(min(scores), 1)
    else:
        result['status'] = 'no_scoring'
    result['reps'] = _count_reps(ex)
    return result


def run_all():
    """Run the invariant over every registered exercise. Returns results list."""
    from strength_app.exercise_system.exercise_registry_v2 import EXERCISE_METADATA

    results = []
    for ex_id, meta in EXERCISE_METADATA.items():
        results.append(run_ideal_trajectory(ex_id, meta['class']))
    return results
