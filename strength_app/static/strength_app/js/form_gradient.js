/*
 * VyayamFormGradient - pure form-quality color gradient. UNWIRED.
 *
 * Replacement logic for the discrete bands in the camera template's
 * computePerJointColors (diff <= 20 green, <= 40 yellow, else red only
 * while a safety window is live, otherwise yellow). Node-tested in
 * tests/js/form_gradient.test.mjs.
 *
 * UNWIRED: no page loads this file. Wiring it in is blocked by the
 * camera/coaching freeze until MASTER_TEST_DAY.md Part F is signed.
 *
 * The rules it owns:
 *  - Continuous GREEN -> YELLOW -> ORANGE gradient from an error in degrees
 *    supplied by the caller. Large errors clamp to ORANGE. The gradient can
 *    never produce red.
 *  - Red comes ONLY from opts.safetyFlag === true (strict boolean). No
 *    error size, trend or CONFIG value reaches red any other way.
 *  - opts.frozen === true (calibrating / low confidence) beats everything,
 *    the safety flag included: neutral, no judgment.
 *  - Trend shifts the error by CONFIG.trendBiasDeg before coloring. Trend
 *    must come from form error (trendFromErrors), never from tempo:
 *    tempo NEVER colors form (locked rule).
 *  - stabilizeDiff holds the shown error inside CONFIG.deadbandDeg so a
 *    jittery reading cannot flicker across a band edge.
 *
 * Pure: no DOM, no timers, no randomness, no shared mutable state. Inputs
 * are never mutated and every call returns a fresh object.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.VyayamFormGradient = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // PROPOSED defaults. Pawan and the physio mentor tune these values.
  // For comparison, today's template bands at 20 (green) and 40 (yellow).
  var CONFIG = Object.freeze({
    greenMaxDeg: 10,   // error at or under this: solid green
    yellowDeg: 20,     // green -> yellow mix ends here (solid yellow)
    orangeDeg: 40,     // yellow -> orange mix ends here; beyond: solid orange
    trendBiasDeg: 5,   // worsening adds this; improving subtracts it (floor 0)
    deadbandDeg: 2,    // trend and stabilize ignore changes smaller than this
  });

  var COLORS = Object.freeze({
    GREEN:   Object.freeze({ r: 0,   g: 255, b: 120 }),
    YELLOW:  Object.freeze({ r: 255, g: 220, b: 0 }),
    ORANGE:  Object.freeze({ r: 255, g: 140, b: 0 }),
    RED:     Object.freeze({ r: 255, g: 50,  b: 50 }),
    NEUTRAL: Object.freeze({ r: 195, g: 205, b: 215 }),
  });

  // Always a fresh object, never a COLORS entry, so callers cannot corrupt COLORS.
  function solid(color, band) {
    return { r: color.r, g: color.g, b: color.b, band: band };
  }

  function mix(from, to, t, band) {
    // With the shipped CONFIG, t is always in (0, 1] here and this clamp
    // changes nothing. It only stops a bad retune from producing NaN or
    // out-of-range channels.
    if (!(t >= 0)) t = 0;
    if (t > 1) t = 1;
    return {
      r: Math.round(from.r + (to.r - from.r) * t),
      g: Math.round(from.g + (to.g - from.g) * t),
      b: Math.round(from.b + (to.b - from.b) * t),
      band: band,
    };
  }

  function bandFor(e) {
    if (e <= CONFIG.greenMaxDeg) return 'green';
    if (e < CONFIG.yellowDeg) return 'yellow_green';
    if (e < (CONFIG.yellowDeg + CONFIG.orangeDeg) / 2) return 'yellow';
    return 'orange';
  }

  // opts = { diffDeg, trend, safetyFlag, frozen }; undefined or null -> {}.
  // Number.isFinite is false for strings, booleans, objects, null, NaN, +-Infinity.
  function formColor(opts) {
    var o = (opts === undefined || opts === null) ? {} : opts;

    // 1. Calibrating / low confidence: no judgment at all.
    if (o.frozen === true) return solid(COLORS.NEUTRAL, 'neutral');

    // 2. The ONLY red in this module. Strict boolean true only.
    if (o.safetyFlag === true) return solid(COLORS.RED, 'red');

    // 3. No usable error: neutral, never a guess.
    if (!Number.isFinite(o.diffDeg)) return solid(COLORS.NEUTRAL, 'neutral');

    // 4. Error magnitude, shifted by trend. Any other trend value: no change.
    var e = Math.abs(o.diffDeg);
    if (o.trend === 'worsening') {
      e = e + CONFIG.trendBiasDeg;
    } else if (o.trend === 'improving') {
      e = Math.max(0, e - CONFIG.trendBiasDeg);
    }

    // 5 + 6. Gradient color and band from the same e. Never red.
    var band = bandFor(e);
    if (e <= CONFIG.greenMaxDeg) return solid(COLORS.GREEN, band);
    if (e <= CONFIG.yellowDeg) {
      return mix(COLORS.GREEN, COLORS.YELLOW,
        (e - CONFIG.greenMaxDeg) / (CONFIG.yellowDeg - CONFIG.greenMaxDeg), band);
    }
    if (e <= CONFIG.orangeDeg) {
      return mix(COLORS.YELLOW, COLORS.ORANGE,
        (e - CONFIG.yellowDeg) / (CONFIG.orangeDeg - CONFIG.yellowDeg), band);
    }
    return solid(COLORS.ORANGE, band);
  }

  // Direction of the error between two readings, compared by magnitude.
  function trendFromErrors(prevDiffDeg, currDiffDeg) {
    if (!Number.isFinite(prevDiffDeg) || !Number.isFinite(currDiffDeg)) return 'steady';
    var d = Math.abs(currDiffDeg) - Math.abs(prevDiffDeg);
    if (Math.abs(d) < CONFIG.deadbandDeg) return 'steady';
    return d < 0 ? 'improving' : 'worsening';
  }

  // Anti-flicker: keep showing the previous error until the new reading
  // moves by at least CONFIG.deadbandDeg.
  function stabilizeDiff(prevShownDiffDeg, newDiffDeg) {
    if (!Number.isFinite(newDiffDeg)) return prevShownDiffDeg;
    if (!Number.isFinite(prevShownDiffDeg)) return newDiffDeg;
    if (Math.abs(newDiffDeg - prevShownDiffDeg) < CONFIG.deadbandDeg) return prevShownDiffDeg;
    return newDiffDeg;
  }

  return {
    CONFIG: CONFIG,
    COLORS: COLORS,
    formColor: formColor,
    trendFromErrors: trendFromErrors,
    stabilizeDiff: stabilizeDiff,
  };
});
