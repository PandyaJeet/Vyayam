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

test('SUPINE_ABD_RX: center/out phases score by spread; pelvis shift faults', () => {
  const def = dark.PHASES.SUPINE_ABD_RX;
  assert.equal(def.phases.length, 4);

  // Feet-view supine: hips ~0.14 wide, ankles just outside the hips.
  const center = frame();
  center[L.leftHip] = P(0.43, 0.45);   center[L.rightHip] = P(0.57, 0.45);
  center[L.leftAnkle] = P(0.42, 0.80); center[L.rightAnkle] = P(0.58, 0.80);
  assert.ok(scorePhase(def, 'center', center) >= 70,
            `center scored ${scorePhase(def, 'center', center)}`);
  assert.ok(scorePhase(def, 'out', center) < 70);

  // Left leg slid out: ankle spread ~2x hip width.
  const out = frame();
  out[L.leftHip] = P(0.43, 0.45);   out[L.rightHip] = P(0.57, 0.45);
  out[L.leftAnkle] = P(0.30, 0.80); out[L.rightAnkle] = P(0.58, 0.80);
  assert.ok(scorePhase(def, 'out', out) >= 70,
            `out scored ${scorePhase(def, 'out', out)}`);
  assert.ok(scorePhase(def, 'center', out) < 70);

  // Pelvis shift: whole pelvis drifts left while legs stay put.
  const shifted = frame();
  shifted[L.leftHip] = P(0.33, 0.45);   shifted[L.rightHip] = P(0.47, 0.45);
  shifted[L.leftAnkle] = P(0.42, 0.80); shifted[L.rightAnkle] = P(0.58, 0.80);

  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0 };
  const obs = dark.FAULTS.SUPINE_ABD_RX;
  obs.resetSet(); obs._lastAt = {};
  // First frame sets the baseline from the centered pose, then the shift
  // sustains past the window → one cue.
  assert.deepEqual(runFaults(obs, [center, shifted, shifted, shifted, shifted], gs),
                   ['pelvis_still']);
  // A clean set never faults.
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [center, out, center, out], gs), []);
});

test('SIDELYING_ABD_RX: stacked/lifted phases score; roll-back faults', () => {
  const def = dark.PHASES.SIDELYING_ABD_RX;
  assert.equal(def.phases.length, 4);

  // Sidelying front view: body horizontal, ankles stacked (~same y).
  const down = frame();
  down[L.leftShoulder] = P(0.25, 0.64); down[L.rightShoulder] = P(0.26, 0.62);
  down[L.leftAnkle] = P(0.75, 0.66);    down[L.rightAnkle] = P(0.75, 0.61);
  assert.ok(scorePhase(def, 'down', down) >= 70,
            `down scored ${scorePhase(def, 'down', down)}`);
  assert.ok(scorePhase(def, 'lift', down) < 70);

  // Top leg lifted ~45°: top ankle well above the bottom one.
  const lift = frame();
  lift[L.leftShoulder] = P(0.25, 0.64); lift[L.rightShoulder] = P(0.26, 0.62);
  lift[L.leftAnkle] = P(0.75, 0.66);    lift[L.rightAnkle] = P(0.72, 0.34);
  assert.ok(scorePhase(def, 'lift', lift) >= 70,
            `lift scored ${scorePhase(def, 'lift', lift)}`);
  assert.ok(scorePhase(def, 'down', lift) < 70);

  // Roll-back: shoulders splay apart horizontally (torso opening up).
  const rolled = frame();
  rolled[L.leftShoulder] = P(0.20, 0.64); rolled[L.rightShoulder] = P(0.40, 0.60);
  rolled[L.leftAnkle] = P(0.75, 0.66);    rolled[L.rightAnkle] = P(0.72, 0.34);

  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0 };
  const obs = dark.FAULTS.SIDELYING_ABD_RX;
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [rolled, rolled, rolled, rolled], gs),
                   ['hips_stacked']);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [lift, lift, lift, lift], gs), []);
});

test('PRESS_DB_RX: rack/lockout phases score; asymmetric press faults', () => {
  const def = dark.PHASES.PRESS_DB_RX;
  assert.equal(def.phases.length, 4);

  // Front view. Racked: elbows bent ~85° at the shoulders.
  const rack = frame();
  rack[L.leftShoulder] = P(0.40, 0.30); rack[L.rightShoulder] = P(0.60, 0.30);
  rack[L.leftElbow] = P(0.38, 0.44);    rack[L.rightElbow] = P(0.62, 0.44);
  rack[L.leftWrist] = P(0.52, 0.42);    rack[L.rightWrist] = P(0.48, 0.42);
  const rackScore = scorePhase(def, 'rack', rack);
  assert.ok(rackScore >= 70, `rack scored ${rackScore}`);
  assert.ok(scorePhase(def, 'press', rack) < 70);

  // Lockout: both arms straight overhead.
  const up = frame();
  up[L.leftShoulder] = P(0.40, 0.30); up[L.rightShoulder] = P(0.60, 0.30);
  up[L.leftElbow] = P(0.40, 0.19);    up[L.rightElbow] = P(0.60, 0.19);
  up[L.leftWrist] = P(0.41, 0.08);    up[L.rightWrist] = P(0.59, 0.08);
  assert.ok(scorePhase(def, 'lockout', up) >= 70,
            `lockout scored ${scorePhase(def, 'lockout', up)}`);
  assert.ok(scorePhase(def, 'rack', up) < 70);

  // Asymmetric: left arm locked out, right still racked.
  const uneven = frame();
  uneven[L.leftShoulder] = P(0.40, 0.30); uneven[L.rightShoulder] = P(0.60, 0.30);
  uneven[L.leftElbow] = P(0.40, 0.19);    uneven[L.rightElbow] = P(0.62, 0.44);
  uneven[L.leftWrist] = P(0.41, 0.08);    uneven[L.rightWrist] = P(0.48, 0.42);

  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0 };
  const obs = dark.FAULTS.PRESS_DB_RX;
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [uneven, uneven, uneven, uneven], gs),
                   ['press_even']);
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [up, up, up, up], gs), []);
});

test('ROW_BAND_RX: reach/pull phases score; lean-back faults', () => {
  const def = dark.PHASES.ROW_BAND_RX;
  assert.equal(def.phases.length, 4);

  // Side view seated: trunk upright, arms long in front (elbow ~straight).
  const reach = frame();
  reach[L.leftShoulder] = P(0.40, 0.30); reach[L.rightShoulder] = P(0.41, 0.30);
  reach[L.leftHip] = P(0.40, 0.55);      reach[L.rightHip] = P(0.41, 0.55);
  reach[L.leftKnee] = P(0.55, 0.60);     reach[L.rightKnee] = P(0.56, 0.60);
  reach[L.leftElbow] = P(0.52, 0.36);    reach[L.rightElbow] = P(0.53, 0.36);
  reach[L.leftWrist] = P(0.64, 0.42);    reach[L.rightWrist] = P(0.65, 0.42);
  assert.ok(scorePhase(def, 'reach', reach) >= 70,
            `reach scored ${scorePhase(def, 'reach', reach)}`);
  assert.ok(scorePhase(def, 'pull', reach) < 70);

  // Pulled: elbow bent to ~70°, wrist back at the ribs.
  const pull = frame();
  pull[L.leftShoulder] = P(0.40, 0.30); pull[L.rightShoulder] = P(0.41, 0.30);
  pull[L.leftHip] = P(0.40, 0.55);      pull[L.rightHip] = P(0.41, 0.55);
  pull[L.leftKnee] = P(0.55, 0.60);     pull[L.rightKnee] = P(0.56, 0.60);
  pull[L.leftElbow] = P(0.44, 0.44);    pull[L.rightElbow] = P(0.45, 0.44);
  pull[L.leftWrist] = P(0.53, 0.38);    pull[L.rightWrist] = P(0.54, 0.38);
  assert.ok(scorePhase(def, 'pull', pull) >= 70,
            `pull scored ${scorePhase(def, 'pull', pull)}`);
  assert.ok(scorePhase(def, 'reach', pull) < 70);

  // Lean-back: shoulders travel behind the hips (trunk opens well past
  // the upright baseline).
  const lean = frame();
  lean[L.leftShoulder] = P(0.28, 0.34); lean[L.rightShoulder] = P(0.29, 0.34);
  lean[L.leftHip] = P(0.40, 0.55);      lean[L.rightHip] = P(0.41, 0.55);
  lean[L.leftKnee] = P(0.55, 0.60);     lean[L.rightKnee] = P(0.56, 0.60);
  lean[L.leftElbow] = P(0.44, 0.44);    lean[L.rightElbow] = P(0.45, 0.44);
  lean[L.leftWrist] = P(0.53, 0.38);    lean[L.rightWrist] = P(0.54, 0.38);

  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0 };
  const obs = dark.FAULTS.ROW_BAND_RX;
  obs.resetSet(); obs._lastAt = {};
  // Baseline set from the upright reach, then the lean sustains → one cue.
  assert.deepEqual(runFaults(obs, [reach, lean, lean, lean, lean], gs),
                   ['row_sit_tall']);
  // Clean rowing never faults.
  obs.resetSet(); obs._lastAt = {};
  assert.deepEqual(runFaults(obs, [reach, pull, reach, pull], gs), []);
});

// ── CURL (bicep_curls) — the one LIVE coach in this file ────────────────
// Side-view synthetic frames. The user faces +x (nose right of the
// shoulders); the LEFT side is nearest the camera (vis 1), the right arm is
// hidden (vis 0.2, junk points).
const DEG = Math.PI / 180;
/** Rotate (x, y) by `deg` in image coords (y down). */
function rot(x, y, deg) {
  const c = Math.cos(deg * DEG), s = Math.sin(deg * DEG);
  return [x * c - y * s, x * s + y * c];
}
/**
 * One side-view curl frame. elbow = near-arm shoulder-elbow-wrist angle;
 * flex = upper arm swung forward from the trunk line; tilt = trunk lean
 * (+ = shoulders ahead of the hips toward +x).
 */
function curlFrame(elbow, { flex = 0, tilt = 0, junk = 0 } = {}) {
  const lm = frame();
  const H = { x: 0.50, y: 0.55 };
  const S = { x: H.x + 0.25 * Math.sin(tilt * DEG), y: H.y - 0.25 * Math.cos(tilt * DEG) };
  // Upper arm: trunk-down direction, rotated forward by flex.
  const [dx, dy] = rot(H.x - S.x, H.y - S.y, -flex);
  const n = Math.hypot(dx, dy);
  const E = { x: S.x + 0.14 * dx / n, y: S.y + 0.14 * dy / n };
  // Forearm: (S - E) rotated toward the front by `elbow` degrees.
  const [fx, fy] = rot(S.x - E.x, S.y - E.y, elbow);
  const fn = Math.hypot(fx, fy);
  const W = { x: E.x + 0.12 * fx / fn, y: E.y + 0.12 * fy / fn };
  lm[L.nose] = P(S.x + 0.05, S.y - 0.10);
  lm[L.leftShoulder] = P(S.x, S.y);     lm[L.leftElbow] = P(E.x, E.y);
  lm[L.leftWrist] = P(W.x, W.y);        lm[L.leftHip] = P(H.x, H.y);
  lm[L.leftKnee] = P(0.50, 0.72);       lm[L.leftAnkle] = P(0.50, 0.90);
  // Hidden far arm: low visibility, junk positions.
  lm[L.rightShoulder] = P(0.30 + junk, 0.10, 0.2);
  lm[L.rightElbow] = P(0.80, 0.20 + junk, 0.2);
  lm[L.rightWrist] = P(0.10 + junk, 0.70, 0.2);
  lm[L.rightHip] = P(0.51, 0.55, 0.2);
  return lm;
}
/** Template rule: >= 70 for 5 frames advances; phases in order; rep at the end. */
function walkReps(def, elbows) {
  let idx = 0, frames = 0, reps = 0;
  for (const e of elbows) {
    const s = cv.computeMatchScore(def.checkAngles(curlFrame(e)), def.phases[idx].joints);
    frames = s >= 70 ? frames + 1 : Math.max(0, frames - 1);
    if (frames >= 5) {
      idx++; frames = 0;
      if (idx >= def.phases.length) { reps++; idx = 1; }
    }
  }
  return reps;
}
const ramp = (a, b, n) => Array.from({ length: n }, (_, i) => a + (b - a) * (i + 1) / n);
const fullCurl = () => [...ramp(165, 45, 12), ...Array(12).fill(40),
                        ...ramp(45, 170, 12), ...Array(8).fill(175)];
const CURL_DARK_KEYS = ['WALL_SIT_RX', 'PLANK_RX', 'SIDE_PLANK_RX', 'BALANCE_RX',
  'SLR_RX', 'KNEE_TO_CHEST_RX', 'PRONE_KNEE_BEND_RX', 'SUPINE_ABD_RX',
  'SIDELYING_ABD_RX', 'PRESS_DB_RX', 'ROW_BAND_RX'];

test('CURL N1: 4 phases start/lift/hold/lower, side view, not a hold', () => {
  const def = dark.PHASES.CURL;
  assert.deepEqual(def.phases.map((p) => p.name), ['start', 'lift', 'hold', 'lower']);
  assert.deepEqual(def.phases.map((p) => p.joints.elbow), [165, 45, 45, 165]);
  assert.equal(def.cameraPosition.view, 'side');
  assert.equal(def.bodyOrientation, 'standing');
  assert.ok(def.commonMistake);
  assert.ok(dark.FAULTS.CURL);
});

test('CURL N2: side-view scoring - down, curled, mid, over-curl, locked', () => {
  const def = dark.PHASES.CURL;
  const down = curlFrame(175), up = curlFrame(40), mid = curlFrame(105);
  assert.ok(Math.abs(def.checkAngles(curlFrame(120)).elbow - 120) < 0.5, 'raw angle reads true');
  for (const ph of ['start', 'lower']) assert.ok(scorePhase(def, ph, down) >= 70, ph);
  assert.ok(scorePhase(def, 'lift', down) < 70);
  for (const ph of ['lift', 'hold']) assert.ok(scorePhase(def, ph, up) >= 70, ph);
  assert.ok(scorePhase(def, 'start', up) < 70);
  for (const ph of ['start', 'lift', 'hold', 'lower']) {
    assert.ok(scorePhase(def, ph, mid) < 70, `mid passed ${ph}`);
  }
  // Over-curl past 45 still matches the top; locked past 165 the bottom.
  assert.ok(scorePhase(def, 'lift', curlFrame(25)) >= 70, 'over-curl');
  assert.ok(scorePhase(def, 'start', curlFrame(180)) >= 70, 'locked elbow');
  // Edge of the 20-degree band: 65 counts, 70 does not.
  assert.ok(scorePhase(def, 'lift', curlFrame(64)) >= 70);
  assert.ok(scorePhase(def, 'lift', curlFrame(70)) < 70);
});

test('CURL N3: near arm wins; far-arm junk never changes the angle', () => {
  const def = dark.PHASES.CURL;
  for (const e of [170, 100, 50]) {
    const a = def.checkAngles(curlFrame(e, { junk: 0 })).elbow;
    const b = def.checkAngles(curlFrame(e, { junk: 0.15 })).elbow;
    assert.equal(a, b, `junk moved the angle at ${e}`);
  }
  // Mirror: right side near, left side hidden -> right arm is read.
  const m = curlFrame(60);
  for (const [l, r] of [[L.leftShoulder, L.rightShoulder], [L.leftElbow, L.rightElbow],
                        [L.leftWrist, L.rightWrist], [L.leftHip, L.rightHip]]) {
    const t = m[l]; m[l] = m[r]; m[r] = t;
  }
  assert.ok(Math.abs(def.checkAngles(m).elbow - 60) < 0.5);
});

test('CURL N4: rep model - full curls count, half and unstraightened do not', () => {
  const def = dark.PHASES.CURL;
  const start = Array(8).fill(170);
  const full = [...start, ...fullCurl(), ...fullCurl(), ...fullCurl()];
  assert.equal(walkReps(def, full), 3);
  const half = () => [...ramp(165, 95, 8), ...Array(10).fill(95), ...ramp(95, 165, 8), ...Array(6).fill(170)];
  assert.equal(walkReps(def, [...start, ...half(), ...half(), ...half()]), 0);
  const bentBack = () => [...ramp(130, 45, 10), ...Array(12).fill(40), ...ramp(45, 130, 10), ...Array(8).fill(130)];
  assert.equal(walkReps(def, [...start, ...ramp(170, 130, 4), ...bentBack(), ...bentBack(), ...bentBack()]), 0);
  // Phase-1 hover at 90 never advances.
  assert.equal(walkReps(def, [...start, ...Array(60).fill(90)]), 0);
});

test('CURL N4b: far-arm-only curls (alternating) do not count for the near arm', () => {
  const def = dark.PHASES.CURL;
  // The hidden arm curls while the near arm stays long: angle stays ~170.
  const frames = [];
  for (let k = 0; k < 40; k++) frames.push(curlFrame(170, { junk: (k % 5) * 0.03 }));
  let idx = 0, n = 0, reps = 0;
  for (const lm of frames) {
    const s = cv.computeMatchScore(def.checkAngles(lm), def.phases[idx].joints);
    n = s >= 70 ? n + 1 : Math.max(0, n - 1);
    if (n >= 5) { idx++; n = 0; if (idx >= def.phases.length) { reps++; idx = 1; } }
  }
  assert.equal(reps, 0);
  assert.equal(idx, 1, 'stuck waiting for the near-arm lift');
});

test('CURL N5: swing, lean, hover each fire their cue; clean curl is silent', () => {
  const obs = dark.FAULTS.CURL;
  const gs = { mode: 'USER_FOLLOWS', isHoldExercise: false, repCount: 0, currentPhaseIndex: 1 };
  const fresh = () => { obs.resetSet(); obs._lastAt = {}; };

  const swing = curlFrame(160, { flex: 45 });
  fresh();
  assert.deepEqual(runFaults(obs, [swing, swing, swing, swing], gs), ['curl_elbows_still']);

  const upright = curlFrame(160), lean = curlFrame(160, { tilt: 20 });
  fresh();
  assert.deepEqual(runFaults(obs, [upright, lean, lean, lean, lean], gs), ['curl_stand_tall']);
  // Leaning back the other way is also caught.
  const leanBack = curlFrame(160, { tilt: -20 });
  fresh();
  assert.deepEqual(runFaults(obs, [upright, leanBack, leanBack, leanBack, leanBack], gs),
                   ['curl_stand_tall']);

  const hover = curlFrame(90);
  fresh();
  assert.deepEqual(runFaults(obs, Array(9).fill(hover), gs), ['curl_full_range']);
  // Hover shorter than 1.5 s, or outside the lift phase, stays silent.
  fresh();
  assert.deepEqual(runFaults(obs, Array(7).fill(hover), gs), []);
  fresh();
  assert.deepEqual(runFaults(obs, Array(12).fill(hover), { ...gs, currentPhaseIndex: 3 }), []);
  // Hover is a USER_FOLLOWS cue only (the ghost is still leading).
  fresh();
  assert.deepEqual(runFaults(obs, Array(12).fill(hover), { ...gs, mode: 'GHOST_LEADS' }), []);

  // Clean strict curl (165 -> 45 -> 165, 200 ms a frame) is silent, even in phase 1.
  const clean = [165, 150, 135, 120, 105, 90, 75, 60, 45, 40, 40, 45, 60, 75, 90, 105,
                 120, 135, 150, 165, 170].map((e) => curlFrame(e));
  fresh();
  assert.deepEqual(runFaults(obs, clean, gs), []);
  // Small natural movement (flex 20, tilt 8) is still clean.
  fresh();
  assert.deepEqual(runFaults(obs, clean.map((_, i) =>
    curlFrame(165 - i * 5, { flex: 20, tilt: i ? 8 : 0 })), gs), []);
  // Faults stay silent while waiting / in the demo.
  fresh();
  assert.deepEqual(runFaults(obs, [swing, swing, swing, swing], { ...gs, mode: 'WAITING' }), []);

  // resetSet clears the lean baseline: a new set that starts leaning is the
  // new baseline and does not fire.
  fresh();
  assert.deepEqual(runFaults(obs, [lean, lean, lean, lean, lean], gs), []);
});

test('CURL N6: curlGhost rotates only the forearms to the asked angle', () => {
  const base = curlFrame(175);
  // Give the far arm a real pose so both arms are checked.
  base[L.rightShoulder] = P(0.51, 0.30); base[L.rightElbow] = P(0.51, 0.44);
  base[L.rightWrist] = P(0.52, 0.56);    base[L.rightHip] = P(0.51, 0.55);
  const fixed = [L.leftShoulder, L.rightShoulder, L.leftElbow, L.rightElbow,
                 L.leftHip, L.rightHip, L.leftKnee, L.rightKnee, L.leftAnkle, L.rightAnkle, L.nose];
  for (const d of [165, 90, 45]) {
    const g = dark.curlGhost(base, d);
    assert.notEqual(g, base, 'returns a copy');
    for (const [s, e, w] of [[L.leftShoulder, L.leftElbow, L.leftWrist],
                             [L.rightShoulder, L.rightElbow, L.rightWrist]]) {
      const a = cv.calcAngle(g[s], g[e], g[w]);
      assert.ok(Math.abs(a - d) <= 1, `arm ${s} at ${d}: ${a}`);
    }
    for (const i of fixed) {
      assert.equal(g[i].x, base[i].x, `x moved ${i}`);
      assert.equal(g[i].y, base[i].y, `y moved ${i}`);
    }
    if (d === 90) {
      assert.ok(g[L.leftWrist].x > g[L.leftElbow].x, 'wrist on the nose side');
      assert.ok(g[L.rightWrist].x > g[L.rightElbow].x, 'far wrist on the nose side');
    }
  }
  // Facing the other way: the forearm swings to -x.
  const mirror = base.map((p) => P(1 - p.x, p.y, p.visibility));
  const gm = dark.curlGhost(mirror, 90);
  assert.ok(gm[L.leftWrist].x < gm[L.leftElbow].x);
  // Input is not mutated.
  assert.ok(Math.abs(cv.calcAngle(base[L.leftShoulder], base[L.leftElbow], base[L.leftWrist]) - 175) < 0.5);
});

test('CURL N7: the 11 dark coaches are still there, nothing else added', () => {
  assert.deepEqual(Object.keys(dark.PHASES).filter((k) => k !== 'CURL'), CURL_DARK_KEYS);
  assert.deepEqual(Object.keys(dark.FAULTS).filter((k) => k !== 'CURL'), CURL_DARK_KEYS);
  for (const id of ['curl_elbows_still', 'curl_stand_tall', 'curl_full_range']) {
    assert.ok(dark.CUE_IDS.includes(id), id);
  }
});

// [VYAYAM-DARK-TESTS-END]
