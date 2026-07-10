"""Wall Sit — prescription tier (2026-07 dark camera coach).

Subclasses WallSitV2 verbatim: same movement, same targets, same H2
behavior. The distinct registry key exists so the therapist-tier camera
coach (js_type WALL_SIT_RX, named-fault cues) can ship DARK without
touching the live self-serve `wall_sit` (SQUAT_HOLD) experience.
"""

from .wall_sit_v2 import WallSitV2


class WallSitRxV2(WallSitV2):
    pass
