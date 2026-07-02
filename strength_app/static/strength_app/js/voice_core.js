/*
 * Phase F: VyayamVoice — the friendlier coach voice.
 *
 * Part 1 (live): pick the best available system voice — names containing
 * Google > Natural > Enhanced > Samantha > Ava, in that preference order,
 * matching the page language — falling back to any language-matching voice,
 * then the browser default. Rate 0.95, pitch 1.0. Voices load async in some
 * browsers, so the pick is re-run on `voiceschanged`.
 *
 * Part 2 (dormant scaffold): the coaching vocabulary is a fixed clip set.
 * When static/strength_app/audio/coach/<key>.mp3 exists, that cue plays the
 * file; when absent, it falls back to speechSynthesis. NO audio files ship
 * with the app — see the README in the audio/coach directory for the exact
 * clip list to record.
 *
 * UMD like cv_core.js so the pure parts run under node
 * (tests/js/voice_core.test.mjs). Browser-only pieces guard on `window`.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.VyayamVoice = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {

  var PREFERRED_NAME_TOKENS = ['Google', 'Natural', 'Enhanced', 'Samantha', 'Ava'];
  var RATE = 0.95;
  var PITCH = 1.0;
  var CLIP_BASE = '/static/strength_app/audio/coach/';

  /* ── Part 1: voice selection ──────────────────────────────────────────── */

  // Pure: pick from a voices array for a page language ('en', 'en-IN', …).
  // Preference tokens are tried in order across the language-matching set;
  // returns the first language match if no token hits; null if none match.
  function pickVoice(voices, pageLang) {
    if (!voices || !voices.length) return null;
    var langPrefix = String(pageLang || 'en').split('-')[0].toLowerCase();
    var candidates = voices.filter(function (v) {
      return v.lang && v.lang.toLowerCase().split('-')[0] === langPrefix;
    });
    if (!candidates.length) return null;
    for (var i = 0; i < PREFERRED_NAME_TOKENS.length; i++) {
      var token = PREFERRED_NAME_TOKENS[i];
      for (var j = 0; j < candidates.length; j++) {
        if (candidates[j].name && candidates[j].name.indexOf(token) !== -1) {
          return candidates[j];
        }
      }
    }
    return candidates[0];
  }

  var _picked;  // undefined = not yet computed; null = keep browser default

  function bestVoice() {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null;
    if (_picked !== undefined) return _picked;
    var lang = (document.documentElement && document.documentElement.lang) || 'en';
    _picked = pickVoice(window.speechSynthesis.getVoices(), lang);
    return _picked;
  }

  // Voices arrive async in Chrome/Android — re-pick when the list changes.
  if (typeof window !== 'undefined' && 'speechSynthesis' in window &&
      window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.addEventListener('voiceschanged', function () {
      _picked = undefined;
      bestVoice();
    });
  }

  // Apply the friendlier profile to an utterance: best voice, rate, pitch.
  function applyTo(utt) {
    utt.rate = RATE;
    utt.pitch = PITCH;
    var v = bestVoice();
    if (v) { utt.voice = v; utt.lang = v.lang; }
    return utt;
  }

  /* ── Part 2: coach clip scaffold (dormant until files exist) ──────────── */

  // The fixed coaching vocabulary: EXACT spoken phrase → clip key.
  // File expected at CLIP_BASE + <key> + '.mp3'.
  var COACH_CLIPS = {
    // Tempo phase cues (TempoCoach)
    'Slowly down': 'slowly_down',
    'Hold': 'hold',
    'Up': 'up',
    'Pause': 'pause',
    // Session flow
    'Watch me first. I will show you the movement.': 'watch_me_first',
    'Watch me. I will show you the movement.': 'watch_me',
    'One more time. Watch the movement.': 'one_more_time',
    'Now you try. Step into me.': 'now_you_try',
    'Ready. Step into the outline and begin when you are set.': 'ready_step_in',
    'Good... hold it right there...': 'good_hold_there',
    'Timer starting. Hold it.': 'timer_starting',
    'Rest over. Next set.': 'rest_over',
    'Next set.': 'next_set',
    'Set complete! Great work.': 'set_complete',
    'Last one. Give it everything.': 'last_one',
    // Short encouragements
    'Nice. One.': 'nice_one',
    'Two. Keep it up.': 'two_keep_it_up',
    'Beautiful. Hold it right there.': 'beautiful_hold',
    'Looking good. Just a little more.': 'looking_good',
    "You're getting there. Keep going.": 'getting_there',
    // Bare rep counts (announceRep speaks these as plain digits)
    '1': 'num_1', '2': 'num_2', '3': 'num_3', '4': 'num_4', '5': 'num_5',
    '6': 'num_6', '7': 'num_7', '8': 'num_8', '9': 'num_9', '10': 'num_10',
  };

  function clipKeyFor(text) {
    return COACH_CLIPS.hasOwnProperty(text) ? COACH_CLIPS[text] : null;
  }

  // key → 'probing' | 'missing' | HTMLAudioElement (ready)
  var _clips = {};
  var _currentClip = null;

  function _probe(key) {
    _clips[key] = 'probing';
    var audio = new Audio();
    audio.preload = 'auto';
    audio.addEventListener('canplaythrough', function () { _clips[key] = audio; });
    audio.addEventListener('error', function () { _clips[key] = 'missing'; });
    audio.src = CLIP_BASE + key + '.mp3';
  }

  // Play the clip for this exact phrase if its file exists. Returns true when
  // the file plays (caller skips speechSynthesis). While a clip is still
  // probing — or absent — returns false so TTS covers the cue. Files dropped
  // into audio/coach/ are picked up without any code or config change.
  function tryPlayClip(text) {
    if (typeof window === 'undefined' || typeof Audio === 'undefined') return false;
    var key = clipKeyFor(text);
    if (!key) return false;
    var state = _clips[key];
    if (state === undefined) { _probe(key); return false; }
    if (state === 'probing' || state === 'missing') return false;
    try {
      stopClip();
      state.currentTime = 0;
      state.play();
      _currentClip = state;
      return true;
    } catch (e) {
      return false;
    }
  }

  function stopClip() {
    if (_currentClip && !_currentClip.paused) {
      try { _currentClip.pause(); } catch (e) { /* already stopped */ }
    }
    _currentClip = null;
  }

  return {
    PREFERRED_NAME_TOKENS: PREFERRED_NAME_TOKENS,
    RATE: RATE,
    PITCH: PITCH,
    CLIP_BASE: CLIP_BASE,
    COACH_CLIPS: COACH_CLIPS,
    pickVoice: pickVoice,
    bestVoice: bestVoice,
    applyTo: applyTo,
    clipKeyFor: clipKeyFor,
    tryPlayClip: tryPlayClip,
    stopClip: stopClip,
  };
});
