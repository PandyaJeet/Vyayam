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

  // ── plank_hold_rx — forearm plank, side view ────────────────────────────
  // Primary: body line (shoulder-hip-ankle ~180) + horizontal body. Faults:
  // hip sag / hip pike via the hip's deviation from the shoulder-ankle line
  // (same construct as cv_core's bodyLine stance check).
  function _plankDeviation(lm) {
    var sh = lm[LM.leftShoulder], hp = lm[LM.leftHip], ak = lm[LM.leftAnkle];
    if (Math.min(vis(sh), vis(hp), vis(ak)) < 0.4) return null;
    var bodyLen = Math.abs(ak.y - sh.y) + Math.abs(ak.x - sh.x);
    if (bodyLen < 0.15) return null;
    var midY = (sh.y + ak.y) / 2;
    return (hp.y - midY) / bodyLen;   // + below the line (sag), - above (pike)
  }

  PHASES.PLANK_RX = {
    name: 'Plank Hold',
    bodyOrientation: 'prone',
    cameraPosition: { view: 'side', instruction: 'Place camera to your side at floor level so your whole body is visible.' },
    setupCues: [
      'Forearms on the ground. Elbows under your shoulders.',
      'Legs straight behind you, toes tucked.',
      'Squeeze your glutes — one straight line, head to heels.',
      'Breathe steadily and hold.',
    ],
    stanceCheck: { shoulderShrug: true, bodyLine: true, label: 'Elbows under shoulders, body straight' },
    phases: [
      { name: 'hold', duration: 0, joints: { bodyLine: 178, plankLevel: 0.05 }, voice: 'Hold a straight line' },
    ],
    checkAngles: function (lm) {
      var bodyLine = (calcAngle(lm[LM.leftShoulder], lm[LM.leftHip], lm[LM.leftAnkle]) +
                      calcAngle(lm[LM.rightShoulder], lm[LM.rightHip], lm[LM.rightAnkle])) / 2;
      var plankLevel = Math.abs(
        (lm[LM.leftShoulder].y + lm[LM.rightShoulder].y) / 2 -
        (lm[LM.leftAnkle].y + lm[LM.rightAnkle].y) / 2);
      return { bodyLine: bodyLine, plankLevel: plankLevel };
    },
    cues: { bodyLine: 'Straighten your body', plankLevel: 'Get into plank on the floor' },
    forceArrows: [],
  };

  FAULTS.PLANK_RX = makeFaults([
    {
      cue: 'plank_hips_sag', modes: ['GUIDING'], minMs: 600,
      test: function (lm) {
        var dev = _plankDeviation(lm);
        if (dev === null || dev <= 0.12) return null;
        return HIP_SEGS;
      },
    },
    {
      cue: 'plank_hips_pike', modes: ['GUIDING'], minMs: 600,
      test: function (lm) {
        var dev = _plankDeviation(lm);
        if (dev === null || dev >= -0.12) return null;
        return HIP_SEGS;
      },
    },
  ]);
  CUE_IDS.push('plank_hips_sag', 'plank_hips_pike');

  // ── side_plank_rx — lateral hold, front view ────────────────────────────
  // Primary: lateral body line (the supporting side reads closest to 180°)
  // + horizontal body. Fault: hip drop (line collapses below ~162°).
  function _lateralLine(lm) {
    var leftLine = calcAngle(lm[LM.leftShoulder], lm[LM.leftHip], lm[LM.leftAnkle]);
    var rightLine = calcAngle(lm[LM.rightShoulder], lm[LM.rightHip], lm[LM.rightAnkle]);
    return (Math.abs(leftLine - 180) < Math.abs(rightLine - 180)) ? leftLine : rightLine;
  }

  PHASES.SIDE_PLANK_RX = {
    name: 'Side Plank',
    bodyOrientation: 'sidelying',
    cameraPosition: { view: 'front', instruction: 'Place camera in front of you at floor level so it sees your whole side-on body.' },
    setupCues: [
      'Lie on your side. Elbow directly under your shoulder.',
      'Stack your feet, or stagger them for balance.',
      'Lift your hips — one straight line from head to feet.',
      'Breathe steadily and hold.',
    ],
    stanceCheck: { hipLevel: true, label: 'Elbow under shoulder, hips lifted' },
    phases: [
      { name: 'hold', duration: 0, joints: { lateralLine: 178, plankLevel: 0.05 }, voice: 'Hips up — hold the line' },
    ],
    checkAngles: function (lm) {
      var plankLevel = Math.abs(
        (lm[LM.leftShoulder].y + lm[LM.rightShoulder].y) / 2 -
        (lm[LM.leftAnkle].y + lm[LM.rightAnkle].y) / 2);
      return { lateralLine: _lateralLine(lm), plankLevel: plankLevel };
    },
    cues: { lateralLine: 'Lift your hip', plankLevel: 'Get into side plank on the floor' },
    forceArrows: [],
  };

  FAULTS.SIDE_PLANK_RX = makeFaults([
    {
      cue: 'side_plank_hip_drop', modes: ['GUIDING'], minMs: 600,
      test: function (lm) {
        if (!allVisible(lm, [LM.leftShoulder, LM.leftHip, LM.leftAnkle])) return null;
        if (_lateralLine(lm) >= 162) return null;
        return HIP_SEGS;
      },
    },
  ]);
  CUE_IDS.push('side_plank_hip_drop');

  // ── single_leg_balance_rx — one-leg hold, front view ────────────────────
  // Primary: lifted knee clearly raised + hips level + tall trunk. Faults:
  // foot back on the ground (hold clock stalls — tell them why) and hip
  // drop (reuses the existing hips_level cue id).
  PHASES.BALANCE_RX = {
    name: 'Single-Leg Balance',
    bodyOrientation: 'standing',
    cameraPosition: { view: 'front', instruction: 'Place camera in front of you. Full body visible including both feet.' },
    setupCues: [
      'Stand tall. Fix your eyes on one point ahead.',
      'Lift one foot clearly off the ground.',
      'Standing knee soft, not locked.',
      'Hips level — hold as still as you can.',
    ],
    stanceCheck: { maxFootRotation: 0.18, hipLevel: true, label: 'Standing foot straight, hips level' },
    phases: [
      { name: 'hold', duration: 0, joints: { hipLevel: 0.03, liftedKnee: 0.10 }, voice: 'Balance — stay tall and still' },
    ],
    checkAngles: function (lm) {
      return {
        hipLevel: Math.abs(lm[LM.leftHip].y - lm[LM.rightHip].y),
        liftedKnee: Math.abs(lm[LM.leftKnee].y - lm[LM.rightKnee].y),
      };
    },
    cues: { hipLevel: 'Level your hips', liftedKnee: 'Lift your foot off the ground' },
    forceArrows: [],
  };

  FAULTS.BALANCE_RX = makeFaults([
    {
      // Foot back on the floor: knees level again while the hold runs.
      cue: 'balance_foot_down', modes: ['GUIDING'], minMs: 700,
      test: function (lm) {
        if (!allVisible(lm, [LM.leftKnee, LM.rightKnee])) return null;
        if (Math.abs(lm[LM.leftKnee].y - lm[LM.rightKnee].y) >= 0.05) return null;
        return kneeShinSegs(true).concat(kneeShinSegs(false));
      },
    },
    {
      // Pelvis tilt: one hip clearly below the other.
      cue: 'hips_level', modes: ['GUIDING'], minMs: 600,
      test: function (lm) {
        if (!allVisible(lm, [LM.leftHip, LM.rightHip])) return null;
        if (Math.abs(lm[LM.leftHip].y - lm[LM.rightHip].y) <= 0.06) return null;
        return HIP_SEGS;
      },
    },
  ]);
  CUE_IDS.push('balance_foot_down');

  // ── straight_leg_raise_rx — supine hip-flexion reps, side view ──────────
  // Primary: working hip angle (shoulder-hip-knee) cycling 172° → 135°.
  // Fault: the raised leg\'s knee bending during the lift (the movement\'s
  // defining error — the lift must come from the hip).
  function _slrWorking(lm) {
    var lHip = calcAngle(lm[LM.leftShoulder], lm[LM.leftHip], lm[LM.leftKnee]);
    var rHip = calcAngle(lm[LM.rightShoulder], lm[LM.rightHip], lm[LM.rightKnee]);
    var left = lHip <= rHip;
    return {
      left: left,
      hip: left ? lHip : rHip,
      knee: left ? calcAngle(lm[LM.leftHip], lm[LM.leftKnee], lm[LM.leftAnkle])
                 : calcAngle(lm[LM.rightHip], lm[LM.rightKnee], lm[LM.rightAnkle]),
    };
  }

  PHASES.SLR_RX = {
    name: 'Straight Leg Raise',
    bodyOrientation: 'supine',
    cameraPosition: { view: 'side', instruction: 'Place camera to your side at floor level while you lie on your back. Full body visible.' },
    setupCues: [
      'Lie on your back. Working leg straight, other knee bent, foot flat.',
      'Tighten the thigh — lock the knee dead straight.',
      'Lift the straight leg to the height of the bent knee.',
      'Lower slowly. The knee never bends.',
    ],
    stanceCheck: null,
    phases: [
      { name: 'rest',  duration: 0,    joints: { workingHip: 172 }, voice: 'Leg flat, knee locked' },
      { name: 'raise', duration: 2000, joints: { workingHip: 135 }, voice: 'Lift the leg — knee straight' },
      { name: 'hold',  duration: 800,  joints: { workingHip: 135 }, voice: 'Hold' },
      { name: 'lower', duration: 2000, joints: { workingHip: 172 }, voice: 'Lower slowly' },
    ],
    checkAngles: function (lm) {
      return { workingHip: _slrWorking(lm).hip };
    },
    cues: { workingHip: 'Lift to the height of your bent knee' },
    forceArrows: [],
  };

  FAULTS.SLR_RX = makeFaults([
    {
      // Knee bend while the leg is raised (hip clearly flexed).
      cue: 'slr_knee_straight', modes: ['USER_FOLLOWS', 'GHOST_LEADS'], minMs: 400,
      test: function (lm) {
        if (!allVisible(lm, [LM.leftHip, LM.leftKnee, LM.leftAnkle,
                             LM.rightHip, LM.rightKnee, LM.rightAnkle])) return null;
        var w = _slrWorking(lm);
        if (w.hip > 160) return null;        // leg not raised — nothing to judge
        if (w.knee >= 155) return null;      // straight enough
        return kneeShinSegs(w.left);
      },
    },
  ]);
  CUE_IDS.push('slr_knee_straight');

  // ── knee_to_chest_rx — supine hip-flexion hold, side view ───────────────
  // Primary: working hip angle drawn to ~55°. Position loss simply pauses
  // the hold clock (score falls under the 40-point hold gate); no separate
  // fault channel — the movement has no reliable camera-visible error
  // beyond losing the position (fewer honest checks over noisy ones).
  PHASES.KNEE_TO_CHEST_RX = {
    name: 'Knee to Chest',
    bodyOrientation: 'supine',
    cameraPosition: { view: 'side', instruction: 'Place camera to your side at floor level while you lie on your back. Full body visible.' },
    setupCues: [
      'Lie on your back, both legs relaxed.',
      'Draw one knee up toward your chest.',
      'Clasp behind the thigh and ease it in gently.',
      'Breathe slowly and hold the stretch.',
    ],
    stanceCheck: null,
    phases: [
      { name: 'hold', duration: 0, joints: { workingHip: 55 }, voice: 'Draw the knee in and hold' },
    ],
    checkAngles: function (lm) {
      var lHip = calcAngle(lm[LM.leftShoulder], lm[LM.leftHip], lm[LM.leftKnee]);
      var rHip = calcAngle(lm[LM.rightShoulder], lm[LM.rightHip], lm[LM.rightKnee]);
      return { workingHip: Math.min(lHip, rHip) };
    },
    cues: { workingHip: 'Draw the knee a little closer' },
    forceArrows: [],
  };

  FAULTS.KNEE_TO_CHEST_RX = makeFaults([]);   // hold-loss handled by the hold gate

  // ── prone_knee_bend_rx — prone knee-flexion reps, side view ─────────────
  // Primary: working knee angle cycling 172° → 90°. Fault: hips lifting
  // off the floor (compensation — the thigh must stay down).
  function _pkbWorking(lm) {
    var lKnee = calcAngle(lm[LM.leftHip], lm[LM.leftKnee], lm[LM.leftAnkle]);
    var rKnee = calcAngle(lm[LM.rightHip], lm[LM.rightKnee], lm[LM.rightAnkle]);
    var left = lKnee <= rKnee;
    return {
      left: left,
      knee: left ? lKnee : rKnee,
      hip: left ? calcAngle(lm[LM.leftShoulder], lm[LM.leftHip], lm[LM.leftKnee])
                : calcAngle(lm[LM.rightShoulder], lm[LM.rightHip], lm[LM.rightKnee]),
    };
  }

  PHASES.PRONE_KNEE_BEND_RX = {
    name: 'Prone Knee Bend',
    bodyOrientation: 'prone',
    cameraPosition: { view: 'side', instruction: 'Place camera to your side at floor level while you lie face down. Full body visible.' },
    setupCues: [
      'Lie face down, both legs straight.',
      'Bend the working knee — heel toward your buttock.',
      'Hips stay flat. Only the knee moves.',
      'Lower back down slowly.',
    ],
    stanceCheck: null,
    phases: [
      { name: 'rest',  duration: 0,    joints: { workingKnee: 172 }, voice: 'Legs flat' },
      { name: 'bend',  duration: 2000, joints: { workingKnee: 90 },  voice: 'Heel toward your buttock' },
      { name: 'hold',  duration: 800,  joints: { workingKnee: 90 },  voice: 'Hold' },
      { name: 'lower', duration: 2000, joints: { workingKnee: 172 }, voice: 'Lower slowly' },
    ],
    checkAngles: function (lm) {
      return { workingKnee: _pkbWorking(lm).knee };
    },
    cues: { workingKnee: 'Bring the heel a little closer' },
    forceArrows: [],
  };

  FAULTS.PRONE_KNEE_BEND_RX = makeFaults([
    {
      // Hip lift: working-side hip angle closes while the knee bends.
      cue: 'prone_hips_flat', modes: ['USER_FOLLOWS', 'GHOST_LEADS'], minMs: 400,
      test: function (lm) {
        if (!allVisible(lm, [LM.leftShoulder, LM.leftHip, LM.leftKnee,
                             LM.rightShoulder, LM.rightHip, LM.rightKnee])) return null;
        var w = _pkbWorking(lm);
        if (w.knee > 150) return null;       // not bending — nothing to judge
        if (w.hip >= 155) return null;       // hips still flat
        return HIP_SEGS;
      },
    },
  ]);
  CUE_IDS.push('prone_hips_flat');

  // ── supine_hip_abduction_rx — supine leg slide, camera at the feet ──────
  // Primary: ankle spread as a % of hip width (CLAMSHELL\'s x100 convention
  // so the 70-point phase gate has real resolution). Fault: pelvis shifting
  // sideways instead of the leg sliding.
  function _supAbd(lm) {
    var hipW = Math.abs(lm[LM.leftHip].x - lm[LM.rightHip].x);
    if (hipW < 0.02) return null;
    return {
      spreadPct: Math.min(400, (Math.abs(lm[LM.leftAnkle].x - lm[LM.rightAnkle].x) / hipW) * 100),
      hipMidX: (lm[LM.leftHip].x + lm[LM.rightHip].x) / 2,
    };
  }

  PHASES.SUPINE_ABD_RX = {
    name: 'Supine Hip Abduction',
    bodyOrientation: 'supine',
    cameraPosition: { view: 'front', instruction: 'Place camera beyond your feet at floor level, looking up your body. Both legs and hips visible.' },
    setupCues: [
      'Lie on your back, legs straight, toes pointing up.',
      'Keep the knee straight the whole time.',
      'Slide the working leg out along the floor.',
      'Slide slowly back to the middle. Pelvis stays still.',
    ],
    stanceCheck: null,
    phases: [
      { name: 'center', duration: 0,    joints: { legSpreadPct: 110 }, voice: 'Legs together, toes up' },
      { name: 'out',    duration: 2000, joints: { legSpreadPct: 200 }, voice: 'Slide the leg out' },
      { name: 'hold',   duration: 800,  joints: { legSpreadPct: 200 }, voice: 'Hold' },
      { name: 'in',     duration: 2000, joints: { legSpreadPct: 110 }, voice: 'Slide back to the middle' },
    ],
    checkAngles: function (lm) {
      var m = _supAbd(lm);
      return { legSpreadPct: m ? m.spreadPct : 110 };
    },
    cues: { legSpreadPct: 'Slide the leg a little further out' },
    forceArrows: [],
  };

  var _supAbdBaseX = { v: null };
  FAULTS.SUPINE_ABD_RX = makeFaults([
    {
      // Pelvis shift: hip midpoint drifting sideways from its set baseline.
      cue: 'pelvis_still', modes: ['USER_FOLLOWS', 'GHOST_LEADS'], minMs: 400,
      test: function (lm) {
        if (!allVisible(lm, [LM.leftHip, LM.rightHip])) return null;
        var m = _supAbd(lm);
        if (!m) return null;
        if (_supAbdBaseX.v === null) { _supAbdBaseX.v = m.hipMidX; return null; }
        if (Math.abs(m.hipMidX - _supAbdBaseX.v) <= 0.05) return null;
        return HIP_SEGS;
      },
    },
  ]);
  // Baseline resets with the observer (new set = new lie-down position).
  var _supAbdReset = FAULTS.SUPINE_ABD_RX.resetSet.bind(FAULTS.SUPINE_ABD_RX);
  FAULTS.SUPINE_ABD_RX.resetSet = function () { _supAbdBaseX.v = null; _supAbdReset(); };
  CUE_IDS.push('pelvis_still');

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
