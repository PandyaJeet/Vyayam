"""
MODULE 2 VERIFICATION — Therapist console: prescription builder, copy-week,
seat limits, messaging, visit notes.

TEST-ONLY. Zero application-code changes. Each test proves the CURRENT behavior
of the codebase as of the run date. Where a scenario exposes a gap, the test
asserts and comments the current reality so a future silent change is flagged —
it does NOT fix the gap.

Placement precedent (Module 1): cross-tenant/console tests live at the
therapist_app ROOT (alongside test_group4.py / test_verification_m1.py), not a
tests/ subdir — so this file sits there too.

Legend:
  PASS    — invariant held as expected.
  FINDING — documents a current gap; the assertion locks in today's reality.
  (Both are "green" at the Django level — a FINDING test asserts, it does not fail.)

Branch: main (ship-ready-2026-06 retired). No overlap with Module 1, which
covered models/auth/access-control; this module covers the builder write paths.
"""

import json
import re

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from therapist_app.models import (
    Prescription,
    PrescriptionItem,
    Therapist,
    TherapistMessage,
    TherapistPatientLink,
    VisitNote,
)
from therapist_app.views import EXERCISES_BY_ID


# ---------------------------------------------------------------------------
# Factories / helpers
# ---------------------------------------------------------------------------

def make_therapist(username, *, seat_limit=12, full_name='Dr. Console'):
    user = User.objects.create_user(username=username, password='pass')
    therapist = Therapist.objects.create(
        user=user, full_name=full_name, seat_limit=seat_limit)
    return user, therapist


def make_link(therapist, username, *, status='active', **extra):
    patient_user = User.objects.create_user(username=username, password='x')
    return TherapistPatientLink.objects.create(
        therapist=therapist, patient=patient_user, status=status, **extra)


# A known-good catalog entry (verified live: ex_bw_squat → "Bodyweight Squat",
# movement_pattern "Squat").
VALID_ID = 'ex_bw_squat'
VALID_NAME = EXERCISES_BY_ID[VALID_ID]['name']
VALID_PATTERN = EXERCISES_BY_ID[VALID_ID]['movement_pattern']


class M2TestBase(TestCase):
    """Cache hygiene, mirroring Module 1 — none of these endpoints are
    rate-limited (see S4), but we keep the process-wide LocMemCache clean so we
    never influence adjacent tests in the run."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def post_program(self, link, payload, client=None):
        client = client or self.client
        return client.post(
            reverse('therapist_save_program', args=[link.id]),
            data=json.dumps(payload), content_type='application/json')


# ===========================================================================
# F — FUNCTIONAL / DATA INTEGRITY
# ===========================================================================

class F1CatalogValidation(M2TestBase):
    """F1 — save_program does NOT cross-validate exercise_id/exercise_name
    against EXERCISES_BY_ID on publish (therapist_app/views.py:1038-1046)."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f1')
        self.link = make_link(self.therapist, 'p_f1')
        self.client.force_login(self.user)

    def test_f1a_unknown_exercise_id_persists_silently(self):
        """FINDING: an exercise_id absent from the catalog is stored anyway —
        movement_pattern='' and exercise_name = whatever the client sent (or the
        raw id). No validation error, no rejection."""
        self.post_program(self.link, {
            'week_number': 1, 'publish': True,
            'items': [{'exercise_id': 'ex_totally_made_up_zzz',
                       'exercise_name': 'Ghost Move', 'sets': 3, 'reps': 10}],
        })
        item = PrescriptionItem.objects.get(exercise_id='ex_totally_made_up_zzz')
        self.assertEqual(item.movement_pattern, '')       # catalog miss → blank
        self.assertEqual(item.exercise_name, 'Ghost Move')  # client string kept verbatim

    def test_f1a_unknown_id_no_name_falls_back_to_raw_id(self):
        """FINDING: with no client name, the raw (bogus) id becomes the name."""
        self.post_program(self.link, {
            'week_number': 2, 'publish': True,
            'items': [{'exercise_id': 'ex_bogus_2', 'sets': 3, 'reps': 10}],
        })
        item = PrescriptionItem.objects.get(exercise_id='ex_bogus_2')
        self.assertEqual(item.exercise_name, 'ex_bogus_2')

    def test_f1b_valid_id_client_name_overrides_catalog(self):
        """FINDING: a REAL id paired with a mismatched client name stores the
        client's name, not the catalog's — the name is client-controlled."""
        self.post_program(self.link, {
            'week_number': 3, 'publish': True,
            'items': [{'exercise_id': VALID_ID, 'exercise_name': 'Banana Squats',
                       'sets': 3, 'reps': 10}],
        })
        item = PrescriptionItem.objects.get(prescription__week_number=3)
        self.assertEqual(item.exercise_id, VALID_ID)
        self.assertEqual(item.exercise_name, 'Banana Squats')   # NOT VALID_NAME
        self.assertNotEqual(item.exercise_name, VALID_NAME)
        # movement_pattern still comes from the catalog (server-side), unaffected.
        self.assertEqual(item.movement_pattern, VALID_PATTERN)


class F2PublishAtomicReplace(M2TestBase):
    """F2 — Publish deletes-all-then-recreates inside transaction.atomic()
    (views.py:1027-1061). A malformed mid-array entry must not leave a
    partial-delete/partial-create state."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f2')
        self.link = make_link(self.therapist, 'p_f2')
        self.client.force_login(self.user)

    def test_f2_bad_entry_rolls_back_leaving_original_three_intact(self):
        """Seed 3 published items, then re-publish with a plain STRING mid-array
        (not a dict). Reports which outcome occurs.

        Live outcome: the string has no .get() → AttributeError inside the atomic
        block → full rollback. The delete-all is undone and the ORIGINAL 3 items
        remain (no partial state). The request surfaces as a 500."""
        base_items = [{'exercise_id': VALID_ID, 'exercise_name': f'Ex{i}',
                       'sets': 3, 'reps': 10} for i in range(3)]
        self.post_program(self.link, {'week_number': 1, 'publish': True, 'items': base_items})
        rx = Prescription.objects.get(link=self.link, week_number=1)
        self.assertEqual(rx.items.count(), 3)
        original_ids = sorted(rx.items.values_list('id', flat=True))

        # A client that returns the 500 instead of re-raising into the test.
        silent = Client(raise_request_exception=False)
        silent.force_login(self.user)
        resp = self.post_program(self.link, {
            'week_number': 1, 'publish': True,
            'items': [base_items[0], 'i-am-a-string-not-a-dict', base_items[1]],
        }, client=silent)

        # Outcome B: it failed AND the original 3 are byte-for-byte intact.
        self.assertEqual(resp.status_code, 500)
        rx.refresh_from_db()
        self.assertEqual(rx.items.count(), 3)
        self.assertEqual(sorted(rx.items.values_list('id', flat=True)), original_ids)


class F3DraftAutosaveUpdatesInPlace(M2TestBase):
    """F3 — Draft autosave (publish=False) on an existing (link, week_number)
    updates the same row; unique_together holds, no IntegrityError."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f3')
        self.link = make_link(self.therapist, 'p_f3')
        self.client.force_login(self.user)

    def test_f3_second_draft_updates_same_row(self):
        self.post_program(self.link, {'week_number': 4, 'publish': False,
                                      'items': [{'exercise_id': VALID_ID, 'sets': 2, 'reps': 8}]})
        self.post_program(self.link, {'week_number': 4, 'publish': False,
                                      'items': [{'exercise_id': VALID_ID, 'sets': 5, 'reps': 5}]})
        rows = Prescription.objects.filter(link=self.link, week_number=4)
        self.assertEqual(rows.count(), 1)  # unique_together (link, week) held
        rx = rows.first()
        self.assertIsNone(rx.published_at)
        self.assertEqual(rx.draft_json['items'][0]['sets'], 5)  # latest payload reflected


class F4CopyPreviousWeek(M2TestBase):
    """F4 — copy_previous_week guards (views.py:471-507)."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f4')
        self.link = make_link(self.therapist, 'p_f4', program_start=None)
        self.client.force_login(self.user)

    def _copy(self):
        return self.client.post(reverse('therapist_copy_week', args=[self.link.id]))

    def _seed_week(self, week, *, pain=7, notes='carry me'):
        rx = Prescription.objects.create(link=self.link, week_number=week,
                                         notes_for_patient=notes,
                                         published_at=None)
        PrescriptionItem.objects.create(
            prescription=rx, order=0, exercise_id=VALID_ID, exercise_name=VALID_NAME,
            movement_pattern=VALID_PATTERN, sets=4, reps=6, load='BW',
            rest_seconds=90, tempo='3-1-1-0', notes='src note',
            pain_stop_threshold=pain)
        return rx

    def test_f4a_no_prescriptions_creates_nothing(self):
        """A: nothing to copy → flash error, redirect, zero rows created."""
        resp = self._copy()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Prescription.objects.filter(link=self.link).count(), 0)
        self.assertEqual(PrescriptionItem.objects.count(), 0)

    def test_f4b_target_week_with_items_untouched(self):
        """B: target week already has items → flash error, existing target NOT
        duplicated or overwritten."""
        self._seed_week(1)                       # source
        target = self._seed_week(2, pain=3, notes='existing wk2')  # target already populated
        target_item_ids = sorted(target.items.values_list('id', flat=True))
        resp = self._copy()
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        # Untouched: same single item, same ids, notes unchanged.
        self.assertEqual(sorted(target.items.values_list('id', flat=True)), target_item_ids)
        self.assertEqual(target.items.count(), 1)
        self.assertEqual(target.notes_for_patient, 'existing wk2')

    def test_f4c_clean_copy_preserves_fields_incl_pain_zero(self):
        """C: clean copy — notes carry over, published_at None, every item field
        matches the source EXACTLY, including an explicit pain_stop_threshold=0
        (must copy as 0, not None, not the default)."""
        src = self._seed_week(1, pain=0, notes='hydrate + rest')
        resp = self._copy()
        self.assertEqual(resp.status_code, 302)
        target = Prescription.objects.get(link=self.link, week_number=2)
        self.assertIsNone(target.published_at)
        self.assertEqual(target.notes_for_patient, 'hydrate + rest')
        s = src.items.first()
        t = target.items.first()
        self.assertEqual(t.pain_stop_threshold, 0)  # explicit 0 preserved
        for f in ('exercise_id', 'exercise_name', 'movement_pattern', 'sets',
                  'reps', 'load', 'rest_seconds', 'tempo', 'notes', 'order',
                  'pain_stop_threshold'):
            self.assertEqual(getattr(t, f), getattr(s, f), f'field {f} mismatch')


class F5SeatLimit(M2TestBase):
    """F5 — Seat-limit enforcement boundary.
    Live: Therapist.active_link_count filters status='active' ONLY
    (models.py:68-69); pending invites are NOT counted. invite_patient gates on
    `active_link_count >= seat_limit` (views.py:646). simulate_accept_invite has
    NO seat re-check (verified: grep of its body finds no seat_limit reference)."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f5', seat_limit=2)
        self.client.force_login(self.user)

    def _invite(self, name, email, phone):
        return self.client.post(reverse('therapist_invite_patient'),
                                data={'name': name, 'email': email, 'phone': phone, 'age': '30'})

    def test_f5_invite_gate_blocks_at_active_seat_limit(self):
        """PASS: with seat_limit active links, invite_patient rejects — no new
        User, no new link (the gate runs BEFORE User creation, views.py:646)."""
        make_link(self.therapist, 'seat_a', status='active')
        make_link(self.therapist, 'seat_b', status='active')
        self.assertEqual(self.therapist.active_link_count, 2)
        users_before = User.objects.count()
        links_before = TherapistPatientLink.objects.filter(therapist=self.therapist).count()
        self._invite('Third Wheel', 'third@x.com', '9160000003')
        self.assertEqual(User.objects.count(), users_before)          # no user created
        self.assertEqual(
            TherapistPatientLink.objects.filter(therapist=self.therapist).count(),
            links_before)                                             # no link created
        self.assertFalse(User.objects.filter(username='third@x.com').exists())

    def test_f5_pending_uncapped_and_accept_bypasses_seat_limit(self):
        """FINDING: seat_limit is trivially exceedable. Pending invites do not
        count toward active_link_count, so invite_patient never blocks them; and
        simulate_accept_invite promotes pending→active with NO seat re-check. Net:
        a seat_limit=2 therapist ends with 3 ACTIVE links."""
        # Three invites all succeed — active_link_count stays 0 throughout.
        self._invite('A One', 'a1@x.com', '9160001001')
        self._invite('B Two', 'b2@x.com', '9160001002')
        self._invite('C Three', 'c3@x.com', '9160001003')
        self.assertEqual(self.therapist.active_link_count, 0)
        pending = TherapistPatientLink.objects.filter(therapist=self.therapist, status='pending')
        self.assertEqual(pending.count(), 3)  # invite gate never capped pending

        for link in pending:
            resp = self.client.post(reverse('therapist_simulate_accept', args=[link.id]))
            self.assertEqual(resp.status_code, 302)  # accepted, never rejected

        self.assertEqual(self.therapist.active_link_count, 3)  # 3 > seat_limit 2 — bypassed


class F6PainStopThresholdZero(M2TestBase):
    """F6 — pain_stop_threshold explicit-0 handling in save_program
    (views.py:1055-1059). Same 0-is-falsy bug class as the fixed D2 finding —
    confirm it wasn't reintroduced in this path."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f6')
        self.link = make_link(self.therapist, 'p_f6')
        self.client.force_login(self.user)

    def test_f6_zero_preserved_blank_becomes_null(self):
        self.post_program(self.link, {'week_number': 1, 'publish': True, 'items': [
            {'exercise_id': VALID_ID, 'exercise_name': 'zero', 'pain_stop_threshold': 0, 'order': 0},
            {'exercise_id': VALID_ID, 'exercise_name': 'blank', 'pain_stop_threshold': '', 'order': 1},
            {'exercise_id': VALID_ID, 'exercise_name': 'absent', 'order': 2},
        ]})
        by_name = {i.exercise_name: i for i in Prescription.objects.get(
            link=self.link, week_number=1).items.all()}
        self.assertEqual(by_name['zero'].pain_stop_threshold, 0)     # explicit 0 kept
        self.assertIsNone(by_name['blank'].pain_stop_threshold)      # '' → NULL
        self.assertIsNone(by_name['absent'].pain_stop_threshold)     # absent → NULL


class F7VisitNoteTruncation(M2TestBase):
    """F7 — add_visit_note stores note[:5000] (views.py:524)."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_f7')
        self.link = make_link(self.therapist, 'p_f7')
        self.client.force_login(self.user)

    def test_f7_6000_chars_truncated_to_5000(self):
        long_note = 'x' * 6000
        resp = self.client.post(reverse('therapist_add_visit_note', args=[self.link.id]),
                                data={'note': long_note})
        self.assertEqual(resp.status_code, 302)  # no error
        note = VisitNote.objects.get(link=self.link)
        self.assertEqual(len(note.note), 5000)


# ===========================================================================
# S — SECURITY
# ===========================================================================

class S1IDOR(M2TestBase):
    """S1 — IDOR light regression: cross-therapist link_id → 404 via
    get_linked_patient_or_404. One case only (broadly covered elsewhere)."""

    def test_s1_save_program_on_other_therapists_link_404(self):
        user_a, therapist_a = make_therapist('dr_s1a')
        _, therapist_b = make_therapist('dr_s1b')
        link_b = make_link(therapist_b, 'p_s1b')
        self.client.force_login(user_a)
        resp = self.post_program(link_b, {'week_number': 1, 'publish': True, 'items': []})
        self.assertEqual(resp.status_code, 404)
        # Nothing was written to B's link.
        self.assertEqual(Prescription.objects.filter(link=link_b).count(), 0)


class S2UnboundedItems(M2TestBase):
    """S2 — save_program's items array has no length cap
    (items_raw = payload.get('items') or []; no bound before the create loop)."""

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_s2')
        self.link = make_link(self.therapist, 'p_s2')
        self.client.force_login(self.user)

    def test_s2_large_items_array_all_created_no_cap(self):
        """FINDING (resource-exhaustion shape): a large items array is accepted
        wholesale — 500 items → 500 PrescriptionItem rows, no rejection, no cap."""
        n = 500
        items = [{'exercise_id': VALID_ID, 'exercise_name': f'E{i}',
                  'sets': 3, 'reps': 10} for i in range(n)]
        resp = self.post_program(self.link, {'week_number': 1, 'publish': True, 'items': items})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['item_count'], n)
        self.assertEqual(
            PrescriptionItem.objects.filter(prescription__link=self.link).count(), n)


class S3BuilderXSSEscaping(M2TestBase):
    """S3 — Program Builder / visit-note XSS regression (Run 2 #2). Storage is
    verbatim (no server-side escaping); safety relies on template autoescape."""

    XSS = '"><script>alert(1)</script>'

    def setUp(self):
        super().setUp()
        self.user, self.therapist = make_therapist('dr_s3')
        self.link = make_link(self.therapist, 'p_s3')
        self.client.force_login(self.user)

    def test_s3_stored_raw_but_rendered_escaped(self):
        # Stored verbatim by save_program / add_visit_note (proves no mark_safe
        # stripping at write — escaping must happen at render).
        self.post_program(self.link, {'week_number': 1, 'publish': True, 'items': [
            {'exercise_id': VALID_ID, 'exercise_name': self.XSS, 'sets': 3, 'reps': 10}]})
        item = Prescription.objects.get(link=self.link, week_number=1).items.first()
        self.assertEqual(item.exercise_name, self.XSS)
        self.client.post(reverse('therapist_add_visit_note', args=[self.link.id]),
                         data={'note': self.XSS})
        self.assertEqual(VisitNote.objects.get(link=self.link).note, self.XSS)

        # Rendered: the raw, live <script> must never appear in any tab's HTML.
        for tab in ('builder', 'notes'):
            resp = self.client.get(
                reverse('therapist_patient_detail', args=[self.link.id]) + f'?tab={tab}')
            self.assertEqual(resp.status_code, 200)
            body = resp.content.decode()
            self.assertNotIn('<script>alert(1)</script>', body,
                             f'raw script leaked on tab={tab}')


class S4MissingRateLimit(M2TestBase):
    """S4 — save_program / add_visit_note / send_message carry NO @rate_limit,
    unlike every comparable write endpoint and all three logins. Confirmed by
    source inspection (sufficient evidence; no timing test needed)."""

    def test_s4_write_endpoints_lack_rate_limit_decorator(self):
        """FINDING: none of the three write endpoints are rate-limited. In
        therapist_app/views.py, `rate_limit` appears only on therapist_login."""
        import inspect
        import therapist_app.views as views
        src = inspect.getsource(views)

        # rate_limit is used exactly once in the module — on therapist_login.
        self.assertEqual(src.count('@rate_limit('), 1)
        login_idx = src.index('def therapist_login')
        self.assertIn('@rate_limit(', src[max(0, login_idx - 200):login_idx])

        # For each target endpoint, the ~8 lines above its def hold no @rate_limit.
        for fn in ('save_program', 'add_visit_note', 'send_message'):
            idx = src.index(f'def {fn}(')
            preamble = src[max(0, idx - 400):idx]
            self.assertNotIn('@rate_limit', preamble, f'{fn} unexpectedly rate-limited')


class S5AnonymousAccess(M2TestBase):
    """S5 — Anonymous access spot-check on the builder surfaces."""

    def setUp(self):
        super().setUp()
        _, self.therapist = make_therapist('dr_s5')
        self.link = make_link(self.therapist, 'p_s5')

    def test_s5_anon_post_save_program_redirects_to_login(self):
        resp = self.post_program(self.link, {'week_number': 1, 'publish': True, 'items': []})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/therapist/login/', resp.url)
        self.assertEqual(Prescription.objects.filter(link=self.link).count(), 0)

    def test_s5_anon_get_patient_detail_redirects_to_login(self):
        resp = self.client.get(reverse('therapist_patient_detail', args=[self.link.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/therapist/login/', resp.url)
        # No patient data leaked in the redirect body.
        self.assertNotIn(self.link.display_name, resp.content.decode())
