from django import template

register = template.Library()


@register.filter(name='friendly_phase')
def friendly_phase(value):
    """Convert internal phase names to user-friendly labels."""
    PHASE_NAMES = {
        'anatomical_adaptation_iso': 'Building Your Foundation',
        'anatomical_adaptation_ecc': 'Building Control',
        'hypertrophy': 'Building Muscle',
        'hypertrophy_plus': 'Building More Muscle',
        'strength': 'Getting Stronger',
        'deload': 'Recovery Week',
        'aa_iso': 'Building Your Foundation',
        'aa_ecc': 'Building Control',
    }
    if isinstance(value, str):
        return PHASE_NAMES.get(value, value.replace('_', ' ').title())
    return value


@register.filter(name='replace_underscores')
def replace_underscores(value):
    """Replace underscores with spaces. Usage: {{ value|replace_underscores }}"""
    if isinstance(value, str):
        return value.replace('_', ' ')
    return value


@register.filter(name='split_comma')
def split_comma(value):
    """Split a comma-separated string. Usage: {% for x in value|split_comma %}"""
    if isinstance(value, str):
        return value.split(',')
    return value


@register.filter(name='get_range')
def get_range(value):
    """{{ 5|get_range }} → range(5). Use: {% for i in exercise.sets|get_range %}"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(3)


@register.simple_tag(name='video_mode_exercises_json')
def video_mode_exercises_json():
    """2026-07 Phase 4: the engine keys that have a filmed reference video,
    as a JSON array for inline use (same '<'-escaping discipline as
    cv_config_json — safe inside a <script> block)."""
    import json
    from django.utils.safestring import mark_safe
    from strength_app.cv_targets import get_video_mode_exercises

    return mark_safe(
        json.dumps(get_video_mode_exercises()).replace('<', '\\u003c'))


@register.simple_tag(name='cv_config_json')
def cv_config_json(exercise_id):
    """R2-W1: emit the generated CV config for this exercise as a JSON
    string for inline use. Unknown IDs get a manual-mode stub — the live
    path never fakes camera tracking for an exercise it can't verify."""
    import json
    from django.utils.safestring import mark_safe
    from strength_app.cv_targets import get_cv_config

    cfg = get_cv_config(exercise_id)
    # json.dumps + escaping '<' keeps this safe inside a <script> block
    return mark_safe(json.dumps(cfg).replace('<', '\\u003c'))
