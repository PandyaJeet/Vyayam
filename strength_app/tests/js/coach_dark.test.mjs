/*
 * 2026-07 dark camera coaches — node harness.
 * Run: node --test strength_app/tests/js/coach_dark.test.mjs
 *
 * Synthetic landmark frames drive each coach's checkAngles through
 * VyayamCV.computeMatchScore against its own phase targets (the same
 * signal the live phase machine gates on at >= 70), and each fault
 * observer through makeFaults' sustain/cooldown plumbing.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const cv = require('../../static/strength_app/js/cv_core.js');
const dark = require('../../static/strength_app/js/coach_dark.js');

const P = (x, y, visibility = 1) => ({ x, y, visibility });
const L = cv.LM;

/** Blank 33-landmark frame, everything visible at (0.5, 0.5). */
function frame() {
  return Array.from({ length: 33 }, () => P(0.5, 0.5, 1));
}

/** Score a frame against a named phase of a dark def. */
function scorePhase(def, phaseName, lm) {
  const phase = def.phases.find((p) => p.name === phaseName);
  assert.ok(phase, `phase ${phaseName} missing`);
  return cv.computeMatchScore(def.checkAngles(lm), phase.joints);
}

/** Drive a fault observer: run `test` frames then return cued ids. */
function runFaults(obs, frames, gs) {
  const cued = [];
  let now = 1_000_000;
  for (const lm of frames) {
    obs.frame(lm, gs, (id) => cued.push(id), now);
    now += 200;
  }
  return cued;
}

test('install never overwrites an existing registry key', () => {
  const registry = { SQUAT: { name: 'frozen' } };
  dark.install(registry);
  assert.equal(registry.SQUAT.name, 'frozen');
  for (const key of Object.keys(dark.PHASES)) {
    assert.ok(registry[key], `${key} not installed`);
  }
});

test('every dark def carries the full template contract', () => {
  for (const [key, def] of Object.entries(dark.PHASES)) {
    assert.ok(def.name, key);
    assert.ok(['standing', 'prone', 'supine', 'sidelying',
               'sidelying_clamshell'].includes(def.bodyOrientation),
              `${key}: bodyOrientation`);
    assert.ok(def.cameraPosition && def.cameraPosition.instruction, key);
    assert.ok(Array.isArray(def.setupCues) && def.setupCues.length >= 3, key);
    assert.ok(Array.isArray(def.phases) && def.phases.length >= 1, key);
    assert.equal(typeof def.checkAngles, 'function', key);
    assert.ok(def.cues && Object.keys(def.cues).length >= 1, key);
    // stanceCheck is soft-warning-only by design; may be null but the
    // property must exist so the template's reads are defined.
    assert.ok('stanceCheck' in def, `${key}: stanceCheck missing`);
  }
});

test('fault factory: sustain window, cooldown, hold vs rep gating', () => {
  const obs = dark.makeFaults([{
    cue: 'test_cue',
    modes: ['GUIDING'],
    minMs: 300,
    cooldownMs: 8000,
    test: (lm) => (lm[0].x > 0.9 ? ['11-23'] : null),
  }]);
  const bad = frame(); bad[0] = P(0.95, 0.5);
  const good = frame();
  const gs = { mode: 'GUIDING', isHoldExercise: true, repCount: 0 };

  // 1 frame (0ms elapsed) — sustain window not met, no cue, no amber
  assert.deepEqual(runFaults(obs, [bad], gs), []);
  // sustained (3 frames @200ms) — cue fires once, amber set
  obs.resetSet();
  const cued = runFaults(obs, [bad, bad, bad, bad], gs);
  assert.deepEqual(cued, ['test_cue']);
  assert.ok(obs.amberUntil > 0);
  assert.deepEqual(obs.amberSegs(), ['11-23']);
  // cooldown suppresses immediate refire even when fault persists
  const again = runFaults(obs, [bad, bad, bad], gs);
  assert.deepEqual(again, []);
  // clean frame resets the sustain clock
  obs.resetSet();
  assert.deepEqual(runFaults(obs, [bad, good, bad], gs), []);
});

// ══ per-exercise suites appended in build order ══════════════════════════

test('WALL_SIT_RX: hold pose scores, standing does not; depth + heel faults fire', () => {
  const def = dark.PHASES.WALL_SIT_RX;
  assert.equal(def.phases.length, 1, 'wall sit is a single-phase hold');

  // Side-view wall sit: thigh horizontal (hip→knee), shin vertical
  // (knee→ankle), torso vertical (shoulder above hip) → knee 90, hip 90.
  const sit = frame();
  sit[L.leftShoulder] = P(0.40, 0.30); sit[L.rightShoulder] = P(0.41, 0.30);
  sit[L.leftHip] = P(0.40, 0.50);      sit[L.rightHip] = P(0.41, 0.50);
  sit[L.leftKnee] = P(0.54, 0.50);     sit[L.rightKnee] = P(0.55, 0.50);
  sit[L.leftAnkle] = P(0.54, 0.66);    sit[L.rightAnkle] = P(0.55, 0.66);
  sit[L.leftHeel] = P(0.53, 0.68);     sit[L.rightHeel] = P(0.54, 0.68);
  sit[L.leftFootIndex] = P(0.58, 0.68); sit[L.rightFootIndex] = P(0.59, 0.68);
  assert.ok(scorePhase(def, 'hold', sit) >= 70,
            `hold pose scored ${scorePhase(def, 'hold', sit)}`);

  // Standing: everything vertical → knee/hip ~180 → nowhere near the hold.
  const stand = frame();
  stand[L.leftShoulder] = P(0.40, 0.20); stand[L.rightShoulder] = P(0.41, 0.20);
  stand[L.leftHip] = P(0.40, 0.50);      stand[L.rightHip] = P(0.41, 0.50);
  stand[L.leftKnee] = P(0.40, 0.70);     stand[L.rightKnee] = P(0.41, 0.70);
  stand[L.leftAnkle] = P(0.40, 0.90);    stand[L.rightAnkle] = P(0.41, 0.90);
  assert.ok(scorePhase(def, 'hold', stand) < 70,
            `standing scored ${scorePhase(def, 'hold', stand)}`);

  // Fault: thighs above parallel (knee angle ~135°) sustained → slide-down.
  const shallow = frame();
  shallow[L.leftHip] = P(0.40, 0.50);   shallow[L.rightHip] = P(0.41, 0.50);
  shallow[L.leftKnee] = P(0.50, 0.60);  shallow[L.rightKnee] = P(0.51, 0.60);
  shallow[L.leftAnkle] = P(0.50, 0.76); shallow[L.rightAnkle] = P(0.51, 0.76);
  const gs = { mode: 'GUIDING', isHoldExercise: true, repCount: 0 };
  const obs = dark.FAULTS.WALL_SIT_RX;
  obs.resetSet(); obs._lastAt = {};
  let cued = runFaults(obs, [shallow, shallow, shallow, shallow, shallow, shallow], gs);
  assert.deepEqual(cued, ['wall_sit_slide_down']);

  // Fault: heel rise (heel well above toe on facing side) → heels cue.
  const heels = frame();
  heels[L.leftHip] = P(0.40, 0.50);   heels[L.rightHip] = P(0.41, 0.50);
  heels[L.leftKnee] = P(0.54, 0.50);  heels[L.rightKnee] = P(0.55, 0.50);
  heels[L.leftAnkle] = P(0.54, 0.66); heels[L.rightAnkle] = P(0.55, 0.66);
  heels[L.leftHeel] = P(0.53, 0.62);  heels[L.rightHeel] = P(0.54, 0.62);   // lifted
  heels[L.leftFootIndex] = P(0.58, 0.68); heels[L.rightFootIndex] = P(0.59, 0.68);
  obs.resetSet(); obs._lastAt = {};
  cued = runFaults(obs, [heels, heels, heels, heels], gs);
  assert.deepEqual(cued, ['wall_sit_heels']);

  // Faults stay silent outside GUIDING (demo/waiting frames never cue).
  obs.resetSet(); obs._lastAt = {};
  cued = runFaults(obs, [shallow, shallow, shallow],
                   { mode: 'DEMO', isHoldExercise: true, repCount: 0 });
  assert.deepEqual(cued, []);
});

test('PLANK_RX: flat plank scores, standing does not; sag and pike fault', () => {
  const def = dark.PHASES.PLANK_RX;
  assert.equal(def.phases.length, 1);

  // Horizontal body: shoulder → hip → ankle in one flat line near floor.
  const plank = frame();
  plank[L.leftShoulder] = P(0.25, 0.68); plank[L.rightShoulder] = P(0.25, 0.69);
  plank[L.leftHip] = P(0.50, 0.70);      plank[L.rightHip] = P(0.50, 0.71);
  plank[L.leftAnkle] = P(0.75, 0.72);    plank[L.rightAnkle] = P(0.75, 0.73);
  assert.ok(scorePhase(def, 'hold', plank) >= 70);

  // Standing: ankles far below shoulders → plankLevel huge.
  const stand = frame();
  stand[L.leftShoulder] = P(0.50, 0.25); stand[L.rightShoulder] = P(0.51, 0.25);
  stand[L.leftHip] = P(0.50, 0.52);      stand[L.rightHip] = P(0.51, 0.52);
  stand[L.leftAnkle] = P(0.50, 0.92);    stand[L.rightAnkle] = P(0.51, 0.92);
  assert.ok(scorePhase(def, 'hold', stand) < 70);

  const gs = { mode: 'GUIDING', isHoldExercise: true, repCount: 0 };
  const obs = dark.FAULTS.PLANK_RX;

  // Sag: hip well below the shoulder-ankle line.
  const sag = frame();
  sag[L.leftShoulder] = P(0.25, 0.70); sag[L.leftHip] = P(0.50, 0.80);
  sag[L.leftAnkle] = P(0.75, 0.70);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [sag, sag, sag, sag, sag], gs), ['plank_hips_sag']);

  // Pike: hip well above the line.
  const pike = frame();
  pike[L.leftShoulder] = P(0.25, 0.70); pike[L.leftHip] = P(0.50, 0.60);
  pike[L.leftAnkle] = P(0.75, 0.70);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [pike, pike, pike, pike, pike], gs), ['plank_hips_pike']);

  // A straight plank never faults.
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [plank, plank, plank, plank], gs), []);
});

test('SIDE_PLANK_RX: straight lateral line scores; dropped hip faults', () => {
  const def = dark.PHASES.SIDE_PLANK_RX;
  assert.equal(def.phases.length, 1);

  // Straight side plank: shoulder-hip-ankle collinear near the floor.
  const hold = frame();
  hold[L.leftShoulder] = P(0.25, 0.66); hold[L.rightShoulder] = P(0.25, 0.64);
  hold[L.leftHip] = P(0.50, 0.68);      hold[L.rightHip] = P(0.50, 0.66);
  hold[L.leftAnkle] = P(0.75, 0.70);    hold[L.rightAnkle] = P(0.75, 0.68);
  assert.ok(scorePhase(def, 'hold', hold) >= 70,
            `hold scored ${scorePhase(def, 'hold', hold)}`);

  // Hip dropped toward the floor: line collapses well below 162.
  const drop = frame();
  drop[L.leftShoulder] = P(0.25, 0.62); drop[L.rightShoulder] = P(0.25, 0.60);
  drop[L.leftHip] = P(0.50, 0.78);      drop[L.rightHip] = P(0.50, 0.76);
  drop[L.leftAnkle] = P(0.75, 0.62);    drop[L.rightAnkle] = P(0.75, 0.60);
  assert.ok(scorePhase(def, 'hold', drop) < 70);

  const gs = { mode: 'GUIDING', isHoldExercise: true, repCount: 0 };
  const obs = dark.FAULTS.SIDE_PLANK_RX;
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [drop, drop, drop, drop, drop], gs),
                   ['side_plank_hip_drop']);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [hold, hold, hold, hold], gs), []);
});

test('BALANCE_RX: raised-knee hold scores; foot-down and hip-drop fault', () => {
  const def = dark.PHASES.BALANCE_RX;
  assert.equal(def.phases.length, 1);

  // Balancing: left knee lifted well above right, hips level.
  const hold = frame();
  hold[L.leftHip] = P(0.46, 0.50);  hold[L.rightHip] = P(0.54, 0.505);
  hold[L.leftKnee] = P(0.46, 0.58); hold[L.rightKnee] = P(0.54, 0.70);
  assert.ok(scorePhase(def, 'hold', hold) >= 70,
            `hold scored ${scorePhase(def, 'hold', hold)}`);

  // Both feet down: knees level → liftedKnee ~0 → misses the 0.10 target.
  const down = frame();
  down[L.leftHip] = P(0.46, 0.50);  down[L.rightHip] = P(0.54, 0.50);
  down[L.leftKnee] = P(0.46, 0.70); down[L.rightKnee] = P(0.54, 0.70);
  assert.ok(scorePhase(def, 'hold', down) < 70);

  const gs = { mode: 'GUIDING', isHoldExercise: true, repCount: 0 };
  const obs = dark.FAULTS.BALANCE_RX;
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [down, down, down, down, down], gs),
                   ['balance_foot_down']);

  // Hip drop while the knee stays up.
  const tilt = frame();
  tilt[L.leftHip] = P(0.46, 0.46);  tilt[L.rightHip] = P(0.54, 0.55);
  tilt[L.leftKnee] = P(0.46, 0.58); tilt[L.rightKnee] = P(0.54, 0.70);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [tilt, tilt, tilt, tilt], gs), ['hips_level']);

  // Clean hold: silent.
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [hold, hold, hold, hold], gs), []);
});

test('SLR_RX: rest/raise phases score in sequence; bent-knee lift faults', () => {
  const def = dark.PHASES.SLR_RX;
  assert.equal(def.phases.length, 4, 'SLR is a 4-phase rep cycle');

  // Supine side view, body horizontal. Flat: everything on one line.
  const flat = frame();
  flat[L.leftShoulder] = P(0.25, 0.70); flat[L.rightShoulder] = P(0.25, 0.71);
  flat[L.leftHip] = P(0.45, 0.70);      flat[L.rightHip] = P(0.45, 0.71);
  flat[L.leftKnee] = P(0.60, 0.70);     flat[L.rightKnee] = P(0.60, 0.71);
  flat[L.leftAnkle] = P(0.72, 0.70);    flat[L.rightAnkle] = P(0.72, 0.71);
  assert.ok(scorePhase(def, 'rest', flat) >= 70,
            `rest scored ${scorePhase(def, 'rest', flat)}`);
  assert.ok(scorePhase(def, 'raise', flat) < 70, 'flat must not pass raise');

  // Left leg raised ~45°, knee straight (hip→knee→ankle collinear).
  const raised = frame();
  raised[L.leftShoulder] = P(0.25, 0.70); raised[L.rightShoulder] = P(0.25, 0.71);
  raised[L.leftHip] = P(0.45, 0.70);      raised[L.rightHip] = P(0.45, 0.71);
  raised[L.leftKnee] = P(0.56, 0.59);     raised[L.rightKnee] = P(0.60, 0.71);
  raised[L.leftAnkle] = P(0.64, 0.51);    raised[L.rightAnkle] = P(0.72, 0.71);
  assert.ok(scorePhase(def, 'raise', raised) >= 70,
            `raise scored ${scorePhase(def, 'raise', raised)}`);
  assert.ok(scorePhase(def, 'rest', raised) < 70, 'raised must not pass rest');

  // Raised but knee bent: ankle hangs straight down from the knee.
  const bent = frame();
  bent[L.leftShoulder] = P(0.25, 0.70); bent[L.rightShoulder] = P(0.25, 0.71);
  bent[L.leftHip] = P(0.45, 0.70);      bent[L.rightHip] = P(0.45, 0.71);
  bent[L.leftKnee] = P(0.56, 0.59);     bent[L.rightKnee] = P(0.60, 0.71);
  bent[L.leftAnkle] = P(0.56, 0.70);    bent[L.rightAnkle] = P(0.72, 0.71);

  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0 };
  const obs = dark.FAULTS.SLR_RX;
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [bent, bent, bent, bent], gs),
                   ['slr_knee_straight']);

  // Straight-leg raise never faults; flat leg never faults (nothing raised).
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [raised, raised, raised, raised], gs), []);
  assert.deepEqual(runFaults(obs, [flat, flat, flat, flat], gs), []);
});

test('KNEE_TO_CHEST_RX: drawn-in knee scores the hold; flat legs do not', () => {
  const def = dark.PHASES.KNEE_TO_CHEST_RX;
  assert.equal(def.phases.length, 1);

  // Supine side view: left knee drawn toward the chest (hip angle ~55°).
  const drawn = frame();
  drawn[L.leftShoulder] = P(0.25, 0.70); drawn[L.rightShoulder] = P(0.25, 0.71);
  drawn[L.leftHip] = P(0.45, 0.70);      drawn[L.rightHip] = P(0.45, 0.71);
  // knee up-and-back toward the chest: ~55° from the shoulder direction
  drawn[L.leftKnee] = P(0.38, 0.58);     drawn[L.rightKnee] = P(0.60, 0.71);
  assert.ok(scorePhase(def, 'hold', drawn) >= 70,
            `drawn scored ${scorePhase(def, 'hold', drawn)}`);

  const flat = frame();
  flat[L.leftShoulder] = P(0.25, 0.70); flat[L.rightShoulder] = P(0.25, 0.71);
  flat[L.leftHip] = P(0.45, 0.70);      flat[L.rightHip] = P(0.45, 0.71);
  flat[L.leftKnee] = P(0.60, 0.70);     flat[L.rightKnee] = P(0.60, 0.71);
  assert.ok(scorePhase(def, 'hold', flat) < 70,
            `flat scored ${scorePhase(def, 'hold', flat)}`);
});

test('PRONE_KNEE_BEND_RX: flat/bent phases score in sequence; hip lift faults', () => {
  const def = dark.PHASES.PRONE_KNEE_BEND_RX;
  assert.equal(def.phases.length, 4);

  // Prone side view, body horizontal, legs flat.
  const flat = frame();
  flat[L.leftShoulder] = P(0.25, 0.70); flat[L.rightShoulder] = P(0.25, 0.71);
  flat[L.leftHip] = P(0.45, 0.70);      flat[L.rightHip] = P(0.45, 0.71);
  flat[L.leftKnee] = P(0.60, 0.70);     flat[L.rightKnee] = P(0.60, 0.71);
  flat[L.leftAnkle] = P(0.72, 0.70);    flat[L.rightAnkle] = P(0.72, 0.71);
  assert.ok(scorePhase(def, 'rest', flat) >= 70);
  assert.ok(scorePhase(def, 'bend', flat) < 70);

  // Left knee bent ~90°: shank rises vertically from the knee.
  const bent = frame();
  bent[L.leftShoulder] = P(0.25, 0.70); bent[L.rightShoulder] = P(0.25, 0.71);
  bent[L.leftHip] = P(0.45, 0.70);      bent[L.rightHip] = P(0.45, 0.71);
  bent[L.leftKnee] = P(0.60, 0.70);     bent[L.rightKnee] = P(0.60, 0.71);
  bent[L.leftAnkle] = P(0.60, 0.56);    bent[L.rightAnkle] = P(0.72, 0.71);
  assert.ok(scorePhase(def, 'bend', bent) >= 70,
            `bend scored ${scorePhase(def, 'bend', bent)}`);
  assert.ok(scorePhase(def, 'rest', bent) < 70);

  // Hip lift while bending: hip rises → working hip angle closes.
  const lifted = frame();
  lifted[L.leftShoulder] = P(0.25, 0.70); lifted[L.rightShoulder] = P(0.25, 0.71);
  lifted[L.leftHip] = P(0.45, 0.58);      lifted[L.rightHip] = P(0.45, 0.59);
  lifted[L.leftKnee] = P(0.60, 0.70);     lifted[L.rightKnee] = P(0.60, 0.71);
  lifted[L.leftAnkle] = P(0.60, 0.56);    lifted[L.rightAnkle] = P(0.72, 0.71);

  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0 };
  const obs = dark.FAULTS.PRONE_KNEE_BEND_RX;
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [lifted, lifted, lifted, lifted], gs),
                   ['prone_hips_flat']);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [bent, bent, bent, bent], gs), []);
  assert.deepEqual(runFaults(obs, [flat, flat, flat], gs), []);
});

// [VYAYAM-DARK-TESTS-END]
