/* Mind Lab runner. Hosts any game; knows none.
 * A game registers a factory:  MindLab.register('some_id', function (ctx) {...})
 *   ctx = { host, level, slowmo, finish }  (host = DOM element to draw into)
 *   The factory returns { start() }. When the game ends it calls
 *   ctx.finish({ n_trials, accuracy, median_rt_ms, summary }).
 * The game loop lives entirely in the browser. */
(function (root) {
  'use strict';
  var games = {};

  function csrf() {
    var m = document.cookie.split(';').map(function (c) { return c.trim(); })
      .filter(function (c) { return c.indexOf('csrftoken=') === 0; })[0];
    return m ? decodeURIComponent(m.slice('csrftoken='.length)) : '';
  }

  function save(cfg, level, slowmo, result) {
    var body = {
      level: level, slowmo_factor: slowmo,
      n_trials: result.n_trials, accuracy: result.accuracy,
      median_rt_ms: result.median_rt_ms, summary: result.summary || {}
    };
    return fetch(cfg.save_url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify(body)
    });
  }

  function run(cfg, host, status) {
    var factory = games[cfg.game_id];
    if (!factory) { status.textContent = 'No game is loaded.'; return; }
    var slowmo = 1.0;
    var game = factory({
      host: host, level: cfg.level, slowmo: slowmo,
      finish: function (result) {
        save(cfg, cfg.level, slowmo, result).then(function (r) {
          status.textContent = r.ok ? 'Saved.' : 'Could not save.';
        }).catch(function () { status.textContent = 'Could not save.'; });
      }
    });
    status.textContent = '';
    game.start();
  }

  root.MindLab = {
    register: function (id, factory) { games[id] = factory; },
    run: run
  };
})(window);
