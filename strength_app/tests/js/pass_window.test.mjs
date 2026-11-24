/* Pass Window pure helpers. Run: node --test strength_app/tests/js/pass_window.test.mjs */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const pw = require('../../static/strength_app/js/pass_window.js');
const scenarios = JSON.parse(readFileSync(
  new URL('../../mind_lab/pass_window_scenarios.json', import.meta.url), 'utf8'));
const byId = (id) => scenarios.find((s) => s.id === id);

test('closing time is base divided by Time Assist factor', () => {
  assert.equal(pw.closingMs(4000, 0.5), 8000);
  assert.equal(pw.closingMs(4000, 1.0), 4000);
});

test('Level 5 limit applies only at level 5 and only when shorter', () => {
  assert.equal(pw.trialLimitMs(5, 4000, 1.0, 3000), 3000);
  assert.equal(pw.trialLimitMs(5, 4000, 1.0, 9000), 4000);
  assert.equal(pw.trialLimitMs(4, 4000, 0.85, 3000), 4000 / 0.85);
});

test('judge: best, acceptable, wrong', () => {
  const sc = byId('PD-008');
  assert.equal(pw.judge(sc, 'T1:direct'), 'best');
  assert.equal(pw.judge(sc, 'T3:direct'), 'acceptable');
  assert.equal(pw.judge(sc, 'T2:direct'), 'wrong');
});

test('gap choice only from Level 3 and only when a gap option exists', () => {
  assert.deepEqual(pw.laneChoices(byId('PD-003'), 3), ['direct', 'gap(D1-D2)']);
  assert.deepEqual(pw.laneChoices(byId('PD-003'), 2), []);
  assert.deepEqual(pw.laneChoices(byId('PD-006'), 4), []);
});

test('mirror flips x, keeps ids and answers', () => {
  const m = pw.mirror(byId('PD-008'));
  assert.deepEqual(m.carrier, [55, 35]);
  assert.equal(m.correct, 'T1:direct');
  assert.deepEqual(m.defenders[0].to, [55, 38]);
  assert.deepEqual(byId('PD-008').carrier, [45, 35]);
});

test('median', () => {
  assert.equal(pw.median([]), null);
  assert.equal(pw.median([3, 1, 2]), 2);
  assert.equal(pw.median([1, 2, 3, 4]), 2.5);
});
