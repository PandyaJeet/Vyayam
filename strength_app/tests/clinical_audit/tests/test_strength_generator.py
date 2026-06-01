"""
Unit tests for Agent 1: Strength Training Synthetic Patient Generator.

Verifies:
  1. Determinism: same seed produces identical cases (compare case_id lists)
  2. Coverage: generate(10000) hits every stratification cell
  3. Adversarial seeds always present in generated batches
  4. No dataclass validation errors across 10,000 cases

Run via Django test runner:
  python manage.py test strength_app.tests.clinical_audit.tests.test_strength_generator

Or via pytest (if installed):
  python -m pytest strength_app/tests/clinical_audit/tests/test_strength_generator.py -v
"""

import os
import sys
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vyayam_project.settings")

import django
django.setup()

from strength_app.tests.clinical_audit.generators.strength_generator import (
    generate,
    coverage_report,
    adversarial_seeds,
    _TOTAL_CELLS,
    PATTERNS,
    AGE_BANDS,
    SEXES,
    PATTERN_PROFILES,
    ASYMMETRY_LEVELS,
    ACUITIES,
    TRAINING_HISTORIES,
)
from strength_app.tests.clinical_audit.core.patient_case import SyntheticPatientCase


def _generate_list(n: int, seed: int) -> list:
    return list(generate(n, seed))


# ── Test 1: Determinism ────────────────────────────────────────────────────────

class TestDeterminism(unittest.TestCase):

    def test_same_seed_same_case_ids(self):
        """Same seed must produce identical case_id sequences."""
        cases_a = _generate_list(200, seed=42)
        cases_b = _generate_list(200, seed=42)
        ids_a = [c.case_id for c in cases_a]
        ids_b = [c.case_id for c in cases_b]
        self.assertEqual(ids_a, ids_b, "case_id lists differ for the same seed")

    def test_different_seeds_different_cases(self):
        """Different seeds should produce different cases (allow very small collision)."""
        cases_a = _generate_list(100, seed=1)
        cases_b = _generate_list(100, seed=999)
        ids_a = set(c.case_id for c in cases_a)
        ids_b = set(c.case_id for c in cases_b)
        overlap = ids_a & ids_b
        self.assertLess(len(overlap), 10,
            f"Too many collisions between seeds: {len(overlap)}")

    def test_case_count_matches_n(self):
        """generate(n) must yield exactly n cases."""
        for n in [1, 50, 97, 200]:
            cases = _generate_list(n, seed=42)
            self.assertEqual(len(cases), n,
                f"Expected {n} cases, got {len(cases)}")


# ── Test 2: Coverage ───────────────────────────────────────────────────────────

class TestCoverage(unittest.TestCase):

    def test_all_cells_hit_at_10000(self):
        """generate(10000) must hit every (age_band × sex × pattern_profile) cell."""
        cases = _generate_list(10_000, seed=42)
        report = coverage_report(cases)
        self.assertEqual(
            report["total_cells_hit"], report["total_cells_possible"],
            f"Only {report['total_cells_hit']} / {report['total_cells_possible']} cells hit"
        )

    def test_all_age_bands_present(self):
        cases = _generate_list(2000, seed=42)
        report = coverage_report(cases)
        for lo, hi in AGE_BANDS:
            label = f"{lo}-{hi}"
            self.assertGreater(
                report["by_age_band"].get(label, 0), 0,
                f"Age band {label!r} missing"
            )

    def test_both_sexes_present(self):
        cases = _generate_list(200, seed=42)
        report = coverage_report(cases)
        self.assertGreater(report["by_sex"].get("M", 0), 0)
        self.assertGreater(report["by_sex"].get("F", 0), 0)

    def test_all_pattern_profiles_present(self):
        cases = _generate_list(2000, seed=42)
        report = coverage_report(cases)
        for pp in PATTERN_PROFILES:
            self.assertGreater(
                report["by_pattern_profile"].get(pp, 0), 0,
                f"Pattern profile {pp!r} never appeared"
            )

    def test_all_acuities_present(self):
        cases = _generate_list(2000, seed=42)
        report = coverage_report(cases)
        for a in ACUITIES:
            self.assertGreater(
                report["by_acuity"].get(a, 0), 0,
                f"Acuity {a!r} missing"
            )

    def test_all_training_histories_present(self):
        cases = _generate_list(2000, seed=42)
        report = coverage_report(cases)
        # Mapped values used in the field
        for th in ["untrained", "recreational", "club", "academy"]:
            self.assertGreater(
                report["by_training"].get(th, 0), 0,
                f"Training history {th!r} missing"
            )


# ── Test 3: Adversarial seeds ─────────────────────────────────────────────────

class TestAdversarialSeeds(unittest.TestCase):

    def test_adversarial_count(self):
        """Must have at least 20 adversarial seeds."""
        seeds = adversarial_seeds()
        self.assertGreaterEqual(len(seeds), 20,
            f"Only {len(seeds)} adversarial seeds defined")

    def test_adversarial_are_valid_cases(self):
        """All adversarial seeds must be valid SyntheticPatientCase instances."""
        seeds = adversarial_seeds()
        for i, c in enumerate(seeds):
            self.assertIsInstance(c, SyntheticPatientCase,
                f"Seed {i} is not a SyntheticPatientCase")
            self.assertTrue(c.case_id, f"Seed {i} has empty case_id")
            self.assertEqual(c.case_kind, "strength",
                f"Seed {i} has wrong case_kind: {c.case_kind}")
            self.assertFalse(c.coach_linked,
                f"Seed {i} should not be coach-linked")
            self.assertTrue(c.unsupervised_context,
                f"Seed {i} should be unsupervised")

    def test_specific_adversarial_cases_present(self):
        """Spot-check specific adversarial cases exist."""
        seeds = adversarial_seeds()

        # Case 1: 16yo severe asymmetry
        has_teen_asym = any(
            c.age == 16 and c.sex == "M"
            and any(v >= 4 for v in c.asymmetries.values())
            for c in seeds
        )
        self.assertTrue(has_teen_asym, "Missing: teen with severe asymmetry")

        # Case 2: pregnant T3 high scores
        has_preg_t3_high = any(
            c.pregnancy and c.pregnancy_trimester == 3
            and all(v >= 4 for v in c.pattern_scores.values())
            for c in seeds
        )
        self.assertTrue(has_preg_t3_high,
            "Missing: pregnant T3 with high pattern scores")

        # Case 3: post-surgery ACL within 12 weeks
        has_acl_recent = any(
            c.recent_surgery
            and c.surgery_weeks_ago is not None
            and c.surgery_weeks_ago <= 12
            and any(
                dict(inj).get("type") == "ACL_R"
                for inj in c.injury_history
            )
            for c in seeds
        )
        self.assertTrue(has_acl_recent,
            "Missing: post-ACL-R within 3 months case")

        # Case 4: elderly + cardiac + acute
        has_elder_cardiac = any(
            c.age >= 65 and c.cardiac_flag and c.acuity == "acute"
            for c in seeds
        )
        self.assertTrue(has_elder_cardiac,
            "Missing: elderly + cardiac + acute case")

        # Case 5: multi-severe asymmetry + acute + untrained
        has_multisevere = any(
            sum(1 for v in c.asymmetries.values() if v >= 3) >= 3
            and c.acuity == "acute"
            and c.training_history == "untrained"
            for c in seeds
        )
        self.assertTrue(has_multisevere,
            "Missing: multi-severe asymmetry + acute + untrained")


# ── Test 4: No validation errors ──────────────────────────────────────────────

class TestNoValidationErrors(unittest.TestCase):

    def test_no_errors_10000_cases(self):
        """Build 10,000 cases and verify all pass basic field invariants."""
        errors = []
        cases = _generate_list(10_000, seed=42)

        for i, c in enumerate(cases):
            # case_id
            if not c.case_id or len(c.case_id) != 16:
                errors.append(f"[{i}] invalid case_id: {c.case_id!r}")

            # age
            if not (16 <= c.age <= 100):
                errors.append(f"[{i}] age out of range: {c.age}")

            # sex
            if c.sex not in ("M", "F"):
                errors.append(f"[{i}] invalid sex: {c.sex!r}")

            # pattern_scores
            if set(c.pattern_scores.keys()) != set(PATTERNS):
                errors.append(
                    f"[{i}] wrong pattern keys: {set(c.pattern_scores.keys())}")
            for p, v in c.pattern_scores.items():
                if not (1 <= v <= 5):
                    errors.append(f"[{i}] pattern {p} score {v} out of [1,5]")

            # asymmetries
            if set(c.asymmetries.keys()) != set(PATTERNS):
                errors.append(f"[{i}] wrong asymmetry keys")
            for p, v in c.asymmetries.items():
                if v < 0:
                    errors.append(f"[{i}] negative asymmetry {p}={v}")

            # pain_vas
            if c.pain_vas is not None and not (0 <= c.pain_vas <= 10):
                errors.append(f"[{i}] pain_vas out of [0,10]: {c.pain_vas}")

            # pregnancy
            if c.pregnancy and c.pregnancy_trimester not in (1, 2, 3):
                errors.append(
                    f"[{i}] pregnant but trimester={c.pregnancy_trimester!r}")

            # surgery
            if c.recent_surgery and (
                c.surgery_weeks_ago is None or c.surgery_weeks_ago <= 0
            ):
                errors.append(
                    f"[{i}] recent_surgery but surgery_weeks_ago={c.surgery_weeks_ago!r}")

            # height/weight sanity
            if not (140 <= c.height_cm <= 220):
                errors.append(
                    f"[{i}] height_cm={c.height_cm} out of range")
            if not (35 <= c.weight_kg <= 180):
                errors.append(
                    f"[{i}] weight_kg={c.weight_kg} out of range")

            # case_kind
            if c.case_kind != "strength":
                errors.append(
                    f"[{i}] case_kind={c.case_kind!r} (expected 'strength')")

            # unsupervised flags
            if c.coach_linked is not False:
                errors.append(f"[{i}] coach_linked should be False")
            if c.unsupervised_context is not True:
                errors.append(f"[{i}] unsupervised_context should be True")

        if errors:
            summary = (
                f"{len(errors)} validation errors in 10,000 cases:\n"
                + "\n".join(errors[:30])
                + ("\n…(truncated)" if len(errors) > 30 else "")
            )
            self.fail(summary)

    def test_to_dict_round_trip(self):
        """Cases must survive a to_dict / from_dict round trip."""
        cases = _generate_list(50, seed=99)
        for c in cases:
            d = c.to_dict()
            c2 = SyntheticPatientCase.from_dict(d)
            self.assertEqual(c.case_id, c2.case_id,
                "Round-trip case_id mismatch")

    def test_no_football_fields(self):
        """Strength cases must not carry football-specific fields."""
        cases = _generate_list(200, seed=42)
        for c in cases:
            self.assertIsNone(c.football_raw_inputs,
                "football_raw_inputs should be None")
            self.assertIsNone(c.position, "position should be None")
            self.assertIsNone(c.competition_phase,
                "competition_phase should be None")


# ── Test 5: Coverage report structure ─────────────────────────────────────────

class TestCoverageReport(unittest.TestCase):

    def test_report_keys_present(self):
        cases = _generate_list(100, seed=42)
        report = coverage_report(cases)
        required_keys = [
            "total_cases", "total_cells_hit", "total_cells_possible",
            "by_age_band", "by_sex", "by_pattern_profile",
            "by_asymmetry", "by_acuity", "by_training",
            "by_red_flag_subset", "by_special_condition", "cell_counts",
        ]
        for k in required_keys:
            self.assertIn(k, report,
                f"Missing key in coverage_report: {k!r}")

    def test_report_total_matches(self):
        n = 150
        cases = _generate_list(n, seed=42)
        report = coverage_report(cases)
        self.assertEqual(report["total_cases"], n)

    def test_total_cells_possible_is_correct(self):
        cases = _generate_list(50, seed=42)
        report = coverage_report(cases)
        expected = len(AGE_BANDS) * len(SEXES) * len(PATTERN_PROFILES)
        self.assertEqual(report["total_cells_possible"], expected)


if __name__ == "__main__":
    unittest.main()
