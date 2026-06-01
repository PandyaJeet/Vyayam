"""
Agent 3: Adversarial Edge Case Generator.

Purpose: generate SyntheticPatientCase objects that SPECIFICALLY target engine
cracks — boundary values, combined conditions, inconsistencies, missing data,
extreme values, orphan states, and time-contradiction states.

Public API:
  generate(n, seed) -> Iterator[SyntheticPatientCase]
  extract_thresholds_from_source() -> list[dict]
  audit_run(**kwargs) -> int
"""

from __future__ import annotations

import ast
import itertools
import json
import os
import pathlib
import random
import sys
from typing import Iterator, Optional

# ── Project root on sys.path ─────────────────────────────────────────────────
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from strength_app.tests.clinical_audit.core.patient_case import SyntheticPatientCase

# ── Paths to source files ─────────────────────────────────────────────────────
_CONSTANTS_FILE = _REPO_ROOT / "strength_app" / "v1_football_constants.py"
_ENGINE_FILE = _REPO_ROOT / "strength_app" / "v1_prescription_engine.py"
_SAFETY_FILE = _REPO_ROOT / "strength_app" / "v1_safety_logic.py"
_V1_CONSTANTS_FILE = _REPO_ROOT / "strength_app" / "v1_constants.py"

# ── Reports directory ─────────────────────────────────────────────────────────
_REPORTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "reports"
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Standard 7-pattern keys ───────────────────────────────────────────────────
_PATTERNS = ["hip_hinge", "squat", "lunge", "push", "pull", "carry", "rotation"]


# ===========================================================================
# THRESHOLD EXTRACTION — programmatic, AST-based
# ===========================================================================

class _ThresholdVisitor(ast.NodeVisitor):
    """
    Walk an AST and collect:
      - All list literals assigned to keys named 'scoring_thresholds'
        or variables matching '*_threshold*' or '*_thresholds*'.
      - All numeric Compare nodes (e.g. `age < 18`).
      - All numeric constants in dict literals assigned to
        keys like 'lsi_min_pct', 'pain_nrs_max', 'hop_score_min',
        'min_football_level', etc.
    """

    # Keys in dict literals we want to capture
    _GATE_KEYS = {
        "lsi_min_pct", "pain_nrs_max", "hop_score_min",
        "nordic_score_min", "sprint_score_min", "min_football_level",
        "max_capability", "max_sets", "rest_modifier",
        "volume_modifier", "intensity_modifier",
        "weeks", "sets", "frequency_per_week",
    }

    def __init__(self, source_file: str):
        self.source_file = source_file
        self.thresholds: list[dict] = []
        self._current_assign_name: Optional[str] = None

    # ── Assignment context tracking ──────────────────────────────────────────
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._current_assign_name = target.id
            elif isinstance(target, ast.Attribute):
                self._current_assign_name = target.attr
        self.generic_visit(node)
        self._current_assign_name = None

    # ── List / scoring_thresholds ────────────────────────────────────────────
    def visit_List(self, node):
        # Check if this list is a value under a 'scoring_thresholds' key
        # (handled by visit_Dict) — also handle direct assignment
        name = self._current_assign_name or ""
        if "threshold" in name.lower():
            nums = [
                elt.value for elt in node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, (int, float))
            ]
            if nums:
                for v in nums:
                    self.thresholds.append({
                        "source": self.source_file,
                        "line": node.lineno,
                        "kind": "list_element",
                        "name": name,
                        "value": v,
                    })
        self.generic_visit(node)

    # ── Dict literals — capture gate keys + scoring_thresholds lists ─────────
    def visit_Dict(self, node):
        for key, val in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant):
                continue
            k = key.value
            # scoring_thresholds list
            if k == "scoring_thresholds" and isinstance(val, ast.List):
                nums = [
                    elt.value for elt in val.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, (int, float))
                ]
                for v in nums:
                    self.thresholds.append({
                        "source": self.source_file,
                        "line": val.lineno,
                        "kind": "scoring_threshold",
                        "name": "scoring_thresholds",
                        "value": v,
                    })
            # Named gate constants
            elif k in self._GATE_KEYS and isinstance(val, ast.Constant) and isinstance(val.value, (int, float)):
                self.thresholds.append({
                    "source": self.source_file,
                    "line": val.lineno,
                    "kind": "gate_constant",
                    "name": str(k),
                    "value": val.value,
                })
        self.generic_visit(node)

    # ── Compare nodes: e.g. age < 18, acwr <= 1.3 ───────────────────────────
    def visit_Compare(self, node):
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                # Try to get LHS name
                lhs = ""
                if isinstance(node.left, ast.Name):
                    lhs = node.left.id
                elif isinstance(node.left, ast.Attribute):
                    lhs = node.left.attr
                self.thresholds.append({
                    "source": self.source_file,
                    "line": node.lineno,
                    "kind": "compare",
                    "name": lhs or "<expr>",
                    "value": comparator.value,
                })
        self.generic_visit(node)


def extract_thresholds_from_source() -> list[dict]:
    """
    Walk v1_football_constants.py and v1_prescription_engine.py (+ v1_constants.py)
    using AST analysis and emit a deduplicated boundary seed list.

    Each entry: {source, line, kind, name, value}
    """
    results: list[dict] = []
    for path in [_CONSTANTS_FILE, _ENGINE_FILE, _SAFETY_FILE, _V1_CONSTANTS_FILE]:
        if not path.exists():
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError:
            continue
        visitor = _ThresholdVisitor(str(path.relative_to(_REPO_ROOT)))
        visitor.visit(tree)
        results.extend(visitor.thresholds)

    # Deduplicate on (source, value) — keep first occurrence
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for t in results:
        key = (t["source"], t["value"])
        if key not in seen:
            seen.add(key)
            deduped.append(t)

    return deduped


def _boundary_triplets(thresholds: list[dict]) -> list[dict]:
    """
    For each unique numeric threshold value, emit three dicts:
      (value-epsilon, value, value+epsilon)
    where epsilon=1 for integers, 0.1 for floats.
    """
    triplets: list[dict] = []
    for t in thresholds:
        v = t["value"]
        eps = 1 if isinstance(v, int) else 0.1
        for delta, label in [(-eps, "below"), (0, "at"), (eps, "above")]:
            triplets.append({**t, "boundary_offset": delta, "boundary_label": label, "boundary_value": round(v + delta, 4)})
    return triplets


# ===========================================================================
# CASE CATEGORY BUILDERS
# ===========================================================================

def _all_patterns(score: int) -> dict:
    return {p: score for p in _PATTERNS}


def _all_asymmetries(gap: int) -> dict:
    return {p: gap for p in _PATTERNS}


def _standard_football_inputs(**overrides) -> dict:
    base = {
        "hop_test_left": 150, "hop_test_right": 155,
        "nordic_test": 6,
        "sprint_test": 3.60,
        "pogo_test": 18,
        "cod_test_left": 2.65, "cod_test_right": 2.60,
        "ybalance_test_left": 90, "ybalance_test_right": 92,
        "lsi_percent": 96.8,
    }
    base.update(overrides)
    return base


# ── Category A: Boundary value cases ─────────────────────────────────────────

def _build_boundary_cases(rng: random.Random, thresholds: list[dict]) -> list[SyntheticPatientCase]:
    """One case per boundary triplet entry, targeting the specific threshold."""
    cases: list[SyntheticPatientCase] = []
    triplets = _boundary_triplets(thresholds)
    rng_local = random.Random(rng.randint(0, 2**31))

    for t in triplets:
        bv = t["boundary_value"]
        name = t["name"]
        kind = t["kind"]

        # Choose base age/sex safely
        age = max(15, min(80, rng_local.randint(18, 45)))
        sex = rng_local.choice(["M", "F"])

        # Set defaults
        kwargs: dict = dict(
            case_kind="adversarial",
            age=age,
            sex=sex,
            height_cm=175.0,
            weight_kg=75.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(0),
            training_history="recreational",
        )

        # Inject boundary value into the right field
        if name == "scoring_thresholds" or kind == "scoring_threshold":
            # Map to football inputs
            fball = _standard_football_inputs()
            if bv > 50:  # likely hop cm or ybalance pct
                fball["hop_test_left"] = int(bv)
                fball["hop_test_right"] = int(bv)
            elif bv > 10:  # pogo/ybalance
                fball["pogo_test"] = int(bv)
            else:  # nordic seconds / sprint seconds / cod seconds
                if isinstance(bv, float):
                    fball["sprint_test"] = bv
                else:
                    fball["nordic_test"] = bv
            kwargs["football_raw_inputs"] = fball
            kwargs["position"] = rng_local.choice(["CB", "CM", "W"])

        elif "lsi" in name.lower():
            fball = _standard_football_inputs(lsi_percent=float(bv))
            kwargs["football_raw_inputs"] = fball

        elif "pain" in name.lower():
            vas = max(0, min(10, int(bv)))
            kwargs["current_pain"] = vas > 0
            kwargs["pain_vas"] = vas if vas > 0 else None

        elif "age" == name.lower() or ("age" in name.lower() and "bracket" not in name.lower()):
            kwargs["age"] = max(10, min(120, int(bv)))

        elif "acwr" in name.lower():
            # Embed ACWR hint in football inputs
            fball = _standard_football_inputs()
            fball["_hint_acwr"] = float(bv)
            kwargs["football_raw_inputs"] = fball

        elif "weeks_to_comp" in name.lower() or "weeks" == name.lower():
            surgery_wks = max(1, min(52, int(bv)))
            kwargs["recent_surgery"] = True
            kwargs["surgery_weeks_ago"] = surgery_wks

        elif "level" in name.lower() and bv <= 5:
            # football level boundary
            fball = _standard_football_inputs()
            fball["_hint_football_level"] = int(bv)
            kwargs["football_raw_inputs"] = fball
            kwargs["position"] = "CM"

        elif "sets" in name.lower():
            pass  # no direct field — no-op

        elif "rest" in name.lower():
            pass  # no direct field

        elif "modifier" in name.lower():
            pass  # no direct field

        try:
            case = SyntheticPatientCase.build(**kwargs)
            cases.append(case)
        except Exception:
            pass  # some boundary combos are invalid — skip silently

    return cases


# ── Category B: Combined-condition cases ─────────────────────────────────────

_COMBINED_SPECS = [
    # (label, kwargs_overlay)
    ("pregnancy+surgery+acute_pain+red_flag", dict(
        pregnancy=True, pregnancy_trimester=2,
        recent_surgery=True, surgery_weeks_ago=3,
        acuity="acute", current_pain=True, pain_vas=7,
        red_flags=["knee_pain", "shoulder_instability"],
        cardiac_flag=False,
    )),
    ("cardiac+acute+youth", dict(
        age=16, cardiac_flag=True,
        acuity="acute", current_pain=True, pain_vas=5,
        training_history="untrained",
    )),
    ("pregnancy_T1+high_acuity+elite_training", dict(
        pregnancy=True, pregnancy_trimester=1,
        acuity="acute", training_history="pro",
        red_flags=["high_blood_pressure"],
    )),
    ("surgery_week1+acute+red_flag+football", dict(
        recent_surgery=True, surgery_weeks_ago=1,
        acuity="acute", current_pain=True, pain_vas=8,
        red_flags=["post_op_clearance_required"],
        football_raw_inputs=_standard_football_inputs(),
        position="CB",
    )),
    ("cardiac+pregnancy+red_flag+acute", dict(
        cardiac_flag=True,
        pregnancy=True, pregnancy_trimester=3,
        red_flags=["chest_pain", "shortness_of_breath"],
        acuity="acute",
    )),
    ("surgery_2wks+pregnancy+acute+pain_8", dict(
        recent_surgery=True, surgery_weeks_ago=2,
        pregnancy=True, pregnancy_trimester=2,
        acuity="acute", current_pain=True, pain_vas=8,
    )),
    ("youth_under18+cardiac+elite_sport", dict(
        age=15, cardiac_flag=True,
        training_history="academy",
        football_raw_inputs=_standard_football_inputs(),
        position="W",
    )),
    ("triple_red_flag+acute+surgery", dict(
        red_flags=["acl_grade_3", "meniscal_tear", "bone_stress"],
        acuity="acute", current_pain=True, pain_vas=9,
        recent_surgery=True, surgery_weeks_ago=4,
    )),
]


def _build_combined_cases(rng: random.Random) -> list[SyntheticPatientCase]:
    cases: list[SyntheticPatientCase] = []
    ages = [16, 22, 28, 35, 42, 55, 65, 72]
    sexes = ["M", "F"]
    rng_local = random.Random(rng.randint(0, 2**31))

    for spec_label, overlay in _COMBINED_SPECS:
        for _rep in range(2):
            age = rng_local.choice(ages)
            sex = rng_local.choice(sexes)
            kwargs: dict = dict(
                case_kind="adversarial",
                age=age,
                sex=sex,
                height_cm=float(rng_local.randint(155, 195)),
                weight_kg=float(rng_local.randint(50, 100)),
                pattern_scores=_all_patterns(rng_local.randint(1, 3)),
                asymmetries=_all_asymmetries(rng_local.randint(0, 3)),
                training_history="recreational",
                acuity="none",
                red_flags=[],
                pregnancy=False,
                cardiac_flag=False,
                current_pain=False,
            )
            kwargs.update(overlay)
            # pregnancy is sex-constrained: only F
            if kwargs.get("pregnancy"):
                kwargs["sex"] = "F"
                kwargs["age"] = max(16, min(45, kwargs["age"]))
            try:
                cases.append(SyntheticPatientCase.build(**kwargs))
            except Exception:
                pass
    return cases


# ── Category C: Inconsistency cases ──────────────────────────────────────────

def _build_inconsistency_cases(rng: random.Random) -> list[SyntheticPatientCase]:
    """Elite claimed training history but bodyweight-level pattern scores."""
    cases: list[SyntheticPatientCase] = []
    rng_local = random.Random(rng.randint(0, 2**31))

    specs = [
        # (training_history, pattern_score, acuity, description)
        ("pro", 1, "none", "self_reported_pro_score_1"),
        ("academy", 1, "none", "academy_score_1"),
        ("pro", 2, "none", "pro_score_2_all_patterns"),
        ("club", 1, "acute", "club_acute_score_1"),
        ("recreational", 5, "none", "untrained_background_score_5"),  # reverse inconsistency
        ("untrained", 5, "none", "untrained_score_5"),
        ("pro", 1, "chronic", "pro_chronic_pain_score_1"),
        ("academy", 2, "subacute", "academy_subacute_score_2"),
        # Elite football inputs but weakness scores
        ("pro", 1, "none", "pro_football_score_1_with_football_inputs"),
        ("club", 2, "none", "club_football_with_poor_hop"),
    ]

    for th, score, acuity, _desc in specs:
        for _rep in range(2):
            age = rng_local.randint(18, 40)
            sex = rng_local.choice(["M", "F"])
            fball = None
            pos = None
            if "football" in _desc:
                # Use worst football scores despite "pro" history
                fball = _standard_football_inputs(
                    hop_test_left=80, hop_test_right=85,  # below threshold
                    nordic_test=0,
                    sprint_test=4.5,  # slow
                    lsi_percent=82.0,
                )
                pos = rng_local.choice(["CB", "CM"])
            kwargs: dict = dict(
                case_kind="adversarial",
                age=age,
                sex=sex,
                height_cm=175.0,
                weight_kg=75.0,
                pattern_scores=_all_patterns(score),
                asymmetries=_all_asymmetries(0),
                training_history=th,
                acuity=acuity,
                football_raw_inputs=fball,
                position=pos,
            )
            try:
                cases.append(SyntheticPatientCase.build(**kwargs))
            except Exception:
                pass
    return cases


# ── Category D: Missing data cases ───────────────────────────────────────────

def _build_missing_data_cases(rng: random.Random) -> list[SyntheticPatientCase]:
    """
    Null fields, empty lists where engine expects populated data.
    NOTE: SyntheticPatientCase is typed — we use legal Python values that are
    semantically 'missing' (empty dicts/lists, None where Optional).
    """
    cases: list[SyntheticPatientCase] = []
    rng_local = random.Random(rng.randint(0, 2**31))

    base = dict(
        case_kind="adversarial",
        age=30, sex="M", height_cm=175.0, weight_kg=75.0,
        pattern_scores=_all_patterns(3),
        asymmetries=_all_asymmetries(0),
    )

    missing_specs = [
        # (description, kwargs_override)
        ("empty_pattern_scores", dict(pattern_scores={})),
        ("all_zero_pattern_scores", dict(pattern_scores=_all_patterns(0))),
        ("empty_asymmetries", dict(asymmetries={})),
        ("null_football_raw_inputs", dict(football_raw_inputs=None)),
        ("empty_football_raw_inputs", dict(football_raw_inputs={})),
        ("football_inputs_missing_hop", dict(
            football_raw_inputs={"nordic_test": 5, "sprint_test": 3.5},
        )),
        ("football_inputs_missing_lsi", dict(
            football_raw_inputs={"hop_test_left": 150, "hop_test_right": 155},
        )),
        ("empty_injury_history", dict(injury_history=[])),
        ("empty_red_flags", dict(red_flags=[])),
        ("empty_equipment", dict(equipment=[])),
        ("no_position_football", dict(
            football_raw_inputs=_standard_football_inputs(),
            position=None,
        )),
        ("no_competition_phase", dict(
            football_raw_inputs=_standard_football_inputs(),
            competition_phase=None,
        )),
        ("pregnancy_no_trimester", dict(
            sex="F", pregnancy=True, pregnancy_trimester=None,
        )),
        ("surgery_no_weeks_ago", dict(
            recent_surgery=True, surgery_weeks_ago=None,
        )),
        ("pain_no_vas", dict(
            current_pain=True, pain_vas=None,
        )),
        ("null_injury_type", dict(
            injury_history=[{"type": None, "side": "left", "months_ago": 6}],
        )),
        ("partial_pattern_scores_missing_rotation", dict(
            pattern_scores={p: 3 for p in _PATTERNS if p != "rotation"},
        )),
        ("only_one_pattern_score", dict(
            pattern_scores={"hip_hinge": 2},
        )),
    ]

    for _desc, override in missing_specs:
        kwargs = {**base, **override}
        try:
            cases.append(SyntheticPatientCase.build(**kwargs))
        except Exception:
            pass

    return cases


# ── Category E: Extreme / out-of-range cases ─────────────────────────────────

# Documentation of which extreme values pass vs fail dataclass validation:
#
# PASS (dataclass accepts — no validation beyond types):
#   age=200 — int, passes; clinically absurd
#   age=0   — int, passes; clinically impossible
#   age=-5  — int, passes; clinically impossible
#   weight_kg=2.0 — float, passes; clinically absurd
#   weight_kg=500.0 — float, passes; clinically absurd
#   height_cm=20.0 — float, passes
#   height_cm=300.0 — float, passes
#   pain_vas=11 — int, passes; above VAS scale
#   pain_vas=-1 — int, passes; below VAS scale
#   pattern score 99 — int dict value, passes
#   nordic hold 60s — football_raw_inputs value, passes
#   hop 400cm — football_raw_inputs value, passes
#   nordic hold -5 — float, passes; below zero
#   sprint 0.001s — float, passes; physically impossible
#
# All extreme cases below are VALID SyntheticPatientCase objects.
# They are clinically hostile but structurally sound.

_EXTREME_SPECS = [
    ("age_200_extreme", dict(age=200)),
    ("age_0_impossible", dict(age=0)),
    ("age_negative_5", dict(age=-5)),
    ("weight_2kg_starvation", dict(weight_kg=2.0)),
    ("weight_500kg", dict(weight_kg=500.0)),
    ("height_20cm", dict(height_cm=20.0)),
    ("height_300cm", dict(height_cm=300.0)),
    ("pain_vas_11_above_scale", dict(current_pain=True, pain_vas=11)),
    ("pain_vas_neg1_below_scale", dict(current_pain=True, pain_vas=-1)),
    ("all_pattern_scores_5", dict(pattern_scores=_all_patterns(5))),
    ("all_pattern_scores_0", dict(pattern_scores=_all_patterns(0))),
    ("all_pattern_scores_99", dict(pattern_scores=_all_patterns(99))),
    ("all_asymmetries_5", dict(asymmetries=_all_asymmetries(5))),
    ("nordic_hold_60s", dict(
        football_raw_inputs=_standard_football_inputs(nordic_test=60),
    )),
    ("nordic_hold_neg5", dict(
        football_raw_inputs=_standard_football_inputs(nordic_test=-5),
    )),
    ("hop_400cm", dict(
        football_raw_inputs=_standard_football_inputs(
            hop_test_left=400, hop_test_right=400,
        ),
    )),
    ("hop_0cm", dict(
        football_raw_inputs=_standard_football_inputs(
            hop_test_left=0, hop_test_right=0,
        ),
    )),
    ("sprint_0001s_physically_impossible", dict(
        football_raw_inputs=_standard_football_inputs(sprint_test=0.001),
    )),
    ("sprint_99s_extreme_slow", dict(
        football_raw_inputs=_standard_football_inputs(sprint_test=99.0),
    )),
    ("lsi_200pct_impossible", dict(
        football_raw_inputs=_standard_football_inputs(lsi_percent=200.0),
    )),
    ("lsi_0pct_impossible", dict(
        football_raw_inputs=_standard_football_inputs(lsi_percent=0.0),
    )),
    ("lsi_94_9pct_boundary", dict(
        football_raw_inputs=_standard_football_inputs(lsi_percent=94.9),
    )),
    ("lsi_95_0pct_boundary", dict(
        football_raw_inputs=_standard_football_inputs(lsi_percent=95.0),
    )),
    ("lsi_95_1pct_boundary", dict(
        football_raw_inputs=_standard_football_inputs(lsi_percent=95.1),
    )),
    ("surgery_0_weeks_ago_day_of_op", dict(
        recent_surgery=True, surgery_weeks_ago=0,
    )),
    ("surgery_200_weeks_ago_ancient", dict(
        recent_surgery=True, surgery_weeks_ago=200,
    )),
    ("pregnancy_trimester_0", dict(
        sex="F", pregnancy=True, pregnancy_trimester=0,
    )),
    ("pregnancy_trimester_9", dict(
        sex="F", pregnancy=True, pregnancy_trimester=9,
    )),
    ("pogo_0_clean_reps", dict(
        football_raw_inputs=_standard_football_inputs(pogo_test=0),
    )),
    ("pogo_100_clean_reps", dict(
        football_raw_inputs=_standard_football_inputs(pogo_test=100),
    )),
    ("ybalance_0pct", dict(
        football_raw_inputs=_standard_football_inputs(
            ybalance_test_left=0, ybalance_test_right=0,
        ),
    )),
    ("ybalance_200pct", dict(
        football_raw_inputs=_standard_football_inputs(
            ybalance_test_left=200, ybalance_test_right=200,
        ),
    )),
]


def _build_extreme_cases(rng: random.Random) -> list[SyntheticPatientCase]:
    cases: list[SyntheticPatientCase] = []
    rng_local = random.Random(rng.randint(0, 2**31))

    base = dict(
        case_kind="adversarial",
        age=30, sex="M", height_cm=175.0, weight_kg=75.0,
        pattern_scores=_all_patterns(3),
        asymmetries=_all_asymmetries(0),
        training_history="recreational",
    )

    for _desc, override in _EXTREME_SPECS:
        kwargs = {**base, **override}
        try:
            cases.append(SyntheticPatientCase.build(**kwargs))
        except Exception as e:
            # Document failures (shouldn't happen given the dataclass accepts any int/float)
            pass

    return cases


# ── Category F: Time-contradiction cases ─────────────────────────────────────

def _build_time_contradiction_cases(rng: random.Random) -> list[SyntheticPatientCase]:
    """
    Surgery more recent than linked injury.
    E.g. injury 'months_ago': 1 but surgery_weeks_ago=8 (surgery was ~2 months before injury).
    Also: injury 12 months ago but surgery_weeks_ago=52 (both about a year, plausible but edge).
    """
    cases: list[SyntheticPatientCase] = []
    rng_local = random.Random(rng.randint(0, 2**31))

    specs = [
        # (label, surgery_weeks_ago, injury_months_ago, acuity)
        ("surgery_before_injury_8wk_1mo",  8, 1, "chronic"),   # surgery ~2mo ago, injury 1mo ago
        ("surgery_same_day_injury", 0, 0, "acute"),
        ("surgery_recent_old_injury", 4, 12, "chronic"),        # plausible but edge
        ("surgery_very_recent_injury_1yr", 1, 12, "chronic"),
        ("injury_1day_surgery_200wks_ago", 200, 0, "acute"),    # extreme time gap
        ("surgery_52wks_injury_52mo", 52, 52, "subacute"),
        ("no_injury_listed_but_surgery", 6, None, "subacute"),  # surgery with no injury in list
        ("surgery_in_future_neg_weeks", -4, 6, "chronic"),      # negative weeks
        ("multiple_injuries_mixed_timeline", 12, 6, "subacute"),
        ("injury_0months_surgery_0weeks_both_today", 0, 0, "acute"),
    ]

    for label, surgery_wks, inj_months, acuity in specs:
        for _rep in range(2):
            age = rng_local.randint(18, 55)
            sex = rng_local.choice(["M", "F"])
            inj_list = []
            if inj_months is not None:
                inj_list = [{"type": "ACL_R", "side": "right", "months_ago": inj_months}]
                if label == "multiple_injuries_mixed_timeline":
                    inj_list.append({"type": "hamstring_strain", "side": "left", "months_ago": 1})

            kwargs: dict = dict(
                case_kind="adversarial",
                age=age, sex=sex,
                height_cm=175.0, weight_kg=75.0,
                pattern_scores=_all_patterns(2),
                asymmetries=_all_asymmetries(1),
                training_history="recreational",
                recent_surgery=True,
                surgery_weeks_ago=surgery_wks,
                injury_history=inj_list,
                acuity=acuity,
                current_pain=(acuity == "acute"),
                pain_vas=6 if acuity == "acute" else None,
            )
            try:
                cases.append(SyntheticPatientCase.build(**kwargs))
            except Exception:
                pass
    return cases


# ── Category G: Gate-testing cases ───────────────────────────────────────────

def _build_gate_cases(rng: random.Random) -> list[SyntheticPatientCase]:
    """
    Orphan states:
      - football case without coach_linked (orphan athlete)
      - strength case with coach_linked=True (unusual: strength patient with coach)
      - football inputs + no position
      - strength inputs + football position
      - unsupervised_context=True + football (high-risk unsupervised)
    """
    cases: list[SyntheticPatientCase] = []
    rng_local = random.Random(rng.randint(0, 2**31))

    gate_specs = [
        # (label, kwargs)
        ("football_orphan_no_coach", dict(
            case_kind="adversarial",
            age=24, sex="M", height_cm=178.0, weight_kg=78.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(0),
            training_history="club",
            football_raw_inputs=_standard_football_inputs(),
            position="CM",
            competition_phase="in",
            coach_linked=False,     # ORPHAN: football without coach
            unsupervised_context=True,
        )),
        ("strength_patient_coach_linked", dict(
            case_kind="adversarial",
            age=35, sex="F", height_cm=165.0, weight_kg=65.0,
            pattern_scores=_all_patterns(4),
            asymmetries=_all_asymmetries(0),
            training_history="recreational",
            football_raw_inputs=None,
            position=None,
            coach_linked=True,      # UNUSUAL: strength patient flagged as coach-linked
            unsupervised_context=False,
        )),
        ("football_inputs_no_position", dict(
            case_kind="adversarial",
            age=22, sex="M", height_cm=182.0, weight_kg=80.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(0),
            training_history="academy",
            football_raw_inputs=_standard_football_inputs(),
            position=None,          # MISSING: football inputs but no position
            coach_linked=True,
        )),
        ("strength_case_football_position", dict(
            case_kind="adversarial",
            age=28, sex="M", height_cm=176.0, weight_kg=82.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(0),
            training_history="recreational",
            football_raw_inputs=None,   # No football inputs
            position="GK",              # But has position (orphan state)
            coach_linked=False,
        )),
        ("football_unsupervised_high_injury", dict(
            case_kind="adversarial",
            age=19, sex="M", height_cm=175.0, weight_kg=72.0,
            pattern_scores=_all_patterns(2),
            asymmetries=_all_asymmetries(2),
            training_history="club",
            football_raw_inputs=_standard_football_inputs(lsi_percent=78.0),
            position="CF",
            competition_phase="return",
            coach_linked=False,
            unsupervised_context=True,  # High-risk: unsupervised + return-to-sport
            injury_history=[{"type": "ACL_L", "side": "left", "months_ago": 9}],
            acuity="subacute",
        )),
        ("both_flags_true_coach_and_unsupervised", dict(
            case_kind="adversarial",
            age=26, sex="F", height_cm=168.0, weight_kg=62.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(0),
            training_history="recreational",
            coach_linked=True,
            unsupervised_context=True,  # CONTRADICTION: both True
        )),
        ("football_inputs_strength_case_kind", dict(
            case_kind="adversarial",
            age=25, sex="M", height_cm=180.0, weight_kg=80.0,
            pattern_scores=_all_patterns(4),
            asymmetries=_all_asymmetries(0),
            training_history="club",
            football_raw_inputs=_standard_football_inputs(),  # Football inputs on strength case
            position=None,
            coach_linked=False,
        )),
        ("missing_both_position_and_competition_phase", dict(
            case_kind="adversarial",
            age=23, sex="M", height_cm=177.0, weight_kg=77.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(1),
            training_history="club",
            football_raw_inputs=_standard_football_inputs(),
            position=None,
            competition_phase=None,
            coach_linked=True,
        )),
    ]

    for _label, kwargs in gate_specs:
        try:
            cases.append(SyntheticPatientCase.build(**kwargs))
        except Exception:
            pass

    # Additional: randomised gate permutations
    for _ in range(20):
        coach = rng_local.choice([True, False])
        unspvsd = rng_local.choice([True, False])
        has_football = rng_local.choice([True, False])
        pos = rng_local.choice(["GK", "CB", "FB", "CM", "W", "CF", None])
        phase = rng_local.choice(["pre", "in", "post", "return", None])

        kwargs = dict(
            case_kind="adversarial",
            age=rng_local.randint(16, 40),
            sex=rng_local.choice(["M", "F"]),
            height_cm=175.0, weight_kg=75.0,
            pattern_scores=_all_patterns(3),
            asymmetries=_all_asymmetries(0),
            training_history="recreational",
            football_raw_inputs=_standard_football_inputs() if has_football else None,
            position=pos,
            competition_phase=phase,
            coach_linked=coach,
            unsupervised_context=unspvsd,
        )
        try:
            cases.append(SyntheticPatientCase.build(**kwargs))
        except Exception:
            pass

    return cases


# ===========================================================================
# MAIN GENERATOR
# ===========================================================================

def generate(n: int, seed: int) -> Iterator[SyntheticPatientCase]:
    """
    Generate up to n adversarial SyntheticPatientCase objects.

    Category distribution (approximate):
      A: Boundary value cases           ~15% (driven by threshold count)
      B: Combined-condition cases       ~15%
      C: Inconsistency cases            ~15%
      D: Missing data cases             ~15%
      E: Extreme / out-of-range cases   ~15%
      F: Time-contradiction cases       ~15%
      G: Gate-testing cases             ~10%
    """
    rng = random.Random(seed)

    thresholds = extract_thresholds_from_source()

    # Build category pools
    cat_a = _build_boundary_cases(rng, thresholds)
    cat_b = _build_combined_cases(rng)
    cat_c = _build_inconsistency_cases(rng)
    cat_d = _build_missing_data_cases(rng)
    cat_e = _build_extreme_cases(rng)
    cat_f = _build_time_contradiction_cases(rng)
    cat_g = _build_gate_cases(rng)

    all_pools = [cat_a, cat_b, cat_c, cat_d, cat_e, cat_f, cat_g]

    # Weighted interleaving: A/B/C/D/E/F each get weight 2, G gets weight 1
    # Build a flat interleaved list by round-robin with weights, then cycle
    weights = [2, 2, 2, 2, 2, 2, 1]  # per-category slot multipliers
    # Build cycled iterators per category
    iters = [itertools.cycle(pool) if pool else itertools.cycle([None]) for pool in all_pools]

    # Build a sequence of (iterator, category_index) slots proportional to weights
    slots = []
    for idx, (pool_iter, w) in enumerate(zip(iters, weights)):
        for _ in range(w):
            slots.append((pool_iter, idx))

    # Shuffle slots deterministically, then cycle
    rng_local = random.Random(seed + 1)
    rng_local.shuffle(slots)
    slot_cycle = itertools.cycle(slots)

    emitted = 0

    # Adversarial pools are finite hand-crafted sets; cycling repeats is intentional —
    # the same boundary condition hitting the engine from different call sites is valid test coverage.
    while emitted < n:
        pool_iter, _cat_idx = next(slot_cycle)
        case = next(pool_iter)
        if case is None:
            continue
        yield case
        emitted += 1


# ===========================================================================
# CATEGORY DISTRIBUTION COUNTER (for reporting)
# ===========================================================================

def _classify_case(case: SyntheticPatientCase) -> str:
    """Heuristically classify an adversarial case into its category."""
    fi = case.football_raw_inputs or {}

    # Category E: extreme numeric values
    if (case.age <= 0 or case.age >= 100
            or case.weight_kg <= 5 or case.weight_kg >= 300
            or case.height_cm <= 50 or case.height_cm >= 280
            or (case.pain_vas is not None and (case.pain_vas > 10 or case.pain_vas < 0))
            or fi.get("nordic_test", 5) < 0 or fi.get("nordic_test", 5) > 30
            or fi.get("hop_test_left", 150) > 300 or fi.get("hop_test_left", 150) < 5
            or fi.get("sprint_test", 3.5) < 0.1
            or fi.get("lsi_percent", 95) > 150 or fi.get("lsi_percent", 95) < 10):
        return "E_extreme"

    # Category F: time contradictions
    if case.recent_surgery and case.injury_history:
        inj = dict(case.injury_history[0]) if case.injury_history else {}
        months = inj.get("months_ago", 99)
        weeks = case.surgery_weeks_ago or 0
        surgery_months = weeks / 4.0
        if isinstance(months, (int, float)) and surgery_months > months + 0.5:
            return "F_time_contradiction"
    if case.surgery_weeks_ago is not None and case.surgery_weeks_ago <= 0:
        return "F_time_contradiction"

    # Category B: combined conditions (3+ special flags)
    flags = sum([
        bool(case.pregnancy),
        bool(case.recent_surgery),
        bool(case.cardiac_flag),
        bool(case.current_pain and case.pain_vas and case.pain_vas >= 6),
        bool(len(case.red_flags) >= 2),
        bool(case.acuity in ("acute", "subacute")),
    ])
    if flags >= 3:
        return "B_combined"

    # Category G: gate mismatches
    if case.football_raw_inputs and not case.coach_linked and case.unsupervised_context:
        return "G_gate"
    if case.coach_linked and case.unsupervised_context:
        return "G_gate"
    if case.football_raw_inputs and case.position is None:
        return "G_gate"
    if case.position and not case.football_raw_inputs:
        return "G_gate"

    # Category C: inconsistency
    avg_score = sum(case.pattern_scores.values()) / max(len(case.pattern_scores), 1) if case.pattern_scores else 3
    if case.training_history in ("pro", "academy") and avg_score <= 2:
        return "C_inconsistency"
    if case.training_history in ("untrained", "recreational") and avg_score >= 5:
        return "C_inconsistency"

    # Category D: missing data
    if (not case.pattern_scores or not case.asymmetries
            or (case.pregnancy and case.pregnancy_trimester is None)
            or (case.recent_surgery and case.surgery_weeks_ago is None)
            or (case.current_pain and case.pain_vas is None)):
        return "D_missing"
    if case.football_raw_inputs == {}:
        return "D_missing"

    # Default: boundary value (A)
    return "A_boundary"


# ===========================================================================
# AUDIT_RUN ENTRY POINT
# ===========================================================================

def audit_run(n: int, seed: int, against_cases: str, read: str, **kwargs) -> int:
    """
    Generate n adversarial cases and write to reports/agent3_cases.jsonl.
    Prints a category distribution summary.
    """
    out_path = _REPORTS_DIR / "agent3_cases.jsonl"

    category_counts: dict[str, int] = {}
    total_written = 0

    with out_path.open("w", encoding="utf-8") as fh:
        for case in generate(n=n, seed=seed):
            cat = _classify_case(case)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            fh.write(json.dumps(case.to_dict()) + "\n")
            total_written += 1

    print(f"\nAgent 3 — Adversarial Generator")
    print(f"  Wrote {total_written} cases → {out_path}")
    print(f"\n  Category distribution:")
    for cat, count in sorted(category_counts.items()):
        pct = 100 * count / max(total_written, 1)
        print(f"    {cat:<25} {count:>5}  ({pct:.1f}%)")

    thresholds = extract_thresholds_from_source()
    print(f"\n  Thresholds extracted: {len(thresholds)} unique (value, source) pairs")
    print(f"  Boundary triplets generated: {len(_boundary_triplets(thresholds))}")

    return 0
