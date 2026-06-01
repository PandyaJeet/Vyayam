"""
Agent 1: Strength Training Synthetic Patient Generator.

Produces adversarial SyntheticPatientCase objects for the strength training
(public, unsupervised) pathway — NOT football.

Coverage target: every meaningful combination of
  (age_band × sex × pattern_profile × asymmetry × acuity × training_history
   × red_flag × special_condition)
is represented at least ceil(n / total_cells) times.
"""

from __future__ import annotations

import json
import math
import os
import random
from collections.abc import Iterator
from typing import Optional

from strength_app.tests.clinical_audit.core.patient_case import SyntheticPatientCase


# ── Vocabulary constants ───────────────────────────────────────────────────────

PATTERNS = ["hip_hinge", "squat", "lunge", "push", "pull", "carry", "rotation"]

AGE_BANDS = [
    (16, 17),
    (18, 29),
    (30, 44),
    (45, 59),
    (60, 74),
    (75, 85),
]

SEXES = ["M", "F"]

PATTERN_PROFILES = [
    "balanced_low",
    "balanced_mid",
    "balanced_high",
    "one_weak",
    "two_weak",
    "upper_dominant",
    "lower_dominant",
    "random_mixed",
]

ASYMMETRY_LEVELS = ["none", "mild", "moderate", "severe", "multi_severe"]

ACUITIES = ["none", "chronic", "subacute", "acute"]

TRAINING_HISTORIES = ["untrained", "recreational", "trained", "highly_trained"]

RED_FLAG_VOCAB = [
    "acl_grade_1_2",
    "knee_pain_patellofemoral",
    "hernia",
    "lower_back_disc",
    "shoulder_impingement",
    "rotator_cuff_partial",
    "osteoporosis",
    "hypertension",
    "ankle_sprain_acute",
    "wrist_pain",
    "elbow_tendinopathy",
]

SPECIAL_CONDITIONS = [
    "none",
    "pregnant_T1",
    "pregnant_T2",
    "pregnant_T3",
    "post_surgery_lt4w",
    "post_surgery_4_12w",
    "cardiac",
    "current_pain_vas_gte7",
    "combined",
]

INJURY_VOCAB = [
    ("ACL_R", ["left", "right"]),
    ("hamstring_strain_I", ["left", "right"]),
    ("hamstring_strain_II", ["left", "right"]),
    ("hamstring_strain_III", ["left", "right"]),
    ("ankle_sprain", ["left", "right"]),
    ("groin_strain", ["left", "right"]),
    ("FAI", ["left", "right", "bilateral"]),
    ("concussion", ["central"]),
    ("lumbar_disc", ["central"]),
    ("chronic_tendinopathy_achilles", ["left", "right"]),
    ("chronic_tendinopathy_patellar", ["left", "right"]),
    ("shoulder_labrum", ["left", "right"]),
    ("meniscus_medial", ["left", "right"]),
    ("hip_flexor_strain", ["left", "right"]),
]

EQUIPMENT_VOCAB = [
    "dumbbells",
    "barbell",
    "resistance_bands",
    "pull_up_bar",
    "kettlebell",
    "bench",
    "cable_machine",
    "foam_roller",
    "gymnastics_rings",
    "dip_bars",
    "ab_wheel",
    "medicine_ball",
    "trx",
    "jump_rope",
    "yoga_mat",
]

# Height/weight distributions: (mean_height, std_height, mean_weight, std_weight)
# keyed by (age_band_index, sex)
_ANTHRO_PARAMS = {
    # (band_idx, sex): (h_mean, h_std, w_mean, w_std)
    (0, "M"): (170.0, 5.0, 62.0, 8.0),
    (0, "F"): (160.0, 5.0, 54.0, 7.0),
    (1, "M"): (177.0, 6.0, 78.0, 12.0),
    (1, "F"): (164.0, 5.5, 63.0, 10.0),
    (2, "M"): (176.0, 6.0, 82.0, 13.0),
    (2, "F"): (163.0, 5.5, 67.0, 11.0),
    (3, "M"): (175.0, 6.0, 84.0, 13.0),
    (3, "F"): (162.0, 5.5, 70.0, 12.0),
    (4, "M"): (173.0, 6.0, 81.0, 13.0),
    (4, "F"): (160.0, 5.5, 68.0, 11.0),
    (5, "M"): (170.0, 6.0, 76.0, 12.0),
    (5, "F"): (158.0, 5.5, 64.0, 10.0),
}


# ── Pattern score builders ─────────────────────────────────────────────────────

def _scores_balanced_low(rng: random.Random) -> dict:
    return {p: rng.randint(1, 2) for p in PATTERNS}


def _scores_balanced_mid(rng: random.Random) -> dict:
    return {p: rng.randint(2, 3) for p in PATTERNS}


def _scores_balanced_high(rng: random.Random) -> dict:
    return {p: rng.randint(4, 5) for p in PATTERNS}


def _scores_one_weak(rng: random.Random) -> dict:
    scores = {p: rng.randint(3, 4) for p in PATTERNS}
    weak_pattern = rng.choice(PATTERNS)
    scores[weak_pattern] = 1
    return scores


def _scores_two_weak(rng: random.Random) -> dict:
    scores = {p: rng.randint(3, 4) for p in PATTERNS}
    weak_patterns = rng.sample(PATTERNS, 2)
    for p in weak_patterns:
        scores[p] = 1
    return scores


# Upper patterns: push, pull; Lower patterns: hip_hinge, squat, lunge, carry
_UPPER = ["push", "pull"]
_LOWER = ["hip_hinge", "squat", "lunge", "carry"]
_MIDDLE = ["rotation"]


def _scores_upper_dominant(rng: random.Random) -> dict:
    scores = {}
    for p in _UPPER:
        scores[p] = rng.randint(4, 5)
    for p in _LOWER:
        scores[p] = rng.randint(1, 2)
    for p in _MIDDLE:
        scores[p] = rng.randint(2, 4)
    return scores


def _scores_lower_dominant(rng: random.Random) -> dict:
    scores = {}
    for p in _LOWER:
        scores[p] = rng.randint(4, 5)
    for p in _UPPER:
        scores[p] = rng.randint(1, 2)
    for p in _MIDDLE:
        scores[p] = rng.randint(2, 4)
    return scores


def _scores_random_mixed(rng: random.Random) -> dict:
    return {p: rng.randint(1, 5) for p in PATTERNS}


_SCORE_BUILDERS = {
    "balanced_low": _scores_balanced_low,
    "balanced_mid": _scores_balanced_mid,
    "balanced_high": _scores_balanced_high,
    "one_weak": _scores_one_weak,
    "two_weak": _scores_two_weak,
    "upper_dominant": _scores_upper_dominant,
    "lower_dominant": _scores_lower_dominant,
    "random_mixed": _scores_random_mixed,
}


# ── Asymmetry builders ─────────────────────────────────────────────────────────

def _asymmetries_for_level(rng: random.Random, level: str) -> dict:
    base = {p: 0 for p in PATTERNS}
    if level == "none":
        return base
    if level == "mild":
        p = rng.choice(PATTERNS)
        base[p] = 1
    elif level == "moderate":
        p = rng.choice(PATTERNS)
        base[p] = 2
    elif level == "severe":
        p = rng.choice(PATTERNS)
        base[p] = rng.randint(3, 5)
    elif level == "multi_severe":
        chosen = rng.sample(PATTERNS, rng.randint(2, 4))
        for p in chosen:
            base[p] = rng.randint(3, 5)
    return base


# ── Injury history ─────────────────────────────────────────────────────────────

def _build_injury_history(rng: random.Random, n_injuries: int) -> list:
    if n_injuries == 0:
        return []
    injuries = []
    for _ in range(n_injuries):
        inj_type, sides = rng.choice(INJURY_VOCAB)
        side = rng.choice(sides)
        months_ago = rng.randint(1, 60)
        injuries.append({"type": inj_type, "side": side, "months_ago": months_ago})
    return injuries


# ── Special condition encoder ─────────────────────────────────────────────────

def _encode_special_condition(
    rng: random.Random,
    condition: str,
    sex: str,
    age: int,
) -> dict:
    """Return keyword args to override on the case builder."""
    kwargs = {}

    if condition == "none":
        pass

    elif condition == "pregnant_T1":
        kwargs["pregnancy"] = True
        kwargs["pregnancy_trimester"] = 1

    elif condition == "pregnant_T2":
        kwargs["pregnancy"] = True
        kwargs["pregnancy_trimester"] = 2

    elif condition == "pregnant_T3":
        kwargs["pregnancy"] = True
        kwargs["pregnancy_trimester"] = 3

    elif condition == "post_surgery_lt4w":
        kwargs["recent_surgery"] = True
        kwargs["surgery_weeks_ago"] = rng.randint(1, 3)

    elif condition == "post_surgery_4_12w":
        kwargs["recent_surgery"] = True
        kwargs["surgery_weeks_ago"] = rng.randint(4, 12)

    elif condition == "cardiac":
        kwargs["cardiac_flag"] = True

    elif condition == "current_pain_vas_gte7":
        kwargs["current_pain"] = True
        kwargs["pain_vas"] = rng.randint(7, 10)

    elif condition == "combined":
        # Two simultaneous special conditions — chosen for clinical realism
        pairs = [
            ("cardiac", "current_pain_vas_gte7"),
            ("post_surgery_lt4w", "current_pain_vas_gte7"),
            ("pregnant_T3", "current_pain_vas_gte7"),
            ("post_surgery_4_12w", "cardiac"),
        ]
        c1, c2 = rng.choice(pairs)
        kwargs.update(_encode_special_condition(rng, c1, sex, age))
        kwargs.update(_encode_special_condition(rng, c2, sex, age))

    return kwargs


def _is_valid_pregnancy(sex: str, age: int) -> bool:
    return sex == "F" and 16 <= age <= 50


def _sanitize_condition(condition: str, sex: str, age: int, rng: random.Random) -> str:
    """Replace pregnancy conditions with a safe alternative if demographics forbid it."""
    if condition.startswith("pregnant") and not _is_valid_pregnancy(sex, age):
        return rng.choice(["post_surgery_4_12w", "cardiac", "current_pain_vas_gte7", "none"])
    if condition == "combined":
        # Combined may pull pregnant — we'll handle in _encode_special_condition itself
        # by drawing from non-pregnancy pairs if female check fails
        return condition
    return condition


# ── Height/weight sampler ─────────────────────────────────────────────────────

def _sample_anthro(rng: random.Random, band_idx: int, sex: str) -> tuple:
    h_mean, h_std, w_mean, w_std = _ANTHRO_PARAMS[(band_idx, sex)]
    height = round(max(140.0, min(220.0, rng.gauss(h_mean, h_std))), 1)
    weight = round(max(35.0, min(180.0, rng.gauss(w_mean, w_std))), 1)
    return height, weight


# ── Core case builder ─────────────────────────────────────────────────────────

def _build_one_case(
    rng: random.Random,
    age_band: tuple,
    sex: str,
    pattern_profile: str,
    asymmetry_level: str,
    acuity: str,
    training_history: str,
    red_flag_subset: str,   # "none" | "single" | "multiple"
    special_condition: str,
    band_idx: int,
) -> SyntheticPatientCase:
    age = rng.randint(age_band[0], age_band[1])
    height, weight = _sample_anthro(rng, band_idx, sex)

    scores = _SCORE_BUILDERS[pattern_profile](rng)
    asymmetries = _asymmetries_for_level(rng, asymmetry_level)

    # Red flags
    if red_flag_subset == "none":
        red_flags = []
    elif red_flag_subset == "single":
        red_flags = [rng.choice(RED_FLAG_VOCAB)]
    else:  # multiple
        count = rng.randint(2, 4)
        red_flags = rng.sample(RED_FLAG_VOCAB, min(count, len(RED_FLAG_VOCAB)))

    # Injury history
    n_injuries = rng.choices([0, 1, 2, 3], weights=[40, 35, 18, 7])[0]
    injury_history = _build_injury_history(rng, n_injuries)

    # Special condition
    sanitized = _sanitize_condition(special_condition, sex, age, rng)
    sc_kwargs = _encode_special_condition(rng, sanitized, sex, age)

    # Acuity → pain linkage
    pain_kwargs = {}
    if acuity == "acute" and "current_pain" not in sc_kwargs:
        pain_kwargs["current_pain"] = True
        pain_kwargs["pain_vas"] = rng.randint(5, 9)
    elif acuity in ("subacute", "chronic") and "current_pain" not in sc_kwargs:
        if rng.random() < 0.5:
            pain_kwargs["current_pain"] = True
            pain_kwargs["pain_vas"] = rng.randint(1, 5)

    # Equipment
    if rng.random() < 0.2:
        equipment = []  # bodyweight only
    else:
        n_eq = rng.randint(2, 5)
        equipment = rng.sample(EQUIPMENT_VOCAB, min(n_eq, len(EQUIPMENT_VOCAB)))

    # Map training_history to the fields accepted by SyntheticPatientCase
    # SyntheticPatientCase.training_history accepts 'untrained'|'recreational'|'club'|'academy'|'pro'
    # We map our labels:
    TH_MAP = {
        "untrained": "untrained",
        "recreational": "recreational",
        "trained": "club",
        "highly_trained": "academy",
    }
    th_field = TH_MAP[training_history]

    merged = {**sc_kwargs, **pain_kwargs}

    return SyntheticPatientCase.build(
        case_kind="strength",
        age=age,
        sex=sex,
        height_cm=height,
        weight_kg=weight,
        pattern_scores=scores,
        asymmetries=asymmetries,
        football_raw_inputs=None,
        injury_history=injury_history,
        acuity=acuity,
        red_flags=red_flags,
        pregnancy=merged.get("pregnancy", False),
        pregnancy_trimester=merged.get("pregnancy_trimester", None),
        recent_surgery=merged.get("recent_surgery", False),
        surgery_weeks_ago=merged.get("surgery_weeks_ago", None),
        cardiac_flag=merged.get("cardiac_flag", False),
        current_pain=merged.get("current_pain", False),
        pain_vas=merged.get("pain_vas", None),
        training_history=th_field,
        position=None,
        competition_phase=None,
        equipment=equipment,
        coach_linked=False,
        unsupervised_context=True,
    )


# ── Stratified cell definitions ───────────────────────────────────────────────

def _all_cells():
    """Generator of (band_idx, age_band, sex, pattern_profile) cells."""
    for band_idx, age_band in enumerate(AGE_BANDS):
        for sex in SEXES:
            for pp in PATTERN_PROFILES:
                yield (band_idx, age_band, sex, pp)


_TOTAL_CELLS = len(AGE_BANDS) * len(SEXES) * len(PATTERN_PROFILES)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate(n: int, seed: int) -> Iterator[SyntheticPatientCase]:
    """
    Deterministic stratified generator.

    Guarantees every (age_band × sex × pattern_profile) cell appears at least
    ceil(n / _TOTAL_CELLS) times. Additional samples fill remaining quota
    randomly.
    """
    rng = random.Random(seed)

    cells = list(_all_cells())
    min_per_cell = math.ceil(n / _TOTAL_CELLS)

    # Build base assignment: min_per_cell copies of each cell
    assignments = []
    for cell in cells:
        assignments.extend([cell] * min_per_cell)

    # Trim or extend to exactly n
    if len(assignments) > n:
        # Deterministically shuffle then trim
        rng.shuffle(assignments)
        assignments = assignments[:n]
    else:
        while len(assignments) < n:
            assignments.append(rng.choice(cells))

    # Shuffle for output order variety
    rng.shuffle(assignments)

    # Secondary dimension sampling helpers
    asymmetry_weights = [25, 30, 25, 15, 5]   # none, mild, moderate, severe, multi_severe
    acuity_weights = [40, 25, 20, 15]
    training_weights = [20, 35, 30, 15]
    red_flag_weights = [45, 35, 20]           # none, single, multiple
    special_weights = [45, 5, 5, 5, 8, 8, 8, 8, 8]  # see SPECIAL_CONDITIONS order

    for band_idx, age_band, sex, pattern_profile in assignments:
        asymmetry_level = rng.choices(ASYMMETRY_LEVELS, weights=asymmetry_weights)[0]
        acuity = rng.choices(ACUITIES, weights=acuity_weights)[0]
        training_history = rng.choices(TRAINING_HISTORIES, weights=training_weights)[0]
        red_flag_subset = rng.choices(["none", "single", "multiple"], weights=red_flag_weights)[0]
        special_condition = rng.choices(SPECIAL_CONDITIONS, weights=special_weights)[0]

        yield _build_one_case(
            rng=rng,
            age_band=age_band,
            sex=sex,
            pattern_profile=pattern_profile,
            asymmetry_level=asymmetry_level,
            acuity=acuity,
            training_history=training_history,
            red_flag_subset=red_flag_subset,
            special_condition=special_condition,
            band_idx=band_idx,
        )


def coverage_report(cases: list) -> dict:
    """
    Returns a dict with counts per stratification cell.

    Keys:
      "by_age_band"        : {band_label: count}
      "by_sex"             : {"M": n, "F": n}
      "by_pattern_profile" : {profile: count}   — inferred from scores
      "by_asymmetry"       : {level: count}
      "by_acuity"          : {acuity: count}
      "by_training"        : {training_history: count}
      "by_red_flag_subset" : {"none": n, "single": n, "multiple": n}
      "by_special"         : {condition_label: count}
      "cell_counts"        : {(age_band_label, sex, pattern_profile): count}
      "total_cases"        : int
      "total_cells_hit"    : int
      "total_cells_possible": int
    """
    from collections import defaultdict

    by_age = defaultdict(int)
    by_sex = defaultdict(int)
    by_pp = defaultdict(int)
    by_asym = defaultdict(int)
    by_acuity = defaultdict(int)
    by_training = defaultdict(int)
    by_rf = defaultdict(int)
    by_special = defaultdict(int)
    cell_counts = defaultdict(int)

    for c in cases:
        # Age band
        band_label = _age_band_label(c.age)
        by_age[band_label] += 1

        # Sex
        by_sex[c.sex] += 1

        # Pattern profile (inferred)
        pp = _infer_pattern_profile(c.pattern_scores)
        by_pp[pp] += 1

        # Asymmetry
        asym = _infer_asymmetry_level(c.asymmetries)
        by_asym[asym] += 1

        # Acuity
        by_acuity[c.acuity] += 1

        # Training
        by_training[c.training_history] += 1

        # Red flag subset
        nf = len(c.red_flags)
        if nf == 0:
            by_rf["none"] += 1
        elif nf == 1:
            by_rf["single"] += 1
        else:
            by_rf["multiple"] += 1

        # Special condition
        sc = _infer_special_condition(c)
        by_special[sc] += 1

        # Cell key
        cell_counts[(band_label, c.sex, pp)] += 1

    total_cells_possible = _TOTAL_CELLS
    total_cells_hit = sum(1 for v in cell_counts.values() if v > 0)

    return {
        "total_cases": len(cases),
        "total_cells_hit": total_cells_hit,
        "total_cells_possible": total_cells_possible,
        "by_age_band": dict(by_age),
        "by_sex": dict(by_sex),
        "by_pattern_profile": dict(by_pp),
        "by_asymmetry": dict(by_asym),
        "by_acuity": dict(by_acuity),
        "by_training": dict(by_training),
        "by_red_flag_subset": dict(by_rf),
        "by_special_condition": dict(by_special),
        "cell_counts": {str(k): v for k, v in cell_counts.items()},
    }


def _age_band_label(age: int) -> str:
    for lo, hi in AGE_BANDS:
        if lo <= age <= hi:
            return f"{lo}-{hi}"
    return "76+"


def _infer_pattern_profile(scores: dict) -> str:
    vals = list(scores.values())
    mn, mx = min(vals), max(vals)
    avg = sum(vals) / len(vals)

    upper_avg = sum(scores.get(p, 3) for p in _UPPER) / len(_UPPER)
    lower_avg = sum(scores.get(p, 3) for p in _LOWER) / len(_LOWER)

    ones = sum(1 for v in vals if v == 1)

    if mn >= 4:
        return "balanced_high"
    if mx <= 2:
        return "balanced_low"
    if 2 <= mn and mx <= 3:
        return "balanced_mid"
    if ones == 1:
        return "one_weak"
    if ones == 2:
        return "two_weak"
    if upper_avg >= 4 and lower_avg <= 2:
        return "upper_dominant"
    if lower_avg >= 4 and upper_avg <= 2:
        return "lower_dominant"
    return "random_mixed"


def _infer_asymmetry_level(asymmetries: dict) -> str:
    vals = list(asymmetries.values())
    max_gap = max(vals) if vals else 0
    severe_count = sum(1 for v in vals if v >= 3)

    if max_gap == 0:
        return "none"
    if max_gap == 1:
        return "mild"
    if max_gap == 2:
        return "moderate"
    if max_gap >= 3 and severe_count == 1:
        return "severe"
    return "multi_severe"


def _infer_special_condition(c: "SyntheticPatientCase") -> str:
    if c.pregnancy:
        t = c.pregnancy_trimester
        return f"pregnant_T{t}" if t else "pregnant_T1"
    if c.recent_surgery:
        w = c.surgery_weeks_ago or 0
        return "post_surgery_lt4w" if w < 4 else "post_surgery_4_12w"
    if c.cardiac_flag:
        return "cardiac"
    if c.current_pain and c.pain_vas is not None and c.pain_vas >= 7:
        return "current_pain_vas_gte7"
    return "none"


# ── Adversarial seeds ─────────────────────────────────────────────────────────

def adversarial_seeds() -> list[SyntheticPatientCase]:
    """
    Hand-curated list of ~20 known-dangerous cases that MUST appear in every
    generated batch regardless of sampling. Each targets a specific clinical gate.
    """
    cases = []

    # 1. 14-year-old (just inside min age) with severe asymmetry claiming
    #    highly_trained history — tests age gate + asymmetry + history
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=16, sex="M",
        height_cm=165.0, weight_kg=58.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 4, "push": 4, "pull": 4, "carry": 4, "rotation": 4},
        asymmetries={"hip_hinge": 4, "squat": 4, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="none", training_history="academy",
        coach_linked=False, unsupervised_context=True,
    ))

    # 2. Pregnant 3rd trimester with high pattern scores — prescription filter
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=28, sex="F",
        height_cm=163.0, weight_kg=72.0,
        pattern_scores={"hip_hinge": 5, "squat": 5, "lunge": 4, "push": 5, "pull": 5, "carry": 5, "rotation": 4},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="none", pregnancy=True, pregnancy_trimester=3,
        training_history="recreational",
        coach_linked=False, unsupervised_context=True,
    ))

    # 3. Post-ACL-R < 3 months wanting to train full programme — surgery gate
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=24, sex="M",
        height_cm=180.0, weight_kg=82.0,
        pattern_scores={"hip_hinge": 3, "squat": 2, "lunge": 2, "push": 4, "pull": 4, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 3, "lunge": 3, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        injury_history=[{"type": "ACL_R", "side": "left", "months_ago": 2}],
        acuity="subacute", red_flags=["acl_grade_1_2"],
        recent_surgery=True, surgery_weeks_ago=8,
        training_history="club",
        coach_linked=False, unsupervised_context=True,
    ))

    # 4. 70-year-old with acute low back pain and cardiac flag — dual safety gate
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=70, sex="M",
        height_cm=172.0, weight_kg=78.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 1, "push": 2, "pull": 2, "carry": 1, "rotation": 1},
        asymmetries={"hip_hinge": 1, "squat": 1, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="acute", red_flags=["lower_back_disc"],
        cardiac_flag=True, current_pain=True, pain_vas=8,
        training_history="untrained",
        coach_linked=False, unsupervised_context=True,
    ))

    # 5. Multi-severe asymmetry + acute pain + untrained — asymmetry gate + pain
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=35, sex="F",
        height_cm=162.0, weight_kg=68.0,
        pattern_scores={"hip_hinge": 2, "squat": 1, "lunge": 2, "push": 3, "pull": 3, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 4, "squat": 3, "lunge": 3, "push": 0, "pull": 0, "carry": 3, "rotation": 0},
        acuity="acute", current_pain=True, pain_vas=9,
        training_history="untrained",
        coach_linked=False, unsupervised_context=True,
    ))

    # 6. 75+ year old, osteoporosis flag, balanced_low scores — frail elder
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=78, sex="F",
        height_cm=156.0, weight_kg=58.0,
        pattern_scores={"hip_hinge": 1, "squat": 1, "lunge": 1, "push": 1, "pull": 1, "carry": 1, "rotation": 1},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="chronic", red_flags=["osteoporosis"],
        training_history="untrained",
        coach_linked=False, unsupervised_context=True,
    ))

    # 7. Teen (17) with herniated disc + high training history — contradiction
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=17, sex="M",
        height_cm=174.0, weight_kg=68.0,
        pattern_scores={"hip_hinge": 1, "squat": 2, "lunge": 2, "push": 3, "pull": 3, "carry": 2, "rotation": 1},
        asymmetries={"hip_hinge": 2, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 2},
        acuity="subacute", red_flags=["lower_back_disc"],
        injury_history=[{"type": "lumbar_disc", "side": "central", "months_ago": 3}],
        training_history="academy",
        coach_linked=False, unsupervised_context=True,
    ))

    # 8. Shoulder impingement + wrist pain + requested upper-dominant programme
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=32, sex="M",
        height_cm=178.0, weight_kg=81.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 5, "pull": 5, "carry": 4, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 2, "pull": 1, "carry": 0, "rotation": 0},
        acuity="chronic",
        red_flags=["shoulder_impingement", "wrist_pain", "rotator_cuff_partial"],
        training_history="club",
        coach_linked=False, unsupervised_context=True,
    ))

    # 9. Post-surgery <4 weeks + cardiac + pain VAS 8 — triple safety
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=55, sex="M",
        height_cm=175.0, weight_kg=88.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 1, "push": 2, "pull": 2, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="acute", cardiac_flag=True,
        recent_surgery=True, surgery_weeks_ago=2,
        current_pain=True, pain_vas=8,
        training_history="recreational",
        coach_linked=False, unsupervised_context=True,
    ))

    # 10. Hypertension + high training load + requesting academy-level programme
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=48, sex="M",
        height_cm=176.0, weight_kg=92.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 4, "push": 4, "pull": 4, "carry": 4, "rotation": 4},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="none", red_flags=["hypertension"],
        training_history="academy",
        coach_linked=False, unsupervised_context=True,
    ))

    # 11. Pregnant T1 claiming untrained, all pattern scores 1 — min viable case
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=22, sex="F",
        height_cm=160.0, weight_kg=58.0,
        pattern_scores={"hip_hinge": 1, "squat": 1, "lunge": 1, "push": 1, "pull": 1, "carry": 1, "rotation": 1},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="none", pregnancy=True, pregnancy_trimester=1,
        training_history="untrained",
        coach_linked=False, unsupervised_context=True,
    ))

    # 12. Knee patellofemoral + hernia + lower dominant — multiple exclusions
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=42, sex="F",
        height_cm=164.0, weight_kg=71.0,
        pattern_scores={"hip_hinge": 5, "squat": 5, "lunge": 5, "push": 2, "pull": 2, "carry": 4, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 1, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="chronic",
        red_flags=["knee_pain_patellofemoral", "hernia"],
        training_history="recreational",
        coach_linked=False, unsupervised_context=True,
    ))

    # 13. 16-year-old female, all 5s, no asymmetry, no flags — max score young
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=16, sex="F",
        height_cm=163.0, weight_kg=56.0,
        pattern_scores={"hip_hinge": 5, "squat": 5, "lunge": 5, "push": 5, "pull": 5, "carry": 5, "rotation": 5},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="none", training_history="academy",
        coach_linked=False, unsupervised_context=True,
    ))

    # 14. 80+ elder, balanced_low, chronic multi-condition — max age edge
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=83, sex="M",
        height_cm=168.0, weight_kg=72.0,
        pattern_scores={"hip_hinge": 1, "squat": 1, "lunge": 1, "push": 2, "pull": 1, "carry": 1, "rotation": 1},
        asymmetries={"hip_hinge": 1, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="chronic", red_flags=["osteoporosis", "hypertension"],
        cardiac_flag=True,
        training_history="untrained",
        coach_linked=False, unsupervised_context=True,
    ))

    # 15. Concussion + acute acuity + any training history — head injury gate
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=19, sex="M",
        height_cm=179.0, weight_kg=77.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        injury_history=[{"type": "concussion", "side": "central", "months_ago": 1}],
        acuity="acute", current_pain=True, pain_vas=6,
        training_history="recreational",
        coach_linked=False, unsupervised_context=True,
    ))

    # 16. Post-ACL-R 10 weeks (within 4-12w window) wanting to return to sport
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=26, sex="F",
        height_cm=165.0, weight_kg=62.0,
        pattern_scores={"hip_hinge": 3, "squat": 2, "lunge": 2, "push": 3, "pull": 3, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 2, "lunge": 2, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        injury_history=[{"type": "ACL_R", "side": "right", "months_ago": 3}],
        acuity="subacute", red_flags=["acl_grade_1_2"],
        recent_surgery=True, surgery_weeks_ago=10,
        training_history="club",
        coach_linked=False, unsupervised_context=True,
    ))

    # 17. Elbow tendinopathy + wrist pain + no upper programme — compound exclusion
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=38, sex="M",
        height_cm=177.0, weight_kg=84.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 3, "push": 1, "pull": 1, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 3, "pull": 3, "carry": 0, "rotation": 0},
        acuity="chronic",
        red_flags=["elbow_tendinopathy", "wrist_pain"],
        injury_history=[
            {"type": "chronic_tendinopathy_achilles", "side": "right", "months_ago": 12},
        ],
        training_history="recreational",
        coach_linked=False, unsupervised_context=True,
    ))

    # 18. Highly trained athlete seeking all patterns 5, zero flags — best case
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=27, sex="M",
        height_cm=183.0, weight_kg=88.0,
        pattern_scores={"hip_hinge": 5, "squat": 5, "lunge": 5, "push": 5, "pull": 5, "carry": 5, "rotation": 5},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="none", training_history="academy",
        equipment=["barbell", "dumbbells", "pull_up_bar", "cable_machine", "gymnastics_rings"],
        coach_linked=False, unsupervised_context=True,
    ))

    # 19. Ankle sprain acute + wanting lower-dominant programme — acute lower gate
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=21, sex="F",
        height_cm=162.0, weight_kg=59.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 4, "push": 2, "pull": 2, "carry": 4, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 3, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="acute",
        red_flags=["ankle_sprain_acute"],
        injury_history=[{"type": "ankle_sprain", "side": "left", "months_ago": 0}],
        current_pain=True, pain_vas=7,
        training_history="recreational",
        coach_linked=False, unsupervised_context=True,
    ))

    # 20. 60-year-old female, post-surgery 3 weeks, balanced_mid, bodyweight only
    cases.append(SyntheticPatientCase.build(
        case_kind="strength", age=62, sex="F",
        height_cm=159.0, weight_kg=65.0,
        pattern_scores={"hip_hinge": 2, "squat": 3, "lunge": 2, "push": 3, "pull": 2, "carry": 3, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        acuity="subacute",
        recent_surgery=True, surgery_weeks_ago=3,
        current_pain=True, pain_vas=5,
        training_history="untrained",
        equipment=[],
        coach_linked=False, unsupervised_context=True,
    ))

    return cases


# ── audit_run entrypoint ──────────────────────────────────────────────────────

def audit_run(n: int, seed: int, against_cases: str, read: str, **kwargs) -> int:
    """
    Main entrypoint called by runner.py.

    Generates n cases, prepends adversarial seeds, writes to
    strength_app/tests/clinical_audit/reports/agent1_cases.jsonl.
    """
    import pathlib

    print(f"[Agent 1] Generating {n} cases with seed={seed} …")

    # Adversarial seeds always included
    adv = adversarial_seeds()
    print(f"[Agent 1] {len(adv)} adversarial seeds prepended")

    cases = list(adv) + list(generate(n, seed))

    # Coverage report
    report = coverage_report(cases)
    print(f"[Agent 1] Total cases: {report['total_cases']}")
    print(f"[Agent 1] Stratification cells hit: {report['total_cells_hit']} / {report['total_cells_possible']}")
    print(f"[Agent 1] by_age_band: {report['by_age_band']}")
    print(f"[Agent 1] by_sex: {report['by_sex']}")
    print(f"[Agent 1] by_pattern_profile: {report['by_pattern_profile']}")
    print(f"[Agent 1] by_acuity: {report['by_acuity']}")
    print(f"[Agent 1] by_training: {report['by_training']}")

    # Write JSONL
    reports_dir = pathlib.Path(__file__).resolve().parents[1] / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "agent1_cases.jsonl"

    with open(out_path, "w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")

    print(f"[Agent 1] Written {len(cases)} cases to {out_path}")
    return 0
