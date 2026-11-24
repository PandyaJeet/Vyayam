/*
 * Exhibition pages: nothing is stored. install(win) wraps win.fetch so every
 * request that is not GET or HEAD resolves to an empty 204 and never leaves
 * the browser. Node-tested in exhibition_squat.test.mjs.
 * shortcut: covers fetch only (no XHR, form submit or sendBeacon); none of
 * those exist on the exhibition pages today. Add them if one ever does.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.ExhibitionGuard = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  function install(win) {
    var orig = win.fetch;
    if (!orig) return;
    win.fetch = function (input, init) {
      var m = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
      if (m !== 'GET' && m !== 'HEAD') {
        // A 204 must have a null body, or the Response constructor throws.
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      return orig.apply(this, arguments);
    };
  }
  return { install: install };
});
if (typeof window !== 'undefined') window.ExhibitionGuard.install(window);
