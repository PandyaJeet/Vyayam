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
