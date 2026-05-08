"""Template helpers for therapist console SVG/maths.

Kept on the template side so we don't pre-compute this stuff in views and
inflate the context — each card calls these once at render time.
"""

import math

from django import template

register = template.Library()


@register.filter
def ring_radius(size):
    return float(size) / 2 - 4


@register.filter
def ring_circ(size):
    return round(2 * math.pi * (float(size) / 2 - 4), 2)


@register.filter
def ring_offset(pct, size):
    try:
        pct = float(pct or 0)
        size = float(size)
    except (TypeError, ValueError):
        return 0
    c = 2 * math.pi * (size / 2 - 4)
    return round(c - (pct / 100.0) * c, 2)


@register.filter
def ring_color(pct):
    try:
        pct = float(pct or 0)
    except (TypeError, ValueError):
        pct = 0
    if pct >= 80:
        return "#22c55e"
    if pct >= 60:
        return "#f59e0b"
    return "#ef4444"


@register.filter
def divide(a, b):
    try:
        return float(a) / float(b)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def ring_text_y(size):
    return float(size) / 2 + 4


@register.filter
def ring_font(size):
    if size >= 64:
        return 16
    if size >= 56:
        return 14
    return 12


@register.filter
def pain_polyline(data, width):
    if not data:
        return ""
    width = float(width)
    height = 32.0
    n = len(data)
    if n == 1:
        x = 0
        y = height - (float(data[0]) / 10.0) * height
        return f"{x:.1f},{y:.1f}"
    step = width / (n - 1)
    pts = []
    for i, v in enumerate(data):
        x = i * step
        y = height - (float(v) / 10.0) * height
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


@register.filter
def pain_color(data):
    if not data or len(data) < 2:
        return "#f59e0b"
    trend = float(data[-1]) - float(data[0])
    if trend < 0:
        return "#22c55e"
    if trend > 0:
        return "#ef4444"
    return "#f59e0b"


@register.filter
def pain_trend(data):
    if not data or len(data) < 2:
        return "right"
    trend = float(data[-1]) - float(data[0])
    if trend < 0:
        return "down"
    if trend > 0:
        return "up"
    return "right"


@register.filter
def get_item(d, key):
    try:
        return d[key]
    except (KeyError, IndexError, TypeError):
        return None
