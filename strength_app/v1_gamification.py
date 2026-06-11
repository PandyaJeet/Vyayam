"""
VYAYAM V1 — Gamification compute layer.

Derives XP, levels, ranks, and streaks from existing models without
requiring new database tables. Drop-in import for views.
"""

import math
from datetime import date, timedelta

from .models import WorkoutSession, StrengthProfile

# ── XP & Level System ─────────────────────────────────────────────────────

XP_PER_SESSION = 40          # base XP per completed session
XP_PER_LEVEL = 200           # XP needed to advance one level
MAX_LEVEL = 99

LEVEL_TITLES = {
    (1, 4):   'Beginner',
    (5, 9):   'Novice Mover',
    (10, 14): 'Dedicated Athlete',
    (15, 19): 'Strong Foundation',
    (20, 29): 'Movement Master',
    (30, 49): 'Elite Performer',
    (50, 99): 'VYAYAM Legend',
}


def compute_xp_and_level(patient):
    """Return dict with total_xp, user_level, xp_current, xp_next_level, xp_percentage, level_title."""
    from django.db.models import Sum
    qs = WorkoutSession.objects.filter(patient=patient)
    total_sessions = qs.count()
    # Sum persisted xp_earned; fall back to flat rate for legacy sessions with xp_earned=0
    stored_xp = qs.aggregate(s=Sum('xp_earned'))['s'] or 0
    legacy_sessions = qs.filter(xp_earned=0).count()
    total_xp = stored_xp + legacy_sessions * XP_PER_SESSION
    user_level = min(MAX_LEVEL, total_xp // XP_PER_LEVEL + 1)
    xp_into_level = total_xp - (user_level - 1) * XP_PER_LEVEL
    xp_next = XP_PER_LEVEL
    xp_pct = min(100, round(xp_into_level / max(1, xp_next) * 100))

    title = 'Beginner'
    for (lo, hi), t in LEVEL_TITLES.items():
        if lo <= user_level <= hi:
            title = t
            break

    return {
        'total_xp': total_xp,
        'user_level': user_level,
        'xp_current': xp_into_level,
        'xp_next_level': xp_next,
        'xp_percentage': xp_pct,
        'level_title': title,
        'sessions_count': total_sessions,
    }


# ── Streak (consecutive days) ────────────────────────────────────────────

def compute_streak_days(patient):
    """Return number of consecutive days (counting back from today) with at least one session."""
    streak = 0
    check = date.today()
    while True:
        has = WorkoutSession.objects.filter(
            patient=patient,
            session_date__date=check,
        ).exists()
        if has:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


# ── Pattern Ranks ────────────────────────────────────────────────────────

RANK_MAP = {
    0: ('UNRANKED', 'unranked'),
    1: ('BRONZE I', 'bronze'),
    2: ('SILVER I', 'silver'),
    3: ('GOLD I', 'gold'),
    4: ('PLATINUM I', 'platinum'),
    5: ('DIAMOND I', 'diamond'),
}

PATTERN_FIELDS = [
    ('Squat', 'squat_score'),
    ('Hinge', 'hinge_score'),
    ('Push',  'push_score'),
    ('Pull',  'pull_score'),
    ('Core',  'core_score'),
    ('Carry', 'rotate_score'),   # mapped from rotate to carry for UI
    ('Lunge', 'lunge_score'),
]


def compute_movement_patterns(profile, prev_profile=None):
    """Return list of 7 pattern dicts with rank, XP, trend, and radar SVG coords."""
    patterns = []
    center_x, center_y = 200, 200
    max_radius = 160
    n = len(PATTERN_FIELDS)

    for i, (name, field) in enumerate(PATTERN_FIELDS):
        score = getattr(profile, field, 0) if profile else 0
        prev_score = getattr(prev_profile, field, 0) if prev_profile else score

        rank_label, rank_class = RANK_MAP.get(score, ('UNRANKED', 'unranked'))
        xp = score * 200  # visual XP per pattern
        xp_pct = min(100, score * 20)

        if score > prev_score:
            trend = 'up'
        elif score < prev_score:
            trend = 'down'
        else:
            trend = 'flat'

        # SVG radar coordinates
        angle = (2 * math.pi * i / n) - math.pi / 2  # start from top
        radius = (score / 5.0) * max_radius if score else 0
        radar_x = round(center_x + radius * math.cos(angle))
        radar_y = round(center_y + radius * math.sin(angle))

        patterns.append({
            'name': name,
            'rank_label': rank_label,
            'rank_class': rank_class,
            'xp': xp,
            'xp_pct': xp_pct,
            'trend': trend,
            'radar_x': radar_x,
            'radar_y': radar_y,
        })

    return patterns


def compute_radar_path(patterns):
    """Return SVG polygon points string from pattern radar coords."""
    if not patterns:
        return ''
    points = ' '.join(f"{p['radar_x']},{p['radar_y']}" for p in patterns)
    return points


# ── Asymmetry Detection ──────────────────────────────────────────────────

def compute_asymmetry(profile):
    """Return asymmetry dict or None if no asymmetry detected."""
    if not profile:
        return None

    for pattern, field, left_f, right_f in [
        ('Hinge', 'hinge_asymmetry', 'hinge_left', 'hinge_right'),
        ('Lunge', 'lunge_asymmetry', 'lunge_left', 'lunge_right'),
        ('Carry', 'rotate_asymmetry', 'rotate_left', 'rotate_right'),
    ]:
        asym = getattr(profile, field, 'none')
        if asym and asym != 'none':
            left_val = getattr(profile, left_f, 0)
            right_val = getattr(profile, right_f, 0)
            gap = abs(left_val - right_val)
            weaker = 'Left' if left_val < right_val else 'Right'
            pct = round(gap / max(1, max(left_val, right_val)) * 100)
            return {
                'description': f"{pattern} pattern: {weaker} side {pct}% weaker — adjusted in your program"
            }

    return None


# ── Achievements ─────────────────────────────────────────────────────────

def compute_achievements(patient, total_sessions, streak_days):
    """Return list of achievement dicts for profile page."""
    achievements = [
        {
            'name': 'First Session',
            'icon': 'emoji_events',
            'unlocked': total_sessions >= 1,
            'status': 'Completed' if total_sessions >= 1 else 'Locked',
        },
        {
            'name': '7-Day Streak',
            'icon': 'event_available',
            'unlocked': streak_days >= 7,
            'status': 'Completed' if streak_days >= 7 else 'Locked',
        },
        {
            'name': 'All Patterns Trained',
            'icon': 'lock',
            'unlocked': False,  # TODO: check if all 7 patterns have been exercised
            'status': 'Locked',
        },
        {
            'name': 'Deload Warrior',
            'icon': 'star',
            'unlocked': False,  # TODO: check if completed a full deload week
            'status': 'Locked',
        },
    ]

    # Unlock All Patterns Trained if latest profile has all scores > 0
    profile = StrengthProfile.objects.filter(patient=patient).order_by('-assessed_at').first()
    if profile:
        all_trained = all(
            getattr(profile, f, 0) > 0
            for _, f in PATTERN_FIELDS
        )
        if all_trained:
            achievements[2]['unlocked'] = True
            achievements[2]['status'] = 'Completed'
            achievements[2]['icon'] = 'verified'

    return achievements


# ── Session-complete XP ──────────────────────────────────────────────────

MIN_FORM_SCORE_FOR_XP = 55    # Below this: 0 XP (unsafe form — injury risk)
REDUCED_FORM_THRESHOLD = 70   # Below this: base XP only (no bonus)
MAX_SESSION_XP = 200          # sanity ceiling — no single session exceeds this


def compute_session_xp(exercise_results):
    """Compute XP earned from a single session's exercise results.

    Form gate:
      avg_form < 55  → 0 XP for that exercise (performed unsafely)
      avg_form 55-79 → base XP only (no quality bonus)
      avg_form ≥ 80  → base + quality bonus

    If results exist but NO exercise passed the gate, the session earns
    0 XP — the safety gate must never be floored back up to base XP
    (that would reward unsafe movement, the exact loop the gate exists
    to break). The XP_PER_SESSION fallback applies only to legacy
    sessions with no per-exercise results at all.
    """
    if not exercise_results:
        return XP_PER_SESSION  # legacy fallback: no per-exercise data

    total_xp = 0
    for r in exercise_results:
        form_score = float(r.get('form_score', 0))
        if form_score < MIN_FORM_SCORE_FOR_XP:
            continue  # 0 XP — unsafe form
        ex_base = 10
        if form_score >= 80:
            ex_base += 5  # quality bonus
        total_xp += ex_base

    return min(total_xp, MAX_SESSION_XP)


# ── Phase display helper ─────────────────────────────────────────────────

PHASE_DISPLAY = {
    'anatomical_adaptation_iso': 'Adaptation',
    'anatomical_adaptation_ecc': 'Adaptation',
    'hypertrophy': 'Hypertrophy',
    'hypertrophy_volume': 'Hypertrophy',
    'strength': 'Strength',
    'deload': 'Deload',
}

TOTAL_CYCLE_WEEKS = 9


def compute_phase_context(state):
    """Return phase display context from PeriodisationState."""
    if not state:
        return {
            'current_phase': 'Adaptation',
            'current_week': 1,
            'total_weeks': TOTAL_CYCLE_WEEKS,
            'phase_range': range(1, TOTAL_CYCLE_WEEKS + 1),
        }
    return {
        'current_phase': PHASE_DISPLAY.get(state.current_phase, state.get_current_phase_display()),
        'current_week': state.current_week,
        'total_weeks': TOTAL_CYCLE_WEEKS,
        'phase_range': range(1, TOTAL_CYCLE_WEEKS + 1),
    }
