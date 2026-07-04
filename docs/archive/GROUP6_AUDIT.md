# Group 6 Audit (Templates + Static UI)

Scope
- strength_app/templates/strength_app (base layouts, login, coach UI, error pages)
- therapist_app/templates/therapist_app (therapist console layouts)
- strength_app/static/strength_app (PWA manifest, service worker, JS)
- therapist_app/static/therapist_app (CSS)

Notes
- UI layers use mixed Bootstrap + Tailwind with CDN delivery and inline Tailwind config.
- PWA manifest/service worker present; static-only caching strategy.

Findings
1) PWA theme/background mismatch
- strength_app/templates/strength_app/base.html sets meta theme-color #0c6c3f.
- strength_app/static/strength_app/manifest.json uses theme_color #667eea and background_color #0a0e27.
- Impact: inconsistent browser UI theming; may look broken in install prompts or splash screens.
- Recommendation: align manifest colors with the UI palette used in base templates.

2) Therapist console uses fixed viewport width
- therapist_app/templates/therapist_app/base_therapist.html sets viewport to width=1280.
- Impact: poor responsiveness on laptops/tablets; mobile rendering appears scaled.
- Recommendation: use responsive viewport (width=device-width, initial-scale=1) and adjust layout if needed.

3) Service worker caches only /static/ assets
- strength_app/static/strength_app/sw.js ignores HTML endpoints and manifest.
- Impact: PWA offline behavior limited; no shell caching for routes like /v1/dashboard/.
- Recommendation: decide if offline shell is desired; if yes, pre-cache shell routes and manifest.

4) External CDN dependencies lack SRI/caching control
- Tailwind/Font Awesome/Google Fonts are loaded from CDNs in base templates.
- Impact: CSP hardening becomes harder; offline use and deterministic builds are not possible.
- Recommendation: consider pinning via SRI or self-hosted assets if CSP/offline is a goal.

5) PWA metadata and SW registration not in base_gamified
- strength_app/templates/strength_app/base_gamified.html has no manifest link or service worker registration.
- Impact: v1 pages using base_gamified do not register the service worker and will not expose install metadata.
- Recommendation: add the manifest link + SW registration to base_gamified or extract shared PWA tags into a partial.

Verification (Static Checks)
- Service worker registration exists in strength_app/templates/strength_app/base.html (registers /sw.js).
- /sw.js is routed in strength_app/urls.py and serves strength_app/static/strength_app/sw.js.
- Manifest link is present in strength_app/templates/strength_app/base.html.

Tests / Verification Ideas
- Visual smoke: login, dashboard, coach dashboard, therapist dashboard on mobile + desktop.
- PWA install: check icon, theme color, splash screen, service worker cache behavior.
- Offline: verify fallback behavior when offline (if required by product).

Status
- Fixes applied: manifest colors aligned, base_gamified PWA tags + SW registration added, therapist viewport set to responsive, SW precache added.
- No runtime UI tests run.
