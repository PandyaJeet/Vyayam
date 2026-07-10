"""
VYAYAM Exercise Registry V2 - COMPLETE ~262 EXERCISES
Central registry for all exercises organized by CATEGORY

Categories:
- STRENGTH: 35 exercises (Foundation 9, Intermediate 18, Advanced 6)
- CARDIO: 11 exercises (Moderate 6, High Intensity 5)
- STRETCHING: 10 exercises (Lower 6, Upper 3, Full Body 1)
- BALANCE: 7 exercises
- MOBILITY: 6 exercises

TOTAL: 68 exercises

Usage:
    from exercise_system.exercise_registry_v2 import EXERCISE_REGISTRY
    from exercise_system.exercise_registry_v2 import get_exercises_by_category
    
    # Get all strength exercises
    strength = get_exercises_by_category('strength')
    
    # Get by level
    foundation = get_exercises_by_level('foundation')
"""

from typing import Dict, List

# ============================================================================
# IMPORTS - ALL 68 EXERCISES
# ============================================================================

# STRENGTH - FOUNDATION (9)
# 2026-07 DARK prescription-tier coaches (catalog flags stay False)
from .exercises import WallSitRxV2
from .exercises import PlankHoldRxV2
from .exercises import SidePlankRxV2
from .exercises import SingleLegBalanceRxV2
from .exercises import StraightLegRaiseRxV2
from .exercises import KneeToChestRxV2
from .exercises import ProneKneeBendRxV2
from .exercises import SupineHipAbductionRxV2
from .exercises import SidelyingHipAbductionRxV2
from .exercises import DbShoulderPressRxV2
from .exercises import BandRowRxV2
from .exercises import PartialSquatsV2
from .exercises import GluteBridgeV2
from .exercises import StraightLegRaisesV2
from .exercises import TerminalKneeExtensionV2
from .exercises import SitToStandV2
from .exercises import ClamshellsV2
from .exercises import BicepCurlsV2  # NEW
from .exercises import TricepExtensionsV2  # NEW
from .exercises import PushUpsV2  # NEW

# STRENGTH - INTERMEDIATE (18)
from .exercises import KneeExtensionSittingV2
from .exercises import HamstringCurlsStandingV2
from .exercises import HipAbductionStandingV2
from .exercises import StepUpsV2
from .exercises import StepDownsV2
from .exercises import MiniSquatsWithBandV2
from .exercises import SpanishSquatV2
from .exercises import DeclineSquatsV2
from .exercises import LateralBandWalksV2
from .exercises import ReverseLungesV2
from .exercises import SingleLegGluteBridgeV2
from .exercises import LungesV2
from .exercises import FullSquatsV2  # NEW
from .exercises import DeadliftDumbbellV2  # NEW
from .exercises import SideStepUpsV2  # NEW
from .exercises import SideStepDownsV2  # NEW
from .exercises import DumbbellRowingV2  # NEW
from .exercises import RotationalSwingsV2  # NEW

# STRENGTH - ADVANCED (6)
from .exercises import SingleLegSquatsV2
from .exercises import BulgarianSplitSquatsV2
from .exercises import LateralLungesV2
from .exercises import SingleLegRDLV2
from .exercises import JumpSquatsV2
from .exercises import PlanksV2  # NEW

# CARDIO - MODERATE (6)
from .exercises import MarchingOnSpotV2
from .exercises import HighKneesV2  # NEW
from .exercises import ButtKicksV2  # NEW
from .exercises import JumpingJacksV2  # NEW
from .exercises import SideToSideHopsV2  # NEW
from .exercises import SkatersV2  # NEW

# CARDIO - HIGH INTENSITY (5)
from .exercises import MountainClimbersV2  # NEW
from .exercises import BurpeesV2  # NEW
from .exercises import TuckJumpsV2  # NEW
from .exercises import SprintInPlaceV2  # NEW
from .exercises import LateralHopsV2  # NEW
from .exercises import BoxJumpsV2  # NEW

# STRETCHING - LOWER BODY (6)
from .exercises import CalfStretchV2
from .exercises import HamstringStretchV2
from .exercises import HipFlexorStretchV2
from .exercises import QuadricepsStretchV2
from .exercises import GroinStretchButterflyV2  # NEW
from .exercises import ITBandStretchStandingV2  # NEW

# STRETCHING - UPPER BODY (3)
from .exercises import ShoulderStretchOverheadV2  # NEW
from .exercises import ChestStretchDoorwayV2  # NEW
from .exercises import WristForearmStretchV2  # NEW

# STRETCHING - FULL BODY (1)
from .exercises import TrunkRotationStretchV2  # NEW

# BALANCE (7)
from .exercises import DoubleLegBalanceV2
from .exercises import SingleLegBalanceV2
from .exercises import TandemWalkingV2
from .exercises import SidewaysWalkingV2
from .exercises import BackwardWalkingV2
from .exercises import ClockReachesV2
from .exercises import LateralGaitTrainingV2  # NEW

# MOBILITY (7)
from .exercises import KneeCirclesV2  # NEW
from .exercises import StaticQuadricepsV2
from .exercises import StaticGluteiV2
from .exercises import StaticHipAdductorsV2
from .exercises import FoamRollingV2
from .exercises import HipAbductionSidelineV2
from .exercises import HeelSlidesV2
# V1 NEW EXERCISES (193)
from .exercises import AbWheelRolloutV2
from .exercises import AdductorRockV2
from .exercises import AnkleDorsiflexionWallV2
from .exercises import AnklePumpsV2
from .exercises import ArcherPullUpV2
from .exercises import ArcherPushUpV2
from .exercises import AustralianRowV2
from .exercises import BStanceRdlV2
from .exercises import BandAssistedPullUpV2
from .exercises import BandPullApartV2
from .exercises import BandWoodchopV2
from .exercises import BandedRdlV2
from .exercises import BandedShoulderDislocateV2
from .exercises import BearCrawlCardioV2
from .exercises import BearCrawlV2
from .exercises import BearCrawlWithReachV2
from .exercises import BedsheetRowV2
from .exercises import BicycleCrunchV2
from .exercises import BirdDogV2
from .exercises import BodyweightRdlV2
from .exercises import BosuBalanceV2
from .exercises import BosuSquatV2
from .exercises import BottomsUpCarryV2
from .exercises import BoxPushUpV2
from .exercises import BoxSquatV2
from .exercises import BroadJumpV2
from .exercises import CatCowV2
from .exercises import ChangeOfDirectionV2
from .exercises import ChinTuckV2
from .exercises import ChinUpV2
from .exercises import ClappingPushUpV2
from .exercises import ClockLungeV2
from .exercises import CloseGripPullUpV2
from .exercises import CloseGripPushUpV2
from .exercises import CommandoPullUpV2
from .exercises import CopenhagenPlankV2
from .exercises import CopenhagenWithMovementV2
from .exercises import CossackSquatV2
from .exercises import CrabWalkV2
from .exercises import CrawlDragV2
from .exercises import CurtsyLungeV2
from .exercises import DeadBugV2
from .exercises import DeadHangV2
from .exercises import DeclinePushUpV2
from .exercises import DeepNeckFlexorActivationV2
from .exercises import DeficitReverseLungeV2
from .exercises import DepthJumpV2
from .exercises import DiamondPushUpV2
from .exercises import DipProgressionV2
from .exercises import DoorframeRowV2
from .exercises import DragonFlagProgressionV2
from .exercises import DropPushUpV2
from .exercises import ElevatedPushUpV2
from .exercises import ElevatedTableRowV2
from .exercises import ExplosivePushUpV2
from .exercises import FacePullBandV2
from .exercises import FarmerCarryV2
from .exercises import FrogStretchV2
from .exercises import FullPullUpV2
from .exercises import GobletSquatV2
from .exercises import GoodMorningV2
from .exercises import HandstandWallHoldV2
from .exercises import HangingLegRaiseV2
from .exercises import HeelDropV2
from .exercises import HeelElevatedSquatV2
from .exercises import HinduPushUpV2
from .exercises import HinduSquatV2
from .exercises import HipCarsV2
from .exercises import HipHingeWallV2
from .exercises import HipThrustBandedV2
from .exercises import HipThrustBodyweightV2
from .exercises import HollowBodyHoldV2
from .exercises import HollowBodyRockV2
from .exercises import HurdleHopV2
from .exercises import InclinePushUpV2
from .exercises import InvertedRowV2
from .exercises import IsometricQuadSetV2
from .exercises import IsometricShoulderErV2
from .exercises import IsometricShoulderIrV2
from .exercises import JumpingPullUpV2
from .exercises import JumpingRopeSimulationV2
from .exercises import KneePushUpV2
from .exercises import LSitFloorV2
from .exercises import LSitPullUpV2
from .exercises import LateralBearCrawlV2
from .exercises import LateralBoundAndStickV2
from .exercises import LateralBoundV2
from .exercises import LateralStepDownV2
from .exercises import LoadedProgressiveStretchV2
from .exercises import MedicineBallSlamV2
from .exercises import MuscleUpProgressionV2
from .exercises import NegativePullUpV2
from .exercises import NegativePushUpV2
from .exercises import NegativeTableRowV2
from .exercises import NinetyNinetyHipSwitchV2
from .exercises import NordicCurlWeightedV2
from .exercises import NordicHamstringCurlV2
from .exercises import OverheadCarryV2
from .exercises import PallofPressDynamicV2
from .exercises import PallofPressIsometricV2
from .exercises import PatellarMobilisationV2
from .exercises import PauseSquatV2
from .exercises import PendulumExerciseV2
from .exercises import PerturbationTrainingV2
from .exercises import PigeonStretchV2
from .exercises import PikePushUpElevatedV2
from .exercises import PikePushUpV2
from .exercises import PistolSquatV2
from .exercises import PlancheLeanV2
from .exercises import PlankShoulderTapV2
from .exercises import PlyometricLungeV2
from .exercises import PnfHamstringStretchV2
from .exercises import PowerSkipV2
from .exercises import PrisonerSquatV2
from .exercises import ProneHipExtensionV2
from .exercises import ProneScorpionV2
from .exercises import ProneTrapRaiseV2
from .exercises import ProneYTWV2
from .exercises import PseudoPlanchePushUpV2
from .exercises import PushUpPlusV2
from .exercises import QuadSetWithShrV2
from .exercises import RenegadeRowV2
from .exercises import ReverseHyperextensionV2
from .exercises import RingPushUpV2
from .exercises import RingRowV2
from .exercises import RotationalThrowV2
from .exercises import RussianTwistBwV2
from .exercises import ScapularPullV2
from .exercises import ScapularSettingV2
from .exercises import SeatedHamstringCurlV2
from .exercises import SeatedHipFlexionV2
from .exercises import SeatedSpinalTwistV2
from .exercises import SerratusWallPushV2
from .exercises import ShortArcQuadV2
from .exercises import ShoulderCarsV2
from .exercises import ShoulderTapPushUpV2
from .exercises import ShuttleRunV2
from .exercises import SideLyingExternalRotationV2
from .exercises import SidePlankHipDipV2
from .exercises import SidePlankRotationV2
from .exercises import SidePlankV2
from .exercises import SingleArmFarmerHeavyV2
from .exercises import SingleArmPlankV2
from .exercises import SingleArmPushUpProgressionV2
from .exercises import SingleArmSingleLegPlankV2
from .exercises import SingleArmTowelRowV2
from .exercises import SingleLegBoundV2
from .exercises import SingleLegDeadBugV2
from .exercises import SingleLegEyesClosedV2
from .exercises import SingleLegHipThrustV2
from .exercises import SingleLegHopAndStickV2
from .exercises import SingleLegHopForwardV2
from .exercises import SingleLegHopLateralV2
from .exercises import SingleLegLandingV2
from .exercises import SingleLegReachV2
from .exercises import SingleLegSliderCurlV2
from .exercises import SingleLegSquatToBoxV2
from .exercises import SissySquatV2
from .exercises import SkaterSquatV2
from .exercises import SkippingLungeV2
from .exercises import SliderReverseLungeV2
from .exercises import SlidingLegCurlV2
from .exercises import SpidermanPushUpV2
from .exercises import SplitSquatJumpV2
from .exercises import SplitSquatStaticV2
from .exercises import SprintStartV2
from .exercises import SquatJumpTurnV2
from .exercises import SquatPulseV2
from .exercises import StaggeredPushUpV2
from .exercises import StarExcursionV2
from .exercises import StepUpWithKneeDriveV2
from .exercises import SuitcaseCarryV2
from .exercises import SumoSquatV2
from .exercises import SupermanHoldV2
from .exercises import SupineHipAbductionV2
from .exercises import TableRowV2
from .exercises import TempoSquatV2
from .exercises import ThoracicRotationV2
from .exercises import TowelRowV2
from .exercises import TurkishGetUpV2
from .exercises import TypewriterPushUpV2
from .exercises import WaiterCarryV2
from .exercises import WaiterFarmerCombinedV2
from .exercises import WalkingLungeV2
from .exercises import WallAngelV2
from .exercises import WallHandstandPushUpV2
from .exercises import WallPushUpV2
from .exercises import WallSitV2
from .exercises import WallSlideV2
from .exercises import WeightedPullUpV2
from .exercises import WideGripPushUpV2
from .exercises import WindshieldWiperV2
from .exercises import WorldsGreatestStretchV2



# ============================================================================
# EXERCISE METADATA
# ============================================================================

EXERCISE_METADATA = {
    # ========================================================================
    # STRENGTH - FOUNDATION (9)
    # ========================================================================
    'partial_squats': {
        'class': PartialSquatsV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 2,
        'display_name': 'Partial Squats',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'glute_bridge': {
        'class': GluteBridgeV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Glute Bridge',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'straight_leg_raises': {
        'class': StraightLegRaisesV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Straight Leg Raises',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'terminal_knee_extension': {
        'class': TerminalKneeExtensionV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Terminal Knee Extension',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'sit_to_stand': {
        'class': SitToStandV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Sit to Stand',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'clamshells': {
        'class': ClamshellsV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Clamshells',
        'unilateral': True,
        'movement_pattern': 'hinge',
    },
    'bicep_curls': {
        'class': BicepCurlsV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Bicep Curls',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'pull',
    },
    'tricep_extensions': {
        'class': TricepExtensionsV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Tricep Extensions',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'push',
    },
    'push_ups': {
        'class': PushUpsV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 2,
        'display_name': 'Push Ups',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'push',
    },
    
    # ========================================================================
    # STRENGTH - INTERMEDIATE (18)
    # ========================================================================
    'knee_extension_sitting': {
        'class': KneeExtensionSittingV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Knee Extension (Sitting)',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'hamstring_curls_standing': {
        'class': HamstringCurlsStandingV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Hamstring Curls (Standing)',
        'unilateral': True,
        'movement_pattern': 'hinge',
    },
    'hip_abduction_standing': {
        'class': HipAbductionStandingV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Hip Abduction (Standing)',
        'unilateral': True,
        'movement_pattern': 'hinge',
    },
    'step_ups': {
        'class': StepUpsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 1,
        'display_name': 'Step Ups',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'step_downs': {
        'class': StepDownsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Step Downs',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'mini_squats_with_band': {
        'class': MiniSquatsWithBandV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Mini Squats with Band',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'spanish_squat': {
        'class': SpanishSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 4,
        'display_name': 'Spanish Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'decline_squats': {
        'class': DeclineSquatsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 4,
        'display_name': 'Decline Squats',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'lateral_band_walks': {
        'class': LateralBandWalksV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Lateral Band Walks',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'reverse_lunges': {
        'class': ReverseLungesV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 1,
        'display_name': 'Reverse Lunges',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'single_leg_glute_bridge': {
        'class': SingleLegGluteBridgeV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Single Leg Glute Bridge',
        'unilateral': True,
        'movement_pattern': 'hinge',
    },
    'lunges': {
        'class': LungesV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Forward Lunges',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'full_squats': {
        'class': FullSquatsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Full Squats',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'deadlift_dumbbell': {
        'class': DeadliftDumbbellV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 4,
        'display_name': 'Dumbbell Deadlift',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'hinge',
    },
    'side_step_ups': {
        'class': SideStepUpsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Side Step Ups',
        'unilateral': True,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    'side_step_downs': {
        'class': SideStepDownsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Side Step Downs',
        'unilateral': True,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    'dumbbell_rowing': {
        'class': DumbbellRowingV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Dumbbell Rowing',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'pull',
    },
    'rotational_swings': {
        'class': RotationalSwingsV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Rotational Swings',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'rotate',
    },
    
    # ========================================================================
    # STRENGTH - ADVANCED (6)
    # ========================================================================
    'single_leg_squats': {
        'class': SingleLegSquatsV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Single Leg Squats',
        'unilateral': True,
        'movement_pattern': 'squat',
    },
    'bulgarian_split_squats': {
        'class': BulgarianSplitSquatsV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Bulgarian Split Squats',
        'unilateral': True,
        'movement_pattern': 'squat',
    },
    'lateral_lunges': {
        'class': LateralLungesV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 2,
        'display_name': 'Lateral Lunges',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'single_leg_rdl': {
        'class': SingleLegRDLV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 3,
        'display_name': 'Single Leg RDL',
        'unilateral': True,
        'movement_pattern': 'hinge',
    },
    'jump_squats': {
        'class': JumpSquatsV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Jump Squats',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'planks': {
        'class': PlanksV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Planks',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'push',
    },
    
    # ========================================================================
    # CARDIO - MODERATE (6)
    # ========================================================================
    'marching_on_spot': {
        'class': MarchingOnSpotV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Marching on Spot',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'high_knees': {
        'class': HighKneesV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'High Knees',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'butt_kicks': {
        'class': ButtKicksV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Butt Kicks',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'hinge',
    },
    'jumping_jacks': {
        'class': JumpingJacksV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Jumping Jacks',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'side_to_side_hops': {
        'class': SideToSideHopsV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Side to Side Hops',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    'skaters': {
        'class': SkatersV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Skaters',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    
    # ========================================================================
    # CARDIO - HIGH INTENSITY (6)
    # ========================================================================
    'mountain_climbers': {
        'class': MountainClimbersV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Mountain Climbers',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'push',
    },
    'burpees': {
        'class': BurpeesV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Burpees',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'tuck_jumps': {
        'class': TuckJumpsV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Tuck Jumps',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'sprint_in_place': {
        'class': SprintInPlaceV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Sprint in Place',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'lateral_hops': {  # DA-H3: canonical lower-case ID (was 'lateral_Hops')
    # tag/red-flag layers always used lateral_hops; the registry was the outlier.

        'class': LateralHopsV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Lateral Hops',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    'box_jumps': {
        'class': BoxJumpsV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Box Jumps',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    
    # ========================================================================
    # STRETCHING - LOWER BODY (6)
    # ========================================================================
    'calf_stretch': {
        'class': CalfStretchV2,
        'category': 'stretching',
        'subcategory': 'lower_body',
        'level': 1,
        'display_name': 'Calf Stretch',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'hamstring_stretch': {
        'class': HamstringStretchV2,
        'category': 'stretching',
        'subcategory': 'lower_body',
        'level': 1,
        'display_name': 'Hamstring Stretch',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'hip_flexor_stretch': {
        'class': HipFlexorStretchV2,
        'category': 'stretching',
        'subcategory': 'lower_body',
        'level': 1,
        'display_name': 'Hip Flexor Stretch',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'quadriceps_stretch': {
        'class': QuadricepsStretchV2,
        'category': 'stretching',
        'subcategory': 'lower_body',
        'level': 1,
        'display_name': 'Quadriceps Stretch',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'groin_stretch_butterfly': {
        'class': GroinStretchButterflyV2,
        'category': 'stretching',
        'subcategory': 'lower_body',
        'level': 1,
        'display_name': 'Groin Stretch (Butterfly)',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'hinge',
    },
    'it_band_stretch': {
        'class': ITBandStretchStandingV2,
        'category': 'stretching',
        'subcategory': 'lower_body',
        'level': 1,
        'display_name': 'IT Band Stretch',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    
    # ========================================================================
    # STRETCHING - UPPER BODY (3)
    # ========================================================================
    'shoulder_stretch': {
        'class': ShoulderStretchOverheadV2,
        'category': 'stretching',
        'subcategory': 'upper_body',
        'level': 1,
        'display_name': 'Shoulder Stretch',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'pull',
    },
    'chest_stretch': {
        'class': ChestStretchDoorwayV2,
        'category': 'stretching',
        'subcategory': 'upper_body',
        'level': 1,
        'display_name': 'Chest Stretch',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'push',
    },
    'wrist_forearm_stretch': {
        'class': WristForearmStretchV2,
        'category': 'stretching',
        'subcategory': 'upper_body',
        'level': 1,
        'display_name': 'Wrist & Forearm Stretch',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'push',
    },
    
    # ========================================================================
    # STRETCHING - FULL BODY (1)
    # ========================================================================
    'trunk_rotation_stretch': {
        'class': TrunkRotationStretchV2,
        'category': 'stretching',
        'subcategory': 'full_body',
        'level': 1,
        'display_name': 'Trunk Rotation Stretch',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'rotate',
    },
    
    # ========================================================================
    # BALANCE (7)
    # ========================================================================
    'double_leg_balance': {
        'class': DoubleLegBalanceV2,
        'category': 'balance',
        'subcategory': 'static',
        'level': 1,
        'display_name': 'Double Leg Balance',
        'unilateral': False,
        'movement_pattern': 'squat',
    },
    'single_leg_balance': {
        'class': SingleLegBalanceV2,
        'category': 'balance',
        'subcategory': 'static',
        'level': 3,
        'display_name': 'Single Leg Balance',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'tandem_walking': {
        'class': TandemWalkingV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Tandem Walking',
        'unilateral': False,
        'movement_pattern': 'lunge',
    },
    'sideways_walking': {
        'class': SidewaysWalkingV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Sideways Walking',
        'unilateral': False,
        'movement_pattern': 'lunge',
    },
    'backward_walking': {
        'class': BackwardWalkingV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 3,
        'display_name': 'Backward Walking',
        'unilateral': False,
        'movement_pattern': 'lunge',
    },
    'clock_reaches': {
        'class': ClockReachesV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Clock Reaches',
        'unilateral': True,
        'movement_pattern': 'lunge',
    },
    'lateral_gait_training': {
        'class': LateralGaitTrainingV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 3,
        'display_name': 'Lateral Gait Training',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'lunge',
    },
    
    # ========================================================================
    # MOBILITY (6)
    # ========================================================================
    'knee_circles': {
        'class': KneeCirclesV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Knee Circles',
        'unilateral': False,
        'new_in_v2': True,
        'movement_pattern': 'squat',
    },
    'static_quadriceps': {
        'class': StaticQuadricepsV2,
        'category': 'mobility',
        'subcategory': 'isometric',
        'level': 1,
        'display_name': 'Static Quadriceps',
        'unilateral': False,
        'movement_pattern': 'rotate',
    },
    'static_glutei': {
        'class': StaticGluteiV2,
        'category': 'mobility',
        'subcategory': 'isometric',
        'level': 1,
        'display_name': 'Static Glute Activation',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'static_hip_adductors': {
        'class': StaticHipAdductorsV2,
        'category': 'mobility',
        'subcategory': 'isometric',
        'level': 1,
        'display_name': 'Static Hip Adductors',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'foam_rolling': {
        'class': FoamRollingV2,
        'category': 'mobility',
        'subcategory': 'recovery',
        'level': 1,
        'display_name': 'Foam Rolling',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },
    'hip_abduction_sideline': {
        'class': HipAbductionSidelineV2,
        'category': 'mobility',
        'subcategory': 'activation',
        'level': 3,
        'display_name': 'Hip Abduction (Sideline)',
        'unilateral': True,
        'movement_pattern': 'hinge',
    },
    'heel_slides': {
        'class': HeelSlidesV2,
        'category': 'mobility',
        'subcategory': 'rom',
        'level': 1,
        'display_name': 'Heel Slides',
        'unilateral': False,
        'movement_pattern': 'hinge',
    },


    # ========================================================================
    # V1 NEW EXERCISES — 193 exercises across 7 movement patterns
    # ========================================================================
    'wall_sit': {
        'class': WallSitV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Wall Sit',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'box_squat': {
        'class': BoxSquatV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Box Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'goblet_squat': {
        'class': GobletSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Goblet Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'sumo_squat': {
        'class': SumoSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Sumo Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'pause_squat': {
        'class': PauseSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Pause Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'heel_elevated_squat': {
        'class': HeelElevatedSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Heel Elevated Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'pistol_squat': {
        'class': PistolSquatV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Pistol Squat',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'single_leg_squat_to_box': {
        'class': SingleLegSquatToBoxV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Single Leg Squat to Box',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'sissy_squat': {
        'class': SissySquatV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Sissy Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'cossack_squat': {
        'class': CossackSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Cossack Squat',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'tempo_squat': {
        'class': TempoSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Tempo Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'prisoner_squat': {
        'class': PrisonerSquatV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Prisoner Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'squat_pulse': {
        'class': SquatPulseV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Squat Pulse',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'skater_squat': {
        'class': SkaterSquatV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Skater Squat',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'hindu_squat': {
        'class': HinduSquatV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Hindu Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'hip_hinge_wall': {
        'class': HipHingeWallV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Hip Hinge to Wall',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'prone_hip_extension': {
        'class': ProneHipExtensionV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Prone Hip Extension',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'bodyweight_rdl': {
        'class': BodyweightRdlV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Bodyweight RDL',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'good_morning': {
        'class': GoodMorningV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Good Morning',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'nordic_hamstring_curl': {
        'class': NordicHamstringCurlV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Nordic Hamstring Curl',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'hip_thrust_bodyweight': {
        'class': HipThrustBodyweightV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Hip Thrust (Bodyweight)',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'sliding_leg_curl': {
        'class': SlidingLegCurlV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Sliding Leg Curl',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'single_leg_hip_thrust': {
        'class': SingleLegHipThrustV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Single Leg Hip Thrust',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'banded_rdl': {
        'class': BandedRdlV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Banded RDL',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'b_stance_rdl': {
        'class': BStanceRdlV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'B-Stance RDL',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'single_leg_slider_curl': {
        'class': SingleLegSliderCurlV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Single Leg Slider Curl',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'nordic_curl_weighted': {
        'class': NordicCurlWeightedV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Nordic Curl (Weighted)',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'hip_thrust_banded': {
        'class': HipThrustBandedV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Banded Hip Thrust',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'reverse_hyperextension': {
        'class': ReverseHyperextensionV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Reverse Hyperextension',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'split_squat_static': {
        'class': SplitSquatStaticV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Split Squat (Static)',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'curtsy_lunge': {
        'class': CurtsyLungeV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Curtsy Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'walking_lunge': {
        'class': WalkingLungeV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Walking Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'deficit_reverse_lunge': {
        'class': DeficitReverseLungeV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Deficit Reverse Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'plyometric_lunge': {
        'class': PlyometricLungeV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Plyometric Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'single_leg_landing': {
        'class': SingleLegLandingV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Single Leg Landing',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'lateral_bound': {
        'class': LateralBoundV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Lateral Bound',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'change_of_direction': {
        'class': ChangeOfDirectionV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Change of Direction',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'slider_reverse_lunge': {
        'class': SliderReverseLungeV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Slider Reverse Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'step_up_with_knee_drive': {
        'class': StepUpWithKneeDriveV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Step-Up with Knee Drive',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'clock_lunge': {
        'class': ClockLungeV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Clock Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'lateral_step_down': {
        'class': LateralStepDownV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Lateral Step-Down',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'skipping_lunge': {
        'class': SkippingLungeV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Skipping Lunge',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'wall_push_up': {
        'class': WallPushUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Wall Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'incline_push_up': {
        'class': InclinePushUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Incline Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'box_push_up': {
        'class': BoxPushUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Box Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'knee_push_up': {
        'class': KneePushUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 2,
        'display_name': 'Knee Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'wide_grip_push_up': {
        'class': WideGripPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Wide Grip Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'close_grip_push_up': {
        'class': CloseGripPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Close Grip Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'decline_push_up': {
        'class': DeclinePushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Decline Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'archer_push_up': {
        'class': ArcherPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Archer Push-Up',
        'unilateral': True,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'pike_push_up': {
        'class': PikePushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Pike Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'pseudo_planche_push_up': {
        'class': PseudoPlanchePushUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Pseudo Planche Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'handstand_wall_hold': {
        'class': HandstandWallHoldV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Handstand Wall Hold',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'pike_push_up_elevated': {
        'class': PikePushUpElevatedV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Pike Push-Up (Elevated)',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'wall_handstand_push_up': {
        'class': WallHandstandPushUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Wall Handstand Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'diamond_push_up': {
        'class': DiamondPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Diamond Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'staggered_push_up': {
        'class': StaggeredPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Staggered Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'spiderman_push_up': {
        'class': SpidermanPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Spiderman Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'hindu_push_up': {
        'class': HinduPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Hindu Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'ring_push_up': {
        'class': RingPushUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Ring Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'planche_lean': {
        'class': PlancheLeanV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Planche Lean',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'dip_progression': {
        'class': DipProgressionV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Dip Progression',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'single_arm_push_up_progression': {
        'class': SingleArmPushUpProgressionV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Single Arm Push-Up',
        'unilateral': True,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'negative_push_up': {
        'class': NegativePushUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Negative Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'push_up_plus': {
        'class': PushUpPlusV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Push-Up Plus',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'typewriter_push_up': {
        'class': TypewriterPushUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Typewriter Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'elevated_push_up': {
        'class': ElevatedPushUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Elevated Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'clapping_push_up': {
        'class': ClappingPushUpV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Clapping Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'shoulder_tap_push_up': {
        'class': ShoulderTapPushUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Shoulder Tap Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'prone_y_t_w': {
        'class': ProneYTWV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Prone Y-T-W',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'superman_hold': {
        'class': SupermanHoldV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Superman Hold',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'doorframe_row': {
        'class': DoorframeRowV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Doorframe Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'towel_row': {
        'class': TowelRowV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Towel Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'table_row': {
        'class': TableRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Table Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'bedsheet_row': {
        'class': BedsheetRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Bedsheet Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'negative_table_row': {
        'class': NegativeTableRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Negative Table Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'elevated_table_row': {
        'class': ElevatedTableRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Elevated Table Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'scapular_pull': {
        'class': ScapularPullV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 2,
        'display_name': 'Scapular Pull',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'negative_pull_up': {
        'class': NegativePullUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Negative Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'band_assisted_pull_up': {
        'class': BandAssistedPullUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Band-Assisted Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'full_pull_up': {
        'class': FullPullUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'chin_up': {
        'class': ChinUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Chin-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'archer_pull_up': {
        'class': ArcherPullUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Archer Pull-Up',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'l_sit_pull_up': {
        'class': LSitPullUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'L-Sit Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'weighted_pull_up': {
        'class': WeightedPullUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Weighted Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'band_pull_apart': {
        'class': BandPullApartV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Band Pull-Apart',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'face_pull_band': {
        'class': FacePullBandV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Face Pull (Band)',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'single_arm_towel_row': {
        'class': SingleArmTowelRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 4,
        'display_name': 'Single Arm Towel Row',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'inverted_row': {
        'class': InvertedRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Inverted Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'close_grip_pull_up': {
        'class': CloseGripPullUpV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Close Grip Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'commando_pull_up': {
        'class': CommandoPullUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Commando Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'dead_hang': {
        'class': DeadHangV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Dead Hang',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'jumping_pull_up': {
        'class': JumpingPullUpV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Jumping Pull-Up',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'australian_row': {
        'class': AustralianRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Australian Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'renegade_row': {
        'class': RenegadeRowV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Renegade Row',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'muscle_up_progression': {
        'class': MuscleUpProgressionV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Muscle-Up Progression',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'ring_row': {
        'class': RingRowV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Ring Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'dead_bug': {
        'class': DeadBugV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Dead Bug',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'bird_dog': {
        'class': BirdDogV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Bird Dog',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'pallof_press_isometric': {
        'class': PallofPressIsometricV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Pallof Press (Isometric)',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'russian_twist_bw': {
        'class': RussianTwistBwV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Russian Twist',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'side_plank': {
        'class': SidePlankV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Side Plank',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'side_plank_rotation': {
        'class': SidePlankRotationV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Side Plank with Rotation',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'pallof_press_dynamic': {
        'class': PallofPressDynamicV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Pallof Press (Dynamic)',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'side_plank_hip_dip': {
        'class': SidePlankHipDipV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Side Plank Hip Dip',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'single_leg_dead_bug': {
        'class': SingleLegDeadBugV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Single Leg Dead Bug',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'copenhagen_plank': {
        'class': CopenhagenPlankV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Copenhagen Plank',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'band_woodchop': {
        'class': BandWoodchopV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Band Woodchop',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'copenhagen_with_movement': {
        'class': CopenhagenWithMovementV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Copenhagen with Movement',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'single_arm_plank': {
        'class': SingleArmPlankV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Single Arm Plank',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'hollow_body_hold': {
        'class': HollowBodyHoldV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Hollow Body Hold',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'dragon_flag_progression': {
        'class': DragonFlagProgressionV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Dragon Flag Progression',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'hanging_leg_raise': {
        'class': HangingLegRaiseV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Hanging Leg Raise',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'hollow_body_rock': {
        'class': HollowBodyRockV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Hollow Body Rock',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'single_arm_single_leg_plank': {
        'class': SingleArmSingleLegPlankV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Single Arm Single Leg Plank',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'l_sit_floor': {
        'class': LSitFloorV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'L-Sit (Floor)',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'windshield_wiper': {
        'class': WindshieldWiperV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Windshield Wipers',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'ab_wheel_rollout': {
        'class': AbWheelRolloutV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Ab Wheel Rollout',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'plank_shoulder_tap': {
        'class': PlankShoulderTapV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Plank Shoulder Tap',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'bicycle_crunch': {
        'class': BicycleCrunchV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Bicycle Crunch',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'turkish_get_up': {
        'class': TurkishGetUpV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Turkish Get-Up',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'farmer_carry': {
        'class': FarmerCarryV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 5,
        'display_name': 'Farmer Carry',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'suitcase_carry': {
        'class': SuitcaseCarryV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Suitcase Carry',
        'unilateral': True,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'waiter_carry': {
        'class': WaiterCarryV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Waiter Carry',
        'unilateral': True,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'bear_crawl': {
        'class': BearCrawlV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Bear Crawl',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'crab_walk': {
        'class': CrabWalkV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Crab Walk',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'lateral_bear_crawl': {
        'class': LateralBearCrawlV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Lateral Bear Crawl',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'bear_crawl_with_reach': {
        'class': BearCrawlWithReachV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Bear Crawl with Reach',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'single_arm_farmer_heavy': {
        'class': SingleArmFarmerHeavyV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 3,
        'display_name': 'Heavy Suitcase Carry',
        'unilateral': True,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'waiter_farmer_combined': {
        'class': WaiterFarmerCombinedV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Waiter + Farmer Carry',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'overhead_carry': {
        'class': OverheadCarryV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Overhead Carry',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'bottoms_up_carry': {
        'class': BottomsUpCarryV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 3,
        'display_name': 'Bottoms-Up Carry',
        'unilateral': True,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'crawl_drag': {
        'class': CrawlDragV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 4,
        'display_name': 'Crawl and Drag',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'depth_jump': {
        'class': DepthJumpV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 5,
        'display_name': 'Depth Jump',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'single_leg_bound': {
        'class': SingleLegBoundV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Single Leg Bound',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'explosive_push_up': {
        'class': ExplosivePushUpV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Explosive Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'hurdle_hop': {
        'class': HurdleHopV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Hurdle Hop',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'sprint_start': {
        'class': SprintStartV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Sprint Start',
        'unilateral': False,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'medicine_ball_slam': {
        'class': MedicineBallSlamV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Medicine Ball Slam',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'rotational_throw': {
        'class': RotationalThrowV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Rotational Throw',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'broad_jump': {
        'class': BroadJumpV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Broad Jump',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'squat_jump_turn': {
        'class': SquatJumpTurnV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Squat Jump with Turn',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'split_squat_jump': {
        'class': SplitSquatJumpV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Split Squat Jump',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'power_skip': {
        'class': PowerSkipV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Power Skip',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'lateral_bound_and_stick': {
        'class': LateralBoundAndStickV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Lateral Bound and Stick',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'drop_push_up': {
        'class': DropPushUpV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Drop Push-Up',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'single_leg_hop_forward': {
        'class': SingleLegHopForwardV2,
        'category': 'cardio',
        'subcategory': 'high_intensity',
        'level': 4,
        'display_name': 'Single Leg Hop Forward',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'single_leg_eyes_closed': {
        'class': SingleLegEyesClosedV2,
        'category': 'balance',
        'subcategory': 'static',
        'level': 3,
        'display_name': 'Single Leg Eyes Closed',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'bosu_balance': {
        'class': BosuBalanceV2,
        'category': 'balance',
        'subcategory': 'static',
        'level': 3,
        'display_name': 'Unstable Surface Balance',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'perturbation_training': {
        'class': PerturbationTrainingV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Perturbation Training',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'single_leg_hop_and_stick': {
        'class': SingleLegHopAndStickV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Single Leg Hop and Stick',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'single_leg_reach': {
        'class': SingleLegReachV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 3,
        'display_name': 'Single Leg Reach',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'star_excursion': {
        'class': StarExcursionV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Star Excursion Balance',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'bosu_squat': {
        'class': BosuSquatV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Bosu Squat',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'single_leg_hop_lateral': {
        'class': SingleLegHopLateralV2,
        'category': 'balance',
        'subcategory': 'dynamic',
        'level': 4,
        'display_name': 'Single Leg Lateral Hop',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'hip_cars': {
        'class': HipCarsV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Hip CARs',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'shoulder_cars': {
        'class': ShoulderCarsV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Shoulder CARs',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'thoracic_rotation': {
        'class': ThoracicRotationV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Thoracic Rotation',
        'unilateral': False,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'cat_cow': {
        'class': CatCowV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Cat-Cow',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'ninety_ninety_hip_switch': {
        'class': NinetyNinetyHipSwitchV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': '90/90 Hip Switch',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'pigeon_stretch': {
        'class': PigeonStretchV2,
        'category': 'mobility',
        'subcategory': 'stretch',
        'level': 1,
        'display_name': 'Pigeon Stretch',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'worlds_greatest_stretch': {
        'class': WorldsGreatestStretchV2,
        'category': 'mobility',
        'subcategory': 'stretch',
        'level': 3,
        'display_name': 'World\'s Greatest Stretch',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'loaded_progressive_stretch': {
        'class': LoadedProgressiveStretchV2,
        'category': 'mobility',
        'subcategory': 'stretch',
        'level': 3,
        'display_name': 'Loaded Progressive Stretch',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'ankle_dorsiflexion_wall': {
        'class': AnkleDorsiflexionWallV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Ankle Dorsiflexion (Wall)',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'frog_stretch': {
        'class': FrogStretchV2,
        'category': 'mobility',
        'subcategory': 'stretch',
        'level': 1,
        'display_name': 'Frog Stretch',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'adductor_rock': {
        'class': AdductorRockV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Adductor Rock',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'prone_scorpion': {
        'class': ProneScorpionV2,
        'category': 'mobility',
        'subcategory': 'stretch',
        'level': 3,
        'display_name': 'Prone Scorpion',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'wall_angel': {
        'class': WallAngelV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 1,
        'display_name': 'Wall Angel',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'seated_spinal_twist': {
        'class': SeatedSpinalTwistV2,
        'category': 'mobility',
        'subcategory': 'stretch',
        'level': 1,
        'display_name': 'Seated Spinal Twist',
        'unilateral': True,
        'movement_pattern': 'rotate',
        'new_in_v2': True,
    },
    'banded_shoulder_dislocate': {
        'class': BandedShoulderDislocateV2,
        'category': 'mobility',
        'subcategory': 'joint_prep',
        'level': 3,
        'display_name': 'Banded Shoulder Dislocate',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'bear_crawl_cardio': {
        'class': BearCrawlCardioV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Bear Crawl (Cardio)',
        'unilateral': False,
        'movement_pattern': 'carry',
        'new_in_v2': True,
    },
    'jumping_rope_simulation': {
        'class': JumpingRopeSimulationV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 1,
        'display_name': 'Jumping Rope Simulation',
        'unilateral': False,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'shuttle_run': {
        'class': ShuttleRunV2,
        'category': 'cardio',
        'subcategory': 'moderate',
        'level': 3,
        'display_name': 'Shuttle Run',
        'unilateral': False,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'isometric_quad_set': {
        'class': IsometricQuadSetV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Isometric Quad Set',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'short_arc_quad': {
        'class': ShortArcQuadV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Short Arc Quad',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'seated_hamstring_curl': {
        'class': SeatedHamstringCurlV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Seated Hamstring Curl',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'seated_hip_flexion': {
        'class': SeatedHipFlexionV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Seated Hip Flexion',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'supine_hip_abduction': {
        'class': SupineHipAbductionV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Supine Hip Abduction',
        'unilateral': True,
        'movement_pattern': 'lunge',
        'new_in_v2': True,
    },
    'ankle_pumps': {
        'class': AnklePumpsV2,
        'category': 'mobility',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Ankle Pumps',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'patellar_mobilisation': {
        'class': PatellarMobilisationV2,
        'category': 'mobility',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Patellar Mobilisation',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'isometric_shoulder_er': {
        'class': IsometricShoulderErV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Isometric Shoulder ER',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'isometric_shoulder_ir': {
        'class': IsometricShoulderIrV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Isometric Shoulder IR',
        'unilateral': True,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'scapular_setting': {
        'class': ScapularSettingV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Scapular Setting',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'chin_tuck': {
        'class': ChinTuckV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Chin Tuck',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'deep_neck_flexor_activation': {
        'class': DeepNeckFlexorActivationV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Deep Neck Flexor Activation',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'pendulum_exercise': {
        'class': PendulumExerciseV2,
        'category': 'mobility',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Pendulum Exercise',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'wall_slide': {
        'class': WallSlideV2,
        'category': 'mobility',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Wall Slide',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'heel_drop': {
        'class': HeelDropV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Heel Drop',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'side_lying_external_rotation': {
        'class': SideLyingExternalRotationV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Side-Lying External Rotation',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'prone_trap_raise': {
        'class': ProneTrapRaiseV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Prone Trap Raise',
        'unilateral': False,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'serratus_wall_push': {
        'class': SerratusWallPushV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Serratus Wall Push',
        'unilateral': False,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },
    'quad_set_with_shr': {
        'class': QuadSetWithShrV2,
        'category': 'strength',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'Quad Set + SLR',
        'unilateral': True,
        'movement_pattern': 'squat',
        'new_in_v2': True,
    },
    'pnf_hamstring_stretch': {
        'class': PnfHamstringStretchV2,
        'category': 'mobility',
        'subcategory': 'rehabilitation',
        'level': 1,
        'display_name': 'PNF Hamstring Stretch',
        'unilateral': True,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    # ========================================================================
    # CHAIN-ONLY ENTRIES (no dedicated V2 class — proxy class used for registry)
    # ========================================================================
    'nordic_curl_partner': {
        'class': NordicCurlWeightedV2,   # proxy — partner-assisted variant
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Nordic Curl (Partner Assisted)',
        'unilateral': False,
        'movement_pattern': 'hinge',
        'new_in_v2': True,
    },
    'single_arm_pull_up_prog': {
        'class': WeightedPullUpV2,        # proxy — closest advanced pull class
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Single Arm Pull-Up Progression',
        'unilateral': True,
        'movement_pattern': 'pull',
        'new_in_v2': True,
    },
    'single_arm_push_up_prog': {
        'class': SingleArmPushUpProgressionV2,
        'category': 'strength',
        'subcategory': 'advanced',
        'level': 5,
        'display_name': 'Single Arm Push-Up Progression',
        'unilateral': True,
        'movement_pattern': 'push',
        'new_in_v2': True,
    },

    # ========================================================================
    # 2026-07 DARK PRESCRIPTION-TIER COACHES — *_rx keys. Reachable only via
    # therapist-catalog v2_exercise_key entries whose v2_ghost_supported flag
    # is still False (ship dark; flip per exercise after filming protocol).
    # ========================================================================
    'wall_sit_rx': {
        'class': WallSitRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Wall Sit',
        'unilateral': False,
        'movement_pattern': 'squat',
        'rx_dark_2026_07': True,
    },
    'band_row_rx': {
        'class': BandRowRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Resistance Band Row',
        'unilateral': False,
        'movement_pattern': 'pull',
        'rx_dark_2026_07': True,
    },
    'db_shoulder_press_rx': {
        'class': DbShoulderPressRxV2,
        'category': 'strength',
        'subcategory': 'intermediate',
        'level': 2,
        'display_name': 'Dumbbell Shoulder Press',
        'unilateral': False,
        'movement_pattern': 'push',
        'rx_dark_2026_07': True,
    },
    'sidelying_hip_abduction_rx': {
        'class': SidelyingHipAbductionRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Side-lying Hip Abduction',
        'unilateral': True,
        'movement_pattern': 'activation',
        'rx_dark_2026_07': True,
    },
    'supine_hip_abduction_rx': {
        'class': SupineHipAbductionRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Supine Hip Abduction',
        'unilateral': True,
        'movement_pattern': 'activation',
        'rx_dark_2026_07': True,
    },
    'prone_knee_bend_rx': {
        'class': ProneKneeBendRxV2,
        'category': 'mobility',
        'subcategory': 'rom',
        'level': 1,
        'display_name': 'Prone Knee Bend',
        'unilateral': True,
        'movement_pattern': 'mobility',
        'rx_dark_2026_07': True,
    },
    'knee_to_chest_rx': {
        'class': KneeToChestRxV2,
        'category': 'mobility',
        'subcategory': 'rom',
        'level': 1,
        'display_name': 'Knee to Chest',
        'unilateral': True,
        'movement_pattern': 'mobility',
        'rx_dark_2026_07': True,
    },
    'straight_leg_raise_rx': {
        'class': StraightLegRaiseRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Straight Leg Raise',
        'unilateral': True,
        'movement_pattern': 'activation',
        'rx_dark_2026_07': True,
    },
    'single_leg_balance_rx': {
        'class': SingleLegBalanceRxV2,
        'category': 'balance',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Single-Leg Balance',
        'unilateral': True,
        'movement_pattern': 'balance',
        'rx_dark_2026_07': True,
    },
    'side_plank_rx': {
        'class': SidePlankRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 2,
        'display_name': 'Side Plank',
        'unilateral': True,
        'movement_pattern': 'core',
        'rx_dark_2026_07': True,
    },
    'plank_hold_rx': {
        'class': PlankHoldRxV2,
        'category': 'strength',
        'subcategory': 'foundation',
        'level': 1,
        'display_name': 'Plank Hold',
        'unilateral': False,
        'movement_pattern': 'core',
        'rx_dark_2026_07': True,
    },
}


# ============================================================================
# EXERCISE REGISTRY - Instantiated Objects
# ============================================================================

# ── Lazy registry ────────────────────────────────────────────────────────────
# Previously this eagerly instantiated all 68 exercise classes at import time.
# Each __init__ creates a VoiceCoachV2 + starts a speech thread, so visiting
# /exercises/ would spawn 68 background threads and trigger "run loop already
# started" errors. Now instances are created on first use only.
class _LazyRegistry(dict):
    """Dict that instantiates exercise classes on first access."""
    def __getitem__(self, key):
        val = super().__getitem__(key)
        if isinstance(val, type):          # still a class, not yet instantiated
            instance = val()
            super().__setitem__(key, instance)
            return instance
        return val

EXERCISE_REGISTRY = _LazyRegistry({
    key: metadata['class']          # store the CLASS, not an instance
    for key, metadata in EXERCISE_METADATA.items()
})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_exercises() -> Dict:
    """Get all 68 exercises"""
    return EXERCISE_REGISTRY


def get_exercises_by_category(category: str) -> Dict:
    """
    Get exercises filtered by category
    
    Args:
        category: 'strength', 'cardio', 'stretching', 'balance', 'mobility'
    
    Returns:
        Dict of exercises in that category
    """
    return {
        key: EXERCISE_REGISTRY[key]
        for key, metadata in EXERCISE_METADATA.items()
        if metadata['category'] == category.lower()
    }


def get_exercises_by_subcategory(category: str, subcategory: str) -> Dict:
    """
    Get exercises filtered by category and subcategory
    
    Examples:
        get_exercises_by_subcategory('strength', 'foundation')
        get_exercises_by_subcategory('cardio', 'high_intensity')
        get_exercises_by_subcategory('stretching', 'upper_body')
    """
    return {
        key: EXERCISE_REGISTRY[key]
        for key, metadata in EXERCISE_METADATA.items()
        if metadata['category'] == category.lower() 
        and metadata['subcategory'] == subcategory.lower()
    }


def get_exercises_by_level(level) -> Dict:
    """
    Get exercises filtered by difficulty level.

    Args:
        level: integer 1-5, or legacy string ('foundation'->1, 'intermediate'->3, 'advanced'->4)
    """
    _str_map = {'foundation': 1, 'intermediate': 3, 'advanced': 4}
    if isinstance(level, str):
        level = _str_map.get(level.lower(), level)
    return {
        key: EXERCISE_REGISTRY[key]
        for key, metadata in EXERCISE_METADATA.items()
        if metadata['level'] == level
    }


def get_new_exercises() -> Dict:
    """Get only the 26 NEW exercises added in V2"""
    return {
        key: EXERCISE_REGISTRY[key]
        for key, metadata in EXERCISE_METADATA.items()
        if metadata.get('new_in_v2', False)
    }


def get_exercise_count() -> Dict[str, int]:
    """Get exercise counts by category and total"""
    counts = {
        'strength': 0,
        'cardio': 0,
        'stretching': 0,
        'balance': 0,
        'mobility': 0,
        'total': 0,
        'new_in_v2': 0,
    }
    
    for metadata in EXERCISE_METADATA.values():
        category = metadata['category']
        counts[category] += 1
        counts['total'] += 1
        if metadata.get('new_in_v2', False):
            counts['new_in_v2'] += 1
    
    return counts


# ============================================================================
# STATS & INFO
# ============================================================================

if __name__ == "__main__":
    counts = get_exercise_count()
    
    print("="*70)
    print("VYAYAM EXERCISE REGISTRY V2 - COMPLETE")
    print("="*70)
    print(f"\n📊 TOTAL EXERCISES: {counts['total']}")
    print(f"\nBy Category:")
    print(f"  - Strength: {counts['strength']}")
    print(f"  - Cardio: {counts['cardio']}")
    print(f"  - Stretching: {counts['stretching']}")
    print(f"  - Balance: {counts['balance']}")
    print(f"  - Mobility: {counts['mobility']}")
    print(f"\n✨ New in V2: {counts['new_in_v2']} exercises")
    print("="*70)