/*
 * Go / No-Go Pass: pure logic (schedule, speed ladder, scoring). No DOM.
 * Demo game. It is not a test of reaction time, ability or readiness.
 * Node-tested in exhibition_gonogo.test.mjs. The page wiring is exhibition_games.js.
 *
 * Speed ladder: a stimulus stays up START_MS (1200 ms, the slowest). After
 * STREAK_TO_RISE (3) correct answers in a row it shortens by STEP_MS (100 ms),
 * down to FLOOR_MS (600 ms, the fastest). Only the time changes. An error
 * restarts the streak and leaves the time as it is. The next stimulus replaces
 * the last one directly (no blank, no full-screen change), so the screen
 * changes at most 1000 / 600 = 1.67 times a second, under MAX_CHANGES_PER_S (3).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ExhibitionGoNoGo = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var ROUND_MS = 45000;
  var START_MS = 1200;      // ceiling on stimulus time (slowest)
  var FLOOR_MS = 600;       // floor on stimulus time (fastest)
  var STEP_MS = 100;
  var STREAK_TO_RISE = 3;
  var MIN_RT_MS = 150;      // taps faster than this are left out of the mean
  var MAX_CHANGES_PER_S = 3;
  var NOGO_SHARE = 0.3;
  var MAX_NOGO_RUN = 2;

  // Small seeded generator (mulberry32) so a schedule is repeatable in tests.
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // n kinds, 'go' (teammate) or 'nogo' (opponent). Starts with a go and never
  // has more than MAX_NOGO_RUN opponents in a row.
  function buildSchedule(n, seed) {
    var r = rng(seed), out = [], run = 0;
    for (var i = 0; i < n; i++) {
      var nogo = i > 0 && run < MAX_NOGO_RUN && r() < NOGO_SHARE;
      out.push(nogo ? 'nogo' : 'go');
      run = nogo ? run + 1 : 0;
    }
    return out;
  }

  function newLadder() { return { durMs: START_MS, streak: 0 }; }

  function step(state, correct) {
    if (!correct) return { durMs: state.durMs, streak: 0 };
    var streak = state.streak + 1;
    if (streak < STREAK_TO_RISE) return { durMs: state.durMs, streak: streak };
    return { durMs: Math.max(FLOOR_MS, state.durMs - STEP_MS), streak: 0 };
  }

  function changesPerSecond(durMs) { return 1000 / durMs; }

  // trial = { kind: 'go'|'nogo', tapped: bool, rtMs: number|null }
  function classify(trial) {
    if (trial.kind === 'go') {
      if (!trial.tapped) return 'miss';
      return trial.rtMs < MIN_RT_MS ? 'anticipation' : 'hit';
    }
    return trial.tapped ? 'false_alarm' : 'correct_reject';
  }

  function isCorrect(outcome) {
    return outcome === 'hit' || outcome === 'anticipation' || outcome === 'correct_reject';
  }

  // Accuracy = correct answers / answered stimuli (null if none).
  // Mean response time = mean of go taps of MIN_RT_MS or more (null if none).
  // Leaves out: taps on opponents (no-go errors), misses and taps under MIN_RT_MS.
  function score(trials) {
    var correct = 0, rts = [];
    trials.forEach(function (t) {
      var o = classify(t);
      if (isCorrect(o)) correct += 1;
      if (o === 'hit') rts.push(t.rtMs);
    });
    var sum = rts.reduce(function (a, b) { return a + b; }, 0);
    return {
      n: trials.length,
      correct: correct,
      accuracy: trials.length ? correct / trials.length : null,
      meanRtMs: rts.length ? sum / rts.length : null,
      rtCount: rts.length
    };
  }

  // Pass Window's Done screen says "Compare only with your own earlier sessions ...".
  // Nothing is saved here, so the page cuts that sentence from the text it shows.
  function dropEarlierSessions(text) {
    return String(text).replace(/\s*Compare only with your own earlier sessions[^.]*\./, '');
  }

  return {
    dropEarlierSessions: dropEarlierSessions,
    ROUND_MS: ROUND_MS, START_MS: START_MS, FLOOR_MS: FLOOR_MS, STEP_MS: STEP_MS,
    STREAK_TO_RISE: STREAK_TO_RISE, MIN_RT_MS: MIN_RT_MS,
    MAX_CHANGES_PER_S: MAX_CHANGES_PER_S,
    buildSchedule: buildSchedule, newLadder: newLadder, step: step,
    changesPerSecond: changesPerSecond, classify: classify, score: score
  };
});
