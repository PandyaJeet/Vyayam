"""
2026-07 dark camera coaches — per-exercise integrity suite.

Every dark coach must satisfy ALL of (manifest-driven; one row per
exercise, appended as each coach lands):
  registry entry · exercise_targets camera entry with phases · catalog
  v2_exercise_key wired but v2_ghost_supported STILL False (the dark
  invariant) · content entry · new cue ids synced between coach_dark.js,
  coach_core.js CUES and report_builder.py CUE_TEXT (forever-rule).
"""

import json
import re
from pathlib import Path

from django.test import TestCase

import strength_app

JS_DIR = Path(strength_app.__file__).parent / 'static' / 'strength_app' / 'js'

# key → (catalog exercise_id, js_type, is_hold, new cue ids)
DARK_COACHES = {
    'wall_sit_rx': ('ex_wall_sit', 'WALL_SIT_RX', True,
                    ['wall_sit_slide_down', 'wall_sit_heels']),
}

# Cue ids the dark coaches reuse from the existing registry.
REUSED_CUE_IDS = {'hips_level', 'hips_stacked'}


def _targets():
    return json.loads((JS_DIR / 'exercise_targets.json').read_text())


def _coach_core_cue_ids():
    text = (JS_DIR / 'coach_core.js').read_text()
    block = text.split('var CUES = {')[1].split('};')[0]
    return set(re.findall(r'^\s{4}(\w+):', block, re.M))


def _report_cue_ids():
    text = (Path(strength_app.__file__).parent / 'report_builder.py').read_text()
    block = text.split('CUE_TEXT = {')[1].split('}')[0]
    return set(re.findall(r"'(\w+)':", block))


class TestDarkCoachIntegrity(TestCase):
    def test_manifest_rows(self):
        if not DARK_COACHES:
            self.skipTest('no dark coaches landed yet')
        from therapist_app.exercise_catalog import EXERCISES_BY_ID
        from strength_app.cv_targets import get_cv_config
        try:
            from strength_app.exercise_system.exercise_registry_v2 import (
                EXERCISE_METADATA,
            )
        except Exception:
            EXERCISE_METADATA = None
        from strength_app.exercise_content_gap_fill import (
            EXERCISE_CONTENT_GAP_FILL,
        )

        dark_js = (JS_DIR / 'coach_dark.js').read_text()
        core_ids = _coach_core_cue_ids()
        report_ids = _report_cue_ids()

        for key, (ex_id, js_type, is_hold, cue_ids) in DARK_COACHES.items():
            # 1. registry
            if EXERCISE_METADATA is not None:
                self.assertIn(key, EXERCISE_METADATA, key)
            # 2. targets artifact: camera + phases + hold semantics
            cfg = get_cv_config(key)
            self.assertEqual(cfg.get('tracking'), 'camera', key)
            self.assertEqual(cfg.get('js_type'), js_type, key)
            self.assertTrue(cfg.get('phases'), f'{key}: no phase targets')
            self.assertEqual(bool(cfg.get('is_hold')), is_hold, key)
            # 3. DARK invariant: key wired, flag STILL False
            entry = EXERCISES_BY_ID[ex_id]
            self.assertEqual(entry['v2_exercise_key'], key, ex_id)
            self.assertFalse(
                entry['v2_ghost_supported'],
                f'{ex_id}: DARK FLAG FLIPPED — not allowed this cycle')
            # 4. content
            self.assertIn(key, EXERCISE_CONTENT_GAP_FILL, key)
            content = EXERCISE_CONTENT_GAP_FILL[key]
            self.assertTrue(content.get('form_cues'), key)
            self.assertTrue(content.get('instructions'), key)
            # 5. js def + cue sync (forever-rule)
            self.assertIn(f'PHASES.{js_type} = {{', dark_js,
                          f'{js_type} def missing in coach_dark.js')
            self.assertIn(f'FAULTS.{js_type}', dark_js,
                          f'{js_type} fault observer missing')
            for cue_id in cue_ids:
                self.assertIn(cue_id, core_ids,
                              f'{cue_id}: missing from coach_core CUES')
                self.assertIn(cue_id, report_ids,
                              f'{cue_id}: missing from report CUE_TEXT')

    def test_no_patient_route_reaches_dark_keys(self):
        """The dark invariant's other half: no progression chain or warmup
        list references any *_rx key."""
        if not DARK_COACHES:
            self.skipTest('no dark coaches landed yet')
        import strength_app.v1_progression_chains as chains_mod
        chains_src = Path(chains_mod.__file__).read_text()
        import strength_app.v1_session_views as sess_mod
        sess_src = Path(sess_mod.__file__).read_text()
        for key in DARK_COACHES:
            self.assertNotIn(f"'{key}'", chains_src,
                             f'{key} leaked into progression chains')
            self.assertNotIn(f"'{key}'", sess_src,
                             f'{key} leaked into session views')
