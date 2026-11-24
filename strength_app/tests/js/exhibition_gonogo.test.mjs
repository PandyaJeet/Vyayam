/* Run: node --test strength_app/tests/js/exhibition_gonogo.test.mjs */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const g = require('../../static/strength_app/js/exhibition_gonogo.js');

test('ladder: three correct in a row shorten the time by one step, then the streak restarts', () => {
  let s = g.newLadder();
  assert.deepEqual(s, { durMs: 1200, streak: 0 });
  s = g.step(s, true); s = g.step(s, true);
  assert.deepEqual(s, { durMs: 1200, streak: 2 });
  s = g.step(s, true);
  assert.deepEqual(s, { durMs: 1100, streak: 0 });
});

test('ladder: an error restarts the streak and keeps the time', () => {
  let s = { durMs: 1000, streak: 2 };
  s = g.step(s, false);
  assert.deepEqual(s, { durMs: 1000, streak: 0 });
});

test('ladder: never goes below the 600 ms floor or above the 1200 ms ceiling', () => {
  let s = g.newLadder();
  for (let i = 0; i < 200; i++) {
    s = g.step(s, true);
    assert.ok(s.durMs >= 600 && s.durMs <= 1200);
  }
  assert.equal(s.durMs, 600);
  for (let i = 0; i < 20; i++) s = g.step(s, false);
  assert.equal(s.durMs, 600);
});

test('ladder: at most 3 screen changes per second at every rung', () => {
  for (let d = g.START_MS; d >= g.FLOOR_MS; d -= g.STEP_MS) {
    assert.ok(g.changesPerSecond(d) <= g.MAX_CHANGES_PER_S, String(d));
  }
});

test('classify: the five outcomes and the 150 ms edge', () => {
  assert.equal(g.classify({ kind: 'go', tapped: true, rtMs: 150 }), 'hit');
  assert.equal(g.classify({ kind: 'go', tapped: true, rtMs: 149.9 }), 'anticipation');
  assert.equal(g.classify({ kind: 'go', tapped: false, rtMs: null }), 'miss');
  assert.equal(g.classify({ kind: 'nogo', tapped: true, rtMs: 400 }), 'false_alarm');
  assert.equal(g.classify({ kind: 'nogo', tapped: false, rtMs: null }), 'correct_reject');
});

test('mean response time leaves out no-go errors, taps under 150 ms and misses', () => {
  const s = g.score([
    { kind: 'go', tapped: true, rtMs: 400 },
    { kind: 'go', tapped: true, rtMs: 600 },
    { kind: 'go', tapped: true, rtMs: 100 },      // too fast: left out
    { kind: 'nogo', tapped: true, rtMs: 300 },    // no-go error: left out
    { kind: 'go', tapped: false, rtMs: null },    // miss: no time
    { kind: 'nogo', tapped: false, rtMs: null }
  ]);
  assert.equal(s.meanRtMs, 500);
  assert.equal(s.rtCount, 2);
});

test('accuracy: correct answers over answered stimuli', () => {
  const s = g.score([
    { kind: 'go', tapped: true, rtMs: 400 },       // correct
    { kind: 'go', tapped: true, rtMs: 100 },       // correct (fast tap still a tap)
    { kind: 'nogo', tapped: true, rtMs: 300 },     // wrong
    { kind: 'go', tapped: false, rtMs: null },     // wrong
    { kind: 'nogo', tapped: false, rtMs: null }    // correct
  ]);
  assert.equal(s.correct, 3);
  assert.equal(s.accuracy, 0.6);
});

test('score: an empty round gives null, not NaN', () => {
  const s = g.score([]);
  assert.equal(s.accuracy, null);
  assert.equal(s.meanRtMs, null);
  const only = g.score([{ kind: 'nogo', tapped: false, rtMs: null }]);
  assert.equal(only.accuracy, 1);
  assert.equal(only.meanRtMs, null);
});

test('schedule: same seed same list, starts with go, no run of 3 opponents, mix of both', () => {
  const a = g.buildSchedule(200, 7), b = g.buildSchedule(200, 7);
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, g.buildSchedule(200, 8));
  assert.equal(a[0], 'go');
  assert.ok(a.includes('nogo') && a.includes('go'));
  assert.ok(!a.join(',').includes('nogo,nogo,nogo'));
});

test('round is 45 s', () => { assert.equal(g.ROUND_MS, 45000); });
