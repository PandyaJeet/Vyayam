/*
 * R4: VyayamCoach — the human-like coaching arbitration core.
 *
 * PURE decision logic, extracted so node can unit-test it
 * (tests/js/coach_core.test.mjs). The execute template feeds it events and
 * speaks/colors according to its answers; it never touches landmarks,
 * angles, the rep machine, or MediaPipe (detection boundary).
 *
 * The rules it owns (handoff R4a–R4g):
 *  - ONE active cue at a time. Priority safety > primary > refinement.
 *    Lower priority never interrupts the occupancy window; safety always
 *    does, immediately. Minimum 1 full rep between spoken cues (safety
 *    exempt). Refinement never fires in the final 2 reps of a set.
 *  - 3-strike fading: the same cue spoken 3x uncorrected in a set stops
 *    repeating; one "Let's slow down — quality over count." then silence
 *    on that cue for the set; the set is flagged cue_resistant.
 *  - Praise: a corrected cue earns ONE specific reinforcement then silence
 *    on that cue; independent praise max ONE per set, only after a
 *    genuinely good window (>=3 consecutive good-form reps), drawn from a
 *    rotating pool so it never feels canned.
 *  - Calibration: first 2 reps of the first set — no colors, no cues
 *    except safety, one "Let's see your natural movement first."
 *  - Confidence gate: low visibility for >1s freezes coloring and says
 *    "I can't see you clearly — step back a little." once per episode.
 *    NEVER color or cue on low-confidence frames.
 *  - Amber-first: red is reserved for the SAFETY cue class and only while
 *    a safety cue is active; everything else ambers. Tempo NEVER colors
 *    form (locked rule) — the tempo adjust line speaks at most once/set.
 *  - Fatigue mode: only safety cues + encouragement for the remainder.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.VyayamCoach = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {

  // ── R4b: the rewritten cue registry (stable cue_ids from R1) ───────────
  // <=8 spoken words, instructive, external-focus, never fault-labels.
  // The full before→after table ships in the phase report for the physio
  // mentor's sign-off.
  var CUES = {
    knee_valgus:         { text: 'Knees toward the camera',      priority: 'safety' },
    knee_valgus_landing: { text: 'Land with your knees wide',    priority: 'safety' },
    soft_landing:        { text: 'Land soft and quiet',          priority: 'safety' },
    orientation_supine:  { text: 'Lie on your back',             priority: 'safety' },
    orientation_prone:   { text: 'Lie face down',                priority: 'safety' },
    orientation_sidelying: { text: 'Lie on your side',           priority: 'safety' },
    hips_even:           { text: 'Hips level, like a tray',      priority: 'primary' },
    stay_hinged:         { text: 'Push your hips back',          priority: 'primary' },
    foot_forward:        { text: 'Front foot further forward',   priority: 'primary' },
    chest_up:            { text: 'Chest proud',                  priority: 'primary' },
    hips_level:          { text: 'Keep your hips level',         priority: 'primary' },
    hips_stacked:        { text: 'Stack your hips straight up',  priority: 'primary' },
    hold_position:       { text: 'Back into position',           priority: 'primary' },
    stand_tall:          { text: 'Grow tall on the step',        priority: 'refinement' },
    feet_together:       { text: 'Glue your feet together',      priority: 'refinement' },
    // R6-P4: squat named-fault cues (side-view checks; amber-first, not red).
    squat_knee_over_toe: { text: 'Knees drifting past your toes — sit your hips back.', priority: 'primary' },
    squat_heel_rise:     { text: 'Keep your heels down. Weight through mid-foot.',      priority: 'primary' },
    // R6-HOTFIX: squat SAFETY faults — the safety class flips redAllowed().
    squat_too_deep:      { text: 'Too deep — come up a little. Stay in your range.',    priority: 'safety' },
    squat_asymmetry:     { text: "Uneven — you're loading one side more. Even out both knees.", priority: 'safety' },
    // Comfort-conditional depth encouragement — never commands depth.
    squat_depth_gentle:  { text: "You can go a little deeper if it's comfortable.",     priority: 'refinement' },
    // 2026-07 dark coaches (*_rx exercises — DARK until catalog flags flip;
    // strings queued for mentor review in MENTOR_REVIEW_QUEUE §2026-07).
    wall_sit_slide_down: { text: 'Slide down — thighs level with the floor', priority: 'primary' },
    wall_sit_heels:      { text: 'Keep both heels on the floor',             priority: 'primary' },
    plank_hips_sag:      { text: 'Lift your hips — straight line',           priority: 'primary' },
    plank_hips_pike:     { text: 'Lower your hips — straight line',          priority: 'primary' },
    side_plank_hip_drop: { text: 'Push your hip up',                          priority: 'primary' },
    balance_foot_down:   { text: 'Lift your foot to restart the clock',       priority: 'primary' },
    slr_knee_straight:   { text: 'Keep that knee locked straight',            priority: 'primary' },
    prone_hips_flat:     { text: 'Keep your hips on the floor',               priority: 'primary' },
  };

  // Reinforcement when a specific cue is corrected (R4c) — specific first,
  // generic fallback.
  var CORRECTED_PRAISE = {
    knee_valgus: 'Better — knees are tracking now',
    hips_even: 'Better — hips are level now',
    stay_hinged: 'Better — that hinge is right',
    chest_up: 'Better — chest is proud now',
    hips_level: 'Better — hips are steady now',
  };
  var CORRECTED_PRAISE_DEFAULT = 'Better — that is it';

  // Independent praise pool (~8 varied lines, rotated deterministically).
  var PRAISE_POOL = [
    'Lovely control — keep that rhythm',
    'Strong and steady — exactly right',
    'That depth is spot on',
    'Smooth — just like that',
    'Great control on the way down',
    'Textbook rep — keep them coming',
    'You own this movement today',
    'Beautiful — same again',
  ];

  var PRIORITY_RANK = { safety: 3, primary: 2, refinement: 1 };
  var OCCUPY_MS = 2500;        // a spoken line owns the voice channel this long
  var STRIKES_TO_FADE = 3;
  var GOOD_FORM_PCT = 75;
  var GOOD_WINDOW_REPS = 3;
  var CONFIDENCE_TRIP_MS = 1000;
  var CALIBRATION_REPS = 2;

  var FADE_LINE = "Let's slow down — quality over count";
  var CALIBRATION_LINE = "Let's see your natural movement first";
  var CONFIDENCE_LINE = "I can't see you clearly — step back a little";
  var FATIGUE_LINE = 'Last set — steady and controlled';

  function createArbiter(opts) {
    opts = opts || {};
    var state = {
      setNumber: 0,
      isFirstSet: true,
      rep: 0,
      targetReps: 10,
      lastSpokenAt: -Infinity,
      lastSpokenPriority: 0,
      lastCueRep: -1,
      lastCueId: null,
      safetyActiveUntil: -Infinity,
      strikes: {},           // cueId -> uncorrected fires this set
      faded: {},             // cueId -> true (silenced for the set)
      fadeLineSaid: false,
      cueResistant: [],      // cueIds flagged this set (feeds the set log)
      praisedThisSet: false,
      praiseIndex: 0,
      goodStreak: 0,
      calibrating: false,
      calibrationAnnounced: false,
      lowSince: null,
      confidenceFrozen: false,
      confidenceAnnounced: false,
      fatigued: false,
      fatigueAnnounced: false,
      tempoAdjustSaid: false,
    };

    function occupy(now, priority) {
      state.lastSpokenAt = now;
      state.lastSpokenPriority = PRIORITY_RANK[priority] || 0;
    }

    var arbiter = {
      cues: CUES,
      state: state,

      // ── set lifecycle ──────────────────────────────────────────────────
      setStarted: function (setNumber, targetReps) {
        state.setNumber = setNumber;
        state.isFirstSet = setNumber <= 1;
        state.targetReps = targetReps || state.targetReps;
        state.rep = 0;
        state.lastCueRep = -1;
        state.strikes = {};
        state.faded = {};
        state.fadeLineSaid = false;
        state.cueResistant = [];
        state.praisedThisSet = false;
        state.goodStreak = 0;
        state.tempoAdjustSaid = false;
        if (state.isFirstSet && !state.calibrationAnnounced) {
          state.calibrating = true;
          state.calibrationAnnounced = true;
          return { line: CALIBRATION_LINE };
        }
        if (state.fatigued && !state.fatigueAnnounced) {
          state.fatigueAnnounced = true;
          return { line: FATIGUE_LINE };
        }
        return { line: null };
      },

      // ── cue requests (R4a) ─────────────────────────────────────────────
      requestCue: function (cueId, now) {
        var def = CUES[cueId] || { text: cueId, priority: 'primary' };
        var rank = PRIORITY_RANK[def.priority];
        var isSafety = def.priority === 'safety';

        if (state.confidenceFrozen) return { action: 'suppress', reason: 'low_confidence' };
        if (state.calibrating && !isSafety) return { action: 'suppress', reason: 'calibrating' };
        if (state.fatigued && !isSafety) return { action: 'suppress', reason: 'fatigued' };
        if (state.faded[cueId]) {
          // 3-strike silence — but say the quality line exactly once.
          if (!state.fadeLineSaid) {
            state.fadeLineSaid = true;
            occupy(now, 'primary');
            return { action: 'speak', text: FADE_LINE, interrupt: false, cue_id: cueId, faded: true };
          }
          return { action: 'suppress', reason: 'faded' };
        }
        if (def.priority === 'refinement' &&
            state.targetReps >= 2 && state.rep >= state.targetReps - 2) {
          return { action: 'suppress', reason: 'final_reps' };
        }
        var channelBusy = (now - state.lastSpokenAt) < OCCUPY_MS;
        if (channelBusy && rank <= state.lastSpokenPriority && !isSafety) {
          return { action: 'suppress', reason: 'channel_busy' };
        }
        if (!isSafety && state.rep <= state.lastCueRep) {
          return { action: 'suppress', reason: 'rep_spacing' };
        }

        state.lastCueRep = state.rep;
        state.lastCueId = cueId;
        state.strikes[cueId] = (state.strikes[cueId] || 0) + 1;
        if (state.strikes[cueId] >= STRIKES_TO_FADE) {
          state.faded[cueId] = true;
          if (state.cueResistant.indexOf(cueId) === -1) state.cueResistant.push(cueId);
        }
        if (isSafety) state.safetyActiveUntil = now + OCCUPY_MS;
        occupy(now, def.priority);
        return { action: 'speak', text: def.text, interrupt: isSafety, cue_id: cueId };
      },

      // ── rep boundary (R4c praise + R4d calibration end) ────────────────
      // correctedCueIds: cues from the PREVIOUS rep now verdicted corrected
      // (RepCapture's next-rep computation). formPct: this rep's average.
      repClosed: function (repNumber, formPct, correctedCueIds, now) {
        state.rep = repNumber;
        var lines = [];

        if (state.calibrating && repNumber >= CALIBRATION_REPS) {
          state.calibrating = false;
        }

        (correctedCueIds || []).forEach(function (cueId) {
          state.strikes[cueId] = 0;   // corrected — strikes reset
          if (!state.praisedThisSet) {
            state.praisedThisSet = true;
            occupy(now, 'primary');
            lines.push(CORRECTED_PRAISE[cueId] || CORRECTED_PRAISE_DEFAULT);
          }
        });

        if (typeof formPct === 'number' && formPct >= GOOD_FORM_PCT) {
          state.goodStreak += 1;
        } else {
          state.goodStreak = 0;
        }
        if (!state.praisedThisSet && state.goodStreak >= GOOD_WINDOW_REPS &&
            !state.calibrating && !state.confidenceFrozen) {
          state.praisedThisSet = true;
          occupy(now, 'primary');
          lines.push(PRAISE_POOL[state.praiseIndex % PRAISE_POOL.length]);
          state.praiseIndex += 1;
        }
        return { lines: lines };
      },

      // ── confidence gate (R4e) ──────────────────────────────────────────
      confidence: function (visible, now) {
        if (visible) {
          state.lowSince = null;
          if (state.confidenceFrozen) {
            state.confidenceFrozen = false;
            state.confidenceAnnounced = false;  // a new episode may speak again
          }
          return { frozen: false, line: null };
        }
        if (state.lowSince === null) state.lowSince = now;
        if (now - state.lowSince >= CONFIDENCE_TRIP_MS) {
          var line = null;
          if (!state.confidenceAnnounced) {
            state.confidenceAnnounced = true;
            occupy(now, 'primary');
            line = CONFIDENCE_LINE;
          }
          state.confidenceFrozen = true;
          return { frozen: true, line: line };
        }
        return { frozen: state.confidenceFrozen, line: null };
      },

      // ── fatigue mode (R4g) ─────────────────────────────────────────────
      setFatigued: function () { state.fatigued = true; },

      // ── tempo channel + adjust line (R4f/R4h) ──────────────────────────
      tempoAllowed: function (now) {
        return (now - state.lastSpokenAt) >= OCCUPY_MS &&
               !state.confidenceFrozen;
      },
      tempoAdjustLine: function (direction) {
        if (state.tempoAdjustSaid) return null;   // max once per set
        state.tempoAdjustSaid = true;
        return direction === 'fast'
          ? 'A bit quick — slow the lowering'
          : 'A touch slow — keep it moving';
      },

      // ── coloring answers (R4d/R4e/R4f) ─────────────────────────────────
      colorsFrozen: function () {
        return state.calibrating || state.confidenceFrozen;
      },
      redAllowed: function (now) {
        return now < state.safetyActiveUntil;
      },

      cueResistantIds: function () { return state.cueResistant.slice(); },
      isCalibrating: function () { return state.calibrating; },
    };
    return arbiter;
  }

  // ── R4d: the calibration wrapper's pure math ─────────────────────────────
  // Given the textbook phase target and the patient's calibrated natural
  // bottom angle for the primary joint, return the adjusted target angle:
  // shallower-than-textbook movers are scored against THEIR range plus a
  // gentle 5° encouragement; textbook-or-deeper movers keep the textbook
  // target. Never demands deeper than textbook; never accepts less than a
  // 40°-shallower floor (garbage calibration can't gut the exercise).
  function calibratedTarget(textbookAngle, naturalBottomAngle) {
    if (typeof textbookAngle !== 'number' ||
        typeof naturalBottomAngle !== 'number') return textbookAngle;
    if (naturalBottomAngle <= textbookAngle + 10) return textbookAngle;
    var adjusted = naturalBottomAngle - 5;
    return Math.min(adjusted, textbookAngle + 40);
  }

  return {
    CUES: CUES,
    PRAISE_POOL: PRAISE_POOL,
    LINES: {
      fade: FADE_LINE,
      calibration: CALIBRATION_LINE,
      confidence: CONFIDENCE_LINE,
      fatigue: FATIGUE_LINE,
    },
    createArbiter: createArbiter,
    calibratedTarget: calibratedTarget,
  };
});
