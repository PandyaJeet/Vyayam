"""
Finding dataclass — shared output format for all audit agents.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MED": 2, "LOW": 3}


@dataclass
class Finding:
    severity: str                   # CRITICAL | HIGH | MED | LOW
    agent_id: str
    category: str
    title: str                      # one line, ≤ 80 chars
    description: str                # ≤ 300 words
    reproduction: str               # code snippet or step sequence
    suggested_fix: str
    clinical_rationale: str         # citation or explicit reasoning

    finding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    case_id: Optional[str] = None   # None for code-level findings
    file_path: str = ""
    line_number: Optional[int] = None

    def __post_init__(self):
        if self.severity not in _SEVERITY_ORDER:
            raise ValueError(f"Invalid severity {self.severity!r}. Use CRITICAL/HIGH/MED/LOW.")

    def severity_rank(self) -> int:
        return _SEVERITY_ORDER[self.severity]

    def __lt__(self, other: "Finding") -> bool:
        return self.severity_rank() < other.severity_rank()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Finding":
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "Finding":
        return cls.from_dict(json.loads(s))

    def short_summary(self) -> str:
        loc = f"{self.file_path}:{self.line_number}" if self.line_number else self.file_path or "—"
        case = self.case_id or "code-level"
        return f"[{self.severity}] {self.title} | {loc} | case={case}"
