"""Prone Knee Bend — prescription tier (2026-07 dark camera coach).

Reuses WallSitV2\'s phase machine as the desktop reference with knee-flexion
targets (prone heel-to-buttock cycle). The live rep cycle + hip-lift fault
live in the JS coach (PRONE_KNEE_BEND_RX); this module is the artifact\'s
phase-target source of truth.
"""

from .wall_sit_v2 import WallSitV2


class ProneKneeBendRxV2(WallSitV2):

    def get_target_poses(self):
        return {
            'setup':   {'working_knee': 172, 'tolerance': 15},
            'holding': {'working_knee': 90,  'tolerance': 18},
            'complete': {'working_knee': 90, 'tolerance': 18},
        }
