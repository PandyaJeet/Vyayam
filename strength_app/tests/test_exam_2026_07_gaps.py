"""
2026-07 final examination — clinical test-coverage gaps E1-E5
(CODEBASE_HEALTH_2026-07.md). These functions carried patient-safety
behavior with zero assertions; each class below pins the contract.
"""

from django.contrib.auth.hashers import make_password
from django.test import TestCase

from strength_app.models import FootballProfile, PatientProfile, StrengthProfile


def _make_patient(patient_id, phone, **extra):
    return PatientProfile.objects.create(
        patient_id=patient_id,
        name='Gap Fixture',
        phone=phone,
        age=28,
        goals='Strength',
        training_history='intermediate',
        password=make_password('pw12345'),
        **extra,
    )


class TestE2RedFlagWorkingSets(TestCase):
    """E2 (S2): red-flag exercise exclusion for WORKING sets — only the
    warmup path was previously asserted."""

    def test_filter_removes_excluded_exercises(self):
        from strength_app.red_flag_map import get_excluded_exercises
        from strength_app.v1_safety_logic import filter_exercises_for_patient
        patient = _make_patient('E2P1', '9000009901',
                                red_flags_json=['lower_back_disc'])
        excluded = get_excluded_exercises(['lower_back_disc'])
        self.assertTrue(excluded, 'fixture flag excludes nothing — pick another')
        candidates = list(excluded)[:3] + ['full_squats']
        filtered = filter_exercises_for_patient(patient, candidates)
        for ex_id in excluded:
            self.assertNotIn(ex_id, filtered)
        self.assertIn('full_squats', filtered)

    def test_alternative_is_not_itself_excluded(self):
        from strength_app.red_flag_map import (RED_FLAG_EXERCISE_MAP,
                                               get_excluded_exercises)
        from strength_app.v1_safety_logic import get_alternative_for_excluded
        flag = 'lower_back_disc'
        patient = _make_patient('E2P2', '9000009902',
                                red_flags_json=[flag])
        replacements = RED_FLAG_EXERCISE_MAP[flag].get('replace_with', {})
        self.assertTrue(replacements, 'fixture flag has no replacements')
        pattern = next(iter(replacements))
        alt = get_alternative_for_excluded(patient, 'anything', pattern)
        self.assertIsNotNone(alt)
        self.assertNotIn(alt, get_excluded_exercises([flag]),
                         'substitution returned an excluded exercise')

    def test_generated_session_contains_no_excluded_exercise(self):
        from strength_app.red_flag_map import get_excluded_exercises
        from strength_app.v1_prescription_engine import generate_v1_session
        patient = _make_patient('E2P3', '9000009903',
                                red_flags_json=['lower_back_disc',
                                                'knee_pain_patellofemoral'])
        StrengthProfile.objects.create(
            patient=patient, assessment_number=1,
            squat_score=3, hinge_score=3, push_score=3,
            pull_score=3, core_score=3, rotate_score=3, lunge_score=3)
        excluded = get_excluded_exercises(patient.red_flags_json)
        session = generate_v1_session(patient)
        working_ids = [ex['exercise_id']
                       for ex in session.get('working_sets', [])]
        self.assertTrue(working_ids, 'engine produced an empty session')
        hits = [x for x in working_ids if x in excluded]
        self.assertEqual(hits, [],
                         f'red-flagged patient prescribed excluded: {hits}')


class TestE4FemaleAclPrevention(TestCase):
    """E4 (S2): apply_female_acl_prevention — female patients get the ACL
    landing/activation notes; others get none; list is never mutated."""

    def test_female_gets_acl_notes(self):
        from strength_app.v1_safety_logic import apply_female_acl_prevention
        patient = _make_patient('E4P1', '9000009904',
                                biological_sex='female')
        exercises = ['full_squats', 'tuck_jumps']
        out, notes = apply_female_acl_prevention(patient, exercises)
        self.assertEqual(out, exercises)
        self.assertTrue(notes)
        blob = ' '.join(notes).lower()
        self.assertIn('valgus', blob)
        self.assertIn('glute', blob)

    def test_non_female_gets_no_notes(self):
        from strength_app.v1_safety_logic import apply_female_acl_prevention
        for sex, pid, phone in (('male', 'E4P2', '9000009905'),
                                ('not_specified', 'E4P3', '9000009906')):
            patient = _make_patient(pid, phone, biological_sex=sex)
            out, notes = apply_female_acl_prevention(patient, ['full_squats'])
            self.assertEqual(out, ['full_squats'])
            self.assertEqual(notes, [], sex)


class TestE5GateClassification(TestCase):
    """E5 (S2): the 5-gate return-to-sport engine's classify_capability
    boundaries and determine_prescription outputs (backend/ is LIVE via
    strength_app/utils.py)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from strength_app.backend.gate_test_system import GateTestEngine
        from strength_app.backend.database_schema import CapabilityLevel
        cls.engine = GateTestEngine()
        cls.L = CapabilityLevel

    def _squat(self, reps, depth, difficulty, pain):
        return self.engine.classify_capability(
            exercise_type='squat', reps_completed=reps,
            depth_achieved=depth, difficulty_reported=difficulty,
            pain_during=pain)

    def test_cannot_do_boundaries(self):
        self.assertEqual(self._squat(10, 90, 1, 6), self.L.CANNOT_DO,
                         'pain >= 6 must gate out')
        self.assertEqual(self._squat(0, 90, 1, 0), self.L.CANNOT_DO,
                         '< 1 rep must gate out')
        self.assertEqual(self._squat(10, 29, 1, 0), self.L.CANNOT_DO,
                         'squat depth < 30 deg must gate out')

    def test_struggling_boundaries(self):
        self.assertEqual(self._squat(4, 90, 1, 0), self.L.STRUGGLING,
                         'reps below 5')
        self.assertEqual(self._squat(10, 90, 6, 0), self.L.STRUGGLING,
                         'difficulty >= 6')
        self.assertEqual(self._squat(10, 44, 1, 0), self.L.STRUGGLING,
                         'depth below 45 deg')

    def test_manageable_and_easy(self):
        self.assertEqual(self._squat(10, 90, 2, 1), self.L.EASY)
        self.assertEqual(self._squat(10, 90, 3, 0), self.L.MANAGEABLE,
                         'difficulty 3 blocks EASY, not STRUGGLING')
        self.assertEqual(self._squat(9, 90, 1, 0), self.L.MANAGEABLE,
                         '9 reps blocks EASY')
        self.assertEqual(self._squat(10, 89, 1, 0), self.L.MANAGEABLE,
                         'depth 89 blocks EASY (needs >= 90)')
        self.assertEqual(self._squat(10, 90, 1, 2), self.L.MANAGEABLE,
                         'pain 2 blocks EASY (needs <= 1)')

    def test_non_squat_type_ignores_depth(self):
        c = self.engine.classify_capability(
            exercise_type='rowing', reps_completed=10, depth_achieved=0,
            difficulty_reported=1, pain_during=0)
        self.assertEqual(c, self.L.EASY)

    def test_prescriptions(self):
        expect = {
            self.L.CANNOT_DO: (0, 0, 'phase_0'),
            self.L.STRUGGLING: (2, 6, 'phase_1_low'),
            self.L.MANAGEABLE: (3, 10, 'phase_1_standard'),
            self.L.EASY: (3, 15, 'phase_1_high'),
        }
        for level, out in expect.items():
            self.assertEqual(self.engine.determine_prescription(level), out,
                             level)


class TestE3P22PlyoGating(TestCase):
    """E3 partial (S2): P22 — high-load plyometrics are stripped from the
    session while the plyometric gate is not cleared."""

    def _fixture(self, cleared):
        patient = _make_patient(f'E3{cleared[:3].upper()}',
                                '900000990' + ('7' if cleared == 'none' else '8'),
                                athlete_tier_eligible=True,
                                athlete_tier_active=True,
                                athlete_sport='football')
        FootballProfile.objects.create(patient=patient,
                                       plyometric_cleared=cleared)
        return patient

    def _run(self, patient):
        from strength_app.v1_prescription_engine import (
            _apply_football_principles,
        )
        working_sets = [
            {'exercise_id': 'depth_jump_basic', 'exercise_name': 'Depth Jump',
             'movement_pattern': 'plyometric', 'sets': 3, 'reps': 5},
            {'exercise_id': 'full_squats', 'exercise_name': 'Full Squats',
             'movement_pattern': 'squat', 'sets': 3, 'reps': 10},
        ]
        notes = []
        _apply_football_principles(patient, working_sets, {}, notes, 1.0)
        return working_sets, notes

    def test_uncleared_gate_blocks_high_load_plyo(self):
        working_sets, notes = self._run(self._fixture('none'))
        ids = [ex['exercise_id'] for ex in working_sets]
        self.assertNotIn('depth_jump_basic', ids,
                         'P22 gate failed to strip a depth jump')
        self.assertIn('full_squats', ids)
        self.assertTrue(any(n.startswith('P22: Blocked') for n in notes),
                        f'no P22 block note in {notes}')

    def test_cleared_gate_keeps_plyo(self):
        working_sets, _ = self._run(self._fixture('high_load'))
        ids = [ex['exercise_id'] for ex in working_sets]
        self.assertIn('depth_jump_basic', ids)


class TestE1FootballScoreBands(TestCase):
    """E1 partial (S2): _score_from_thresholds band edges, both directions."""

    def test_higher_is_better_bands(self):
        from strength_app.v1_football_views import _score_from_thresholds
        test = {'scoring_thresholds': [120, 150, 180, 210],
                'scoring_thresholds_reverse': False}
        for raw, want in ((119, 1), (120, 2), (149, 2), (150, 3),
                          (209, 4), (210, 5), (400, 5)):
            self.assertEqual(_score_from_thresholds(test, raw), want, raw)

    def test_lower_is_better_bands(self):
        from strength_app.v1_football_views import _score_from_thresholds
        test = {'scoring_thresholds': [4.0, 3.70, 3.40, 3.09],
                'scoring_thresholds_reverse': True}
        for raw, want in ((4.5, 1), (4.0, 2), (3.8, 2), (3.70, 3),
                          (3.10, 4), (3.09, 5), (2.5, 5)):
            self.assertEqual(_score_from_thresholds(test, raw), want, raw)

    def test_junk_input_scores_1(self):
        from strength_app.v1_football_views import _score_from_thresholds
        test = {'scoring_thresholds': [1, 2, 3, 4]}
        self.assertEqual(_score_from_thresholds(test, 'not-a-number'), 1)
        self.assertEqual(_score_from_thresholds(test, None), 1)
