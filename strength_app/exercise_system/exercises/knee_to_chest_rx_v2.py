"""Knee to Chest — prescription tier (2026-07 dark camera coach).

Reuses WallSitV2\'s isometric-hold state machine (setup → holding →
complete, time-accumulating) with hip-flexion targets: the movement is a
~20s supine hold with the working knee drawn to the chest. The JS coach
(KNEE_TO_CHEST_RX) reads the working hip angle; this module is the
phase-target source of truth for the artifact.
"""

from .wall_sit_v2 import WallSitV2


class KneeToChestRxV2(WallSitV2):

    def get_target_poses(self):
        return {
            'setup':   {'working_hip': 130, 'tolerance': 25},
            'holding': {'working_hip': 55,  'tolerance': 20},
            'complete': {'working_hip': 55, 'tolerance': 20},
        }
