"""
Data models used across the system - EXACT COPY from working code
"""

from dataclasses import dataclass
from enum import Enum


class FormStatus(Enum):
    CORRECT = "correct"
    NEEDS_ADJUSTMENT = "adjustment"
    INCORRECT = "incorrect"
    # Aliases (DA-EX-core): 63 modules reference FormStatus.WARNING and 13
    # FormStatus.GOOD — both crashed with AttributeError at runtime. Enum
    # aliasing keeps the value space unchanged for downstream comparisons.
    GOOD = "correct"
    WARNING = "adjustment"


@dataclass
class JointFeedback:
    status: FormStatus
    angle: float
    message: str


@dataclass
class ExerciseStats:
    reps_completed: int = 0
    target_reps: int = 10
    form_score: float = 100.0
    elapsed_time: float = 0.0
    current_phase: str = "standing"
    practice_reps: int = 0
    rejected_reps: int = 0
