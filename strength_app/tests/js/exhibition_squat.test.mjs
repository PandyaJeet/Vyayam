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

test('stateKey: changes with mode, phase and rep; empty without state', () => {
  const a = { mode: 'ACTIVE', currentPhaseIndex: 0, repCount: 1 };
  assert.equal(ex.stateKey(null), '');
  assert.equal(ex.stateKey(a), ex.stateKey({ ...a }));
  assert.notEqual(ex.stateKey(a), ex.stateKey({ ...a, currentPhaseIndex: 1 }));
  assert.notEqual(ex.stateKey(a), ex.stateKey({ ...a, mode: 'DEMO' }));
  assert.notEqual(ex.stateKey(a), ex.stateKey({ ...a, repCount: 2 }));
});

const guard = require('../../static/strength_app/js/exhibition_guard.js');

test('fetch guard: a blocked POST resolves to a 204 response and never reaches the network', async () => {
  const calls = [];
  const win = { fetch: (...a) => { calls.push(a); return Promise.resolve(new Response('ok')); } };
  guard.install(win);
  const p = win.fetch('/x', { method: 'POST', body: '{}' });
  assert.ok(p instanceof Promise);
  const r = await p;
  assert.equal(r.status, 204);
  assert.equal((await win.fetch('/y', { method: 'delete' })).status, 204);
  assert.equal((await win.fetch(new Request('http://localhost/z', { method: 'PUT', body: 'a' }))).status, 204);
  assert.equal(calls.length, 0);
  assert.equal((await win.fetch('/g')).status, 200);
  assert.equal(calls.length, 1);
});
