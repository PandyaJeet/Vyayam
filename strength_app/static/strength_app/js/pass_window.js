/* Pass Window: game loop, browser side only. Demo scenarios, UNREVIEWED.
 * Registers with MindLab (mind_lab_runner.js). Config arrives as ctx.cfg:
 *   { level, scenarios:[...], order:[ids], base_closing_ms, l5_limit_ms,
 *     freeze_ms, max_s, factors:{1:0.3,...}, visitor:bool }
 * The server rescores every trial; nothing scored here is trusted. */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.PassWindow = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';

  function closingMs(base, factor) { return base / factor; }

  /* Level 5 also has a decision limit; the earlier of the two ends the trial. */
  function trialLimitMs(level, base, factor, l5Limit) {
    var c = closingMs(base, factor);
    return level === 5 ? Math.min(c, l5Limit) : c;
  }

  function parseOption(opt) {
    var i = opt.indexOf(':');
    var lane = opt.slice(i + 1);
    var g = /^gap\((D\d+)-(D\d+)\)$/.exec(lane);
    return { mate: opt.slice(0, i), lane: lane, gap: g ? [g[1], g[2]] : null };
  }

  function judge(sc, chosen) {
    if (chosen === sc.correct) return 'best';
    if (sc.acceptable.indexOf(chosen) !== -1) return 'acceptable';
    return 'wrong';
  }

  /* Level 3+: lanes the athlete may pick after tapping a teammate. */
  function laneChoices(sc, level) {
    if (level < 3) return [];
    var gaps = [];
    sc.options.forEach(function (o) {
      var p = parseOption(o);
      if (p.gap && gaps.indexOf(p.lane) === -1) gaps.push(p.lane);
    });
    return gaps.length ? ['direct'].concat(gaps) : [];
  }

  function mirror(sc) {
    function m(pt) { return [100 - pt[0], pt[1]]; }
    var c = JSON.parse(JSON.stringify(sc));
    c.carrier = m(c.carrier);
    c.mates.forEach(function (x) { x.at = m(x.at); });
    c.defenders.forEach(function (d) { d.at = m(d.at); if (d.to) d.to = m(d.to); });
    return c;
  }

  function median(a) {
    if (!a.length) return null;
    var s = a.slice().sort(function (x, y) { return x - y; });
    var h = s.length >> 1;
    return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
  }

  function byId(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function el(name, attrs, text) {
    var n = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text) n.textContent = text;
    return n;
  }
  function html(tag, text, css) {
    var n = document.createElement(tag);
    if (text) n.textContent = text;
    if (css) n.style.cssText = css;
    return n;
  }

  function create(ctx) {
    var cfg = ctx.cfg, host = ctx.host, level = cfg.level;
    var factor = cfg.factors[level];
    var trials = [], results = [], idx = 0, t0 = Date.now();

    function say(text) { box.textContent = text; }
    var box = html('div', '', 'min-height:2.6em; margin-top:8px;');
    var lanes = html('div', '', 'margin-top:8px;');

    function rules() {
      host.textContent = '';
      host.appendChild(html('h3', 'Pass Window', 'margin:0 0 6px;'));
      host.appendChild(html('p', 'Demo scenarios. Tap the best teammate to pass to before the defender closes in.'));
      host.appendChild(html('p', 'Circle: you. Squares: teammates. Triangles: defenders.'));
      host.appendChild(html('p', 'Time Assist: ' + factor + 'x. 1.0x is the app\'s base speed.'));
      host.appendChild(html('p', 'This is a training game. It is not a return-to-play test and says nothing about match performance.',
        'font-size:.8rem; opacity:.8;'));
      var b = html('button', 'Start', 'width:100%; padding:12px;');
      b.className = 'ath-btn';
      b.onclick = nextTrial;
      host.appendChild(b);
    }

    function nextTrial() {
      var out = (Date.now() - t0) / 1000 >= cfg.max_s;
      if (idx >= cfg.order.length || out) return end();
      var sc = byId(cfg.scenarios, cfg.order[idx]);
      if (level === 5 && Math.random() < 0.5) sc = mirror(sc);
      play(sc);
    }

    function play(sc) {
      host.textContent = '';
      var svg = el('svg', { viewBox: '0 0 100 100', role: 'img',
        'aria-label': 'Pitch. Circle is you, squares are teammates, triangles are defenders.',
        style: 'width:100%; max-width:420px; background:#1d3b2a; border-radius:8px; touch-action:manipulation;' });
      var pos = {}, defs = [];
      var cx = sc.carrier;
      svg.appendChild(el('circle', { cx: cx[0], cy: cx[1], r: 3, fill: '#fff' }));
      sc.defenders.forEach(function (d) {
        var g = el('polygon', { points: '0,-3.6 3.2,2.6 -3.2,2.6', fill: '#b48cff', stroke: '#2b1a4d', 'stroke-width': 0.4 });
        var t = el('text', { 'font-size': 3, fill: '#fff', 'text-anchor': 'middle' }, d.id);
        svg.appendChild(g); svg.appendChild(t);
        defs.push({ d: d, g: g, t: t });
        pos[d.id] = d.at;
      });
      var done = false;
      function finishTrial(chosen, timeout, ms) {
        if (done) return; done = true;
        cancelAnimationFrame(raf);
        lanes.textContent = '';
        trials.push({ scenario_id: sc.id, chosen: chosen, timeout: timeout,
          decision_ms: timeout ? null : Math.round(ms) });
        var r = timeout ? 'timeout' : judge(sc, chosen);
        results.push(r);
        reveal(sc, svg, r);
      }
      sc.mates.forEach(function (m) {
        var g = el('g', { tabindex: 0, role: 'button', 'aria-label': 'Pass to ' + m.id, style: 'cursor:pointer;' });
        g.appendChild(el('rect', { x: m.at[0] - 3, y: m.at[1] - 3, width: 6, height: 6, fill: '#3fd0c0', stroke: '#0b3d36', 'stroke-width': 0.4 }));
        g.appendChild(el('text', { x: m.at[0], y: m.at[1] - 4.5, 'font-size': 3, fill: '#fff', 'text-anchor': 'middle' }, m.id));
        function pick() { onMate(m.id); }
        g.addEventListener('click', pick);
        g.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') pick(); });
        svg.appendChild(g);
      });
      host.appendChild(svg); host.appendChild(box); host.appendChild(lanes);
      say('Pick the best pass.');

      function onMate(id) {
        var ms = performance.now() - start;
        var choices = laneChoices(sc, level);
        if (!choices.length) return finishTrial(id + ':direct', false, ms);
        // Gap choice (Level 3+): the clock keeps running while the lane is picked.
        lanes.textContent = '';
        say('Which lane for ' + id + '?');
        choices.forEach(function (lane) {
          var b = html('button', lane === 'direct' ? 'Direct' : 'Through the gap ' + lane.slice(4, -1).replace('-', ' and '),
            'margin:4px 6px 0 0; padding:10px;');
          b.className = 'ath-btn';
          b.onclick = function () { finishTrial(id + ':' + lane, false, performance.now() - start); };
          lanes.appendChild(b);
        });
      }

      var limit = trialLimitMs(level, cfg.base_closing_ms, factor, cfg.l5_limit_ms);
      var closeMs = closingMs(cfg.base_closing_ms, factor);
      var start = performance.now(), raf = 0;
      function frame(now) {
        var el_ = now - start;
        var f = Math.min(1, el_ / closeMs);
        defs.forEach(function (o) {
          var to = o.d.to || o.d.at;
          var x = o.d.at[0] + (to[0] - o.d.at[0]) * f, y = o.d.at[1] + (to[1] - o.d.at[1]) * f;
          pos[o.d.id] = [x, y];
          o.g.setAttribute('transform', 'translate(' + x + ',' + y + ')');
          o.t.setAttribute('x', x); o.t.setAttribute('y', y + 7);
        });
        if (el_ >= limit) return finishTrial(null, true, limit);
        raf = requestAnimationFrame(frame);
      }
      raf = requestAnimationFrame(frame);
    }

    function reveal(sc, svg, r) {
      var c = parseOption(sc.correct), m = byId(sc.mates, c.mate).at, from = sc.carrier, pts = [from];
      if (c.gap) {
        var a = byId(sc.defenders, c.gap[0]), b = byId(sc.defenders, c.gap[1]);
        pts.push([(a.at[0] + b.at[0]) / 2, (a.at[1] + b.at[1]) / 2]);
      }
      pts.push(m);
      svg.appendChild(el('polyline', { points: pts.map(function (p) { return p.join(','); }).join(' '),
        fill: 'none', stroke: '#f4be4f', 'stroke-width': 1.4, 'stroke-dasharray': '3 2' }));
      var head = { best: 'Best pass.', acceptable: 'Also OK. The best pass is shown.',
        wrong: 'Not the best pass. The best pass is shown.', timeout: 'Time ran out. The best pass is shown.' }[r];
      say(head + ' ' + sc.why + ' (Demo scenario)');
      idx += 1;
      setTimeout(nextTrial, cfg.freeze_ms);
    }

    function end() {
      var best = results.filter(function (r) { return r === 'best'; }).length;
      var rt = median(trials.filter(function (t) { return !t.timeout; }).map(function (t) { return t.decision_ms; }));
      host.textContent = '';
      host.appendChild(html('h3', 'Done', 'margin:0 0 6px;'));
      host.appendChild(html('p', best + ' of ' + results.length + ' best passes at ' + factor + 'x Time Assist.'));
      host.appendChild(html('p', 'Demo scenarios. Not a return-to-play test. Compare only with your own earlier sessions at the same level.',
        'font-size:.8rem; opacity:.8;'));
      ctx.finish({ n_trials: results.length, accuracy: results.length ? best / results.length : null,
        median_rt_ms: rt, summary: { trials: trials, demo_scenarios: true } });
    }

    return { start: rules };
  }

  if (typeof window !== 'undefined' && window.MindLab) window.MindLab.register('pass_window', create);
  return { closingMs: closingMs, trialLimitMs: trialLimitMs, parseOption: parseOption, judge: judge,
           laneChoices: laneChoices, mirror: mirror, median: median, create: create };
});
