"""Pass Window scenario data loader. Reads the JSON file once.

The 8 scenarios are demo scenarios copied from the G2 spec. Every one is
review == "UNREVIEWED": a coach or physio must check each correct answer
before real use. Do not edit them here.
"""

import json
from functools import lru_cache
from pathlib import Path

from . import config
from . import pass_window as pw

GAME_ID = 'pass_window'
_PATH = Path(__file__).with_name('pass_window_scenarios.json')


@lru_cache(maxsize=1)
def load_scenarios():
    """Return the scenarios as a tuple of dicts (treat as read-only)."""
    return tuple(json.loads(_PATH.read_text(encoding='utf-8')))


def game_config(level, visitor=False):
    """Everything the browser needs. Same shape for athlete and visitor."""
    scenarios = list(load_scenarios())
    n = config.PASS_WINDOW_VISITOR_TRIALS if visitor else config.PASS_WINDOW_TRIALS
    return {
        'game_id': GAME_ID,
        'level': level,
        'scenarios': scenarios,
        'order': pw.trial_order(scenarios, level, n),
        'factors': pw.LEVEL_FACTORS,
        'base_closing_ms': config.PASS_WINDOW_BASE_CLOSING_MS,
        'l5_limit_ms': config.PASS_WINDOW_L5_DECISION_LIMIT_MS,
        'freeze_ms': config.PASS_WINDOW_FREEZE_MS,
        'max_s': config.PASS_WINDOW_SESSION_MAX_S,
    }
