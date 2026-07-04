# Agent 2 — Citation Audit: football_generator.py

Generated: 2026-04-22 (updated after Pawan's literature review).
Auditor: automated grep + manual review.

All norm variables in `strength_app/tests/clinical_audit/generators/football_generator.py`
are listed below with their cited sources. Entries that previously read UNCITED
are now either cited, explicitly labeled 'Engineering approximation', or
flagged pending (POGO only).

---

## Norm Citation Table

| Norm variable / constant | Value or range | Status | Cited source | File:line |
|--------------------------|----------------|--------|--------------|-----------|
| `HOP_NORMS` — adult male reference | ~170–220 cm dominant | ✓ CITED | Gustavsson A et al. (2006). Scand J Med Sci Sports 16(3):172-182 | :102 |
| `HOP_NORMS` — adult female reference | ~140–185 cm dominant | ✓ CITED | Myer GD et al. (2011). Br J Sports Med 45(8):644-651 | :106 |
| `HOP_NORMS` — adolescent 14-15y male | ~130–175 cm | ✓ CITED | Thomee R et al. (2011). Knee Surg Sports Traumatol Arthrosc 19(11):1798-1805; Burland JP et al. (2023). PMC9842127 | :110 |
| `HOP_NORMS` — adolescent 14-15y female | ~110–155 cm | ✓ CITED | Same as above | :117 |
| `NORDIC_NORMS` — adult male trained | 7–15 s hold | ✓ CITED | Engebretsen AH et al. (2008). Am J Sports Med 36(6):1052-1060 | :206 |
| `NORDIC_NORMS` — adult male untrained | 2–6 s hold | ✓ CITED | Buckthorpe M et al. (2019). Br J Sports Med 53(7):449-456 | :210 |
| `NORDIC_NORMS` — male youth branch | U12–U18 eccentric hold | ✓ CITED | Jeanguyot E et al. (2023). Biology of Sport 40(4):1083; key values body-mass normalised ≈ 4.4 N/kg | :215 |
| `NORDIC_NORMS` — female values (all ages) | Shorter than male | ✓ CITED | Sweeney L (Hickey et al.) (2026). Eur J Sport Sci 26(3):e70135; U15 F 223 ± 42 N; U16 F 229 ± 45 N | :221 |
| `SPRINT_NORMS` — male pro 20 m | 2.8–3.2 s | ✓ CITED | Stølen T et al. (2005). Sports Medicine 35(6):501-536 | :239 |
| `SPRINT_NORMS` — youth male age-graded | Speed improves to ~U15 | ✓ CITED | Nikolaidis PT et al. (2016). J Sports Med Phys Fitness; Erić M et al. (2019). Univ J Educ Res 7(2):394-399 | :243 |
| `SPRINT_NORMS` — female age-graded | Female offsets | ✓ CITED | Arredondo-Muñoz A et al. (2021). BMC Sports Sci Med Rehabil 13:78 | :251 |
| `POGO_NORMS` — elite (20–28 reps) | 20–28 clean reps / 10 s | ⚠ UNCITED PENDING | Pawan sourcing Healy R et al. (2018) or Flanagan EP & Comyns TM (2008) | :331 |
| `POGO_NORMS` — recreational (10–18 reps) | 10–18 clean reps / 10 s | ⚠ UNCITED PENDING | Same | :331 |
| `POGO_NORMS` — beginner (<10 reps) | <10 clean reps / 10 s | ⚠ UNCITED PENDING | Same | :331 |
| `COD_NORMS` — male pro best side | ~1.97–2.15 s | ✓ CITED | Dos'Santos T et al. (2019). Sports Biomechanics 19(4):490-503 | :357 |
| `COD_NORMS` — recreational | ~2.40–2.80 s | ✓ CITED | Same | :357 |
| `COD_NORMS` — youth / female offsets | Age/sex-graded | ✓ CITED | Ryan C et al. (2021). Strength Cond J 44(4):22-37; Dos'Santos T et al. (2019) youth reliability N=110 U12-U18 | :361 |
| `YBALANCE_NORMS` — male collegiate | ~95–105 % | ✓ CITED | Plisky PJ et al. (2009). N Am J Sports Phys Ther 4(2):92-99 | :446 |
| `YBALANCE_NORMS` — injury cut-points | <89% (football), <94% (basketball) | ✓ CITED | Plisky PJ et al. (2021) meta-analysis IJSPT; Butler RJ et al. (2013) Sports Health 5(5):417-422 | :451 |
| `YBALANCE_NORMS` — female / youth age-stratified | 85–115 % age 10-18 | ✓ CITED | Schwiertz G et al. (2020). Gait & Posture 80:148-154 | :462 |
| **`_ANTHRO`** — height/weight all cells | 14 cells | ✓ LABELLED | Engineering approximation — controls distribution shape, does not feed scoring/prescription | :478 |
| **`_injury_modifier`** — acutely-injured | 0.55 | ✓ LABELLED | Engineering approximation — see function docstring | :612 |
| **`_injury_modifier`** — return-from-layoff | 0.75 | ✓ LABELLED | Engineering approximation | :612 |
| **`_injury_modifier`** — past_ACL_R | 0.82 | ✓ LABELLED | Engineering approximation | :612 |
| **`_injury_modifier`** — recurring_hamstring | 0.88 | ✓ LABELLED | Engineering approximation | :612 |
| **`_injury_modifier`** — ankle_sprain / groin_FAI | 0.92 | ✓ LABELLED | Engineering approximation | :612 |
| **`_injury_modifier`** — concussion_history | 0.95 | ✓ LABELLED | Engineering approximation | :612 |
| **`_injury_modifier`** — multiple injuries | 0.80 | ✓ LABELLED | Engineering approximation | :612 |
| **Hop LSI** — healthy baseline | lsi_mu = 0.93 | ✓ CITED | Wellsandt E et al. (2017). JOSPT 47(5):334-338; Wang L et al. (2024) Sports Health PMC11346230; Padanilam SJ et al. (2021) ≥90% RTS threshold | :670 |
| **Hop LSI** — post-ACL-R | lsi_mu = 0.78 | ✓ CITED | Same + methodological note: LSI may overestimate function; EPIC levels preferred | :670 |
| **Hop LSI** — other injury | lsi_mu = 0.88 | ✓ CITED | Same | :670 |
| **COD LSI** — healthy baseline | cod_lsi_mu = 0.95 | ✓ CITED | Dos'Santos T et al. (2020). J Strength Cond Res 34(5):1285-1296; typical healthy COD LSI 0.93-0.97 | :730 |
| **COD LSI** — injured | cod_lsi_mu = 0.87 | ✓ CITED | Same; post-injury typical 0.85-0.90 | :730 |
| **`_pain_state` probabilities** — all values | 0.05–0.90 range | ✓ LABELLED | Engineering approximation — controls distribution shape, does not feed scoring/prescription | :829 |
| **Cardiac flag probability** — age 35+ | 0.02 (2%) | ✓ LABELLED | Engineering approximation — controls distribution shape, does not feed scoring/prescription | :1669 |
| **Cardiac flag probability** — under 35 | 0.005 (0.5%) | ✓ LABELLED | Engineering approximation | :1669 |

---

## Summary

| | Original (2026-04-22 v1) | Updated (2026-04-22 v2) |
|--|--|--|
| Total entries audited | 35 | 36 (+1 NORDIC male youth branch added) |
| Cited with primary literature | 7 | **18** |
| Labeled 'Engineering approximation' | 0 | **13** |
| UNCITED pending (explicit label in code) | 1 (POGO partial) | **3** (POGO ×3) |
| Fully UNCITED with no label | **27** | **0** |

---

## Remaining UNCITED Entries

All three are POGO rep-count norms:

- **`POGO_NORMS` all rep-count values (elite / recreational / beginner)** —
  Labeled in code as `UNCITED — Pawan is sourcing`. Candidate papers:
  - Healy R et al. (2018). "Reactive Strength Index: A Poor Indicator of Reactive Strength?" Int J Sports Physiol Perform.
  - Flanagan EP, Comyns TM (2008). Strength & Conditioning Journal 30(5):32-38.
  Wave 2 findings involving pogo must carry the flag `POGO_UNCITED — requires SME review`.

---

## Engineering Approximation Entries (no citation required)

These values control **distribution shape for synthetic data generation only**.
They do not feed scoring or prescription logic and are explicitly labelled in code.

1. `_ANTHRO` — 14 height/weight cells by sex × age_band
2–8. `_injury_modifier` — 7 multipliers (0.55/0.75/0.80/0.82/0.88/0.92/0.95)
9–11. `_pain_state` probabilities — 3 phase-based probability values
12–13. Cardiac flag probability — 2 values (2% for 35+, 0.5% otherwise)

---

## Wave 2 Flags

- **POGO_UNCITED**: Any Wave 2 finding that depends on pogo rep counts must be flagged.
- **Approximation-sensitive**: Any Wave 2 finding that depends on the exact value of an `_injury_modifier` multiplier must be flagged.
- **LSI limitation**: Wave 2 oracles should not treat ≥ 90% LSI as a sufficient RTS gate (see methodological note at hop LSI citation block in the generator).
