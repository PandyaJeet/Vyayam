# UX Findings — Run 2 persona walk (W3/W4)

Method: walked every user-facing flow as four personas — (1) brand-new home
user with no equipment, (2) 55-year-old healthy-ageing user, (3)
athlete-tier footballer, (4) therapist-managed B2B2C patient — plus the
therapist console as a physio running a caseload. Severity: **P1** blocks
or seriously erodes real use · **P2** friction · **P3** polish.

## Patient side

| # | Finding | Sev | Disposition |
|---|---|---|---|
| U1 | Phone+password login had **no recovery path at all** — a forgotten password permanently locked the account (no email flow, nothing for therapist-managed patients) | P1 | **BUILT** — emailed 1-hour single-use reset link (enumeration-safe responses), therapist-console temp-password button with forced change at next sign-in, support copy for the no-email case |
| U2 | Half-finished session was orphaned: dashboard offered no way back in; results sat in the session store invisible | P1 | **BUILT** — "Session in progress — N of M done · Continue" banner; markers cleared at feedback; same-day regeneration was already guarded |
| U3 | No way to fix a wrong rep count or an accidental skip — data errors were permanent within the session | P1 | **BUILT** — per-set Undo on the execute page + "Redo previous exercise" (pops the last saved result, returns to it) |
| U4 | No session history: a user could not see what they did last Tuesday, what hurt, or what they skipped | P1 | **BUILT** — /v1/history/ list + per-session detail (sets×reps, completion, pain, traffic light; form % only where measured — guided rows say "no form tracking") |
| U5 | Exercises never explain themselves — physio-grade apps build trust by saying why | P2 | **BUILT** — per-pattern rationale + real target muscles line on the execute page |
| U6 | Session time estimate | P2 | **ALREADY EXISTED** (dashboard + overview show estimated minutes) — no action |
| U7 | Profile page cards ("Equipment", "Training goals") were dead `href="#"` links; no way to update weight/email/equipment after onboarding | P2 | **BUILT** — edit form (name/email/weight/equipment); equipment change clears the cached session so the next one regenerates honestly |
| U8 | List pages mostly lacked empty states with a next action | P2 | **PARTIAL** — history empty state built; progress radar + food log already had fallbacks; remaining pages are P3 polish |
| U9 | Offline = broken fetch; no install-prompt moment | P2 | **PARTIAL** — offline fallback page now pre-cached and served on failed navigations; install-prompt moment left open (P3, needs UX decision on timing) |
| U10 | (Found during walk) The camera-failure fallback asked users to self-rate "form quality 1–5" and stored it as a form score | P1 | **BUILT in W1-4** — removed; no-camera sessions store no form score at all |
| U11 | (Found during walk) Marching/stretches/carries ghost-coached with the wrong animation and produced confident wrong scores | P1 | **BUILT in W1** — honest guided mode for all 176 unverified exercises |

## Therapist side

| # | Finding | Sev | Disposition |
|---|---|---|---|
| T1 | Patient list ordered by status+name — the morning question "who needs me?" took manual scanning | P1 | **BUILT** — triage sort: unreviewed alerts → red compliance → flagged → name; alerts stat on screen one |
| T2 | Sharp-pain and red-flag events were appended as text lines into `link.notes` — invisible unless the therapist happened to read the notes blob; nothing was reviewable | P1 | **BUILT** — Alert model + global inbox + per-patient strip + mark-as-reviewed (ownership-checked); note stamps kept as redundant trail |
| T3 | Rebuilding the same week's program by hand every week | P1 | **BUILT** — "Copy last week" clones into an unpublished draft; refuses to overwrite |
| T7 | No dated clinical notes — `link.notes` is one untyped blob (and the demo seeder stores JSON in it!) | P2 | **BUILT** — VisitNote model + Visit Notes tab |
| T4 | Program templates (save named template, load into any patient) | P2 | **SPEC'D** — ProgramTemplate model (therapist FK, name, items_json), save-from-builder + load-into-draft endpoints, manage page. ~1 day. Not built: builder JS state is the risky part; do it with a human eyeballing the builder |
| T5 | Printable patient-facing program PDF | P2 | **SPEC'D** — `generate_prescription_pdf(prescription)` in pdf_generator (reuse report styles), button on program tab. ~0.5 day |
| T6 | Adherence at a glance | P2 | **PARTIAL already** — cards show compliance % + 7-day sparkline; SVG ring is pure polish (P3) |
| T8 | Discharge summary export | P3 | **SPEC'D** — narrative + outcomes PDF assembled from ProgressReports + VisitNotes + final test scores; needs clinical copy review before building |
| T9 | (Found during walk) Patient-detail page 500'd for an invited patient who hadn't activated their app account | P1 | **BUILT** — template guard (fixed in the W4 commit) |
| T10 | (Found during walk) `_seed_demo_metrics` reads JSON out of `link.notes` — the same field alert/pain stamps append to. Works (json.loads fails → {}), but appending a stamp to a DEMO patient destroys its seeded metrics | P3 | **LOGGED** — migrate demo metrics out of `notes` when the demo seeder is next touched |

## Known remaining friction (honest list, not built this run)

- Install-prompt moment (U9 half) and remaining empty states (U8 tail).
- Weight history (U7 stores only current weight).
- Per-set RPE and skip-with-reason picker (Run-1 F9/F11 spec still open).
- Therapist console is desktop-first; tablet is fine, phone is cramped (by
  design per Run-1 viewport fix, but worth a pass before clinic sales).
