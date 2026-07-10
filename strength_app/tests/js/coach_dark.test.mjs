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

// [VYAYAM-DARK-TESTS-END]
