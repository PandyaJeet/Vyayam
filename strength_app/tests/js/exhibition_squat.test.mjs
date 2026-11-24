/* Run: node --test strength_app/tests/js/exhibition_squat.test.mjs */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ex = require('../../static/strength_app/js/exhibition_squat.js');

test('shouldReset: only at or after the limit', () => {
  assert.equal(ex.shouldReset(59999, 0, 60000), false);
  assert.equal(ex.shouldReset(60000, 0, 60000), true);
  assert.equal(ex.shouldReset(70000, 20000, 60000), false);
});

test('noFrames: frame seen means no failure, timeout without frame means failure', () => {
  const live = { videoWidth: 640, readyState: 4 };
  const dead = { videoWidth: 0, readyState: 0 };
  assert.equal(ex.noFrames(live, 0, 20000, 10000), false);
  assert.equal(ex.noFrames(dead, 0, 9999, 10000), false);
  assert.equal(ex.noFrames(dead, 0, 10000, 10000), true);
  assert.equal(ex.noFrames(null, 0, 10000, 10000), true);
});
