/*
 * Exhibition squat page wrapper (no edits to the camera template or camera JS).
 * Pure parts (shouldReset, noFrames) are node-tested in exhibition_squat.test.mjs.
 * The DOM part runs only when window.EXH_CFG is set by exhibition_squat.html.
 *
 * Page flow: Start screen -> tap -> unlock speech, startCamera() -> coaching.
 * A reload is the reset: it releases the camera (pagehide handler in the
 * camera template) and returns to the Start screen.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ExhibitionSquat = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // True when nothing has happened for limitMs. All times in ms.
  function shouldReset(now, lastActivity, limitMs) {
    return (now - lastActivity) >= limitMs;
  }

  // True when the camera was granted at startedAt but still shows no frame.
  // video: {videoWidth, readyState}.
  function noFrames(video, startedAt, now, timeoutMs) {
    var hasFrame = !!(video && video.videoWidth > 0 && video.readyState >= 2);
    return !hasFrame && (now - startedAt) >= timeoutMs;
  }

  // One string that changes whenever the coach moves on (mode, phase or rep).
  function stateKey(gs) {
    return gs ? [gs.mode, gs.currentPhaseIndex, gs.repCount].join(':') : '';
  }

  // Start-tap sequence: demo play 1, demo play 2, then the camera. Each method returns
  // {do: 'play', n} or {do: 'camera'} (or null when nothing changes). An error or the
  // timeout goes straight to the camera. Once it returned 'camera' it stays silent.
  function createSequencer(plays, timeoutMs) {
    var startedAt = 0, played = 0, done = false;
    function toCamera() { done = true; return { do: 'camera' }; }
    return {
      start: function (now) { startedAt = now; return { do: 'play', n: 1 }; },
      ended: function () {
        if (done) return null;
        played += 1;
        return played >= plays ? toCamera() : { do: 'play', n: played + 1 };
      },
      error: function () { return done ? null : toCamera(); },
      tick: function (now) {
        return (!done && (now - startedAt) >= timeoutMs) ? toCamera() : null;
      },
      isDone: function () { return done; }
    };
  }

  return { shouldReset: shouldReset, noFrames: noFrames, stateKey: stateKey,
           createSequencer: createSequencer };
});

// ---- DOM wiring (browser only) ------------------------------------------
(function () {
  if (typeof window === 'undefined' || !window.EXH_CFG) return;
  var CFG = window.EXH_CFG;
  var core = window.ExhibitionSquat;
  var $ = function (id) { return document.getElementById(id); };
  var S = window.__exh;               // shared state set by the early script
  var lastActivity = Date.now();
  var camStartedAt = 0;
  var lastReps = '';
  var lastState = '';

  function touch() { lastActivity = Date.now(); }

  function fail(reason) {
    if (S.failed) return;
    S.failed = true;
    window._cameraFailed = true;       // makes the template's own fallback a no-op
    try { console.warn('exhibition: camera failed:', reason); } catch (e) {}
    try {
      var v = $('cameraFeed');
      var st = v && v.srcObject;
      if (st && st.getTracks) st.getTracks().forEach(function (t) { t.stop(); });
    } catch (e) {}
    $('exhFail').style.display = 'flex';
    var vid = $('exhFailVideo');
    try { vid.load(); var p = vid.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
    touch();
  }
  S.fail = fail;
  if (S.pendingFail) fail(S.pendingFail);

  // Restart the failure-panel clip from the top.
  function replay(id) {
    var v = $(id);
    if (!v) return;
    try { v.currentTime = 0; var p = v.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
    touch();
  }

  var seq = null;

  function say(text) {
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
        return;
      }
    } catch (e) {}
    if (S.caption) S.caption(text);   // no speech engine: still show the caption
  }

  function playDemo(n) {
    var v = $('exhDemo');
    say(n === 1 ? CFG.demo_line1 : CFG.demo_line2);
    touch();
    try {
      v.currentTime = 0;
      var p = v.play();
      if (p && p.catch) p.catch(function () { step(seq.error()); });
    } catch (e) { step(seq.error()); }
  }

  function step(act) {
    if (!act || S.failed) return;
    if (act.do === 'play') playDemo(act.n);
    else if (act.do === 'camera') startCameraNow();
  }

  function begin() {
    if (S.started) return;
    S.started = true;
    // Unlock speech INSIDE this tap (iPhone/iPad Safari stay silent otherwise).
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(CFG.unlock));
      }
    } catch (e) {}
    $('exhStart').style.display = 'none';
    touch();
    var v = $('exhDemo');
    seq = core.createSequencer(2, CFG.demo_timeout_seconds * 1000);
    $('exhDemoStage').style.display = 'flex';
    v.addEventListener('ended', function () { touch(); step(seq.ended()); });
    v.addEventListener('error', function () { step(seq.error()); });
    step(seq.start(Date.now()));
  }

  // After the demo: plain startCamera() (never showDemo(): no third demo).
  function startCameraNow() {
    $('exhDemoStage').style.display = 'none';
    try { $('exhDemo').pause(); } catch (e) {}
    touch();
    if (!window.isSecureContext && location.hostname !== 'localhost') {
      return fail('insecure context');
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return fail('no getUserMedia');
    }
    if (typeof window.Pose === 'undefined' || S.scriptFailed) {
      return fail('MediaPipe script did not load');
    }
    camStartedAt = Date.now();
    try {
      var r = window.startCamera();
      if (r && r.catch) r.catch(function (e) { fail('startCamera: ' + e); });
    } catch (e) { fail('startCamera: ' + e); }
  }

  function tick() {
    var now = Date.now();
    if (seq) step(seq.tick(now));
    if (S.started && !S.failed && camStartedAt && S.granted) {
      if (core.noFrames($('cameraFeed'), S.grantedAt, now, CFG.no_frame_seconds * 1000)) {
        fail('no camera frames');
      }
    }
    var reps = ($('repCountDisplay') || {}).textContent || '';
    if (reps !== lastReps) { lastReps = reps; touch(); }
    var key = core.stateKey(window.ghostState);
    if (key !== lastState) { lastState = key; touch(); }
    if (S.started && core.shouldReset(now, Math.max(lastActivity, S.lastCaptionAt), CFG.idle_seconds * 1000)) {
      location.reload();
    }
  }

  $('exhGo').addEventListener('click', begin);
  $('exhFailReplay').addEventListener('click', function () { replay('exhFailVideo'); });
  $('exhRetry').addEventListener('click', function () { location.reload(); });
  ['pointerdown', 'touchstart', 'keydown'].forEach(function (ev) {
    document.addEventListener(ev, touch, true);
  });
  setInterval(tick, 1000);
})();
