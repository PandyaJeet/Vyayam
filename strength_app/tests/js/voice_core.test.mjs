/*
 * Phase F: node test harness for the voice core (pure parts only —
 * pickVoice ordering and the coach-clip phrase map).
 * Run:  node --test strength_app/tests/js/voice_core.test.mjs
 * (Not part of the Django suite — run manually or in CI where node exists.)
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const voice = require('../../static/strength_app/js/voice_core.js');

const V = (name, lang) => ({ name, lang });

test('prefers Google over Natural/Enhanced/Samantha/Ava, in order', () => {
  const voices = [
    V('Ava (Premium)', 'en-US'),
    V('Samantha', 'en-US'),
    V('Microsoft Aria Natural', 'en-US'),
    V('Google UK English Female', 'en-GB'),
    V('Fred', 'en-US'),
  ];
  assert.equal(voice.pickVoice(voices, 'en').name, 'Google UK English Female');

  const noGoogle = voices.filter(v => !v.name.includes('Google'));
  assert.equal(voice.pickVoice(noGoogle, 'en').name, 'Microsoft Aria Natural');

  const noNatural = noGoogle.filter(v => !v.name.includes('Natural'));
  assert.equal(voice.pickVoice(noNatural, 'en').name, 'Samantha');

  const noSamantha = noNatural.filter(v => v.name !== 'Samantha');
  assert.equal(voice.pickVoice(noSamantha, 'en').name, 'Ava (Premium)');
});

test('matches the page language, falls back to first language match', () => {
  const voices = [
    V('Google Deutsch', 'de-DE'),
    V('Anna', 'de-DE'),
    V('Fred', 'en-US'),
  ];
  // German page: the Google German voice wins.
  assert.equal(voice.pickVoice(voices, 'de-DE').name, 'Google Deutsch');
  // English page: no preferred-name English voice — first English match.
  assert.equal(voice.pickVoice(voices, 'en').name, 'Fred');
  // No voice for the page language at all → null (browser default).
  assert.equal(voice.pickVoice(voices, 'hi'), null);
  // Empty list → null.
  assert.equal(voice.pickVoice([], 'en'), null);
});

test('rate and pitch match the spec', () => {
  assert.equal(voice.RATE, 0.95);
  assert.equal(voice.PITCH, 1.0);
});

test('clip map: every spoken coach phrase resolves to a filename-safe key', () => {
  const keys = Object.values(voice.COACH_CLIPS);
  assert.ok(keys.length >= 25 && keys.length <= 35,
    `vocabulary should stay a fixed ~30-clip set (got ${keys.length})`);
  // Keys must be unique and filename-safe.
  assert.equal(new Set(keys).size, keys.length);
  for (const k of keys) assert.match(k, /^[a-z0-9_]+$/);
  // Spot checks: tempo cues + the Phase D ready cue are covered.
  assert.equal(voice.clipKeyFor('Slowly down'), 'slowly_down');
  assert.equal(voice.clipKeyFor('Hold'), 'hold');
  assert.equal(voice.clipKeyFor('Up'), 'up');
  assert.equal(voice.clipKeyFor(
    'Ready. Step into the outline and begin when you are set.'), 'ready_step_in');
  // Unknown phrases fall back to TTS (null key).
  assert.equal(voice.clipKeyFor('Some unmapped sentence'), null);
});

test('tryPlayClip is a safe no-op outside the browser', () => {
  assert.equal(voice.tryPlayClip('Hold'), false);
});

/* ── Part 3 (R6): tiered speech-queue policy ─────────────────────────────── */

test('tierFromPriority: legacy booleans map true→cue, false→flow; opts pass through', () => {
  assert.equal(voice.tierFromPriority(true), 'cue');
  assert.equal(voice.tierFromPriority(false), 'flow');
  assert.equal(voice.tierFromPriority(undefined), 'flow');
  assert.equal(voice.tierFromPriority({ tier: 'safety' }), 'safety');
  assert.equal(voice.tierFromPriority({ tier: 'cue' }), 'cue');
  assert.equal(voice.tierFromPriority({ tier: 'flow' }), 'flow');
  // Unknown tier falls back to the legacy truthiness path (object → cue).
  assert.equal(voice.tierFromPriority({ tier: 'shout' }), 'cue');
});

test('speechDecision: idle channel always speaks', () => {
  assert.equal(voice.speechDecision('safety', false), 'speak');
  assert.equal(voice.speechDecision('cue', false), 'speak');
  assert.equal(voice.speechDecision('flow', false), 'speak');
});

test('speechDecision: busy channel — safety cancels, cue queues, flow drops', () => {
  assert.equal(voice.speechDecision('safety', true), 'cancel_speak');
  assert.equal(voice.speechDecision('cue', true), 'queue');
  assert.equal(voice.speechDecision('flow', true), 'drop');
});

test('queueCue: max length 1 — a newer cue replaces a queued older cue', () => {
  const q1 = voice.queueCue([], { text: 'first' });
  assert.deepEqual(q1.map(i => i.text), ['first']);
  const q2 = voice.queueCue(q1, { text: 'second' });
  assert.deepEqual(q2.map(i => i.text), ['second']);
});

test('watchdogMs: 6s floor, scales with text length so long lines are never beheaded', () => {
  assert.equal(voice.watchdogMs('Up.'), 6000);
  assert.equal(voice.watchdogMs(''), 6000);
  const long = 'x'.repeat(120);
  assert.equal(voice.watchdogMs(long), 9600);
});

/* ── R6-P2: briefing tempo line ──────────────────────────────────────────── */

test('briefingTempoLine: words only, number only as a 3s+ pacing hint, never a countdown', () => {
  // Blank / 0-0-0-0 tempo → steady-pace line.
  assert.equal(voice.briefingTempoLine([0, 0, 0, 0]), 'Move at a steady, controlled pace.');
  assert.equal(voice.briefingTempoLine(null), 'Move at a steady, controlled pace.');
  // Short eccentric (<3s): no numbers at all.
  assert.equal(voice.briefingTempoLine([2, 1, 2, 0]),
    "We'll go slowly down, hold, then push up.");
  // 3s+ eccentric: number appears as a pacing hint word.
  assert.equal(voice.briefingTempoLine([3, 1, 2, 0]),
    "We'll go slowly down for a slow three count, hold, then push up.");
  // No hold → the hold clause is dropped.
  assert.equal(voice.briefingTempoLine([4, 0, 2, 0]),
    "We'll go slowly down for a slow four count, then push up.");
  // No digits ever leak into the sentence.
  for (const parts of [[3,1,2,0],[10,2,3,1],[2,0,2,0],[15,0,1,0]]) {
    assert.doesNotMatch(voice.briefingTempoLine(parts), /\d/);
  }
});

/* ── R6-P3: movement-synced tempo phrases ────────────────────────────────── */

test('tempoPhaseWord: phrase length matches phase duration, no numbers, 0s silent', () => {
  assert.equal(voice.tempoPhaseWord('ecc', 1), 'Down.');
  assert.equal(voice.tempoPhaseWord('ecc', 2), 'Slowly down.');
  assert.equal(voice.tempoPhaseWord('ecc', 3), 'Slowly… all the way down.');
  assert.equal(voice.tempoPhaseWord('ecc', 5), 'Slowly… all the way down.');
  assert.equal(voice.tempoPhaseWord('hold', 1), 'Hold.');
  assert.equal(voice.tempoPhaseWord('hold', 3), 'Hold.');
  assert.equal(voice.tempoPhaseWord('con', 1), 'Up.');
  assert.equal(voice.tempoPhaseWord('con', 2), 'Push up.');
  assert.equal(voice.tempoPhaseWord('con', 4), 'Slowly push up, squeeze.');
  assert.equal(voice.tempoPhaseWord('pause', 2), 'Reset.');
  // 0s / unprescribed phases are silent; unknown kind is silent.
  assert.equal(voice.tempoPhaseWord('ecc', 0), null);
  assert.equal(voice.tempoPhaseWord('pause', 0), null);
  assert.equal(voice.tempoPhaseWord('mystery', 3), null);
  // NO spoken numbers anywhere.
  for (const kind of ['ecc', 'hold', 'con', 'pause']) {
    for (let s = 1; s <= 10; s++) {
      const w = voice.tempoPhaseWord(kind, s);
      if (w) assert.doesNotMatch(w, /\d/);
    }
  }
});
