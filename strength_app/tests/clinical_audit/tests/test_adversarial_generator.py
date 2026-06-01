"""
Unit tests for Agent 3: Adversarial Edge Case Generator.

Coverage:
  1.  Generator handles invalid/zero n without crashing
  2.  All returned cases are valid SyntheticPatientCase objects with case_kind='adversarial'
  3.  Boundary triplets present for all extracted thresholds
  4.  Determinism: same seed → same case_ids
  5.  Extreme cases pass dataclass validation (or explicit documentation of failures)
  6.  Category diversity: at least 5 of 7 categories present in n=100 run
  7.  extract_thresholds_from_source() returns non-empty list
  8.  Each threshold entry has required keys
  9.  Pregnancy + male sex guard
  10. Missing-data cases construct without raising
  11. Gate cases produce orphan states
  12. Time-contradiction cases have surgery flag set
  13. to_dict / from_dict round-trip
  14. All cases JSON-serialisable
"""

from __future__ import annotations

import json
import random
import unittest

from strength_app.tests.clinical_audit.generators.adversarial_generator import (
    generate,
    extract_thresholds_from_source,
    _boundary_triplets,
    _build_extreme_cases,
    _build_missing_data_cases,
    _build_combined_cases,
    _build_time_contradiction_cases,
    _build_gate_cases,
    _build_boundary_cases,
    _build_inconsistency_cases,
    _classify_case,
)
from strength_app.tests.clinical_audit.core.patient_case import SyntheticPatientCase


class TestGeneratorBasics(unittest.TestCase):

    def test_generate_zero_n(self):
        """generate(n=0) must return an empty iterator without raising."""
        cases = list(generate(n=0, seed=42))
        self.assertEqual(cases, [])

    def test_generate_negative_n(self):
        """generate(n=-1) must not raise and must return nothing."""
        cases = list(generate(n=-1, seed=42))
        self.assertEqual(len(cases), 0)

    def test_generate_n_1(self):
        """generate(n=1) must return exactly 1 case."""
        cases = list(generate(n=1, seed=42))
        self.assertEqual(len(cases), 1)

    def test_all_cases_are_synthetic_patient_cases(self):
        cases = list(generate(n=30, seed=99))
        for i, c in enumerate(cases):
            self.assertIsInstance(c, SyntheticPatientCase, f"Case {i} is not SyntheticPatientCase: {type(c)}")

    def test_all_cases_have_adversarial_kind(self):
        cases = list(generate(n=30, seed=7))
        for c in cases:
            self.assertEqual(c.case_kind, "adversarial", f"Expected case_kind='adversarial', got {c.case_kind!r}")

    def test_all_cases_have_non_empty_case_id(self):
        cases = list(generate(n=20, seed=123))
        for c in cases:
            self.assertTrue(c.case_id, "case_id must be non-empty")
            self.assertGreaterEqual(len(c.case_id), 8, "case_id must be at least 8 chars")


class TestBoundaryTriplets(unittest.TestCase):

    def test_boundary_triplets_cover_all_thresholds(self):
        """Every threshold must have exactly 3 triplets (below/at/above)."""
        from collections import defaultdict
        thresholds = extract_thresholds_from_source()
        triplets = _boundary_triplets(thresholds)

        groups: dict = defaultdict(list)
        for t in triplets:
            groups[(t["source"], t["value"])].append(t["boundary_label"])

        for key, labels in groups.items():
            self.assertEqual(
                set(labels), {"below", "at", "above"},
                f"Threshold {key} does not have all 3 boundary labels: {labels}"
            )

    def test_boundary_triplets_epsilon_integer(self):
        """Integer thresholds must use epsilon=1."""
        thresholds = [{"source": "test.py", "line": 1, "kind": "test", "name": "x", "value": 10}]
        triplets = _boundary_triplets(thresholds)
        vals = {t["boundary_label"]: t["boundary_value"] for t in triplets}
        self.assertEqual(vals["below"], 9)
        self.assertEqual(vals["at"], 10)
        self.assertEqual(vals["above"], 11)

    def test_boundary_triplets_epsilon_float(self):
        """Float thresholds must use epsilon=0.1."""
        thresholds = [{"source": "test.py", "line": 1, "kind": "test", "name": "x", "value": 3.5}]
        triplets = _boundary_triplets(thresholds)
        vals = {t["boundary_label"]: t["boundary_value"] for t in triplets}
        self.assertAlmostEqual(vals["below"], 3.4)
        self.assertAlmostEqual(vals["at"], 3.5)
        self.assertAlmostEqual(vals["above"], 3.6)


class TestDeterminism(unittest.TestCase):

    def test_determinism_same_seed(self):
        """Same seed must produce same case_ids in same order."""
        run1 = [c.case_id for c in generate(n=20, seed=42)]
        run2 = [c.case_id for c in generate(n=20, seed=42)]
        self.assertEqual(run1, run2, "Generator is not deterministic with same seed")

    def test_different_seeds_produce_different_cases(self):
        """Different seeds should produce different outputs."""
        run1 = set(c.case_id for c in generate(n=20, seed=1))
        run2 = set(c.case_id for c in generate(n=20, seed=999))
        overlap = run1 & run2
        self.assertLess(len(overlap), len(run1), "Different seeds should produce different cases")


class TestExtremeCases(unittest.TestCase):

    def test_extreme_cases_all_valid_objects(self):
        rng = random.Random(42)
        cases = _build_extreme_cases(rng)
        self.assertGreater(len(cases), 0)
        for c in cases:
            self.assertIsInstance(c, SyntheticPatientCase)
            self.assertEqual(c.case_kind, "adversarial")

    def test_extreme_age_200_is_valid(self):
        case = SyntheticPatientCase.build(
            case_kind="adversarial", age=200, sex="M",
            height_cm=175.0, weight_kg=75.0,
            pattern_scores={"hip_hinge": 3}, asymmetries={"hip_hinge": 0},
        )
        self.assertEqual(case.age, 200)

    def test_extreme_pain_vas_11_is_valid(self):
        case = SyntheticPatientCase.build(
            case_kind="adversarial", age=30, sex="F",
            height_cm=165.0, weight_kg=60.0,
            pattern_scores={"squat": 2}, asymmetries={"squat": 0},
            current_pain=True, pain_vas=11,
        )
        self.assertEqual(case.pain_vas, 11)

    def test_extreme_weight_2kg_is_valid(self):
        case = SyntheticPatientCase.build(
            case_kind="adversarial", age=25, sex="M",
            height_cm=170.0, weight_kg=2.0,
            pattern_scores={"hip_hinge": 1}, asymmetries={"hip_hinge": 0},
        )
        self.assertAlmostEqual(case.weight_kg, 2.0)

    def test_extreme_lsi_boundary(self):
        for lsi in [94.9, 95.0, 95.1]:
            case = SyntheticPatientCase.build(
                case_kind="adversarial", age=22, sex="M",
                height_cm=178.0, weight_kg=78.0,
                pattern_scores={"hip_hinge": 4}, asymmetries={"hip_hinge": 0},
                football_raw_inputs={"lsi_percent": lsi, "hop_test_left": 165},
            )
            self.assertEqual(case.football_raw_inputs["lsi_percent"], lsi)


class TestCategoryDiversity(unittest.TestCase):

    def test_category_diversity_in_n100(self):
        """At least 5 of 7 categories must appear in a n=100 run."""
        cases = list(generate(n=100, seed=42))
        categories = set(_classify_case(c) for c in cases)
        self.assertGreaterEqual(
            len(categories), 5,
            f"Expected >=5 categories in n=100, got {len(categories)}: {categories}"
        )

    def test_each_builder_produces_cases(self):
        rng = random.Random(42)
        thresholds = extract_thresholds_from_source()
        pools = {
            "boundary": _build_boundary_cases(rng, thresholds),
            "combined": _build_combined_cases(rng),
            "inconsistency": _build_inconsistency_cases(rng),
            "missing": _build_missing_data_cases(rng),
            "extreme": _build_extreme_cases(rng),
            "time_contradiction": _build_time_contradiction_cases(rng),
            "gate": _build_gate_cases(rng),
        }
        for name, pool in pools.items():
            self.assertGreater(len(pool), 0, f"Builder '{name}' produced 0 cases")


class TestThresholdExtraction(unittest.TestCase):

    def test_thresholds_non_empty(self):
        thresholds = extract_thresholds_from_source()
        self.assertGreater(len(thresholds), 0)

    def test_thresholds_have_required_keys(self):
        thresholds = extract_thresholds_from_source()
        required = {"source", "line", "kind", "name", "value"}
        for t in thresholds:
            missing = required - set(t.keys())
            self.assertFalse(missing, f"Threshold entry missing keys {missing}: {t}")

    def test_thresholds_values_are_numeric(self):
        thresholds = extract_thresholds_from_source()
        for t in thresholds:
            self.assertIsInstance(t["value"], (int, float), f"Threshold value must be numeric: {t}")

    def test_thresholds_include_known_football_values(self):
        """Spot-check: known thresholds from v1_football_constants.py must appear."""
        thresholds = extract_thresholds_from_source()
        values = {t["value"] for t in thresholds}
        known_expected = {120, 150, 180, 210, 1, 4, 7, 10, 80, 85, 90}
        missing = known_expected - values
        self.assertFalse(missing, f"Expected known threshold values not found: {missing}")

    def test_thresholds_include_age_boundaries(self):
        thresholds = extract_thresholds_from_source()
        values = {t["value"] for t in thresholds}
        age_bounds = {18, 30, 50, 65}
        found = age_bounds & values
        self.assertGreaterEqual(len(found), 2, f"Expected age boundaries; found: {found}")


class TestSpecialCaseGuards(unittest.TestCase):

    def test_combined_cases_pregnancy_only_female(self):
        rng = random.Random(42)
        cases = _build_combined_cases(rng)
        for c in cases:
            if c.pregnancy:
                self.assertEqual(c.sex, "F", f"Pregnancy case must have sex='F', got {c.sex!r}")

    def test_missing_data_cases_valid(self):
        rng = random.Random(42)
        cases = _build_missing_data_cases(rng)
        self.assertGreater(len(cases), 0)
        for c in cases:
            self.assertIsInstance(c, SyntheticPatientCase)
            self.assertEqual(c.case_kind, "adversarial")

    def test_missing_empty_pattern_scores_valid(self):
        case = SyntheticPatientCase.build(
            case_kind="adversarial", age=30, sex="M",
            height_cm=175.0, weight_kg=75.0,
            pattern_scores={}, asymmetries={},
        )
        self.assertEqual(case.pattern_scores, {})

    def test_gate_cases_produce_orphan_states(self):
        rng = random.Random(42)
        cases = _build_gate_cases(rng)
        orphan = [c for c in cases if c.football_raw_inputs and not c.coach_linked]
        self.assertGreaterEqual(len(orphan), 1, "Expected at least one football orphan (no coach)")

    def test_gate_cases_produce_position_without_football(self):
        rng = random.Random(42)
        cases = _build_gate_cases(rng)
        orphan = [c for c in cases if c.position and not c.football_raw_inputs]
        self.assertGreaterEqual(len(orphan), 1, "Expected at least one position-without-football case")

    def test_time_contradiction_cases_have_surgery(self):
        rng = random.Random(42)
        cases = _build_time_contradiction_cases(rng)
        self.assertGreater(len(cases), 0)
        for c in cases:
            self.assertTrue(c.recent_surgery, "Time-contradiction cases should have recent_surgery=True")

    def test_generates_exactly_n_cases(self):
        """generate(n=50) must yield exactly 50 cases even when pools are smaller than n."""
        cases = list(generate(n=50, seed=42))
        self.assertEqual(len(cases), 50, f"Expected 50 cases, got {len(cases)}")


class TestSerialisation(unittest.TestCase):

    def test_to_dict_from_dict_roundtrip(self):
        cases = list(generate(n=5, seed=77))
        for original in cases:
            restored = SyntheticPatientCase.from_dict(original.to_dict())
            self.assertEqual(original.case_id, restored.case_id, "Round-trip failed: case_id mismatch")

    def test_all_cases_json_serialisable(self):
        cases = list(generate(n=30, seed=42))
        for c in cases:
            try:
                json.dumps(c.to_dict())
            except (TypeError, ValueError) as e:
                raise AssertionError(f"Case {c.case_id} is not JSON-serialisable: {e}") from e
