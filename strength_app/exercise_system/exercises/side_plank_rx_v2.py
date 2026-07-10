"""Side Plank — prescription tier (2026-07 dark camera coach).

Subclasses SidePlankV2 and ADDS get_target_poses (the parent has none —
H2 status was no_targets): the artifact needs real phase targets, and the
lateral body line is the movement's single source of truth. Distinct key
so the therapist-tier coach (js_type SIDE_PLANK_RX, hip-drop fault) ships
DARK without touching the live self-serve `side_plank` (SIDE_PLANK).
"""

from .side_plank_v2 import SidePlankV2


class SidePlankRxV2(SidePlankV2):

    def get_target_poses(self):
        return {
            'holding': {'body_line': 178, 'tolerance': 12},
        }
