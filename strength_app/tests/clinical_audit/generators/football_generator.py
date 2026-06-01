"""
Agent 2: Football Synthetic Athlete Generator.

Produces SyntheticPatientCase objects (case_kind='football') representing
realistic football athletes for the VYAYAM club-gated football assessment
battery.  Every case carries raw test inputs in football_raw_inputs — no
scoring or prescription is performed here.

Design principles
-----------------
- Stratified across age_band × sex × position × training_history ×
  competition_phase (~2,500 cells; >=2 cases per cell)
- ~30 mandatory adversarial/edge-case seeds injected into every batch
- Physiological ranges grounded in published norms (see inline citations)
- coach_linked=False in ~5 % of cases to test the gating pathway
- All test values generated via realistic_test_inputs() — never elite numbers
  for non-elite athlete profiles

Raw input keys (matching v1_football_constants.py FootballProfile fields)
---------------------------------------------------------------------------
  hop_test.left_cm          float  (hop distance, cm)
  hop_test.right_cm         float
  nordic.hold_time_seconds  float  (eccentric hold, seconds)
  sprint.20m_time_seconds   float  (20 m sprint time, seconds)
  pogo.clean_reps_10s       int    (clean bilateral pogo reps in 10 s)
  cod.left_505_seconds      float  (505 COD time, seconds, left pivot)
  cod.right_505_seconds     float
  ybalance.left_pct         float  (anterior reach as % limb length)
  ybalance.right_pct        float
"""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, Iterator, List, Optional

from strength_app.tests.clinical_audit.core.patient_case import SyntheticPatientCase

# ── Output path ───────────────────────────────────────────────────────────────
_REPORTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "reports"
)


# ============================================================================
# DIMENSION DEFINITIONS
# ============================================================================

AGE_BANDS = [
    (14, 15, "14-15"),   # youth — PHV risk
    (16, 17, "16-17"),   # late adolescent
    (18, 19, "18-19"),   # U20
    (20, 23, "20-23"),   # senior early
    (24, 29, "24-29"),   # senior peak
    (30, 34, "30-34"),   # senior veteran
    (35, 42, "35+"),     # masters
]

SEXES = ["M", "F"]

POSITIONS = ["GK", "CB", "FB", "CM", "WIDE", "CF"]

TRAINING_HISTORIES = [
    "academy_pro",
    "club_senior",
    "club_amateur",
    "recreational",
    "recent_comeback",
]

INJURY_TYPES = [
    "none",
    "past_ACL_R",
    "recurring_hamstring",
    "ankle_sprain_history",
    "groin_FAI",
    "concussion_history",
    "multiple",
]

COMPETITION_PHASES = [
    "pre-season",
    "in-season",
    "post-season",
    "return-from-layoff",
    "acutely-injured",
]


# ============================================================================
# PUBLISHED NORMS — used for realistic_test_inputs()
#
# Citations embedded per norm cluster below.
# ============================================================================

# -- Single-leg hop for distance (cm) --
# Norms from:
#   Gustavsson A et al. (2006). "A test battery for performance testing in
#   football players." Scandinavian Journal of Medicine & Science in Sports,
#   16(3), 172-182.
#   Myer GD et al. (2011). "Predictors of anterior cruciate ligament injury
#   risk in female athletes." British Journal of Sports Medicine, 45(8), 644-651.
# Adult male professional reference: ~170-220 cm dominant leg
# Adult female professional reference: ~140-185 cm dominant leg
# Source: Thomee R et al., "Muscle strength and hop performance criteria
#   prior to return to sports after anterior cruciate ligament reconstruction,"
#   Knee Surg Sports Traumatol Arthrosc 19(11):1798-1805, 2011 — pooled
#   normative data for healthy and post-ACLR athletes.
# Secondary: Burland JP et al., "Identification of Age-Relevant and
#   Activity-Relevant Hop Test Targets in Young Athletes After ACL
#   Reconstruction," PMC9842127, 2023 — age-stratified youth targets.
# Adolescent male 14-15y: ~130-175 cm (derived from above age-stratified data)
# Adolescent female 14-15y: ~110-155 cm (derived from above age-stratified data)

HOP_NORMS: Dict[str, Dict[str, tuple]] = {
    # (mean, std, min_clip, max_clip)  for dominant leg, by (training, sex, age_band_key)
    "academy_pro": {
        "M_14-15": (155, 20, 90, 210),
        "M_16-17": (175, 20, 110, 225),
        "M_18-19": (195, 18, 130, 235),
        "M_20-23": (205, 18, 140, 240),
        "M_24-29": (210, 18, 150, 245),
        "M_30-34": (200, 20, 135, 235),
        "M_35+":   (185, 22, 120, 225),
        "F_14-15": (130, 18, 80, 175),
        "F_16-17": (148, 18, 90, 190),
        "F_18-19": (165, 18, 110, 205),
        "F_20-23": (170, 18, 115, 210),
        "F_24-29": (172, 18, 115, 210),
        "F_30-34": (165, 20, 105, 205),
        "F_35+":   (152, 22, 95, 195),
    },
    "club_senior": {
        "M_14-15": (145, 22, 80, 200),
        "M_16-17": (162, 22, 95, 210),
        "M_18-19": (180, 20, 120, 225),
        "M_20-23": (190, 20, 125, 230),
        "M_24-29": (195, 20, 130, 230),
        "M_30-34": (185, 22, 120, 225),
        "M_35+":   (170, 24, 105, 215),
        "F_14-15": (120, 20, 70, 165),
        "F_16-17": (135, 20, 80, 180),
        "F_18-19": (152, 20, 95, 195),
        "F_20-23": (158, 20, 100, 200),
        "F_24-29": (160, 20, 100, 200),
        "F_30-34": (152, 22, 90, 195),
        "F_35+":   (140, 24, 80, 185),
    },
    "club_amateur": {
        "M_14-15": (130, 25, 65, 185),
        "M_16-17": (148, 25, 80, 200),
        "M_18-19": (162, 22, 100, 210),
        "M_20-23": (170, 22, 110, 215),
        "M_24-29": (172, 22, 110, 215),
        "M_30-34": (162, 25, 100, 210),
        "M_35+":   (150, 28, 85, 205),
        "F_14-15": (108, 22, 60, 152),
        "F_16-17": (120, 22, 68, 165),
        "F_18-19": (135, 22, 80, 180),
        "F_20-23": (140, 22, 82, 185),
        "F_24-29": (142, 22, 82, 185),
        "F_30-34": (135, 25, 75, 180),
        "F_35+":   (122, 28, 60, 170),
    },
    "recreational": {
        "M_14-15": (115, 28, 55, 172),
        "M_16-17": (130, 28, 65, 185),
        "M_18-19": (145, 25, 80, 195),
        "M_20-23": (152, 25, 85, 200),
        "M_24-29": (155, 25, 88, 200),
        "M_30-34": (145, 28, 80, 195),
        "M_35+":   (132, 32, 65, 185),
        "F_14-15": (95, 25, 50, 142),
        "F_16-17": (107, 25, 55, 155),
        "F_18-19": (118, 25, 62, 168),
        "F_20-23": (122, 25, 65, 170),
        "F_24-29": (125, 25, 65, 170),
        "F_30-34": (118, 28, 58, 165),
        "F_35+":   (105, 32, 45, 155),
    },
    "recent_comeback": {
        "M_14-15": (120, 30, 55, 175),
        "M_16-17": (138, 30, 65, 190),
        "M_18-19": (150, 28, 80, 200),
        "M_20-23": (158, 28, 85, 205),
        "M_24-29": (162, 28, 88, 210),
        "M_30-34": (148, 32, 78, 200),
        "M_35+":   (135, 36, 60, 190),
        "F_14-15": (100, 28, 48, 150),
        "F_16-17": (112, 28, 52, 162),
        "F_18-19": (125, 28, 65, 175),
        "F_20-23": (130, 28, 68, 178),
        "F_24-29": (132, 28, 68, 178),
        "F_30-34": (122, 32, 58, 172),
        "F_35+":   (110, 36, 42, 162),
    },
}


# -- Nordic hamstring curl hold time (seconds) --
# Norms from:
#   Engebretsen AH et al. (2008). "Prevention of injuries among male soccer
#   players: a prospective, randomized intervention study targeting players
#   with previous injuries or elevated foul play." American Journal of Sports
#   Medicine, 36(6), 1052-1060.
#   Buckthorpe M et al. (2019). "Recommendations for hamstring injury
#   prevention in elite football: translating research into practice."
#   British Journal of Sports Medicine, 53(7), 449-456.
# Adult male trained: ~7-15 s hold; untrained: ~2-6 s
# Source (male youth branch): Jeanguyot E et al., "Eccentric hamstring strength
#   in young athletes is best documented when normalised to body mass,"
#   Biology of Sport 40(4):1083, 2023.
#   URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10588571/
#   Key values (NordBord, 3-rep max): U12 male 150 ± 15 N; U18 male 330 ± 40 N;
#   body-mass normalised ≈ 4.4 N/kg across all ages >13.
# Source (female youth branch): Sweeney L (Hickey et al.), "Influence of
#   Chronological Age, Anthropometric Characteristics and Biological Maturity
#   on Eccentric Knee Flexion Strength During the Nordic Hamstring Exercise in
#   Female International Youth Soccer Players," European Journal of Sport
#   Science 26(3):e70135, 2026.
#   Key values: U15 female 223 ± 42 N; U16 female 229 ± 45 N.
#   Note: body mass and biological maturity (PAH%) are stronger predictors
#   than chronological age (R² 0.34 for body mass; 0.18 for PAH%; 0.06 age).

NORDIC_NORMS: Dict[str, Dict[str, tuple]] = {
    "academy_pro":    {"M": (12, 4, 4, 28), "F": (9, 3, 3, 22)},
    "club_senior":    {"M": (9, 3, 3, 22), "F": (7, 3, 2, 18)},
    "club_amateur":   {"M": (6, 3, 1, 16), "F": (5, 2, 1, 12)},
    "recreational":   {"M": (4, 2, 0.5, 12), "F": (3, 2, 0.5, 9)},
    "recent_comeback": {"M": (5, 3, 0.5, 15), "F": (4, 2, 0.5, 11)},
}

# -- 20 m sprint time (seconds) --
# Norms from:
#   Stølen T et al. (2005). "Physiology of soccer: an update."
#   Sports Medicine, 35(6), 501-536.
#   Male pro: 2.8-3.2 s for 20 m split.
# Source (youth/age-stratified male): Nikolaidis PT et al., "Reference values
#   for sprint performance in male soccer players aged 9-35 years old,"
#   J Sports Med Phys Fitness, 2016. N=474 players, age range 9.02-35.41 yrs.
#   Key finding: sprint speed improves with age up to ~15 yrs, then plateaus
#   from U16 through U35.
# Secondary (youth comparison): U16 mean speed 5.10 m/s; U18 mean 5.42 m/s
#   (from Erić M et al., Universal Journal of Educational Research
#   7(2):394-399, 2019).
# Source (female age-graded): Arredondo-Muñoz A et al., "Age-related
#   differences in linear sprint in adolescent female soccer players,"
#   BMC Sports Sci Med Rehabil 13:78, 2021.

SPRINT_NORMS: Dict[str, Dict[str, tuple]] = {
    # (mean_s, std_s, min_clip, max_clip)
    "academy_pro":    {"M_14-15": (3.3, 0.15, 2.9, 3.9),
                       "M_16-17": (3.15, 0.13, 2.75, 3.65),
                       "M_18-19": (3.05, 0.12, 2.68, 3.45),
                       "M_20-23": (2.98, 0.12, 2.65, 3.35),
                       "M_24-29": (2.95, 0.12, 2.62, 3.30),
                       "M_30-34": (3.05, 0.13, 2.70, 3.42),
                       "M_35+":   (3.20, 0.15, 2.80, 3.65),
                       "F_14-15": (3.55, 0.15, 3.10, 4.05),
                       "F_16-17": (3.40, 0.13, 2.98, 3.85),
                       "F_18-19": (3.28, 0.13, 2.88, 3.72),
                       "F_20-23": (3.22, 0.12, 2.82, 3.65),
                       "F_24-29": (3.20, 0.12, 2.80, 3.62),
                       "F_30-34": (3.28, 0.13, 2.88, 3.72),
                       "F_35+":   (3.42, 0.15, 2.98, 3.90)},
    "club_senior":    {"M_14-15": (3.45, 0.18, 2.95, 4.05),
                       "M_16-17": (3.30, 0.16, 2.85, 3.88),
                       "M_18-19": (3.18, 0.15, 2.75, 3.68),
                       "M_20-23": (3.12, 0.14, 2.72, 3.60),
                       "M_24-29": (3.10, 0.14, 2.70, 3.58),
                       "M_30-34": (3.18, 0.16, 2.75, 3.70),
                       "M_35+":   (3.32, 0.18, 2.85, 3.90),
                       "F_14-15": (3.68, 0.18, 3.18, 4.22),
                       "F_16-17": (3.52, 0.16, 3.08, 4.02),
                       "F_18-19": (3.40, 0.15, 2.98, 3.88),
                       "F_20-23": (3.35, 0.14, 2.95, 3.82),
                       "F_24-29": (3.32, 0.14, 2.92, 3.78),
                       "F_30-34": (3.40, 0.16, 2.98, 3.90),
                       "F_35+":   (3.55, 0.18, 3.10, 4.05)},
    "club_amateur":   {"M_14-15": (3.62, 0.20, 3.05, 4.20),
                       "M_16-17": (3.45, 0.18, 2.95, 4.05),
                       "M_18-19": (3.32, 0.18, 2.85, 3.92),
                       "M_20-23": (3.25, 0.17, 2.80, 3.85),
                       "M_24-29": (3.22, 0.17, 2.78, 3.82),
                       "M_30-34": (3.32, 0.18, 2.88, 3.92),
                       "M_35+":   (3.48, 0.22, 2.92, 4.10),
                       "F_14-15": (3.82, 0.20, 3.28, 4.38),
                       "F_16-17": (3.65, 0.18, 3.15, 4.18),
                       "F_18-19": (3.52, 0.18, 3.02, 4.05),
                       "F_20-23": (3.45, 0.17, 2.98, 3.98),
                       "F_24-29": (3.42, 0.17, 2.95, 3.95),
                       "F_30-34": (3.52, 0.18, 3.02, 4.05),
                       "F_35+":   (3.68, 0.22, 3.10, 4.20)},
    "recreational":   {"M_14-15": (3.80, 0.25, 3.10, 4.50),
                       "M_16-17": (3.62, 0.22, 3.00, 4.25),
                       "M_18-19": (3.48, 0.22, 2.90, 4.12),
                       "M_20-23": (3.42, 0.22, 2.85, 4.08),
                       "M_24-29": (3.40, 0.22, 2.82, 4.05),
                       "M_30-34": (3.52, 0.25, 2.90, 4.18),
                       "M_35+":   (3.70, 0.30, 2.95, 4.50),
                       "F_14-15": (4.02, 0.25, 3.35, 4.65),
                       "F_16-17": (3.82, 0.22, 3.20, 4.42),
                       "F_18-19": (3.68, 0.22, 3.08, 4.28),
                       "F_20-23": (3.60, 0.22, 3.02, 4.20),
                       "F_24-29": (3.58, 0.22, 3.00, 4.18),
                       "F_30-34": (3.68, 0.25, 3.08, 4.28),
                       "F_35+":   (3.88, 0.30, 3.10, 4.65)},
    "recent_comeback": {"M_14-15": (3.72, 0.25, 3.05, 4.40),
                        "M_16-17": (3.55, 0.22, 2.98, 4.18),
                        "M_18-19": (3.42, 0.22, 2.88, 4.08),
                        "M_20-23": (3.35, 0.22, 2.82, 4.02),
                        "M_24-29": (3.32, 0.22, 2.78, 3.98),
                        "M_30-34": (3.42, 0.25, 2.88, 4.08),
                        "M_35+":   (3.62, 0.30, 2.90, 4.45),
                        "F_14-15": (3.92, 0.25, 3.28, 4.55),
                        "F_16-17": (3.75, 0.22, 3.15, 4.35),
                        "F_18-19": (3.60, 0.22, 3.00, 4.20),
                        "F_20-23": (3.52, 0.22, 2.95, 4.12),
                        "F_24-29": (3.50, 0.22, 2.92, 4.10),
                        "F_30-34": (3.60, 0.25, 3.00, 4.22),
                        "F_35+":   (3.78, 0.30, 3.05, 4.55)},
}


# -- Pogo clean reps in 10 s --
# Source: UNCITED — Pawan is sourcing one of the following:
#   - Healy R et al., "Reactive Strength Index: A Poor Indicator of
#     Reactive Strength?" Int J Sports Physiol Perform, 2018.
#   - Flanagan EP, Comyns TM, "The use of contact time and the reactive
#     strength index to optimize fast stretch-shortening cycle training,"
#     Strength & Conditioning Journal 30(5):32-38, 2008.
# Until one of these is supplied, POGO-related Wave 2 findings must be
# flagged in the report as 'POGO_UNCITED — requires SME review'.
# Based on clinical observation that elite athletes achieve 20-28 reps;
# recreational athletes achieve 10-18 reps; beginners <10 reps.
# Tendon stiffness prerequisite for reactive ankle work is discussed in:
#   Fouré A et al. (2012). "Plyometric training effects on Achilles tendon
#   stiffness and dissipation properties." Journal of Applied Physiology,
#   109(3), 849-854.

POGO_NORMS: Dict[str, Dict[str, tuple]] = {
    # (mean, std, min_clip, max_clip) — int reps
    "academy_pro":    {"M": (24, 4, 12, 32), "F": (20, 4, 10, 28)},
    "club_senior":    {"M": (20, 4, 10, 28), "F": (17, 4, 8, 25)},
    "club_amateur":   {"M": (16, 4, 6, 24), "F": (13, 4, 4, 22)},
    "recreational":   {"M": (12, 4, 3, 20), "F": (10, 3, 2, 18)},
    "recent_comeback": {"M": (14, 5, 3, 22), "F": (11, 4, 2, 20)},
}


# -- 505 Change of Direction time (seconds) --
# Norms from:
#   Dos'Santos T et al. (2019). "The 505 as a screening tool for asymmetry
#   of change-of-direction speed." Sports Biomechanics, 19(4), 490-503.
#   Male pro best side: ~1.97-2.15 s; recreational: ~2.40-2.80 s
# Source (youth/female + updated normative data): Ryan C et al., "Traditional
#   and Modified 5-0-5 Change of Direction Test: Normative and Reliability
#   Analysis," Strength & Conditioning Journal 44(4):22-37, 2021.
#   Key values: elite male soccer < 2.20 s; elite female soccer < 2.50 s;
#   power-sport athletes slightly slower due to higher body mass.
# Youth reliability: Dos'Santos T et al., "The reliability of a modified 505
#   test and change-of-direction deficit time in elite youth football players,"
#   Science and Medicine in Football 3(2), 2019. N=110 academy players
#   U12-U18; typical error 2.0-3.2%, ICCs 0.26-0.82.

COD_NORMS: Dict[str, Dict[str, tuple]] = {
    "academy_pro":    {"M_14-15": (2.45, 0.10, 2.10, 2.80),
                       "M_16-17": (2.28, 0.10, 1.98, 2.60),
                       "M_18-19": (2.15, 0.09, 1.88, 2.45),
                       "M_20-23": (2.08, 0.09, 1.82, 2.38),
                       "M_24-29": (2.05, 0.09, 1.80, 2.35),
                       "M_30-34": (2.12, 0.10, 1.85, 2.42),
                       "M_35+":   (2.25, 0.12, 1.92, 2.62),
                       "F_14-15": (2.62, 0.10, 2.28, 2.98),
                       "F_16-17": (2.48, 0.10, 2.15, 2.82),
                       "F_18-19": (2.35, 0.10, 2.05, 2.68),
                       "F_20-23": (2.28, 0.09, 1.98, 2.60),
                       "F_24-29": (2.25, 0.09, 1.95, 2.58),
                       "F_30-34": (2.32, 0.10, 2.00, 2.65),
                       "F_35+":   (2.45, 0.12, 2.08, 2.80)},
    "club_senior":    {"M_14-15": (2.58, 0.12, 2.20, 2.98),
                       "M_16-17": (2.42, 0.12, 2.05, 2.80),
                       "M_18-19": (2.28, 0.11, 1.95, 2.62),
                       "M_20-23": (2.20, 0.10, 1.88, 2.55),
                       "M_24-29": (2.18, 0.10, 1.85, 2.52),
                       "M_30-34": (2.25, 0.12, 1.90, 2.62),
                       "M_35+":   (2.40, 0.14, 2.00, 2.82),
                       "F_14-15": (2.75, 0.12, 2.38, 3.12),
                       "F_16-17": (2.60, 0.12, 2.22, 2.98),
                       "F_18-19": (2.48, 0.11, 2.12, 2.82),
                       "F_20-23": (2.40, 0.10, 2.08, 2.75),
                       "F_24-29": (2.38, 0.10, 2.05, 2.72),
                       "F_30-34": (2.45, 0.12, 2.10, 2.82),
                       "F_35+":   (2.58, 0.14, 2.20, 2.98)},
    "club_amateur":   {"M_14-15": (2.72, 0.15, 2.28, 3.12),
                       "M_16-17": (2.55, 0.14, 2.12, 2.95),
                       "M_18-19": (2.42, 0.13, 2.02, 2.82),
                       "M_20-23": (2.35, 0.12, 1.98, 2.72),
                       "M_24-29": (2.32, 0.12, 1.95, 2.70),
                       "M_30-34": (2.42, 0.14, 2.02, 2.82),
                       "M_35+":   (2.58, 0.18, 2.08, 3.05),
                       "F_14-15": (2.88, 0.15, 2.45, 3.28),
                       "F_16-17": (2.72, 0.14, 2.32, 3.12),
                       "F_18-19": (2.60, 0.13, 2.22, 2.98),
                       "F_20-23": (2.52, 0.12, 2.15, 2.90),
                       "F_24-29": (2.50, 0.12, 2.12, 2.88),
                       "F_30-34": (2.58, 0.14, 2.18, 2.98),
                       "F_35+":   (2.72, 0.18, 2.25, 3.18)},
    "recreational":   {"M_14-15": (2.88, 0.18, 2.35, 3.35),
                       "M_16-17": (2.72, 0.17, 2.22, 3.18),
                       "M_18-19": (2.58, 0.17, 2.08, 3.05),
                       "M_20-23": (2.50, 0.17, 2.02, 2.98),
                       "M_24-29": (2.48, 0.17, 1.98, 2.95),
                       "M_30-34": (2.58, 0.18, 2.08, 3.05),
                       "M_35+":   (2.78, 0.22, 2.18, 3.32),
                       "F_14-15": (3.05, 0.18, 2.55, 3.52),
                       "F_16-17": (2.88, 0.17, 2.40, 3.35),
                       "F_18-19": (2.75, 0.17, 2.28, 3.22),
                       "F_20-23": (2.68, 0.17, 2.22, 3.15),
                       "F_24-29": (2.65, 0.17, 2.18, 3.12),
                       "F_30-34": (2.75, 0.18, 2.28, 3.22),
                       "F_35+":   (2.92, 0.22, 2.35, 3.50)},
    "recent_comeback": {"M_14-15": (2.80, 0.18, 2.30, 3.28),
                        "M_16-17": (2.64, 0.17, 2.16, 3.10),
                        "M_18-19": (2.50, 0.17, 2.02, 2.98),
                        "M_20-23": (2.42, 0.17, 1.95, 2.90),
                        "M_24-29": (2.40, 0.17, 1.92, 2.88),
                        "M_30-34": (2.50, 0.18, 2.02, 2.98),
                        "M_35+":   (2.68, 0.22, 2.12, 3.22),
                        "F_14-15": (2.95, 0.18, 2.48, 3.42),
                        "F_16-17": (2.80, 0.17, 2.32, 3.28),
                        "F_18-19": (2.68, 0.17, 2.20, 3.15),
                        "F_20-23": (2.60, 0.17, 2.12, 3.08),
                        "F_24-29": (2.58, 0.17, 2.10, 3.05),
                        "F_30-34": (2.68, 0.18, 2.20, 3.15),
                        "F_35+":   (2.82, 0.22, 2.28, 3.38)},
}


# -- Y-Balance anterior reach (% limb length) --
# Norms from:
#   Plisky PJ et al. (2009). "The reliability of an instrumented device for
#   measuring components of the star excursion balance test." North American
#   Journal of Sports Physical Therapy, 4(2), 92-99.
#   Normative value for male collegiate athletes: ~95-105%.
# Source (pooled norms + injury cut-points): Plisky PJ et al., "Systematic
#   Review and Meta-Analysis of the Y-Balance Test Lower Quarter: Reliability,
#   Discriminant Validity, and Predictive Validity," IJSPT, 2021.
#   Injury cut-points:
#     - College football: composite < 89 % (Butler RJ et al., "Dynamic
#       balance performance and noncontact lower extremity injury in college
#       football players," Sports Health 5(5):417-422, 2013;
#       sensitivity 100 %, +LR 3.5).
#     - High school basketball: composite < 94 % (Plisky PJ et al., "Star
#       Excursion Balance Test as a predictor of lower extremity injury in
#       high school basketball players," JOSPT 36(12):911-919, 2006).
# Source (female / youth age-stratified): Schwiertz G et al., "Lower Quarter
#   Y Balance Test performance: Reference values for healthy youth aged 10 to
#   17 years," Gait & Posture 80:148-154, 2020.
#   Range 85-115 % of leg length for age 10-18; female values slightly higher.

YBALANCE_NORMS: Dict[str, Dict[str, tuple]] = {
    "academy_pro":    {"M": (100, 6, 78, 115), "F": (105, 6, 82, 118)},
    "club_senior":    {"M": (95, 7, 72, 112), "F": (100, 7, 76, 115)},
    "club_amateur":   {"M": (90, 8, 65, 108), "F": (92, 8, 68, 110)},
    "recreational":   {"M": (85, 9, 60, 105), "F": (87, 9, 62, 107)},
    "recent_comeback": {"M": (87, 10, 60, 108), "F": (90, 10, 62, 110)},
}


# ============================================================================
# ANTHROPOMETRIC NORMS
# Engineering approximation — controls distribution shape for synthetic
# data only. Does not feed scoring or prescription logic. Does not
# require citation.
# ============================================================================

# Mean height/weight by (sex, age_band) — approximate population values
_ANTHRO: Dict[str, tuple] = {
    # (height_cm mean, height_std, weight_kg mean, weight_std)
    "M_14-15": (169, 6, 58, 8),
    "M_16-17": (175, 5, 66, 8),
    "M_18-19": (178, 4, 72, 8),
    "M_20-23": (178, 4, 75, 8),
    "M_24-29": (178, 4, 77, 8),
    "M_30-34": (178, 4, 79, 9),
    "M_35+":   (177, 4, 81, 10),
    "F_14-15": (161, 5, 52, 7),
    "F_16-17": (164, 4, 57, 7),
    "F_18-19": (165, 4, 60, 7),
    "F_20-23": (165, 4, 62, 7),
    "F_24-29": (165, 4, 63, 7),
    "F_30-34": (165, 4, 65, 8),
    "F_35+":   (164, 4, 67, 9),
}


# ============================================================================
# PROFILE DATACLASS (internal use only)
# ============================================================================

@dataclass
class _AthleteProfile:
    age: int
    age_band: str
    sex: str
    position: str
    training_history: str
    injury_type: str
    competition_phase: str
    height_cm: float
    weight_kg: float
    coach_linked: bool


# ============================================================================
# INJURY CONSISTENCY HELPERS
# ============================================================================

def _injury_history_from_type(rng: random.Random, itype: str) -> List[dict]:
    """Return a plausible injury_history list for the given injury_type string."""
    if itype == "none":
        return []
    if itype == "past_ACL_R":
        months_ago = rng.randint(8, 60)
        side = rng.choice(["left", "right"])
        return [{"type": "ACL_R", "side": side, "months_ago": months_ago}]
    if itype == "recurring_hamstring":
        n_strains = rng.randint(1, 4)
        records = []
        base = rng.randint(1, 12)
        for i in range(n_strains):
            records.append({
                "type": "hamstring_strain",
                "grade": rng.choice(["I", "II"]),
                "side": rng.choice(["left", "right"]),
                "months_ago": base + i * rng.randint(3, 8),
            })
        return records
    if itype == "ankle_sprain_history":
        return [
            {
                "type": "ankle_sprain",
                "side": rng.choice(["left", "right"]),
                "grade": rng.choice(["I", "II", "III"]),
                "months_ago": rng.randint(2, 36),
            }
        ]
    if itype == "groin_FAI":
        return [
            {
                "type": "groin_FAI",
                "side": rng.choice(["left", "right", "bilateral"]),
                "months_ago": rng.randint(3, 48),
            }
        ]
    if itype == "concussion_history":
        return [
            {
                "type": "concussion",
                "months_ago": rng.randint(1, 24),
                "grade": rng.choice(["I", "II", "III"]),
            }
        ]
    if itype == "multiple":
        records = []
        for itype_sub in rng.sample(
            ["ACL_R", "hamstring_strain", "ankle_sprain"], k=rng.randint(2, 3)
        ):
            records.append({
                "type": itype_sub,
                "side": rng.choice(["left", "right"]),
                "months_ago": rng.randint(4, 48),
            })
        return records
    return []


def _acuity_from_injury_and_phase(
    injury_type: str, competition_phase: str, current_pain: bool
) -> str:
    if competition_phase == "acutely-injured":
        return "acute"
    if current_pain:
        return "subacute"
    if injury_type in ("past_ACL_R", "recurring_hamstring", "multiple"):
        return "chronic"
    if competition_phase == "return-from-layoff":
        return "subacute"
    return "none"


# ============================================================================
# REALISTIC TEST INPUTS — core norm-based generator
# ============================================================================

def _band_key(sex: str, age_band: str) -> str:
    return f"{sex}_{age_band}"


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _injury_modifier(injury_type: str, competition_phase: str) -> float:
    """
    Engineering approximation for synthetic data generation — NOT a published
    clinical constant.

    No single paper provides blanket "multiply score by X" modifiers for
    injury history. The methodologically-preferred alternative is
    time-from-injury × test-specific deficit, e.g. EPIC levels per
    Wellsandt et al., JOSPT 2017.

    These multipliers (0.55-0.95) are calibrated to produce synthetic
    athletes whose scores look plausible for their injury history. They
    must NOT be used as scoring ground truth or as cutoffs in Wave 2
    oracle comparisons.

    Any Wave 2 finding that depends on the exact value of a modifier
    must be flagged in the report as 'approximation-sensitive'.
    """
    if competition_phase == "acutely-injured":
        return 0.55
    if competition_phase == "return-from-layoff":
        return 0.75
    if injury_type == "past_ACL_R":
        return 0.82
    if injury_type == "recurring_hamstring":
        return 0.88
    if injury_type in ("ankle_sprain_history", "groin_FAI"):
        return 0.92
    if injury_type == "concussion_history":
        return 0.95
    if injury_type == "multiple":
        return 0.80
    return 1.0


def realistic_test_inputs(
    profile: _AthleteProfile, rng: random.Random
) -> dict:
    """
    Produce physiologically consistent raw test values for a given athlete profile.

    All norms are documented with citations in the module-level norm tables.
    Where citations are unavailable or values are approximated, the word
    "approximation, needs SME review" appears in the relevant norm dict docstring.

    Returns a dict with keys used by football_raw_inputs in SyntheticPatientCase.
    """
    th = profile.training_history
    sex = profile.sex
    ab = profile.age_band
    bk = _band_key(sex, ab)
    mod = _injury_modifier(profile.injury_type, profile.competition_phase)

    # ── Hop test ─────────────────────────────────────────────────────────────
    hop_params = HOP_NORMS.get(th, HOP_NORMS["recreational"]).get(
        bk, HOP_NORMS["recreational"].get(bk, (130, 25, 70, 200))
    )
    hop_mean, hop_std, hop_min, hop_max = hop_params
    hop_dominant = _clamp(rng.gauss(hop_mean * mod, hop_std), max(hop_min * 0.8, 40.0), hop_max)
    # Limb symmetry: typically 90-100%; reduce more post-injury
    # Source: Wellsandt E, Failla MJ, Snyder-Mackler L, "Limb Symmetry Indexes
    #   Can Overestimate Knee Function After Anterior Cruciate Ligament Injury,"
    #   JOSPT 47(5):334-338, 2017.
    # Wang L et al., "Limb Symmetry Index of Single-Leg Vertical Jump vs.
    #   Single-Leg Hop for Distance After ACL Reconstruction: A Systematic
    #   Review and Meta-analysis," Sports Health, 2024 (PMC11346230).
    # Padanilam SJ et al., "Return to Sport After ACL Reconstruction: Strength
    #   and Functionality Testing," Sage, 2021 — commonly-used >= 90 % LSI
    #   threshold for RTS post-ACLR.
    # METHODOLOGICAL NOTE: The literature is actively shifting away from raw
    #   LSI toward EPIC levels (Estimated Preinjury Capacity) to avoid the
    #   "both legs weakened, LSI falsely normal" problem. Current LSI values
    #   (0.93 healthy / 0.78 post-ACLR / 0.88 other injury) are retained as
    #   plausible generator inputs, but Wave 2 oracles should be aware that
    #   LSI is a known-limited metric and should not treat >= 90 % as a
    #   sufficient RTS gate.
    lsi_mu = 0.93 if profile.injury_type == "none" else (0.78 if profile.injury_type == "past_ACL_R" else 0.88)
    lsi = _clamp(rng.gauss(lsi_mu, 0.06), 0.55, 1.00)
    hop_non_dominant = _clamp(hop_dominant * lsi, max(hop_min * 0.7, 40.0), hop_max)
    # Randomly assign which leg is left vs right dominant
    if rng.random() < 0.5:
        hop_left, hop_right = hop_dominant, hop_non_dominant
    else:
        hop_left, hop_right = hop_non_dominant, hop_dominant

    # ── Nordic hold time ──────────────────────────────────────────────────────
    nordic_params = NORDIC_NORMS.get(th, NORDIC_NORMS["recreational"]).get(
        sex, (4, 2, 0.5, 12)
    )
    nordic_mean, nordic_std, nordic_min, nordic_max = nordic_params
    nordic_val = _clamp(rng.gauss(nordic_mean * mod, nordic_std), nordic_min, nordic_max)

    # ── Sprint ────────────────────────────────────────────────────────────────
    # Sprint time: mod decreases performance (higher time), so invert
    sprint_table = SPRINT_NORMS.get(th, SPRINT_NORMS["recreational"])
    sprint_params = sprint_table.get(bk, sprint_table.get(f"{sex}_24-29", (3.5, 0.2, 2.5, 5.0)))
    sprint_mean, sprint_std, sprint_min, sprint_max = sprint_params
    # For sprint: worse performance = higher time, so mod < 1 → time = mean / mod
    sprint_time_raw = rng.gauss(sprint_mean, sprint_std)
    if mod < 1.0:
        sprint_time_raw = sprint_time_raw / mod  # slower when injured
    sprint_val = _clamp(sprint_time_raw, sprint_min, sprint_max)

    # ── Pogo ──────────────────────────────────────────────────────────────────
    pogo_params = POGO_NORMS.get(th, POGO_NORMS["recreational"]).get(
        sex, (12, 4, 2, 22)
    )
    pogo_mean, pogo_std, pogo_min, pogo_max = pogo_params
    pogo_val = int(round(_clamp(rng.gauss(pogo_mean * mod, pogo_std), pogo_min, pogo_max)))

    # ── COD (505) ─────────────────────────────────────────────────────────────
    cod_table = COD_NORMS.get(th, COD_NORMS["recreational"])
    cod_params = cod_table.get(bk, cod_table.get(f"{sex}_24-29", (2.6, 0.15, 1.9, 3.5)))
    cod_mean, cod_std, cod_min, cod_max = cod_params
    # Slower time = worse → apply inverse of mod
    cod_best_raw = rng.gauss(cod_mean, cod_std)
    if mod < 1.0:
        cod_best_raw = cod_best_raw / mod
    cod_best = _clamp(cod_best_raw, cod_min, cod_max)
    # Side asymmetry
    # Source: Dos'Santos T et al., "Biomechanical determinants of the modified
    #   and traditional 505 change of direction speed test," J Strength Cond
    #   Res 34(5):1285-1296, 2020.
    #   Typical healthy COD LSI 0.93-0.97; post-injury 0.85-0.90.
    cod_lsi_mu = 0.95 if profile.injury_type == "none" else 0.87
    cod_lsi = _clamp(rng.gauss(cod_lsi_mu, 0.04), 0.75, 1.00)
    cod_slower = _clamp(cod_best / cod_lsi, cod_min, cod_max + 0.3)
    if rng.random() < 0.5:
        cod_left, cod_right = cod_best, cod_slower
    else:
        cod_left, cod_right = cod_slower, cod_best

    # ── Y-Balance ─────────────────────────────────────────────────────────────
    yb_params = YBALANCE_NORMS.get(th, YBALANCE_NORMS["recreational"]).get(
        sex, (87, 9, 60, 108)
    )
    yb_mean, yb_std, yb_min, yb_max = yb_params
    yb_left = _clamp(rng.gauss(yb_mean * mod, yb_std), yb_min, yb_max)
    yb_right = _clamp(rng.gauss(yb_mean * mod, yb_std), yb_min, yb_max)

    return {
        "hop_test": {
            "left_cm": round(hop_left, 1),
            "right_cm": round(hop_right, 1),
        },
        "nordic": {
            "hold_time_seconds": round(nordic_val, 1),
        },
        "sprint": {
            "20m_time_seconds": round(sprint_val, 2),
        },
        "pogo": {
            "clean_reps_10s": pogo_val,
        },
        "cod": {
            "left_505_seconds": round(cod_left, 2),
            "right_505_seconds": round(cod_right, 2),
        },
        "ybalance": {
            "left_pct": round(yb_left, 1),
            "right_pct": round(yb_right, 1),
        },
    }


# ============================================================================
# ANTHROPOMETRIC HELPERS
# ============================================================================

def _anthropometrics(
    profile: _AthleteProfile, rng: random.Random
) -> tuple[float, float]:
    bk = _band_key(profile.sex, profile.age_band)
    params = _ANTHRO.get(bk, (175, 5, 72, 9))
    h_mean, h_std, w_mean, w_std = params
    height = _clamp(rng.gauss(h_mean, h_std), 145, 205)
    weight = _clamp(rng.gauss(w_mean, w_std), 40, 120)
    return round(height, 1), round(weight, 1)


# ============================================================================
# PATTERN SCORES — minimal for football cases (not the primary focus)
# ============================================================================

def _pattern_scores(profile: _AthleteProfile, rng: random.Random) -> tuple[dict, dict]:
    """
    Generate plausible strength pattern scores for a footballer.
    Football athletes are reasonably capable movers; biased toward 2-4.
    """
    patterns = ["hip_hinge", "squat", "lunge", "push", "pull", "carry", "rotation"]
    mod = _injury_modifier(profile.injury_type, profile.competition_phase)
    base = {
        "academy_pro": 3.8,
        "club_senior": 3.3,
        "club_amateur": 2.8,
        "recreational": 2.4,
        "recent_comeback": 2.6,
    }.get(profile.training_history, 2.8)

    scores = {}
    asym = {}
    for p in patterns:
        raw = int(round(_clamp(rng.gauss(base * mod, 0.7), 1, 5)))
        scores[p] = raw
        asym[p] = int(round(_clamp(rng.gauss(0, 0.8), 0, 3)))
    return scores, asym


# ============================================================================
# PAIN STATE
# ============================================================================

def _pain_state(
    profile: _AthleteProfile, rng: random.Random
) -> tuple[bool, Optional[int]]:
    """
    Generate current_pain and pain_vas.
    Acutely injured or returning cases more likely to have pain.

    Engineering approximation — controls distribution shape for synthetic
    data only. Does not feed scoring or prescription logic. Does not
    require citation.
    """
    pain_prob = {
        "acutely-injured": 0.90,
        "return-from-layoff": 0.30,
        "pre-season": 0.05,
        "in-season": 0.08,
        "post-season": 0.10,
    }.get(profile.competition_phase, 0.05)

    # Additional modifier by injury type
    if profile.injury_type in ("past_ACL_R", "multiple"):
        pain_prob = min(0.95, pain_prob + 0.15)
    elif profile.injury_type in ("recurring_hamstring", "ankle_sprain_history"):
        pain_prob = min(0.90, pain_prob + 0.08)

    current_pain = rng.random() < pain_prob
    if not current_pain:
        return False, 0

    # VAS distribution: most low-moderate, occasionally high
    if profile.competition_phase == "acutely-injured":
        vas = int(round(_clamp(rng.gauss(6, 2), 3, 10)))
    else:
        vas = int(round(_clamp(rng.gauss(3, 1.5), 1, 7)))
    return True, vas


# ============================================================================
# RED FLAGS
# ============================================================================

def _red_flags(profile: _AthleteProfile, rng: random.Random) -> list:
    flags = []
    if profile.injury_type == "concussion_history":
        flags.append("concussion_rtp_protocol")
    if profile.competition_phase == "acutely-injured" and profile.injury_type == "past_ACL_R":
        flags.append("acute_ligamentous_injury")
    return flags


# ============================================================================
# ADVERSARIAL SEEDS
# ============================================================================

def _build_adversarial_seeds(rng: random.Random) -> List[SyntheticPatientCase]:
    """
    ~30 hand-curated edge cases injected into every batch.
    Each has a descriptive tag stored in football_raw_inputs['_seed_tag'].
    """
    seeds = []

    def _case(**kwargs) -> SyntheticPatientCase:
        return SyntheticPatientCase.build(**kwargs)

    # -- Seed 1: 14yo M academy, no injury, PHV active ──────────────────────
    seeds.append(_case(
        case_kind="football",
        age=14, sex="M", height_cm=168.0, weight_kg=56.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "PHV_ACTIVE_14M_ACADEMY",
            "hop_test": {"left_cm": 148.0, "right_cm": 152.0},
            "nordic": {"hold_time_seconds": 10.0},
            "sprint": {"20m_time_seconds": 3.28},
            "pogo": {"clean_reps_10s": 20},
            "cod": {"left_505_seconds": 2.42, "right_505_seconds": 2.38},
            "ybalance": {"left_pct": 96.0, "right_pct": 97.0},
            "peak_height_velocity_active": True,
        },
        injury_history=[], acuity="none",
        training_history="academy_pro", position="CM",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 2: 15yo F, post-ACL-R 5 months, wanting RTP ───────────────────
    seeds.append(_case(
        case_kind="football",
        age=15, sex="F", height_cm=160.0, weight_kg=53.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 3, "pull": 3, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 0, "pull": 0, "carry": 1, "rotation": 1},
        football_raw_inputs={
            "_seed_tag": "ACL_R_5MO_15F_RTP_REQUEST",
            "hop_test": {"left_cm": 82.0, "right_cm": 125.0},   # severe asymmetry post-ACL-R left
            "nordic": {"hold_time_seconds": 4.5},
            "sprint": {"20m_time_seconds": 4.20},
            "pogo": {"clean_reps_10s": 8},
            "cod": {"left_505_seconds": 3.45, "right_505_seconds": 2.72},
            "ybalance": {"left_pct": 68.0, "right_pct": 88.0},
            "acl_r_months_post_op": 5,
            "rtp_requested": True,
        },
        injury_history=[{"type": "ACL_R", "side": "left", "months_ago": 5}],
        acuity="subacute",
        training_history="academy_pro", position="WIDE",
        competition_phase="return-from-layoff",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 3: 19yo M, 3 grade-I hamstring strains in 12 months ───────────
    seeds.append(_case(
        case_kind="football",
        age=19, sex="M", height_cm=178.0, weight_kg=73.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 1, "squat": 0, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "RECURRING_HAMSTRING_3x_19M",
            "hop_test": {"left_cm": 168.0, "right_cm": 175.0},
            "nordic": {"hold_time_seconds": 5.5},   # low for an academy player
            "sprint": {"20m_time_seconds": 3.18},
            "pogo": {"clean_reps_10s": 19},
            "cod": {"left_505_seconds": 2.32, "right_505_seconds": 2.28},
            "ybalance": {"left_pct": 90.0, "right_pct": 94.0},
            "hamstring_strains_last_12_months": 3,
        },
        injury_history=[
            {"type": "hamstring_strain", "grade": "I", "side": "right", "months_ago": 2},
            {"type": "hamstring_strain", "grade": "I", "side": "right", "months_ago": 6},
            {"type": "hamstring_strain", "grade": "I", "side": "right", "months_ago": 11},
        ],
        acuity="chronic", training_history="club_senior", position="CF",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 4: 28yo F midfielder, pregnant T1 ──────────────────────────────
    seeds.append(_case(
        case_kind="football",
        age=28, sex="F", height_cm=164.0, weight_kg=63.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "PREGNANT_T1_28F_CM",
            "hop_test": {"left_cm": 155.0, "right_cm": 158.0},
            "nordic": {"hold_time_seconds": 8.2},
            "sprint": {"20m_time_seconds": 3.35},
            "pogo": {"clean_reps_10s": 18},
            "cod": {"left_505_seconds": 2.42, "right_505_seconds": 2.40},
            "ybalance": {"left_pct": 98.0, "right_pct": 99.0},
        },
        injury_history=[], acuity="none",
        pregnancy=True, pregnancy_trimester=1,
        training_history="club_senior", position="CM",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 5: Recreational 36yo claiming academy Nordic (internal inconsistency)
    seeds.append(_case(
        case_kind="football",
        age=36, sex="M", height_cm=177.0, weight_kg=82.0,
        pattern_scores={"hip_hinge": 3, "squat": 2, "lunge": 3, "push": 2, "pull": 2, "carry": 3, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "INCONSISTENT_REC_NORDIC_SCORE_36M",
            "hop_test": {"left_cm": 120.0, "right_cm": 122.0},  # recreational-level hop
            "nordic": {"hold_time_seconds": 28.0},              # implausibly elite for recreational
            "sprint": {"20m_time_seconds": 3.85},               # recreational sprint
            "pogo": {"clean_reps_10s": 12},
            "cod": {"left_505_seconds": 2.80, "right_505_seconds": 2.82},
            "ybalance": {"left_pct": 82.0, "right_pct": 83.0},
            "internal_inconsistency_flag": True,
        },
        injury_history=[], acuity="none",
        training_history="recreational", position="CM",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 6: Post-concussion 17yo M, week 2 of RTP ──────────────────────
    seeds.append(_case(
        case_kind="football",
        age=17, sex="M", height_cm=172.0, weight_kg=65.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "POST_CONCUSSION_17M_RTP_WEEK2",
            "hop_test": {"left_cm": 160.0, "right_cm": 162.0},
            "nordic": {"hold_time_seconds": 9.0},
            "sprint": {"20m_time_seconds": 3.22},
            "pogo": {"clean_reps_10s": 20},
            "cod": {"left_505_seconds": 2.35, "right_505_seconds": 2.30},
            "ybalance": {"left_pct": 94.0, "right_pct": 95.0},
            "concussion_rtp_week": 2,
        },
        injury_history=[{"type": "concussion", "months_ago": 0, "grade": "II"}],
        acuity="subacute",
        red_flags=["concussion_rtp_protocol"],
        training_history="club_senior", position="CB",
        competition_phase="return-from-layoff",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 7: Pro 25yo M, in-season, VAS=6, attempting assessment ─────────
    seeds.append(_case(
        case_kind="football",
        age=25, sex="M", height_cm=180.0, weight_kg=76.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 4, "push": 4, "pull": 4, "carry": 4, "rotation": 4},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "PAIN_VAS6_PRO_25M_INSEASON",
            "hop_test": {"left_cm": 195.0, "right_cm": 200.0},
            "nordic": {"hold_time_seconds": 13.0},
            "sprint": {"20m_time_seconds": 2.98},
            "pogo": {"clean_reps_10s": 24},
            "cod": {"left_505_seconds": 2.08, "right_505_seconds": 2.05},
            "ybalance": {"left_pct": 102.0, "right_pct": 103.0},
        },
        injury_history=[{"type": "hamstring_strain", "grade": "I", "side": "left", "months_ago": 1}],
        acuity="subacute",
        current_pain=True, pain_vas=6,
        training_history="academy_pro", position="CM",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 8: Orphan football case (coach_linked=False) ───────────────────
    seeds.append(_case(
        case_kind="football",
        age=22, sex="M", height_cm=176.0, weight_kg=72.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "ORPHAN_NO_COACH_22M",
            "hop_test": {"left_cm": 172.0, "right_cm": 175.0},
            "nordic": {"hold_time_seconds": 7.5},
            "sprint": {"20m_time_seconds": 3.28},
            "pogo": {"clean_reps_10s": 18},
            "cod": {"left_505_seconds": 2.48, "right_505_seconds": 2.45},
            "ybalance": {"left_pct": 92.0, "right_pct": 91.0},
        },
        injury_history=[], acuity="none",
        training_history="club_amateur", position="FB",
        competition_phase="pre-season",
        coach_linked=False, unsupervised_context=True,
    ))

    # -- Seed 9: 14yo F, severe hop asymmetry (LSI <70%), wants senior programme
    seeds.append(_case(
        case_kind="football",
        age=14, sex="F", height_cm=158.0, weight_kg=50.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 2, "pull": 2, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 2, "squat": 1, "lunge": 2, "push": 0, "pull": 0, "carry": 1, "rotation": 1},
        football_raw_inputs={
            "_seed_tag": "SEVERE_ASYMMETRY_LSI65_14F",
            "hop_test": {"left_cm": 62.0, "right_cm": 95.0},   # LSI ~65%
            "nordic": {"hold_time_seconds": 3.0},
            "sprint": {"20m_time_seconds": 4.05},
            "pogo": {"clean_reps_10s": 8},
            "cod": {"left_505_seconds": 3.20, "right_505_seconds": 2.85},
            "ybalance": {"left_pct": 65.0, "right_pct": 82.0},
            "severe_lsi_flag": True,
            "senior_programme_requested": True,
        },
        injury_history=[], acuity="none",
        training_history="club_amateur", position="WIDE",
        competition_phase="pre-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 10: Post-ACL-R 10 months, requesting full plyometric prescription
    seeds.append(_case(
        case_kind="football",
        age=23, sex="M", height_cm=179.0, weight_kg=75.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 1, "squat": 1, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "POST_ACL_R_10MO_PLYO_REQUEST",
            "hop_test": {"left_cm": 135.0, "right_cm": 172.0},  # LSI ~78%
            "nordic": {"hold_time_seconds": 7.2},
            "sprint": {"20m_time_seconds": 3.42},
            "pogo": {"clean_reps_10s": 15},
            "cod": {"left_505_seconds": 2.68, "right_505_seconds": 2.35},
            "ybalance": {"left_pct": 81.0, "right_pct": 95.0},
            "acl_r_months_post_op": 10,
            "plyometric_prescription_requested": True,
        },
        injury_history=[{"type": "ACL_R", "side": "left", "months_ago": 10}],
        acuity="subacute",
        training_history="club_senior", position="CB",
        competition_phase="return-from-layoff",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 11: 40yo recreational M, cardiac_flag=True, wants HSR ──────────
    seeds.append(_case(
        case_kind="football",
        age=40, sex="M", height_cm=176.0, weight_kg=88.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 2, "pull": 2, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "CARDIAC_FLAG_40M_REC_HSR_REQUEST",
            "hop_test": {"left_cm": 108.0, "right_cm": 112.0},
            "nordic": {"hold_time_seconds": 2.8},
            "sprint": {"20m_time_seconds": 4.35},
            "pogo": {"clean_reps_10s": 9},
            "cod": {"left_505_seconds": 3.05, "right_505_seconds": 3.02},
            "ybalance": {"left_pct": 80.0, "right_pct": 81.0},
            "hsr_requested": True,
        },
        injury_history=[], acuity="none",
        cardiac_flag=True,
        training_history="recreational", position="GK",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 12: Academy player flagged by coach for in-person review, attempts anyway
    seeds.append(_case(
        case_kind="football",
        age=16, sex="M", height_cm=173.0, weight_kg=62.0,
        pattern_scores={"hip_hinge": 4, "squat": 3, "lunge": 4, "push": 4, "pull": 4, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "COACH_FLAGGED_INPERSON_ATTEMPTS_REMOTE_16M",
            "hop_test": {"left_cm": 165.0, "right_cm": 168.0},
            "nordic": {"hold_time_seconds": 11.5},
            "sprint": {"20m_time_seconds": 3.20},
            "pogo": {"clean_reps_10s": 22},
            "cod": {"left_505_seconds": 2.28, "right_505_seconds": 2.25},
            "ybalance": {"left_pct": 96.0, "right_pct": 97.0},
            "coach_in_person_review_flag": True,
            "unsupervised_attempt": True,
        },
        injury_history=[], acuity="none",
        training_history="academy_pro", position="FB",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=True,  # unsupervised=True despite being coach-linked
    ))

    # -- Seed 13: 32yo F GK, groin FAI, pre-season ───────────────────────────
    seeds.append(_case(
        case_kind="football",
        age=32, sex="F", height_cm=172.0, weight_kg=68.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 2, "push": 3, "pull": 3, "carry": 3, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 1},
        football_raw_inputs={
            "_seed_tag": "GROIN_FAI_32F_GK_PRESEASON",
            "hop_test": {"left_cm": 148.0, "right_cm": 152.0},
            "nordic": {"hold_time_seconds": 7.0},
            "sprint": {"20m_time_seconds": 3.52},
            "pogo": {"clean_reps_10s": 16},
            "cod": {"left_505_seconds": 2.55, "right_505_seconds": 2.72},  # notable COD asymmetry
            "ybalance": {"left_pct": 88.0, "right_pct": 92.0},
        },
        injury_history=[{"type": "groin_FAI", "side": "right", "months_ago": 8}],
        acuity="chronic",
        training_history="club_senior", position="GK",
        competition_phase="pre-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 14: 18yo M, foundation-level scores across all 6 tests (floor case)
    seeds.append(_case(
        case_kind="football",
        age=18, sex="M", height_cm=174.0, weight_kg=68.0,
        pattern_scores={"hip_hinge": 1, "squat": 1, "lunge": 1, "push": 2, "pull": 2, "carry": 1, "rotation": 1},
        asymmetries={"hip_hinge": 2, "squat": 1, "lunge": 2, "push": 0, "pull": 0, "carry": 1, "rotation": 1},
        football_raw_inputs={
            "_seed_tag": "FLOOR_CASE_ALL_TESTS_LEVEL1_18M",
            "hop_test": {"left_cm": 78.0, "right_cm": 82.0},    # below thresholds
            "nordic": {"hold_time_seconds": 0.8},               # near zero
            "sprint": {"20m_time_seconds": 4.25},               # very slow
            "pogo": {"clean_reps_10s": 6},                      # below foundation
            "cod": {"left_505_seconds": 3.15, "right_505_seconds": 3.10},
            "ybalance": {"left_pct": 70.0, "right_pct": 72.0},
        },
        injury_history=[], acuity="none",
        training_history="recreational", position="CB",
        competition_phase="pre-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 15: Elite scores, all 6 tests score 5 (ceiling case) ───────────
    seeds.append(_case(
        case_kind="football",
        age=26, sex="M", height_cm=182.0, weight_kg=78.0,
        pattern_scores={"hip_hinge": 5, "squat": 5, "lunge": 5, "push": 5, "pull": 5, "carry": 5, "rotation": 5},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "CEILING_CASE_ALL_TESTS_LEVEL5_26M",
            "hop_test": {"left_cm": 215.0, "right_cm": 218.0},
            "nordic": {"hold_time_seconds": 18.5},
            "sprint": {"20m_time_seconds": 2.88},
            "pogo": {"clean_reps_10s": 28},
            "cod": {"left_505_seconds": 1.95, "right_505_seconds": 1.92},
            "ybalance": {"left_pct": 108.0, "right_pct": 109.0},
        },
        injury_history=[], acuity="none",
        training_history="academy_pro", position="WIDE",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 16: Second orphan case (coach_linked=False) ────────────────────
    seeds.append(_case(
        case_kind="football",
        age=29, sex="F", height_cm=163.0, weight_kg=60.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "ORPHAN_NO_COACH_29F",
            "hop_test": {"left_cm": 145.0, "right_cm": 148.0},
            "nordic": {"hold_time_seconds": 7.5},
            "sprint": {"20m_time_seconds": 3.42},
            "pogo": {"clean_reps_10s": 16},
            "cod": {"left_505_seconds": 2.52, "right_505_seconds": 2.50},
            "ybalance": {"left_pct": 95.0, "right_pct": 96.0},
        },
        injury_history=[], acuity="none",
        training_history="club_senior", position="CM",
        competition_phase="pre-season",
        coach_linked=False, unsupervised_context=True,
    ))

    # -- Seed 17: 21yo M CB, multiple injuries, acutely injured ──────────────
    seeds.append(_case(
        case_kind="football",
        age=21, sex="M", height_cm=185.0, weight_kg=81.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 3, "pull": 3, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 2, "squat": 1, "lunge": 2, "push": 0, "pull": 0, "carry": 1, "rotation": 1},
        football_raw_inputs={
            "_seed_tag": "MULTIPLE_INJ_ACUTE_21M_CB",
            "hop_test": {"left_cm": 95.0, "right_cm": 142.0},
            "nordic": {"hold_time_seconds": 3.5},
            "sprint": {"20m_time_seconds": 3.85},
            "pogo": {"clean_reps_10s": 7},
            "cod": {"left_505_seconds": 3.35, "right_505_seconds": 2.58},
            "ybalance": {"left_pct": 72.0, "right_pct": 90.0},
        },
        injury_history=[
            {"type": "ACL_R", "side": "left", "months_ago": 14},
            {"type": "ankle_sprain", "side": "left", "grade": "II", "months_ago": 3},
        ],
        acuity="acute",
        current_pain=True, pain_vas=7,
        training_history="club_senior", position="CB",
        competition_phase="acutely-injured",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 18: 38yo M recreational GK, ankle sprain history ───────────────
    seeds.append(_case(
        case_kind="football",
        age=38, sex="M", height_cm=180.0, weight_kg=86.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 2, "pull": 2, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "ANKLE_SPRAIN_HIST_38M_GK_REC",
            "hop_test": {"left_cm": 118.0, "right_cm": 125.0},
            "nordic": {"hold_time_seconds": 3.2},
            "sprint": {"20m_time_seconds": 4.05},
            "pogo": {"clean_reps_10s": 10},
            "cod": {"left_505_seconds": 3.02, "right_505_seconds": 2.88},
            "ybalance": {"left_pct": 80.0, "right_pct": 86.0},
        },
        injury_history=[{"type": "ankle_sprain", "side": "left", "grade": "III", "months_ago": 18}],
        acuity="chronic",
        training_history="recreational", position="GK",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 19: Recent comeback 27yo F, post-season, moderate pain (VAS=3) --
    seeds.append(_case(
        case_kind="football",
        age=27, sex="F", height_cm=166.0, weight_kg=62.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "COMEBACK_27F_POSTSEASON_VAS3",
            "hop_test": {"left_cm": 135.0, "right_cm": 140.0},
            "nordic": {"hold_time_seconds": 6.5},
            "sprint": {"20m_time_seconds": 3.68},
            "pogo": {"clean_reps_10s": 14},
            "cod": {"left_505_seconds": 2.62, "right_505_seconds": 2.58},
            "ybalance": {"left_pct": 88.0, "right_pct": 90.0},
        },
        injury_history=[{"type": "hamstring_strain", "grade": "II", "side": "left", "months_ago": 5}],
        acuity="subacute",
        current_pain=True, pain_vas=3,
        training_history="recent_comeback", position="WIDE",
        competition_phase="post-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 20: 25yo F CF, force-dominant FV profile ───────────────────────
    seeds.append(_case(
        case_kind="football",
        age=25, sex="F", height_cm=167.0, weight_kg=62.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 4, "push": 4, "pull": 3, "carry": 4, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "FORCE_DOMINANT_FV_25F_CF",
            "hop_test": {"left_cm": 175.0, "right_cm": 178.0},  # high hop
            "nordic": {"hold_time_seconds": 10.5},
            "sprint": {"20m_time_seconds": 3.55},               # slow sprint → force-dominant
            "pogo": {"clean_reps_10s": 17},
            "cod": {"left_505_seconds": 2.48, "right_505_seconds": 2.44},
            "ybalance": {"left_pct": 100.0, "right_pct": 101.0},
            "fv_expected": "force_dominant",
        },
        injury_history=[], acuity="none",
        training_history="club_senior", position="CF",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 21: 23yo M, velocity-dominant FV profile ───────────────────────
    seeds.append(_case(
        case_kind="football",
        age=23, sex="M", height_cm=176.0, weight_kg=71.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 4, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "VELOCITY_DOMINANT_FV_23M_WIDE",
            "hop_test": {"left_cm": 138.0, "right_cm": 140.0},  # moderate hop
            "nordic": {"hold_time_seconds": 7.0},
            "sprint": {"20m_time_seconds": 2.92},               # very fast sprint → velocity-dominant
            "pogo": {"clean_reps_10s": 24},
            "cod": {"left_505_seconds": 2.05, "right_505_seconds": 2.02},
            "ybalance": {"left_pct": 93.0, "right_pct": 94.0},
            "fv_expected": "velocity_dominant",
        },
        injury_history=[], acuity="none",
        training_history="club_senior", position="WIDE",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 22: 14yo F, PHV risk, academy level ────────────────────────────
    seeds.append(_case(
        case_kind="football",
        age=14, sex="F", height_cm=159.0, weight_kg=49.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "PHV_ACTIVE_14F_ACADEMY",
            "hop_test": {"left_cm": 118.0, "right_cm": 121.0},
            "nordic": {"hold_time_seconds": 7.5},
            "sprint": {"20m_time_seconds": 3.62},
            "pogo": {"clean_reps_10s": 16},
            "cod": {"left_505_seconds": 2.68, "right_505_seconds": 2.65},
            "ybalance": {"left_pct": 92.0, "right_pct": 94.0},
            "peak_height_velocity_active": True,
        },
        injury_history=[], acuity="none",
        training_history="academy_pro", position="CM",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 23: 31yo M CB, return from 10-week layoff ──────────────────────
    seeds.append(_case(
        case_kind="football",
        age=31, sex="M", height_cm=186.0, weight_kg=83.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 1, "squat": 0, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "RETURN_FROM_LAYOFF_31M_CB_10WK",
            "hop_test": {"left_cm": 155.0, "right_cm": 162.0},
            "nordic": {"hold_time_seconds": 7.8},
            "sprint": {"20m_time_seconds": 3.38},
            "pogo": {"clean_reps_10s": 16},
            "cod": {"left_505_seconds": 2.42, "right_505_seconds": 2.35},
            "ybalance": {"left_pct": 90.0, "right_pct": 93.0},
            "layoff_weeks": 10,
        },
        injury_history=[], acuity="subacute",
        training_history="club_senior", position="CB",
        competition_phase="return-from-layoff",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 24: 17yo M, Osgood-Schlatter, in-season ────────────────────────
    seeds.append(_case(
        case_kind="football",
        age=17, sex="M", height_cm=174.0, weight_kg=64.0,
        pattern_scores={"hip_hinge": 3, "squat": 2, "lunge": 2, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 1, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "OSGOOD_SCHLATTER_17M_INSEASON",
            "hop_test": {"left_cm": 142.0, "right_cm": 148.0},
            "nordic": {"hold_time_seconds": 7.5},
            "sprint": {"20m_time_seconds": 3.32},
            "pogo": {"clean_reps_10s": 16},
            "cod": {"left_505_seconds": 2.45, "right_505_seconds": 2.40},
            "ybalance": {"left_pct": 88.0, "right_pct": 91.0},
            "osgood_schlatter": True,
        },
        injury_history=[{"type": "osgood_schlatter", "side": "bilateral", "months_ago": 0}],
        acuity="subacute",
        current_pain=True, pain_vas=2,
        training_history="club_senior", position="CM",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 25: 20yo F, post-season, low nordic (hamstring deficit) ─────────
    seeds.append(_case(
        case_kind="football",
        age=20, sex="F", height_cm=163.0, weight_kg=58.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "LOW_NORDIC_HAMSTRING_DEFICIT_20F",
            "hop_test": {"left_cm": 152.0, "right_cm": 155.0},
            "nordic": {"hold_time_seconds": 1.8},   # very low — hamstring deficit
            "sprint": {"20m_time_seconds": 3.38},
            "pogo": {"clean_reps_10s": 17},
            "cod": {"left_505_seconds": 2.48, "right_505_seconds": 2.45},
            "ybalance": {"left_pct": 95.0, "right_pct": 96.0},
            "hamstring_deficit_flag": True,
        },
        injury_history=[], acuity="none",
        training_history="club_senior", position="CM",
        competition_phase="post-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 26: 33yo M GK, recent surgery (meniscus, 6 weeks ago) ───────────
    seeds.append(_case(
        case_kind="football",
        age=33, sex="M", height_cm=188.0, weight_kg=86.0,
        pattern_scores={"hip_hinge": 3, "squat": 2, "lunge": 2, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 1, "lunge": 1, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "POST_MENISCUS_SURGERY_6WK_33M_GK",
            "hop_test": {"left_cm": 120.0, "right_cm": 172.0},
            "nordic": {"hold_time_seconds": 5.5},
            "sprint": {"20m_time_seconds": 3.72},
            "pogo": {"clean_reps_10s": 10},
            "cod": {"left_505_seconds": 3.05, "right_505_seconds": 2.38},
            "ybalance": {"left_pct": 79.0, "right_pct": 95.0},
        },
        injury_history=[{"type": "meniscus_surgery", "side": "left", "months_ago": 0}],
        acuity="acute",
        recent_surgery=True, surgery_weeks_ago=6,
        current_pain=True, pain_vas=4,
        training_history="club_senior", position="GK",
        competition_phase="return-from-layoff",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 27: 16yo F, first football assessment, no prior data ────────────
    seeds.append(_case(
        case_kind="football",
        age=16, sex="F", height_cm=161.0, weight_kg=54.0,
        pattern_scores={"hip_hinge": 2, "squat": 2, "lunge": 2, "push": 2, "pull": 2, "carry": 2, "rotation": 2},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "FIRST_ASSESSMENT_16F_NO_HISTORY",
            "hop_test": {"left_cm": 110.0, "right_cm": 112.0},
            "nordic": {"hold_time_seconds": 4.2},
            "sprint": {"20m_time_seconds": 3.78},
            "pogo": {"clean_reps_10s": 12},
            "cod": {"left_505_seconds": 2.78, "right_505_seconds": 2.75},
            "ybalance": {"left_pct": 86.0, "right_pct": 88.0},
            "first_assessment": True,
        },
        injury_history=[], acuity="none",
        training_history="club_amateur", position="WIDE",
        competition_phase="pre-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 28: 42yo M, recreational CF, very low performance across all tests
    seeds.append(_case(
        case_kind="football",
        age=42, sex="M", height_cm=174.0, weight_kg=90.0,
        pattern_scores={"hip_hinge": 2, "squat": 1, "lunge": 1, "push": 2, "pull": 2, "carry": 2, "rotation": 1},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "MASTERS_LOW_PERF_42M_CF_REC",
            "hop_test": {"left_cm": 88.0, "right_cm": 92.0},
            "nordic": {"hold_time_seconds": 1.5},
            "sprint": {"20m_time_seconds": 4.55},
            "pogo": {"clean_reps_10s": 7},
            "cod": {"left_505_seconds": 3.18, "right_505_seconds": 3.20},
            "ybalance": {"left_pct": 74.0, "right_pct": 76.0},
        },
        injury_history=[], acuity="none",
        training_history="recreational", position="CF",
        competition_phase="in-season",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 29: 19yo F, academy, acutely injured during assessment attempt ---
    seeds.append(_case(
        case_kind="football",
        age=19, sex="F", height_cm=164.0, weight_kg=59.0,
        pattern_scores={"hip_hinge": 4, "squat": 4, "lunge": 4, "push": 3, "pull": 3, "carry": 4, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "ACUTELY_INJURED_DURING_ASSESSMENT_19F",
            "hop_test": {"left_cm": 155.0, "right_cm": 158.0},
            "nordic": {"hold_time_seconds": 9.5},
            "sprint": {"20m_time_seconds": 3.22},
            "pogo": {"clean_reps_10s": 20},
            "cod": {"left_505_seconds": 2.30, "right_505_seconds": 2.28},
            "ybalance": {"left_pct": 97.0, "right_pct": 98.0},
            "assessment_stopped_due_to_pain": True,
        },
        injury_history=[{"type": "ankle_sprain", "side": "right", "grade": "I", "months_ago": 0}],
        acuity="acute",
        current_pain=True, pain_vas=8,
        training_history="academy_pro", position="FB",
        competition_phase="acutely-injured",
        coach_linked=True, unsupervised_context=False,
    ))

    # -- Seed 30: Third coach_linked=False (second orphan, different profile) --
    seeds.append(_case(
        case_kind="football",
        age=35, sex="M", height_cm=178.0, weight_kg=79.0,
        pattern_scores={"hip_hinge": 3, "squat": 3, "lunge": 3, "push": 3, "pull": 3, "carry": 3, "rotation": 3},
        asymmetries={"hip_hinge": 0, "squat": 0, "lunge": 0, "push": 0, "pull": 0, "carry": 0, "rotation": 0},
        football_raw_inputs={
            "_seed_tag": "ORPHAN_NO_COACH_35M_MASTERS",
            "hop_test": {"left_cm": 140.0, "right_cm": 145.0},
            "nordic": {"hold_time_seconds": 6.2},
            "sprint": {"20m_time_seconds": 3.55},
            "pogo": {"clean_reps_10s": 15},
            "cod": {"left_505_seconds": 2.62, "right_505_seconds": 2.58},
            "ybalance": {"left_pct": 88.0, "right_pct": 89.0},
        },
        injury_history=[], acuity="none",
        training_history="club_amateur", position="CM",
        competition_phase="in-season",
        coach_linked=False, unsupervised_context=True,
    ))

    return seeds


# ============================================================================
# STRATIFIED CASE GENERATOR
# ============================================================================

def generate(n: int, seed: int) -> Iterator[SyntheticPatientCase]:
    """
    Stratified generator: yields n SyntheticPatientCase objects (case_kind='football').

    The first ~30 cases are adversarial seeds (injected every batch).
    Remaining cases fill the stratification grid:
      age_band × sex × position × training_history × competition_phase

    Parameters
    ----------
    n    : total cases requested (≥ 30)
    seed : random seed for determinism
    """
    rng = random.Random(seed)

    # Always emit adversarial seeds first
    adv_seeds = _build_adversarial_seeds(rng)
    for s in adv_seeds:
        yield s

    remaining = max(0, n - len(adv_seeds))
    if remaining == 0:
        return

    # Build the full stratification grid (2,520 cells for 7×2×6×5×3 subset)
    # We cycle competition phases across cells deterministically then randomise
    # injury type and coach_linked per cell.
    grid = list(product(
        [ab[2] for ab in AGE_BANDS],   # age band labels
        SEXES,
        POSITIONS,
        TRAINING_HISTORIES,
        COMPETITION_PHASES,
    ))

    # Shuffle grid with fixed seed so distribution is deterministic
    rng.shuffle(grid)

    # Build mapping: age_band_label → (min_age, max_age)
    age_band_ranges = {ab[2]: (ab[0], ab[1]) for ab in AGE_BANDS}

    idx = 0
    generated = 0

    while generated < remaining:
        ab_label, sex, position, th, comp_phase = grid[idx % len(grid)]
        idx += 1

        age_lo, age_hi = age_band_ranges[ab_label]
        age = rng.randint(age_lo, age_hi)

        # Injury type — weighted toward 'none' for most, injury-consistent with phase
        if comp_phase == "acutely-injured":
            injury_type = rng.choice(["past_ACL_R", "recurring_hamstring",
                                       "ankle_sprain_history", "multiple"])
        elif comp_phase == "return-from-layoff":
            injury_type = rng.choice(["none", "past_ACL_R", "recurring_hamstring",
                                       "ankle_sprain_history", "groin_FAI"])
        else:
            injury_type = rng.choices(
                INJURY_TYPES,
                weights=[0.40, 0.12, 0.15, 0.13, 0.08, 0.06, 0.06],
            )[0]

        # coach_linked: ~95% True, ~5% False
        coach_linked = rng.random() > 0.05

        profile = _AthleteProfile(
            age=age,
            age_band=ab_label,
            sex=sex,
            position=position,
            training_history=th,
            injury_type=injury_type,
            competition_phase=comp_phase,
            height_cm=0.0,
            weight_kg=0.0,
            coach_linked=coach_linked,
        )
        profile.height_cm, profile.weight_kg = _anthropometrics(profile, rng)

        raw_inputs = realistic_test_inputs(profile, rng)
        pattern_scores, asymmetries = _pattern_scores(profile, rng)
        current_pain, pain_vas = _pain_state(profile, rng)
        injury_history = _injury_history_from_type(rng, injury_type)
        acuity = _acuity_from_injury_and_phase(injury_type, comp_phase, current_pain)
        red_flags = _red_flags(profile, rng)

        # Pregnancy — only for F, rare
        pregnancy = sex == "F" and rng.random() < 0.02
        pregnancy_trimester = rng.randint(1, 3) if pregnancy else None

        # Recent surgery — rare, consistent with injury
        recent_surgery = injury_type in ("past_ACL_R", "multiple") and rng.random() < 0.05
        surgery_weeks_ago = rng.randint(4, 52) if recent_surgery else None

        # Cardiac flag — rare, elevated for masters
        # Engineering approximation — controls distribution shape for synthetic
        # data only. Does not feed scoring or prescription logic. Does not
        # require citation.
        cardiac_base = 0.02 if ab_label == "35+" else 0.005
        cardiac_flag = rng.random() < cardiac_base

        try:
            case = SyntheticPatientCase.build(
                case_kind="football",
                age=age,
                sex=sex,
                height_cm=profile.height_cm,
                weight_kg=profile.weight_kg,
                pattern_scores=pattern_scores,
                asymmetries=asymmetries,
                football_raw_inputs=raw_inputs,
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
                training_history=th,
                position=position,
                competition_phase=comp_phase,
                equipment=["full_gym"],
                coach_linked=coach_linked,
                unsupervised_context=not coach_linked,
            )
            yield case
            generated += 1
        except Exception:
            # Skip malformed cases; extremely rare
            continue


# ============================================================================
# AUDIT RUN ENTRY POINT
# ============================================================================

def audit_run(n: int, seed: int, against_cases: str = "", read: str = "", **kwargs) -> int:
    """
    Entry point called by the clinical audit runner.

    Generates n cases, writes them to reports/agent2_cases.jsonl.
    Returns 0 on success.
    """
    os.makedirs(_REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(_REPORTS_DIR, "agent2_cases.jsonl")

    total = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for case in generate(n=n, seed=seed):
            fh.write(json.dumps(case.to_dict(), ensure_ascii=False) + "\n")
            total += 1

    print(f"agent2_football_gen: wrote {total} cases → {out_path}")

    # Verify adversarial seed count
    adv_rng = random.Random(seed)
    adv_count = len(_build_adversarial_seeds(adv_rng))
    print(f"agent2_football_gen: adversarial seeds in batch = {adv_count}")

    # Quick coverage summary
    from collections import Counter
    positions_seen: Counter = Counter()
    phases_seen: Counter = Counter()
    coach_false = 0

    with open(out_path, "r", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("position"):
                positions_seen[rec["position"]] += 1
            if rec.get("competition_phase"):
                phases_seen[rec["competition_phase"]] += 1
            if not rec.get("coach_linked", True):
                coach_false += 1

    print(f"agent2_football_gen: positions = {dict(positions_seen)}")
    print(f"agent2_football_gen: phases = {dict(phases_seen)}")
    print(f"agent2_football_gen: coach_linked=False count = {coach_false} / {total} "
          f"({100 * coach_false / max(total, 1):.1f}%)")

    return 0
