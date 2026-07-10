/*
 * 2026-07 FINAL SESSION: VyayamDark — dark-shipped camera coaches.
 *
 * Eleven prescription-tier exercises get camera-ghost coaches here, each
 * behind a NEW `<name>_rx` registry key. DARK MECHANISM (proofs in
 * CODEBASE_HEALTH_2026-07.md / PHASE3 notes):
 *   - the therapist path opens the camera only when the catalog entry has
 *     BOTH v2_ghost_supported=True AND a v2_exercise_key
 *     (v1_therapist_session_views.py:263). All 11 flags remain False.
 *   - self-serve reaches only progression-chain/warmup keys; no chain
 *     references any *_rx key.
 *   - flip day per exercise = set v2_ghost_supported True. One line.
 *
 * This file follows the cv_core/coach_core UMD pattern so node can unit-test
 * every checkAngles + fault observer (coach_dark.test.mjs). It depends ONLY
 * on VyayamCV. The execute template:
 *   1. installs PHASES into its EXERCISE_PHASES registry (install() never
 *      overwrites an existing key — the frozen audited templates win), and
 *   2. dispatches FAULTS[exerciseType].frame(lm, ghostState, coachCue, now)
 *      once per pose frame (inert for every existing js_type).
 *
 * Coaching rules honoured (locked): amber-first — every fault cue here is
 * class 'primary'/'refinement', NEVER safety/red; tempo never colors form;
 * cue ids exist in coach_core.js CUES and report_builder.py CUE_TEXT
 * (forever-rule sync, asserted by tests).
 * DETECTION BOUNDARY: nothing here touches the shared rep state machine,
 * angle math, or MediaPipe setup — new data + observers only.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory(require('./cv_core.js'));
  } else {
    root.VyayamDark = factory(root.VyayamCV);
  }
})(typeof self !== 'undefined' ? self : this, function (CV) {
  'use strict';

  var LM = CV.LM;
  var calcAngle = CV.calcAngle;

  // ── helpers ─────────────────────────────────────────────────────────────
  function vis(p) {
    return p ? (p.visibility === undefined ? 1 : p.visibility) : 0;
  }
  function allVisible(lm, idxs, floor) {
    floor = floor || 0.4;
    for (var i = 0; i < idxs.length; i++) {
      if (vis(lm[idxs[i]]) < floor) return false;
    }
    return true;
  }
  // Both key orders — the skeleton painter's segment keys are order-proof
  // this way (same convention as SquatFaults._kneeSegsFor).
  function segs(pairs) {
    var out = [];
    for (var i = 0; i < pairs.length; i++) {
      out.push(pairs[i][0] + '-' + pairs[i][1]);
      out.push(pairs[i][1] + '-' + pairs[i][0]);
    }
    return out;
  }
  var HIP_SEGS = segs([[11, 23], [12, 24], [23, 25], [24, 26], [23, 24]]);
  function kneeShinSegs(left) {
    return left ? segs([[23, 25], [25, 27]]) : segs([[24, 26], [26, 28]]);
  }
  function armSegs(left) {
    return left ? segs([[11, 13], [13, 15]]) : segs([[12, 14], [14, 16]]);
  }
  var TRUNK_SEGS = segs([[11, 23], [12, 24], [11, 12]]);

  // ── fault-observer factory ──────────────────────────────────────────────
  // checks: [{ cue, modes, minMs, cooldownMs, test(lm, gs) -> segs[]|null }]
  // Amber-first: observers only ever paint amber (the template applies them
  // through the same worst-color contest as SquatFaults ambers; there is no
  // red channel here by design — none of these movements has a camera-
  // detectable danger state, and red is reserved for the safety cue class.
  function makeFaults(checks) {
    return {
      _since: {},
      _lastAt: {},
      _cuedRepKey: null,
      _segs: [],
      amberUntil: 0,
      amberSegs: function () { return this._segs; },
      resetSet: function () {
        this._since = {};
        this._cuedRepKey = null;
        this.amberUntil = 0;
      },
      frame: function (lm, gs, cue, now) {
        if (!lm || !gs) return;
        now = now || Date.now();
        var repKey = (gs.repCount || 0) + ':' + (gs.partialRomReps || 0);
        for (var i = 0; i < checks.length; i++) {
          var c = checks[i];
          if (c.modes && c.modes.indexOf(gs.mode) === -1) {
            this._since[c.cue] = 0;
            continue;
          }
          var hit = null;
          try { hit = c.test(lm, gs); } catch (e) { hit = null; }
          if (!hit) { this._since[c.cue] = 0; continue; }
          if (!this._since[c.cue]) this._since[c.cue] = now;
          if (now - this._since[c.cue] < (c.minMs || 300)) continue;
          this._segs = hit;
          this.amberUntil = now + 600;
          // Rep exercises: max one fault cue per rep (holds have no rep
          // boundary — the per-cue cooldown alone gates them).
          if (!gs.isHoldExercise && this._cuedRepKey === repKey) continue;
          if (now - (this._lastAt[c.cue] || 0) < (c.cooldownMs || 8000)) continue;
          this._lastAt[c.cue] = now;
          this._cuedRepKey = repKey;
          if (typeof cue === 'function') cue(c.cue);
        }
      },
    };
  }

  var PHASES = {};
  var FAULTS = {};
  // Cue text mirror for the sync tests (source of truth for SPEECH is
  // coach_core.js CUES; report copy is report_builder.py CUE_TEXT).
  var CUE_IDS = [];

  // ══ DARK COACH DEFINITIONS — one block per exercise, appended in build
  //    order. INSERTION MARKER below; do not remove. ══════════════════════

  // ── wall_sit_rx — isometric wall hold, side view ────────────────────────
  // Primary: knee depth band (90°) + hip stacked under shoulder. Faults:
  // thighs-above-parallel drift, heel rise. Hold-time counting comes from
  // the template's single-phase hold machinery (phases.length === 1).
  function _legKnee(lm, left) {
    var hp = lm[left ? LM.leftHip : LM.rightHip];
    var kn = lm[left ? LM.leftKnee : LM.rightKnee];
    var ak = lm[left ? LM.leftAnkle : LM.rightAnkle];
    var v = Math.min(vis(hp), vis(kn), vis(ak));
    return { vis: v, angle: calcAngle(hp, kn, ak) };
  }

  PHASES.WALL_SIT_RX = {
    name: 'Wall Sit',
    bodyOrientation: 'standing',
    cameraPosition: { view: 'side', instruction: 'Place camera to your side. Your whole body and the wall must be visible.' },
    setupCues: [
      'Back flat against the wall. Feet about hip width.',
      'Walk your feet forward, then slide down the wall.',
      'Stop when your thighs are level with the floor.',
      'Knees above your ankles. Hold and breathe.',
    ],
    stanceCheck: { kneeOverAnkle: true, label: 'Back on the wall, knees over ankles' },
    phases: [
      { name: 'hold', duration: 0, joints: { knee: 90, hip: 95 }, voice: 'Slide down and hold' },
    ],
    checkAngles: function (lm) {
      var knee = (calcAngle(lm[LM.leftHip], lm[LM.leftKnee], lm[LM.leftAnkle]) +
                  calcAngle(lm[LM.rightHip], lm[LM.rightKnee], lm[LM.rightAnkle])) / 2;
      var hip = (calcAngle(lm[LM.leftShoulder], lm[LM.leftHip], lm[LM.leftKnee]) +
                 calcAngle(lm[LM.rightShoulder], lm[LM.rightHip], lm[LM.rightKnee])) / 2;
      return { knee: knee, hip: hip };
    },
    cues: { knee: 'Slide to a right angle at the knee', hip: 'Back against the wall' },
    forceArrows: [],
  };

  FAULTS.WALL_SIT_RX = makeFaults([
    {
      // Depth band drift: thighs above parallel for >700ms.
      cue: 'wall_sit_slide_down', modes: ['GUIDING'], minMs: 700,
      test: function (lm) {
        var l = _legKnee(lm, true), r = _legKnee(lm, false);
        var best = (l.vis >= r.vis) ? l : r;
        if (best.vis < 0.4 || best.angle <= 112) return null;
        return segs([[23, 25], [24, 26]]);
      },
    },
    {
      // Heel rise on the camera-facing side.
      cue: 'wall_sit_heels', modes: ['GUIDING'], minMs: 500,
      test: function (lm) {
        var lVis = Math.min(vis(lm[LM.leftHeel]), vis(lm[LM.leftFootIndex]));
        var rVis = Math.min(vis(lm[LM.rightHeel]), vis(lm[LM.rightFootIndex]));
        if (Math.max(lVis, rVis) < 0.4) return null;
        var left = lVis >= rVis;
        var heel = lm[left ? LM.leftHeel : LM.rightHeel];
        var toe = lm[left ? LM.leftFootIndex : LM.rightFootIndex];
        if ((toe.y - heel.y) <= 0.03) return null;
        return left ? segs([[25, 27], [27, 29], [27, 31]])
                    : segs([[26, 28], [28, 30], [28, 32]]);
      },
    },
  ]);
  CUE_IDS.push('wall_sit_slide_down', 'wall_sit_heels');

  // [VYAYAM-DARK-DEFS-END]

  return {
    PHASES: PHASES,
    FAULTS: FAULTS,
    CUE_IDS: CUE_IDS,
    makeFaults: makeFaults,   // exported for node tests
    install: function (registry) {
      for (var key in PHASES) {
        if (!registry[key]) registry[key] = PHASES[key];
      }
    },
  };
});
