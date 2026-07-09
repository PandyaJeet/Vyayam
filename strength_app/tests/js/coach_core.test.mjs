/*
 * R4: node test harness for the coaching arbitration core.
 * Run:  node --test strength_app/tests/js/coach_core.test.mjs
 * (Not part of the Django suite — run manually or in CI where node exists.)
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const coach = require('../../static/strength_app/js/coach_core.js');

function freshArbiter(setNumber = 2, targetReps = 10) {
  // setNumber 2 by default so calibration (first set) doesn't interfere.
  const a = coach.createArbiter();
  a.setStarted(setNumber, targetReps);
  return a;
}

test('one cue at a time: lower priority never interrupts, safety always does', () => {
  const a = freshArbiter();
  assert.equal(a.requestCue('chest_up', 1000).action, 'speak');
  // Channel occupied — a refinement request is suppressed…
  assert.equal(a.requestCue('feet_together', 1500).action, 'suppress');
  // …and so is another primary…
  assert.equal(a.requestCue('hips_level', 2000).action, 'suppress');
  // …but safety interrupts immediately, mid-occupancy.
  const safety = a.requestCue('knee_valgus', 2100);
  assert.equal(safety.action, 'speak');
  assert.equal(safety.interrupt, true);
});

test('minimum one full rep between spoken cues (safety exempt)', () => {
  const a = freshArbiter();
  assert.equal(a.requestCue('chest_up', 0).action, 'speak');
  // Same rep, occupancy elapsed — still suppressed (rep spacing).
  assert.equal(a.requestCue('hips_level', 5000).action, 'suppress');
  a.repClosed(1, 80, [], 5100);
  assert.equal(a.requestCue('hips_level', 9000).action, 'speak');
  // Safety ignores rep spacing.
  assert.equal(a.requestCue('knee_valgus', 9100).action, 'speak');
});

test('refinement cues never fire in the final 2 reps; safety still can', () => {
  const a = freshArbiter(2, 10);
  a.repClosed(8, 80, [], 0);          // rep 8 of 10 → final-2 window
  assert.equal(a.requestCue('feet_together', 10000).action, 'suppress');
  assert.equal(a.requestCue('knee_valgus', 10001).action, 'speak');
  // Primary movement faults still allowed in the final reps.
  a.repClosed(9, 80, [], 10500);
  assert.equal(a.requestCue('chest_up', 20000).action, 'speak');
});

test('3-strike fading: quality line once, then silence, set flagged', () => {
  const a = freshArbiter();
  let now = 0;
  for (let rep = 1; rep <= 3; rep++) {
    const d = a.requestCue('hips_level', now);
    assert.equal(d.action, 'speak', `strike ${rep}`);
    a.repClosed(rep, 60, [], now + 100);   // never corrected
    now += 10000;
  }
  // 4th attempt: the one-time quality-over-count line…
  const fadeLine = a.requestCue('hips_level', now);
  assert.equal(fadeLine.action, 'speak');
  assert.equal(fadeLine.text, coach.LINES.fade);
  // …then pure silence on that cue for the set.
  a.repClosed(4, 60, [], now + 100);
  assert.equal(a.requestCue('hips_level', now + 10000).action, 'suppress');
  assert.deepEqual(a.cueResistantIds(), ['hips_level']);
  // New set clears the fade.
  a.setStarted(3, 10);
  assert.equal(a.requestCue('hips_level', now + 20000).action, 'speak');
});

test('corrected cue earns ONE specific reinforcement, then silence', () => {
  const a = freshArbiter();
  a.requestCue('knee_valgus', 0);
  const closed = a.repClosed(1, 80, ['knee_valgus'], 3000);
  assert.deepEqual(closed.lines, ['Better — knees are tracking now']);
  // A second correction in the same set does not praise again.
  a.requestCue('chest_up', 12000);
  const closed2 = a.repClosed(2, 80, ['chest_up'], 15000);
  assert.deepEqual(closed2.lines, []);
});

test('independent praise: only after 3 good reps, max one per set, varied', () => {
  const a = freshArbiter();
  assert.deepEqual(a.repClosed(1, 80, [], 0).lines, []);
  assert.deepEqual(a.repClosed(2, 82, [], 5000).lines, []);
  const third = a.repClosed(3, 85, [], 10000);
  assert.equal(third.lines.length, 1);
  assert.ok(coach.PRAISE_POOL.includes(third.lines[0]));
  // Streak continues — but the set already had its praise.
  assert.deepEqual(a.repClosed(4, 90, [], 15000).lines, []);
  // Next set praises again with the NEXT pool line (rotation).
  a.setStarted(3, 10);
  a.repClosed(1, 80, [], 20000); a.repClosed(2, 80, [], 25000);
  const next = a.repClosed(3, 80, [], 30000);
  assert.equal(next.lines[0], coach.PRAISE_POOL[1]);
  // A bad rep resets the streak.
  const b = freshArbiter();
  b.repClosed(1, 80, [], 0); b.repClosed(2, 40, [], 5000);
  b.repClosed(3, 80, [], 10000);
  assert.deepEqual(b.repClosed(4, 80, [], 15000).lines, []);
});

test('calibration: first set opens frozen + announced, only safety passes, ends after 2 reps', () => {
  const a = coach.createArbiter();
  const start = a.setStarted(1, 10);
  assert.equal(start.line, coach.LINES.calibration);
  assert.equal(a.colorsFrozen(), true);
  assert.equal(a.requestCue('chest_up', 0).action, 'suppress');
  assert.equal(a.requestCue('knee_valgus', 100).action, 'speak');
  a.repClosed(1, 50, [], 4000);
  assert.equal(a.colorsFrozen(), true);
  a.repClosed(2, 55, [], 8000);
  assert.equal(a.colorsFrozen(), false);
  assert.equal(a.requestCue('chest_up', 20000).action, 'speak');
  // Second set never re-calibrates.
  a.setStarted(2, 10);
  assert.equal(a.colorsFrozen(), false);
});

test('confidence gate: trips after 1s, speaks once per episode, resumes', () => {
  const a = freshArbiter();
  assert.equal(a.confidence(false, 0).frozen, false);      // not yet 1s
  const tripped = a.confidence(false, 1100);
  assert.equal(tripped.frozen, true);
  assert.equal(tripped.line, coach.LINES.confidence);
  assert.equal(a.confidence(false, 2000).line, null);      // no nagging
  assert.equal(a.requestCue('chest_up', 2100).action, 'suppress');
  assert.equal(a.requestCue('knee_valgus', 2200).action, 'suppress');  // NEVER cue on low confidence
  const back = a.confidence(true, 3000);
  assert.equal(back.frozen, false);
  // A fresh episode may speak again.
  a.confidence(false, 10000);
  assert.equal(a.confidence(false, 11500).line, coach.LINES.confidence);
});

test('fatigue mode: safety only + one announcement at next set start', () => {
  const a = freshArbiter();
  a.setFatigued();
  assert.equal(a.requestCue('chest_up', 0).action, 'suppress');
  assert.equal(a.requestCue('feet_together', 1).action, 'suppress');
  assert.equal(a.requestCue('knee_valgus', 2).action, 'speak');
  const start = a.setStarted(3, 10);
  assert.equal(start.line, coach.LINES.fatigue);
  assert.equal(a.setStarted(4, 10).line, null);  // announced once
});

test('tempo channel yields to cues; adjust line max once per set', () => {
  const a = freshArbiter();
  assert.equal(a.tempoAllowed(0), true);
  a.requestCue('chest_up', 1000);
  assert.equal(a.tempoAllowed(2000), false);   // cue owns the channel
  assert.equal(a.tempoAllowed(4000), true);    // released after occupancy
  assert.equal(a.tempoAdjustLine('fast'), 'A bit quick — slow the lowering');
  assert.equal(a.tempoAdjustLine('fast'), null);
  a.setStarted(3, 10);
  assert.ok(a.tempoAdjustLine('slow'));
});

test('calibrated target math: their range + 5°, clamped both ways', () => {
  // Textbook squat bottom knee 90°. Shallower mover (120°) → 115°.
  assert.equal(coach.calibratedTarget(90, 120), 115);
  // Within 10° of textbook → textbook stands.
  assert.equal(coach.calibratedTarget(90, 96), 90);
  // Deeper than textbook → never demand more than textbook.
  assert.equal(coach.calibratedTarget(90, 80), 90);
  // Garbage-shallow calibration → 40° floor above textbook.
  assert.equal(coach.calibratedTarget(90, 170), 130);
  // Missing data → unchanged.
  assert.equal(coach.calibratedTarget(90, undefined), 90);
});

test('every registry cue is <=8 words and never a fault-label', () => {
  const banned = /wrong|bad|rounding|cave|don't|do not|stop/i;
  // R6-P4/HOTFIX: exact-wording cues shipped verbatim per Pawan (authored
  // strings; depth line must stay comfort-conditional). Only these may
  // exceed the 8-word registry convention, each capped at its shipped length.
  const exactAuthored = {
    squat_knee_over_toe: 10,
    squat_depth_gentle: 10,
    squat_too_deep: 11,
    squat_asymmetry: 11,
  };
  for (const [id, def] of Object.entries(coach.CUES)) {
    const words = def.text.split(/\s+/).length;
    const cap = exactAuthored[id] || 8;
    assert.ok(words <= cap, `${id}: ${words} words`);
    assert.ok(!banned.test(def.text), `${id}: fault-label phrasing`);
    assert.ok(['safety', 'primary', 'refinement'].includes(def.priority));
  }
});
