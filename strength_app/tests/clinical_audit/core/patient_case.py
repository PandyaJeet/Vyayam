"""
Shared dataclass for synthetic patient cases used across all audit agents.
"""

from __future__ import annotations

import hashlib
import json
import functools
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class SyntheticPatientCase:
    case_id: str
    case_kind: str          # 'strength' | 'football' | 'adversarial'

    # Demographics
    age: int
    sex: str                # 'M' | 'F'
    height_cm: float
    weight_kg: float

    # Strength screening (7-pattern scores 0-5)
    pattern_scores: dict    # {"hip_hinge": 3, "squat": 2, ...}
    asymmetries: dict       # {"hip_hinge": 0, "squat": 2, ...} — per-pattern L/R gap

    # Football assessment raw inputs (optional)
    football_raw_inputs: Optional[dict]

    # Injury history: [{"type": "ACL_R", "side": "left", "months_ago": 8}, ...]
    injury_history: tuple   # immutable list of dicts

    # Clinical state
    acuity: str             # 'none' | 'chronic' | 'subacute' | 'acute'
    red_flags: tuple        # immutable list of str

    pregnancy: bool
    pregnancy_trimester: Optional[int]

    recent_surgery: bool
    surgery_weeks_ago: Optional[int]

    cardiac_flag: bool

    current_pain: bool
    pain_vas: Optional[int]

    # Training context
    training_history: str   # 'untrained' | 'recreational' | 'club' | 'academy' | 'pro'

    # Football specifics
    position: Optional[str]             # GK | CB | FB | CM | W | CF
    competition_phase: Optional[str]    # pre | in | post | return

    # Equipment
    equipment: tuple        # immutable list of str

    # Gating flags
    coach_linked: bool
    unsupervised_context: bool

    @classmethod
    def build(
        cls,
        *,
        case_kind: str,
        age: int,
        sex: str,
        height_cm: float,
        weight_kg: float,
        pattern_scores: dict,
        asymmetries: dict,
        football_raw_inputs: Optional[dict] = None,
        injury_history: list = None,
        acuity: str = "none",
        red_flags: list = None,
        pregnancy: bool = False,
        pregnancy_trimester: Optional[int] = None,
        recent_surgery: bool = False,
        surgery_weeks_ago: Optional[int] = None,
        cardiac_flag: bool = False,
        current_pain: bool = False,
        pain_vas: Optional[int] = None,
        training_history: str = "recreational",
        position: Optional[str] = None,
        competition_phase: Optional[str] = None,
        equipment: list = None,
        coach_linked: bool = False,
        unsupervised_context: bool = True,
    ) -> "SyntheticPatientCase":
        injury_history = tuple(
            tuple(sorted(d.items())) for d in (injury_history or [])
        )
        red_flags = tuple(red_flags or [])
        equipment = tuple(equipment or [])

        case_id = _make_case_id(
            case_kind, age, sex, height_cm, weight_kg,
            pattern_scores, asymmetries, football_raw_inputs,
            injury_history, acuity, red_flags, pregnancy,
            pregnancy_trimester, recent_surgery, surgery_weeks_ago,
            cardiac_flag, current_pain, pain_vas, training_history,
            position, competition_phase, equipment, coach_linked,
            unsupervised_context,
        )
        return cls(
            case_id=case_id,
            case_kind=case_kind,
            age=age,
            sex=sex,
            height_cm=height_cm,
            weight_kg=weight_kg,
            pattern_scores=pattern_scores,
            asymmetries=asymmetries,
            football_raw_inputs=football_raw_inputs,
            injury_history=injury_history,
            acuity=acuity,
            red_flags=red_flags,
            pregnancy=pregnancy,
            pregnancy_trimester=pregnancy_trimester,
            recent_surgery=recent_surgery,
            surgery_weeks_ago=surgery_weeks_ago,
            cardiac_flag=cardiac_flag,
            current_pain=current_pain,
            pain_vas=pain_vas,
            training_history=training_history,
            position=position,
            competition_phase=competition_phase,
            equipment=equipment,
            coach_linked=coach_linked,
            unsupervised_context=unsupervised_context,
        )

    def hash(self) -> str:
        return self.case_id

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert tuples back to lists for JSON serialisation
        d["injury_history"] = [dict(t) for t in self.injury_history]
        d["red_flags"] = list(self.red_flags)
        d["equipment"] = list(self.equipment)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SyntheticPatientCase":
        return cls.build(
            case_kind=d["case_kind"],
            age=d["age"],
            sex=d["sex"],
            height_cm=d["height_cm"],
            weight_kg=d["weight_kg"],
            pattern_scores=d["pattern_scores"],
            asymmetries=d["asymmetries"],
            football_raw_inputs=d.get("football_raw_inputs"),
            injury_history=d.get("injury_history", []),
            acuity=d.get("acuity", "none"),
            red_flags=d.get("red_flags", []),
            pregnancy=d.get("pregnancy", False),
            pregnancy_trimester=d.get("pregnancy_trimester"),
            recent_surgery=d.get("recent_surgery", False),
            surgery_weeks_ago=d.get("surgery_weeks_ago"),
            cardiac_flag=d.get("cardiac_flag", False),
            current_pain=d.get("current_pain", False),
            pain_vas=d.get("pain_vas"),
            training_history=d.get("training_history", "recreational"),
            position=d.get("position"),
            competition_phase=d.get("competition_phase"),
            equipment=d.get("equipment", []),
            coach_linked=d.get("coach_linked", False),
            unsupervised_context=d.get("unsupervised_context", True),
        )


def _make_case_id(*args) -> str:
    payload = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Invariant decorator ────────────────────────────────────────────────────────

_REGISTERED_INVARIANTS: list[dict] = []


def invariant_decorator(
    severity: str,
    title: str,
    clinical_rationale: str,
    agent_id: str = "invariant",
    category: str = "safety",
):
    """Register a function as a named clinical invariant.

    Decorated function signature: (case: SyntheticPatientCase, engine_output: dict) -> Optional[Finding]
    Returns None on pass, a Finding on violation.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(case, engine_output):
            return fn(case, engine_output)

        wrapper._invariant_meta = {
            "severity": severity,
            "title": title,
            "clinical_rationale": clinical_rationale,
            "agent_id": agent_id,
            "category": category,
            "fn": wrapper,
        }
        _REGISTERED_INVARIANTS.append(wrapper._invariant_meta)
        return wrapper

    return decorator
