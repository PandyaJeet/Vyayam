"""
Unit tests for Agent 2: Football Synthetic Athlete Generator.

Written using Python's built-in unittest so they run without pytest.

Run via Django test runner:
  python manage.py test strength_app.tests.clinical_audit.tests.test_football_generator --verbosity 2

Or directly:
  python -m unittest strength_app.tests.clinical_audit.tests.test_football_generator -v

When pytest IS available:
  python -m pytest strength_app/tests/clinical_audit/tests/test_football_generator.py -v
"""

from __future__ import annotations

import json
import os
import random
import sys
import unittest
from collections import Counter
from typing import List

# ── Django setup (for SyntheticPatientCase imports) ─────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vyayam_django.settings")

try:
    import django
    django.setup()
except Exception:
    pass  # Already configured in management command / test runner context


from strength_app.tests.clinical_audit.generators.football_generator import (
    _AthleteProfile,
    _build_adversarial_seeds,
    AGE_BANDS,
    COMPETITION_PHASES,
    POSITIONS,
    SEXES,
    TRAINING_HISTORIES,
    generate,
    realistic_test_inputs,
)
from strength_app.tests.clinical_audit.core.patient_case import SyntheticPatientCase


# ── Module-level cached fixtures (computed once per test run) ────────────────

def _get_cases_50() -> List[SyntheticPatientCase]:
    if not hasattr(_get_cases_50, "_cache"):
        _get_cases_50._cache = list(generate(n=50, seed=42))
    return _get_cases_50._cache


def _get_cases_500() -> List[SyntheticPatientCase]:
    if not hasattr(_get_cases_500, "_cache"):
        _get_cases_500._cache = list(generate(n=500, seed=42))
    return _get_cases_500._cache


def _get_adv_seeds() -> List[SyntheticPatientCase]:
    if not hasattr(_get_adv_seeds, "_cache"):
        rng = random.Random(42)
        _get_adv_seeds._cache = _build_adversarial_seeds(rng)
    return _get_adv_seeds._cache


# ============================================================================
# 1. DETERMINISM
# ============================================================================

class TestDeterminism(unittest.TestCase):

    def test_same_seed_same_cases(self):
        """Identical seed → identical case IDs in identical order."""
        batch_a = list(generate(n=30, seed=42))
        batch_b = list(generate(n=30, seed=42))
        self.assertEqual(
            [c.case_id for c in batch_a],
            [c.case_id for c in batch_b],
            "generate() must be deterministic: same seed → same output",
        )

    def test_different_seed_different_cases(self):
        """Different seeds → different case sets (n must exceed adversarial seed count ~30)."""
        ids_a = {c.case_id for c in generate(n=50, seed=1)}
        ids_b = {c.case_id for c in generate(n=50, seed=2)}
        # The first ~30 adversarial seeds are identical; stratified portion must differ
        self.assertNotEqual(ids_a, ids_b, "Different seeds must produce different batches")

    def test_case_id_stable_round_trip(self):
        """case_id survives to_dict()/from_dict() round-trip."""
        for c in _get_cases_50():
            restored = SyntheticPatientCase.from_dict(c.to_dict())
            self.assertEqual(
                restored.case_id, c.case_id,
                f"case_id changed on round-trip for case {c.case_id}",
            )


# ============================================================================
# 2. CASE KIND AND REQUIRED FIELDS
# ============================================================================

class TestCaseKind(unittest.TestCase):

    def test_all_cases_are_football(self):
        for c in _get_cases_50():
            self.assertEqual(c.case_kind, "football",
                             f"case_kind must be 'football', got {c.case_kind}")

    def test_all_cases_have_football_raw_inputs(self):
        for c in _get_cases_50():
            self.assertIsNotNone(c.football_raw_inputs,
                                 f"football_raw_inputs is None for {c.case_id}")
            self.assertIsInstance(c.football_raw_inputs, dict)

    def test_raw_inputs_have_all_six_tests(self):
        required = {"hop_test", "nordic", "sprint", "pogo", "cod", "ybalance"}
        for c in _get_cases_50():
            missing = required - set(c.football_raw_inputs.keys())
            self.assertFalse(missing,
                             f"Case {c.case_id}: missing raw input keys {missing}")

    def test_hop_test_bilateral(self):
        for c in _get_cases_50():
            hop = c.football_raw_inputs.get("hop_test", {})
            self.assertIn("left_cm", hop,
                          f"hop_test missing left_cm (case {c.case_id})")
            self.assertIn("right_cm", hop,
                          f"hop_test missing right_cm (case {c.case_id})")

    def test_cod_bilateral(self):
        for c in _get_cases_50():
            cod = c.football_raw_inputs.get("cod", {})
            self.assertIn("left_505_seconds", cod)
            self.assertIn("right_505_seconds", cod)

    def test_ybalance_bilateral(self):
        for c in _get_cases_50():
            yb = c.football_raw_inputs.get("ybalance", {})
            self.assertIn("left_pct", yb)
            self.assertIn("right_pct", yb)


# ============================================================================
# 3. PHYSIOLOGICAL RANGE VALIDATION
# ============================================================================

class TestPhysiologicalRanges(unittest.TestCase):

    def test_hop_range(self):
        for c in _get_cases_50():
            hop = c.football_raw_inputs.get("hop_test", {})
            for side in ("left_cm", "right_cm"):
                val = hop.get(side)
                if val is not None:
                    self.assertTrue(
                        40 <= val <= 260,
                        f"Hop {side}={val} out of range [40, 260] cm (case {c.case_id})",
                    )

    def test_nordic_range(self):
        for c in _get_cases_50():
            nordic = c.football_raw_inputs.get("nordic", {})
            val = nordic.get("hold_time_seconds")
            if val is not None:
                self.assertTrue(0 <= val <= 30,
                                f"Nordic={val}s out of range [0,30] (case {c.case_id})")

    def test_sprint_range(self):
        for c in _get_cases_50():
            sprint = c.football_raw_inputs.get("sprint", {})
            val = sprint.get("20m_time_seconds")
            if val is not None:
                self.assertTrue(2.5 <= val <= 5.5,
                                f"Sprint={val}s out of range [2.5,5.5] (case {c.case_id})")

    def test_pogo_range(self):
        for c in _get_cases_50():
            pogo = c.football_raw_inputs.get("pogo", {})
            val = pogo.get("clean_reps_10s")
            if val is not None:
                self.assertTrue(0 <= val <= 40,
                                f"Pogo={val} out of range [0,40] (case {c.case_id})")

    def test_cod_range(self):
        for c in _get_cases_50():
            cod = c.football_raw_inputs.get("cod", {})
            for side in ("left_505_seconds", "right_505_seconds"):
                val = cod.get(side)
                if val is not None:
                    self.assertTrue(1.5 <= val <= 4.5,
                                    f"COD {side}={val}s out of range (case {c.case_id})")

    def test_ybalance_range(self):
        for c in _get_cases_50():
            yb = c.football_raw_inputs.get("ybalance", {})
            for side in ("left_pct", "right_pct"):
                val = yb.get(side)
                if val is not None:
                    self.assertTrue(50 <= val <= 125,
                                    f"Y-Balance {side}={val}% out of range (case {c.case_id})")

    def test_lsi_realistic_hop(self):
        """LSI must be ≤100% and ≥30%."""
        for c in _get_cases_500():
            hop = c.football_raw_inputs.get("hop_test", {})
            left = hop.get("left_cm")
            right = hop.get("right_cm")
            if left and right and left > 0 and right > 0:
                lsi = min(left, right) / max(left, right) * 100
                self.assertLessEqual(lsi, 100.0,
                                     f"LSI > 100% for case {c.case_id}")
                self.assertGreaterEqual(lsi, 30.0,
                                        f"LSI < 30% is physiologically impossible (case {c.case_id})")


# ============================================================================
# 4. COVERAGE ACROSS ALL SIX STRATIFICATION DIMENSIONS
# ============================================================================

class TestCoverage(unittest.TestCase):

    def test_all_positions_covered(self):
        seen = {c.position for c in _get_cases_500() if c.position}
        missing = set(POSITIONS) - seen
        self.assertFalse(missing, f"Positions not covered in 500 cases: {missing}")

    def test_all_sexes_covered(self):
        seen = {c.sex for c in _get_cases_500()}
        missing = set(SEXES) - seen
        self.assertFalse(missing, f"Sexes not covered: {missing}")

    def test_all_training_histories_covered(self):
        seen = {c.training_history for c in _get_cases_500()}
        missing = set(TRAINING_HISTORIES) - seen
        self.assertFalse(missing, f"Training histories not covered: {missing}")

    def test_all_competition_phases_covered(self):
        seen = {c.competition_phase for c in _get_cases_500()}
        missing = set(COMPETITION_PHASES) - seen
        self.assertFalse(missing, f"Competition phases not covered: {missing}")

    def test_all_age_bands_covered(self):
        band_labels = {ab[2] for ab in AGE_BANDS}

        def age_to_band(age):
            for lo, hi, label in AGE_BANDS:
                if lo <= age <= hi:
                    return label
            return "unknown"

        covered = {age_to_band(c.age) for c in _get_cases_500()}
        missing = band_labels - covered
        self.assertFalse(missing, f"Age bands not covered: {missing}")

    def test_both_sexes_substantial(self):
        cases = _get_cases_500()
        total = len(cases)
        m_count = sum(1 for c in cases if c.sex == "M")
        f_count = sum(1 for c in cases if c.sex == "F")
        self.assertGreaterEqual(m_count / total, 0.20,
                                f"Too few M cases: {m_count}/{total}")
        self.assertGreaterEqual(f_count / total, 0.20,
                                f"Too few F cases: {f_count}/{total}")

    def test_all_positions_substantial(self):
        cases = _get_cases_500()
        counts = Counter(c.position for c in cases if c.position)
        total = len(cases)
        for pos in POSITIONS:
            frac = counts.get(pos, 0) / total
            self.assertGreaterEqual(frac, 0.03,
                                    f"Position {pos!r} appears in only {100*frac:.1f}%")


# ============================================================================
# 5. ADVERSARIAL SEEDS
# ============================================================================

_EXPECTED_SEED_TAGS = [
    "PHV_ACTIVE_14M_ACADEMY",
    "ACL_R_5MO_15F_RTP_REQUEST",
    "RECURRING_HAMSTRING_3x_19M",
    "PREGNANT_T1_28F_CM",
    "INCONSISTENT_REC_NORDIC_SCORE_36M",
    "POST_CONCUSSION_17M_RTP_WEEK2",
    "PAIN_VAS6_PRO_25M_INSEASON",
    "ORPHAN_NO_COACH_22M",
    "SEVERE_ASYMMETRY_LSI65_14F",
    "POST_ACL_R_10MO_PLYO_REQUEST",
    "CARDIAC_FLAG_40M_REC_HSR_REQUEST",
    "COACH_FLAGGED_INPERSON_ATTEMPTS_REMOTE_16M",
    "GROIN_FAI_32F_GK_PRESEASON",
    "FLOOR_CASE_ALL_TESTS_LEVEL1_18M",
    "CEILING_CASE_ALL_TESTS_LEVEL5_26M",
    "ORPHAN_NO_COACH_29F",
    "MULTIPLE_INJ_ACUTE_21M_CB",
    "ANKLE_SPRAIN_HIST_38M_GK_REC",
    "COMEBACK_27F_POSTSEASON_VAS3",
    "FORCE_DOMINANT_FV_25F_CF",
    "VELOCITY_DOMINANT_FV_23M_WIDE",
    "PHV_ACTIVE_14F_ACADEMY",
    "RETURN_FROM_LAYOFF_31M_CB_10WK",
    "OSGOOD_SCHLATTER_17M_INSEASON",
    "LOW_NORDIC_HAMSTRING_DEFICIT_20F",
    "POST_MENISCUS_SURGERY_6WK_33M_GK",
    "FIRST_ASSESSMENT_16F_NO_HISTORY",
    "MASTERS_LOW_PERF_42M_CF_REC",
    "ACUTELY_INJURED_DURING_ASSESSMENT_19F",
    "ORPHAN_NO_COACH_35M_MASTERS",
]


class TestAdversarialSeeds(unittest.TestCase):

    def test_adversarial_seed_count_at_least_30(self):
        seeds = _get_adv_seeds()
        self.assertGreaterEqual(len(seeds), 30,
                                f"Expected >= 30 adversarial seeds, got {len(seeds)}")

    def test_all_seed_tags_present_in_n50_batch(self):
        cases = _get_cases_50()
        tags = {
            c.football_raw_inputs.get("_seed_tag")
            for c in cases
            if c.football_raw_inputs and c.football_raw_inputs.get("_seed_tag")
        }
        for tag in _EXPECTED_SEED_TAGS:
            self.assertIn(tag, tags,
                          f"Adversarial seed tag {tag!r} not found in n=50 batch")

    def test_phv_seeds_have_phv_flag(self):
        phv_seeds = [
            s for s in _get_adv_seeds()
            if s.football_raw_inputs.get("peak_height_velocity_active") is True
        ]
        self.assertGreaterEqual(len(phv_seeds), 2,
                                "Expected >= 2 PHV-active seeds")

    def test_acl_r_seed_has_asymmetric_hop(self):
        seed = next(
            (s for s in _get_adv_seeds()
             if s.football_raw_inputs.get("_seed_tag") == "ACL_R_5MO_15F_RTP_REQUEST"),
            None,
        )
        self.assertIsNotNone(seed, "ACL_R seed not found")
        hop = seed.football_raw_inputs["hop_test"]
        lsi = min(hop["left_cm"], hop["right_cm"]) / max(hop["left_cm"], hop["right_cm"])
        self.assertLess(lsi, 0.70,
                        f"ACL-R seed should have LSI < 70%, got {lsi:.2f}")

    def test_pregnant_seed(self):
        seed = next(
            (s for s in _get_adv_seeds()
             if s.football_raw_inputs.get("_seed_tag") == "PREGNANT_T1_28F_CM"),
            None,
        )
        self.assertIsNotNone(seed)
        self.assertTrue(seed.pregnancy)
        self.assertEqual(seed.pregnancy_trimester, 1)

    def test_cardiac_seed(self):
        seed = next(
            (s for s in _get_adv_seeds()
             if s.football_raw_inputs.get("_seed_tag") == "CARDIAC_FLAG_40M_REC_HSR_REQUEST"),
            None,
        )
        self.assertIsNotNone(seed)
        self.assertTrue(seed.cardiac_flag)

    def test_pain_vas6_seed(self):
        seed = next(
            (s for s in _get_adv_seeds()
             if s.football_raw_inputs.get("_seed_tag") == "PAIN_VAS6_PRO_25M_INSEASON"),
            None,
        )
        self.assertIsNotNone(seed)
        self.assertTrue(seed.current_pain)
        self.assertEqual(seed.pain_vas, 6)

    def test_orphan_seeds_not_coach_linked(self):
        orphan_tags = {
            "ORPHAN_NO_COACH_22M",
            "ORPHAN_NO_COACH_29F",
            "ORPHAN_NO_COACH_35M_MASTERS",
        }
        orphan_seeds = [
            s for s in _get_adv_seeds()
            if s.football_raw_inputs.get("_seed_tag") in orphan_tags
        ]
        self.assertEqual(len(orphan_seeds), 3,
                         f"Expected 3 orphan seeds, found {len(orphan_seeds)}")
        for s in orphan_seeds:
            self.assertFalse(s.coach_linked,
                             f"Orphan seed {s.football_raw_inputs['_seed_tag']} should have coach_linked=False")

    def test_seeds_are_all_football_kind(self):
        for s in _get_adv_seeds():
            self.assertEqual(s.case_kind, "football")

    def test_seeds_injected_into_n500_batch(self):
        tags = {
            c.football_raw_inputs.get("_seed_tag")
            for c in _get_cases_500()
            if c.football_raw_inputs
        }
        for tag in _EXPECTED_SEED_TAGS:
            self.assertIn(tag, tags,
                          f"Seed tag {tag!r} missing from n=500 batch")


# ============================================================================
# 6. COACH LINKED RATE
# ============================================================================

class TestCoachLinkedRate(unittest.TestCase):

    def test_coach_linked_false_rate_in_500(self):
        """coach_linked=False rate should be ~5% (allow 2-20% band)."""
        cases = _get_cases_500()
        false_count = sum(1 for c in cases if not c.coach_linked)
        rate = false_count / len(cases)
        self.assertGreaterEqual(rate, 0.02,
                                f"coach_linked=False rate={rate:.2%} < 2% minimum")
        self.assertLessEqual(rate, 0.20,
                             f"coach_linked=False rate={rate:.2%} > 20% maximum")

    def test_at_least_one_orphan_in_50(self):
        false_cases = [c for c in _get_cases_50() if not c.coach_linked]
        self.assertGreaterEqual(len(false_cases), 1,
                                "Expected >= 1 coach_linked=False case in n=50 batch")


# ============================================================================
# 7. REALISTIC TEST INPUTS — level consistency
# ============================================================================

class TestRealisticTestInputs(unittest.TestCase):

    @staticmethod
    def _avg_hop_dominant(cases):
        vals = []
        for c in cases:
            hop = c.football_raw_inputs.get("hop_test", {})
            left = hop.get("left_cm", 0)
            right = hop.get("right_cm", 0)
            if left > 0 and right > 0:
                vals.append(max(left, right))
        return sum(vals) / len(vals) if vals else 0.0

    def test_academy_hops_higher_than_recreational(self):
        """Academy M 24-29 average hop > recreational M 24-29 average hop."""
        acad = [
            c for c in generate(n=500, seed=99)
            if c.training_history == "academy_pro"
            and c.sex == "M"
            and 24 <= c.age <= 29
            and not (c.football_raw_inputs or {}).get("_seed_tag")
        ]
        rec = [
            c for c in generate(n=500, seed=99)
            if c.training_history == "recreational"
            and c.sex == "M"
            and 24 <= c.age <= 29
            and not (c.football_raw_inputs or {}).get("_seed_tag")
        ]
        if len(acad) < 3 or len(rec) < 3:
            self.skipTest("Not enough cases for comparison at n=500")
        self.assertGreater(
            self._avg_hop_dominant(acad),
            self._avg_hop_dominant(rec),
            "Academy M 24-29 average hop should exceed recreational",
        )

    def test_sprint_times_have_variance(self):
        cases = list(generate(n=100, seed=42))
        sprint_vals = [
            c.football_raw_inputs["sprint"]["20m_time_seconds"]
            for c in cases
            if not (c.football_raw_inputs or {}).get("_seed_tag")
        ]
        unique_vals = set(sprint_vals)
        self.assertGreater(len(unique_vals), 20,
                           "Sprint times should have at least 20 unique values")

    def test_no_zero_hop_values_outside_adversarial(self):
        for c in generate(n=100, seed=42):
            if (c.football_raw_inputs or {}).get("_seed_tag"):
                continue
            hop = c.football_raw_inputs.get("hop_test", {})
            self.assertGreater(hop.get("left_cm", 1), 0)
            self.assertGreater(hop.get("right_cm", 1), 0)


# ============================================================================
# 8. PROFILE CONSISTENCY
# ============================================================================

class TestProfileConsistency(unittest.TestCase):

    def test_pregnancy_only_for_female(self):
        for c in _get_cases_500():
            if c.pregnancy:
                self.assertEqual(c.sex, "F",
                                 f"Pregnant case must be F, got {c.sex} (case {c.case_id})")

    def test_pain_vas_positive_when_pain_reported(self):
        for c in _get_cases_500():
            if c.current_pain:
                self.assertIsNotNone(c.pain_vas)
                self.assertGreater(c.pain_vas, 0,
                                   f"pain_vas must be > 0 when current_pain=True (case {c.case_id})")

    def test_age_within_defined_bands(self):
        for c in _get_cases_500():
            age = c.age
            in_band = any(lo <= age <= hi for lo, hi, _ in AGE_BANDS)
            self.assertTrue(in_band, f"Age {age} not within any age band (case {c.case_id})")

    def test_position_is_valid(self):
        valid = set(POSITIONS)
        for c in _get_cases_500():
            if c.position is not None:
                self.assertIn(c.position, valid,
                              f"Invalid position {c.position!r} (case {c.case_id})")

    def test_training_history_is_valid(self):
        valid = set(TRAINING_HISTORIES)
        for c in _get_cases_500():
            self.assertIn(c.training_history, valid,
                          f"Invalid training_history {c.training_history!r} (case {c.case_id})")


# ============================================================================
# 9. SERIALISATION ROUND-TRIP
# ============================================================================

class TestSerialisation(unittest.TestCase):

    def test_to_dict_and_back(self):
        for c in _get_cases_50():
            d = c.to_dict()
            restored = SyntheticPatientCase.from_dict(d)
            self.assertEqual(restored.case_id, c.case_id,
                             f"Round-trip case_id mismatch for case {c.case_id}")

    def test_json_serialisable(self):
        for c in _get_cases_50():
            try:
                json.dumps(c.to_dict())
            except (TypeError, ValueError) as e:
                self.fail(f"Case {c.case_id} is not JSON-serialisable: {e}")


# ============================================================================
# 10. BATCH SIZE
# ============================================================================

class TestBatchSize(unittest.TestCase):

    def test_n_50_produces_50_cases(self):
        self.assertEqual(len(_get_cases_50()), 50,
                         f"Expected 50 cases, got {len(_get_cases_50())}")

    def test_n_500_produces_500_cases(self):
        self.assertEqual(len(_get_cases_500()), 500,
                         f"Expected 500 cases, got {len(_get_cases_500())}")

    def test_exactly_30_adversarial_seeds_in_n50_batch(self):
        """Adversarial seeds account for exactly 30 of the first 50 cases."""
        cases = _get_cases_50()
        seed_count = sum(
            1 for c in cases
            if c.football_raw_inputs and c.football_raw_inputs.get("_seed_tag")
        )
        self.assertEqual(seed_count, 30,
                         f"Expected exactly 30 seeded cases in first 50, got {seed_count}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
