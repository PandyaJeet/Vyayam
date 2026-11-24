/*
 * Node test harness for the pure form-quality gradient (UNWIRED).
 * Run:  node --test strength_app/tests/js/form_gradient.test.mjs
 * (Not part of the Django suite — run manually or in CI where node exists.)
 *
 * No page loads the module yet. The last test enforces that; delete it in
 * the phase that wires the gradient into the camera page.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const G = require('../../static/strength_app/js/form_gradient.js');

const GREEN_OUT = { r: 0, g: 255, b: 120, band: 'green' };
const ORANGE_OUT = { r: 255, g: 140, b: 0, band: 'orange' };
const RED_OUT = { r: 255, g: 50, b: 50, band: 'red' };
const NEUTRAL_OUT = { r: 195, g: 205, b: 215, band: 'neutral' };

const BAND_RANK = { green: 0, yellow_green: 1, yellow: 2, orange: 3 };

const REAL_TRENDS = ['improving', 'steady', 'worsening'];
// Near-misses must behave exactly like "no trend".
const JUNK_TRENDS = [undefined, null, '', 'Worsening', 'IMPROVING', ' improving',
  'bogus', 1, true, {}];
const ALL_TRENDS = [...REAL_TRENDS, ...JUNK_TRENDS];

// diff -5..200 in 0.5 steps (integer stepping, so no float drift).
const SWEEP = [];
for (let i = -10; i <= 400; i++) SWEEP.push(i / 2);
const POSITIVE_SWEEP = SWEEP.filter((d) => d >= 0);
const EXTREME_DIFFS = [1e9, -1e9, NaN, Infinity, -Infinity, null, undefined];
const ALL_DIFFS = [...SWEEP, ...EXTREME_DIFFS];

function show(v) {
  return typeof v === 'string' ? JSON.stringify(v) : String(v);
}

// Cheap exact match; falls back to deepEqual only to print a readable diff.
function assertOut(out, want, where) {
  const same = Object.keys(out).length === 4 &&
    out.r === want.r && out.g === want.g && out.b === want.b && out.band === want.band;
  if (!same) assert.deepEqual(out, want, where);
}

function assertShape(out, where) {
  const keys = Object.keys(out).sort().join(',');
  if (keys !== 'b,band,g,r') assert.fail(`${where}: keys are ${keys}`);
  for (const ch of ['r', 'g', 'b']) {
    const v = out[ch];
    if (!(Number.isInteger(v) && v >= 0 && v <= 255)) assert.fail(`${where}: ${ch}=${v}`);
  }
}

test('exports exactly the five API names; CONFIG and COLORS match the spec and are frozen', () => {
  assert.deepEqual(Object.keys(G).sort(),
    ['COLORS', 'CONFIG', 'formColor', 'stabilizeDiff', 'trendFromErrors']);
  for (const fn of ['formColor', 'trendFromErrors', 'stabilizeDiff']) {
    assert.equal(typeof G[fn], 'function', fn);
  }
  assert.deepEqual(G.CONFIG,
    { greenMaxDeg: 10, yellowDeg: 20, orangeDeg: 40, trendBiasDeg: 5, deadbandDeg: 2 });
  assert.deepEqual(G.COLORS, {
    GREEN: { r: 0, g: 255, b: 120 },
    YELLOW: { r: 255, g: 220, b: 0 },
    ORANGE: { r: 255, g: 140, b: 0 },
    RED: { r: 255, g: 50, b: 50 },
    NEUTRAL: { r: 195, g: 205, b: 215 },
  });
  assert.ok(Object.isFrozen(G.CONFIG), 'CONFIG frozen');
  assert.ok(Object.isFrozen(G.COLORS), 'COLORS frozen');
  for (const name of Object.keys(G.COLORS)) {
    assert.ok(Object.isFrozen(G.COLORS[name]), `COLORS.${name} frozen`);
  }
});

test('red is unreachable unless safetyFlag === true', () => {
  const NOT_TRUE_SAFETY = [false, 0, 1, 'true', {}, undefined, null];
  const NOT_FROZEN = [undefined, false];
  let checked = 0;
  for (const diffDeg of ALL_DIFFS) {
    for (const trend of ALL_TRENDS) {
      for (const safetyFlag of NOT_TRUE_SAFETY) {
        for (const frozen of NOT_FROZEN) {
          const out = G.formColor({ diffDeg, trend, safetyFlag, frozen });
          const where = `diff=${show(diffDeg)} trend=${show(trend)} ` +
            `safetyFlag=${show(safetyFlag)} frozen=${show(frozen)}`;
          assert.notEqual(out.band, 'red', where);
          assert.ok(!(out.r === 255 && out.g === 50 && out.b === 50), where);
          // Every gradient/neutral color keeps g >= 140 (ORANGE); red's g is 50.
          assert.ok(out.g >= 140, where);
          assertShape(out, where);
          checked++;
        }
      }
    }
  }
  assert.equal(checked,
    ALL_DIFFS.length * ALL_TRENDS.length * NOT_TRUE_SAFETY.length * NOT_FROZEN.length);
});

test('safetyFlag === true returns red for any diff and any trend', () => {
  const DIFFS = [...ALL_DIFFS, '15', '', {}, [], true, 15n];
  const NOT_FROZEN = [undefined, false, null, 0, 1, 'true', {}];
  for (const diffDeg of DIFFS) {
    for (const trend of ALL_TRENDS) {
      for (const frozen of NOT_FROZEN) {
        assertOut(G.formColor({ diffDeg, trend, safetyFlag: true, frozen }), RED_OUT,
          `diff=${show(diffDeg)} trend=${show(trend)} frozen=${show(frozen)}`);
      }
    }
  }
});

test('frozen === true overrides everything, even safetyFlag; only strict true freezes', () => {
  for (const diffDeg of [...ALL_DIFFS, '15', {}]) {
    for (const trend of ALL_TRENDS) {
      for (const safetyFlag of [true, false, undefined, 1]) {
        assertOut(G.formColor({ diffDeg, trend, safetyFlag, frozen: true }), NEUTRAL_OUT,
          `diff=${show(diffDeg)} trend=${show(trend)} safetyFlag=${show(safetyFlag)}`);
      }
    }
  }
  // Truthy-but-not-true values do not freeze.
  for (const frozen of [1, 'true', {}, [], 0, false, null, undefined]) {
    assertOut(G.formColor({ diffDeg: 0, frozen }), GREEN_OUT, `frozen=${show(frozen)}`);
    assertOut(G.formColor({ diffDeg: 50, frozen }), ORANGE_OUT, `frozen=${show(frozen)}`);
  }
});

test("monotonic with trend 'steady': r never drops, g never rises, bands never go back", () => {
  let prev = null;
  const bandsSeen = [];
  for (const diffDeg of POSITIVE_SWEEP) {
    const out = G.formColor({ diffDeg, trend: 'steady' });
    assert.ok(Object.hasOwn(BAND_RANK, out.band), `diff=${diffDeg}: unexpected band ${out.band}`);
    if (prev) {
      assert.ok(out.r >= prev.r, `r dropped at diff=${diffDeg}`);
      assert.ok(out.g <= prev.g, `g rose at diff=${diffDeg}`);
      assert.ok(BAND_RANK[out.band] >= BAND_RANK[prev.band], `band went back at diff=${diffDeg}`);
    }
    if (bandsSeen[bandsSeen.length - 1] !== out.band) bandsSeen.push(out.band);
    prev = out;
  }
  // The sweep visits all four bands, once each, in order.
  assert.deepEqual(bandsSeen, ['green', 'yellow_green', 'yellow', 'orange']);
});

test('band edges and anchor colors follow the spec', () => {
  const cases = [
    [0, { r: 0, g: 255, b: 120, band: 'green' }],
    [10, { r: 0, g: 255, b: 120, band: 'green' }],
    [10.5, { r: 13, g: 253, b: 114, band: 'yellow_green' }],
    [15, { r: 128, g: 238, b: 60, band: 'yellow_green' }],
    [20, { r: 255, g: 220, b: 0, band: 'yellow' }],
    [29.5, { r: 255, g: 182, b: 0, band: 'yellow' }],
    [30, { r: 255, g: 180, b: 0, band: 'orange' }],
    [40, { r: 255, g: 140, b: 0, band: 'orange' }],
    [40.5, { r: 255, g: 140, b: 0, band: 'orange' }],
  ];
  for (const [diffDeg, want] of cases) {
    assert.deepEqual(G.formColor({ diffDeg }), want, `diff=${diffDeg}`);
  }
});

test('improving is never worse than steady, worsening never better; each shifts a band somewhere', () => {
  let improvingShifted = false;
  let worseningShifted = false;
  for (const diffDeg of SWEEP) {
    const s = G.formColor({ diffDeg, trend: 'steady' });
    const i = G.formColor({ diffDeg, trend: 'improving' });
    const w = G.formColor({ diffDeg, trend: 'worsening' });
    const at = `diff=${diffDeg}`;
    assert.ok(BAND_RANK[i.band] <= BAND_RANK[s.band], `improving band worse at ${at}`);
    assert.ok(i.r <= s.r && i.g >= s.g, `improving color worse at ${at}`);
    assert.ok(BAND_RANK[w.band] >= BAND_RANK[s.band], `worsening band better at ${at}`);
    assert.ok(w.r >= s.r && w.g <= s.g, `worsening color better at ${at}`);
    if (BAND_RANK[i.band] < BAND_RANK[s.band]) improvingShifted = true;
    if (BAND_RANK[w.band] > BAND_RANK[s.band]) worseningShifted = true;
  }
  assert.ok(improvingShifted, 'improving never moved a band in the sweep');
  assert.ok(worseningShifted, 'worsening never moved a band in the sweep');
  // Concrete witnesses.
  assert.equal(G.formColor({ diffDeg: 12, trend: 'steady' }).band, 'yellow_green');
  assert.equal(G.formColor({ diffDeg: 12, trend: 'improving' }).band, 'green');
  assert.equal(G.formColor({ diffDeg: 16, trend: 'steady' }).band, 'yellow_green');
  assert.equal(G.formColor({ diffDeg: 16, trend: 'worsening' }).band, 'yellow');
  // Improving floors the error at zero.
  assertOut(G.formColor({ diffDeg: 3, trend: 'improving' }), GREEN_OUT, 'diff=3 improving');
});

test('any trend value other than the three exact strings changes nothing', () => {
  for (const diffDeg of SWEEP) {
    const base = G.formColor({ diffDeg });
    assertOut(G.formColor({ diffDeg, trend: 'steady' }), base, `diff=${diffDeg} trend="steady"`);
    for (const trend of JUNK_TRENDS) {
      assertOut(G.formColor({ diffDeg, trend }), base, `diff=${diffDeg} trend=${show(trend)}`);
    }
  }
});

test('diff sign does not matter; large diffs clamp to ORANGE', () => {
  for (const diffDeg of SWEEP) {
    for (const trend of ALL_TRENDS) {
      assertOut(G.formColor({ diffDeg: -diffDeg, trend }), G.formColor({ diffDeg, trend }),
        `diff=${diffDeg} trend=${show(trend)}`);
    }
  }
  // Far past orangeDeg: ORANGE for every trend, improving included.
  for (const diffDeg of [46, 100, 1e6, 1e9, -1e9, Number.MAX_VALUE, -Number.MAX_VALUE]) {
    for (const trend of ALL_TRENDS) {
      assertOut(G.formColor({ diffDeg, trend }), ORANGE_OUT, `diff=${diffDeg} trend=${show(trend)}`);
    }
  }
  // Just past orangeDeg with no trend.
  assertOut(G.formColor({ diffDeg: 40.5 }), ORANGE_OUT, 'diff=40.5');
  assertOut(G.formColor({ diffDeg: -41 }), ORANGE_OUT, 'diff=-41');
});

test('invalid input returns neutral and never throws; formColor() with no argument is neutral', () => {
  assert.deepEqual(G.formColor(), NEUTRAL_OUT);
  for (const opts of [undefined, null, {}, [], 5, 'x', true]) {
    let out;
    assert.doesNotThrow(() => { out = G.formColor(opts); }, `opts=${show(opts)}`);
    assertOut(out, NEUTRAL_OUT, `opts=${show(opts)}`);
  }
  const BAD_DIFFS = [undefined, null, NaN, Infinity, -Infinity, '15', '', '0', {}, [], [15],
    true, false, new Number(15), 15n];
  for (const diffDeg of BAD_DIFFS) {
    for (const trend of ALL_TRENDS) {
      let out;
      assert.doesNotThrow(() => { out = G.formColor({ diffDeg, trend }); },
        `diff=${show(diffDeg)} trend=${show(trend)}`);
      assertOut(out, NEUTRAL_OUT, `diff=${show(diffDeg)} trend=${show(trend)}`);
    }
  }
});

test('trendFromErrors: improving, worsening, deadband steady, invalid -> steady', () => {
  assert.equal(G.trendFromErrors(20, 15), 'improving');
  assert.equal(G.trendFromErrors(10, 15), 'worsening');
  // Inside the 2-degree deadband.
  assert.equal(G.trendFromErrors(10, 11.5), 'steady');
  assert.equal(G.trendFromErrors(10, 8.5), 'steady');
  assert.equal(G.trendFromErrors(10, 10), 'steady');
  // Exactly at the deadband counts as a real change.
  assert.equal(G.trendFromErrors(10, 12), 'worsening');
  assert.equal(G.trendFromErrors(12, 10), 'improving');
  // Magnitudes are compared, not signs.
  assert.equal(G.trendFromErrors(-10, 14), 'worsening');
  assert.equal(G.trendFromErrors(10, -7), 'improving');
  assert.equal(G.trendFromErrors(-10, 10), 'steady');
  // Any invalid argument -> steady.
  for (const bad of [undefined, null, NaN, Infinity, -Infinity, '10', '', {}, [], true]) {
    assert.equal(G.trendFromErrors(bad, 10), 'steady', `prev=${show(bad)}`);
    assert.equal(G.trendFromErrors(10, bad), 'steady', `curr=${show(bad)}`);
    assert.equal(G.trendFromErrors(bad, bad), 'steady', `both=${show(bad)}`);
  }
  assert.equal(G.trendFromErrors(), 'steady');
});

test('stabilizeDiff: deadband holds, real change passes, invalid input handled', () => {
  // Inside the deadband the shown value holds.
  assert.equal(G.stabilizeDiff(20, 21.9), 20);
  assert.equal(G.stabilizeDiff(20, 18.1), 20);
  assert.equal(G.stabilizeDiff(20, 20), 20);
  // At or past the deadband the new value passes.
  assert.equal(G.stabilizeDiff(20, 22), 22);
  assert.equal(G.stabilizeDiff(20, 18), 18);
  assert.equal(G.stabilizeDiff(20, 15), 15);
  // The spec compares the signed difference, not magnitudes.
  assert.equal(G.stabilizeDiff(20, -20), -20);
  // Invalid new -> previous returned unchanged (same reference for objects).
  for (const bad of [undefined, null, NaN, Infinity, -Infinity, '25', {}, true]) {
    assert.equal(G.stabilizeDiff(20, bad), 20, `new=${show(bad)}`);
  }
  const prevRef = {};
  assert.equal(G.stabilizeDiff(prevRef, NaN), prevRef);
  // Invalid previous -> new.
  for (const bad of [undefined, null, NaN, Infinity, '20', {}]) {
    assert.equal(G.stabilizeDiff(bad, 25), 25, `prev=${show(bad)}`);
  }
  // Both invalid -> previous unchanged.
  assert.equal(G.stabilizeDiff(undefined, NaN), undefined);
  assert.equal(G.stabilizeDiff(null, 'x'), null);
  assert.ok(Number.isNaN(G.stabilizeDiff(NaN, undefined)));
});

test('stabilizeDiff: 200 noisy frames of edge +/- 0.9 produce zero band flips', () => {
  // Deterministic noise in [-0.9, 0.9]: Park-Miller LCG with a fixed seed,
  // first 10 frames forced to the +/-0.9 extremes.
  function noisyFrames(center, n, seed) {
    let s = seed;
    const frames = [];
    for (let k = 0; k < n; k++) {
      s = (s * 16807) % 2147483647;
      let noise = ((s / 2147483647) * 2 - 1) * 0.9;
      if (k < 10) noise = (k % 2 === 0) ? 0.9 : -0.9;
      frames.push(center + noise);
    }
    return frames;
  }
  function bandFlips(values) {
    let flips = 0;
    let prevBand = null;
    for (const v of values) {
      const band = G.formColor({ diffDeg: v, trend: 'steady' }).band;
      if (prevBand !== null && band !== prevBand) flips++;
      prevBand = band;
    }
    return flips;
  }
  // 20 is the edge the spec names; 10 and 30 are the other two band edges.
  for (const center of [20, 10, 30]) {
    const raw = noisyFrames(center, 200, 42 + center);
    assert.equal(raw.length, 200);
    assert.ok(raw.every((v) => Math.abs(v - center) <= 0.9 + 1e-9), `noise out of range at ${center}`);
    // Control: without stabilizing, this jitter does flip bands.
    assert.ok(bandFlips(raw) > 0, `raw frames never crossed the edge at ${center}`);
    let shown;
    const stabilized = raw.map((v) => (shown = G.stabilizeDiff(shown, v)));
    assert.equal(bandFlips(stabilized), 0, `stabilized frames flipped at ${center}`);
  }
});

test('inputs are never mutated; CONFIG/COLORS unchanged; every result is a fresh object', () => {
  const configBefore = JSON.stringify(G.CONFIG);
  const colorsBefore = JSON.stringify(G.COLORS);
  // Frozen options: a write anywhere in the (strict-mode) module would throw.
  for (const diffDeg of ALL_DIFFS) {
    for (const trend of REAL_TRENDS) {
      for (const safetyFlag of [true, false]) {
        for (const frozen of [true, false]) {
          const opts = Object.freeze({ diffDeg, trend, safetyFlag, frozen });
          assert.doesNotThrow(() => G.formColor(opts));
        }
      }
    }
  }
  // A plain options object is left exactly as it was.
  const plain = { diffDeg: 25, trend: 'worsening', safetyFlag: false, frozen: false };
  const copy = { ...plain };
  G.formColor(plain);
  assert.deepEqual(plain, copy);
  // Exported constants untouched by all of the above.
  assert.equal(JSON.stringify(G.CONFIG), configBefore);
  assert.equal(JSON.stringify(G.COLORS), colorsBefore);
  // Results are fresh: editing one never leaks into COLORS or the next call.
  const first = G.formColor({ diffDeg: 0 });
  first.r = 999;
  first.band = 'edited';
  assertOut(G.formColor({ diffDeg: 0 }), GREEN_OUT, 'after editing a result');
  assert.deepEqual(G.COLORS.GREEN, { r: 0, g: 255, b: 120 });
  const red = G.formColor({ safetyFlag: true });
  assert.notEqual(red, G.COLORS.RED);
  red.g = 0;
  assert.equal(G.COLORS.RED.g, 50);
});

test('UNWIRED: no template references the gradient module (delete in the wiring phase)', () => {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const roots = [
    path.resolve(here, '../../templates'),                   // strength_app/templates
    path.resolve(here, '../../../therapist_app/templates'),
  ];
  let scanned = 0;
  for (const root of roots) {
    for (const rel of readdirSync(root, { recursive: true })) {
      const name = String(rel);
      if (!name.endsWith('.html')) continue;
      const text = readFileSync(path.join(root, name), 'utf8');
      assert.ok(!text.includes('form_gradient') && !text.includes('VyayamFormGradient'),
        `${name} references the gradient module`);
      scanned++;
    }
  }
  assert.ok(scanned > 0, 'no templates scanned; did the template folders move?');
});
