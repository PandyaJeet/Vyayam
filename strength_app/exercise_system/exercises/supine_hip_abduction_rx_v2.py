"""Supine Hip Abduction — prescription tier (2026-07 dark camera coach).

Subclasses SupineHipAbductionV2 verbatim (H2 green at 100). Distinct key so
the therapist-tier coach (js_type SUPINE_ABD_RX: leg-spread ratio reps +
pelvis-shift fault) ships DARK; `supine_hip_abduction` stays MANUAL for
self-serve.
"""

from .supine_hip_abduction_v2 import SupineHipAbductionV2


class SupineHipAbductionRxV2(SupineHipAbductionV2):
    pass
