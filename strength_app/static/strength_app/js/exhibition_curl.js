/*
 * Exhibition bicep curl page wrapper (no edits to the camera template or camera JS).
 * DOM wiring only. It reuses the pure, node-tested parts of exhibition_squat.js
 * (window.ExhibitionSquat), which loads first WITHOUT window.EXH_CFG, so the squat
 * DOM part stays off. This page sets window.EXH_CURL_CFG (exhibition_curl.html).
 *
 * Page flow: Start screen -> tap -> unlock speech -> the camera page's own showDemo()
 * (camera on, framing check, setup cues, two ghost reps, "Now you try") -> coaching.
 * There is no clip. A reload is the reset, as on the squat page.
 */
(function () {
  if (typeof window === 'undefined' || !window.EXH_CURL_CFG || !window.ExhibitionSquat) return;
  var CFG = window.EXH_CURL_CFG;
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
    touch();
  }
  S.fail = fail;
  if (S.pendingFail) fail(S.pendingFail);

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
    try { window.showDemo(); } catch (e) { fail('showDemo: ' + e); }
  }

  function tick() {
    var now = Date.now();
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
  $('exhRetry').addEventListener('click', function () { location.reload(); });
  ['pointerdown', 'touchstart', 'keydown'].forEach(function (ev) {
    document.addEventListener(ev, touch, true);
  });
  setInterval(tick, 1000);
})();
