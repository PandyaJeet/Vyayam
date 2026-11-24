/*
 * /exhibition/games/ page wiring (browser only). Needs window.EXH_GAMES_CFG
 * (set by exhibition_games.html), pass_window.js (window.PassWindow) and
 * exhibition_gonogo.js (window.ExhibitionGoNoGo). Nothing is stored or sent:
 * scores live in the variables below and a reload clears them.
 * Input is pointerdown. Timing is performance.now(). No sound, no fullscreen API.
 */
(function () {
  'use strict';
  if (typeof window === 'undefined' || !window.EXH_GAMES_CFG) return;
  var CFG = window.EXH_GAMES_CFG, T = CFG.text;
  var GN = window.ExhibitionGoNoGo, PW = window.PassWindow;
  var NS = 'http://www.w3.org/2000/svg';
  var $ = function (id) { return document.getElementById(id); };

  var lastActivity = Date.now();
  var prevRound = null;            // this visitor's previous Go / No-Go round, page memory only
  var gn = null;                   // the Go / No-Go round in progress

  function touch() { lastActivity = Date.now(); }
  ['pointerdown', 'keydown'].forEach(function (ev) {
    document.addEventListener(ev, touch, true);
  });
  // Idle reset: a reload returns to the choice screen and clears prevRound.
  setInterval(function () {
    if (Date.now() - lastActivity >= CFG.idle_seconds * 1000) location.reload();
  }, 1000);

  function show(id) {
    ['gChoice', 'gGnIntro', 'gGnPlay', 'gGnScore', 'gPw'].forEach(function (s) {
      $(s).hidden = (s !== id);
    });
  }
  function node(tag, text, cls) {
    var n = document.createElement(tag);
    if (text) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }
  function button(text, fn, cls) {
    var b = node('button', text, cls || 'btn');
    b.type = 'button';
    b.addEventListener('pointerdown', function (e) { e.preventDefault(); fn(); });
    return b;
  }
  // Back to the choice screen keeps prevRound; only the idle reset reloads the page.
  function backToChoice() { $('pwHost').textContent = ''; show('gChoice'); }

  // ---- Pass Window ------------------------------------------------------
  function startPassWindow() {
    show('gPw');
    var host = $('pwHost');
    host.textContent = '';
    var game = PW.create({
      cfg: CFG.pass_window, host: host, level: CFG.pass_window.level, slowmo: 1,
      finish: function () {
        var row = node('div', '', 'row');
        row.appendChild(button(T.again, startPassWindow, 'btn'));
        row.appendChild(button(T.back, backToChoice, 'btn ghost'));
        host.appendChild(row);
        var ps = host.querySelectorAll('p');   // C5: no earlier sessions exist on this page
        for (var i = 0; i < ps.length; i++) ps[i].textContent = GN.dropEarlierSessions(ps[i].textContent);
      }
    });
    game.start();
    var go = host.querySelector('button');   // skip the rules screen: one tap starts the round
    if (go) go.click();
  }

  // pass_window.js listens for click. Fire it on pointerdown so the tap is counted at touch
  // time; the click that follows is ignored by the game (its trial is already done).
  // Only this page's own synthetic click (isTrusted false) may reach the game. The real
  // click that follows the same tap is stopped, so it cannot answer a scenario by chance.
  $('pwHost').addEventListener('click', function (e) {
    if (e.isTrusted) e.stopPropagation();
  }, true);
  $('pwHost').addEventListener('pointerdown', function (e) {
    var g = e.target.closest && e.target.closest('g[role="button"]');
    if (g) g.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  }, true);

  // ---- Go / No-Go Pass --------------------------------------------------
  function shape(kind, big) {
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('class', big ? 'stim' : 'legend-shape');
    svg.setAttribute('aria-hidden', 'true');
    var s;
    if (kind === 'go') {            // teammate: blue circle
      s = document.createElementNS(NS, 'circle');
      s.setAttribute('cx', 50); s.setAttribute('cy', 50); s.setAttribute('r', 42);
      s.setAttribute('fill', '#3b82f6');
    } else {                        // opponent: orange triangle
      s = document.createElementNS(NS, 'polygon');
      s.setAttribute('points', '50,8 94,88 6,88');
      s.setAttribute('fill', '#f59e0b');
    }
    svg.appendChild(s);
    return svg;
  }

  function fillIntro() {
    var a = $('gnLegendGo'), b = $('gnLegendNo');
    a.textContent = ''; b.textContent = '';
    a.appendChild(shape('go')); a.appendChild(node('span', T.gn_go));
    b.appendChild(shape('nogo')); b.appendChild(node('span', T.gn_nogo));
  }

  function startGoNoGo() {
    show('gGnPlay');
    var area = $('gnArea');
    area.textContent = '';
    area.appendChild(node('p', T.get_ready, 'ready'));
    gn = { ladder: GN.newLadder(), sched: GN.buildSchedule(120, Date.now()), i: 0,
           trials: [], cur: null, timer: 0, endTimer: 0, tick: 0, over: false };
    setTimeout(function () {
      if (!gn || gn.over) return;
      var round = gn;
      round.t0 = performance.now();
      round.endTimer = setTimeout(function () { endGoNoGo(round); }, GN.ROUND_MS);
      round.tick = setInterval(function () {
        var left = Math.max(0, Math.ceil((GN.ROUND_MS - (performance.now() - round.t0)) / 1000));
        $('gnClock').textContent = left + ' s';
      }, 250);
      nextStim(round);
    }, 800);
  }

  function resolve(round) {
    var c = round.cur;
    if (!c) return;
    var t = { kind: c.kind, tapped: c.tapped, rtMs: c.tapped ? c.rtMs : null };
    round.trials.push(t);
    var o = GN.classify(t);
    round.ladder = GN.step(round.ladder, o === 'hit' || o === 'anticipation' || o === 'correct_reject');
    round.cur = null;
  }

  function nextStim(round) {
    if (round.over) return;
    resolve(round);
    var kind = round.sched[round.i++ % round.sched.length];
    var area = $('gnArea');
    area.textContent = '';
    area.appendChild(shape(kind, true));
    var c = round.cur = { kind: kind, tapped: false, rtMs: null, onset: 0 };
    requestAnimationFrame(function () { c.onset = performance.now(); });
    round.timer = setTimeout(function () { nextStim(round); }, round.ladder.durMs);
  }

  function onGnTap() {
    var round = gn;
    if (!round || round.over || !round.cur) return;
    var c = round.cur;
    if (c.tapped || !c.onset) return;          // first tap on a stimulus only
    c.tapped = true;
    c.rtMs = performance.now() - c.onset;
  }

  function endGoNoGo(round) {
    if (round.over) return;
    round.over = true;
    clearTimeout(round.timer); clearTimeout(round.endTimer); clearInterval(round.tick);
    // A stimulus still up counts only if it was tapped. An unanswered one is dropped.
    if (round.cur && round.cur.tapped) resolve(round);
    var s = GN.score(round.trials);
    renderScore(s);
    prevRound = s;
    gn = null;
  }

  function fmtAcc(s) { return s.accuracy === null ? T.none : Math.round(s.accuracy * 100) + '%'; }
  function fmtRt(s) { return s.meanRtMs === null ? T.no_rt : Math.round(s.meanRtMs) + ' ms'; }

  function renderScore(s) {
    show('gGnScore');
    var box = $('gnScore');
    box.textContent = '';
    box.appendChild(node('h2', T.gn_done));
    var tbl = node('table', '', 'score');
    function row(label, a, b) {
      var tr = document.createElement('tr');
      [label, a, b].forEach(function (v, i) {
        var td = node(i === 0 ? 'th' : 'td', v);
        tr.appendChild(td);
      });
      tbl.appendChild(tr);
    }
    row('', T.this_round, T.prev_round);
    row(T.accuracy, fmtAcc(s), prevRound ? fmtAcc(prevRound) : T.no_prev);
    row(T.mean_rt, fmtRt(s), prevRound ? fmtRt(prevRound) : T.no_prev);
    box.appendChild(tbl);
    box.appendChild(node('p', T.own_only, 'note'));
    var r = node('div', '', 'row');
    r.appendChild(button(T.again, function () { show('gGnIntro'); }, 'btn'));
    r.appendChild(button(T.back, backToChoice, 'btn ghost'));
    box.appendChild(r);
  }

  // ---- wiring -----------------------------------------------------------
  $('chooseGn').addEventListener('pointerdown', function (e) { e.preventDefault(); fillIntro(); show('gGnIntro'); });
  $('choosePw').addEventListener('pointerdown', function (e) { e.preventDefault(); startPassWindow(); });
  $('gnStart').addEventListener('pointerdown', function (e) { e.preventDefault(); startGoNoGo(); });
  $('gnArea').addEventListener('pointerdown', function (e) { e.preventDefault(); onGnTap(); });

  // Optional QR image: shown only once Pawan adds the file.
  var img = new Image();
  img.onload = function () {
    var q = $('qrBox');
    q.textContent = '';
    q.hidden = false;
    img.alt = T.qr_alt;
    q.appendChild(img);
  };
  img.src = CFG.qr_src;
})();
