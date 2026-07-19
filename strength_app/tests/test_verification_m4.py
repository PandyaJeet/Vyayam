"""
MODULE 4 VERIFICATION — Camera/ghost SERVER-SIDE rendering contract.

TEST-ONLY. Zero application-code changes. Zero JS. Zero new JS tests.

SCOPE BOUNDARY (respected): this file tests only the Django routing/data-assembly
layer in strength_app/v1_therapist_session_views.py — `therapist_session_exercise`,
`_render_v2_ghost`, `_enriched_items` — which sits UPSTREAM of the frozen
detection system. No file under exercise_system/ and none of the frozen JS files
(cv_core/coach_core/coach_dark/voice_core) were read to write these tests. The
ONLY thing read from exercise_system was `EXERCISE_METADATA`'s keys/shape from
exercise_registry_v2.py (sanctioned by the prompt). No landmark math, joint
angles, rep counting, or MediaPipe is read or reasoned about here. Rendering
v1_exercise_execute.html via the view (to assert HTTP 200 / context) is
observing output, not editing or pinning detection behavior.

Follows up on Module 2's F1 finding (a bad exercise_id can reach PrescriptionItem)
— F1 here proves what that bad id does at render time.
"""

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.utils import timezone

from strength_app.models import PatientProfile
from strength_app.v1_therapist_session_views import (
    EXERCISES_BY_ID,
    _enriched_items,
    _render_v2_ghost,
)
from therapist_app.models import (
    Prescription,
    PrescriptionItem,
    Therapist,
    TherapistPatientLink,
)


def _url(idx):
    return f'/therapist-session/exercise/{idx}/'


class M4Base(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.tuser = User.objects.create_user('dr_m4', password='pass')
        self.therapist = Therapist.objects.create(user=self.tuser, full_name='Dr. M4')
        self.puser = User.objects.create_user('pt_m4', password='x')
        self.link = TherapistPatientLink.objects.create(
            therapist=self.therapist, patient=self.puser,
            status='active', accepted_at=timezone.now())
        self.patient = PatientProfile.objects.create(
            patient_id='M4P', name='Pat Four', phone='9400000001', age=30,
            goals='rehab', user=self.puser, therapist_managed=True)

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def publish_item(self, *, exercise_id='ex_bw_squat', tempo='3-1-2-0',
                     name='Bodyweight Squat'):
        rx = Prescription.objects.create(
            link=self.link, week_number=1, published_at=timezone.now())
        item = PrescriptionItem.objects.create(
            prescription=rx, order=0, exercise_id=exercise_id,
            exercise_name=name, tempo=tempo, sets=3, reps=10)
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session['therapist_session'] = {'rx_id': rx.id}
        session.save()
        return rx, item


# ===========================================================================
# F — FUNCTIONAL / RENDERING CONTRACT
# ===========================================================================

class F1UnknownIdDegradesToSimple(M4Base):
    """F1 — an exercise_id absent from EXERCISES_BY_ID (reachable per Module 2 F1)
    degrades to the simple template; never camera, never 500."""

    def test_f1_unknown_id_renders_simple_200(self):
        self.publish_item(exercise_id='ex_totally_made_up_zzz', name='Ghost Move')
        resp = self.client.get(_url(0))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'strength_app/therapist_session_exercise.html')
        self.assertTemplateNotUsed(resp, 'strength_app/v1_exercise_execute.html')


class F2TempoZeroSurvives(M4Base):
    """F2 — third occurrence of the D2 / pain_stop_threshold '0-is-falsy' bug
    class. tempo_parts must stay STRINGS so an explicit '0' survives the
    template's `|default:N` filter (views.py:311-315 comment). The comment warns
    that if they were ints, '4-0-1-0' would display as '4-1-1-0'."""

    def test_f2_explicit_zero_position_survives(self):
        self.publish_item(exercise_id='ex_bw_squat', tempo='4-0-1-0')
        resp = self.client.get(_url(0))
        self.assertEqual(resp.status_code, 200)
        # Ghost template rendered.
        self.assertTemplateUsed(resp, 'strength_app/v1_exercise_execute.html')
        # Parts are strings, '0' preserved in the second position.
        self.assertEqual(resp.context['exercise']['tempo_parts'], ['4', '0', '1', '0'])
        self.assertTrue(all(isinstance(p, str) for p in resp.context['exercise']['tempo_parts']))
        body = resp.content.decode()
        self.assertIn('4-0-1-0', body)          # the 0 survived to the HTML
        self.assertNotIn('4-1-1-0', body)        # the exact corruption the comment warns of


class F3MalformedTempoNoCrash(M4Base):
    """F3 — empty / non-numeric / short tempo strings pad to length 4 and render
    200, no IndexError/ValueError (views.py:313-315)."""

    def test_f3_bad_tempos_render_200(self):
        for tempo in ('', 'abc', '4-0'):
            rx, item = self.publish_item(exercise_id='ex_bw_squat', tempo=tempo)
            resp = self.client.get(_url(0))
            self.assertEqual(resp.status_code, 200, f'tempo={tempo!r}')
            self.assertEqual(len(resp.context['exercise']['tempo_parts']), 4,
                             f'tempo={tempo!r} not padded to 4')
            # reset for next iteration (unique_together link+week)
            rx.delete()


class F4MetadataOnlyKeyNoCrash(M4Base):
    """F4 — content fallback chain (views.py:304) on a v2_key present in
    EXERCISE_METADATA but absent from both content dicts → renders with empty
    cue/form/instructions, no KeyError. (57 such metadata-only keys exist live.)"""

    def _rf_request(self):
        rf = RequestFactory()
        req = rf.get(_url(0))
        req.user = AnonymousUser()
        req.session = self.client.session
        return req

    def test_f4_metadata_only_key_renders_empty_content(self):
        from strength_app.exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        from strength_app.exercise_content import EXERCISE_CONTENT
        from strength_app.exercise_content_gap_fill import EXERCISE_CONTENT_GAP_FILL
        gap_keys = sorted(set(EXERCISE_METADATA)
                          - set(EXERCISE_CONTENT) - set(EXERCISE_CONTENT_GAP_FILL))
        self.assertTrue(gap_keys, 'expected metadata-only keys to exist live')
        v2_key = gap_keys[0]

        # The content dicts genuinely have nothing for this key → fallback is {}.
        self.assertIsNone(EXERCISE_CONTENT.get(v2_key))
        self.assertIsNone(EXERCISE_CONTENT_GAP_FILL.get(v2_key))

        _, item = self.publish_item()
        enriched = {'item': item, 'v2_exercise_key': v2_key}
        # status 200 proves the fallback chain didn't KeyError on the missing content.
        resp = _render_v2_ghost(self._rf_request(), self.patient, enriched, 0, 1, True)
        self.assertEqual(resp.status_code, 200)
        # A2 note (CLAUDE.md A8): content is surfaced via `*_en` keys that exist in
        # ZERO entries, so mind_muscle_cue/form_cues/instructions are empty even for
        # keys that DO have content — the metadata-only case is simply empty too.


class F5AllMetadataKeysResolve(M4Base):
    """F5 — every v2_exercise_key in EXERCISE_METADATA renders through
    _render_v2_ghost without a 500. Swept via direct calls (routing gate
    v2_ghost_supported is irrelevant to whether the assembler is safe)."""

    def _rf_request(self):
        rf = RequestFactory()
        req = rf.get(_url(0))
        req.user = AnonymousUser()
        req.session = self.client.session
        return req

    def test_f5_sweep_all_keys(self):
        from strength_app.exercise_system.exercise_registry_v2 import EXERCISE_METADATA
        _, item = self.publish_item()
        req = self._rf_request()
        failures = []
        keys = list(EXERCISE_METADATA.keys())
        for key in keys:
            enriched = {'item': item, 'v2_exercise_key': key}
            try:
                resp = _render_v2_ghost(req, self.patient, enriched, 0, 1, True)
                if resp.status_code != 200:
                    failures.append((key, f'status {resp.status_code}'))
            except Exception as exc:  # noqa: BLE001 — sweep, capture per-key
                failures.append((key, repr(exc)))
        self.assertEqual(failures, [], f'{len(failures)}/{len(keys)} keys failed: {failures[:5]}')
        # Sweep size recorded for the report.
        self.assertEqual(len(keys), 276)


class F6LocalVideoFlag(M4Base):
    """F6 — local_video is True only when the v2_key is in the filmed set
    (views.py:112). Never fires for a non-filmed key."""

    def test_f6_local_video_matches_filmed_set(self):
        from strength_app.cv_targets import get_video_mode_exercises
        filmed = set(get_video_mode_exercises())

        # A catalog id whose v2_key is NOT filmed → local_video False.
        not_filmed = next(
            (eid for eid, e in EXERCISES_BY_ID.items()
             if e.get('v2_exercise_key') and e['v2_exercise_key'] not in filmed),
            None)
        self.assertIsNotNone(not_filmed, 'expected some non-filmed keyed exercise')
        rx, _ = self.publish_item(exercise_id=not_filmed)
        enriched = _enriched_items(rx)[0]
        self.assertFalse(enriched['local_video'])

        # Positive control: ex_bw_squat → full_squats IS filmed → True.
        rx.delete()
        rx2, _ = self.publish_item(exercise_id='ex_bw_squat')
        self.assertIn('full_squats', filmed)
        self.assertTrue(_enriched_items(rx2)[0]['local_video'])


# ===========================================================================
# S — LIGHT CHECKS
# ===========================================================================

class S1AnonymousAccess(M4Base):
    """S1 — anonymous GET → redirect to patient_login, no data leaked."""

    def test_s1_anon_redirects(self):
        # Fresh client, no session priming.
        resp = self.client.get(_url(0))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)


class S2StaleSession(M4Base):
    """S2 — session rx_id not matching the active prescription → flash + redirect
    to therapist_session_today (views.py:249-251), never a mixed render."""

    def test_s2_stale_rx_id_redirects_to_today(self):
        rx, _ = self.publish_item(exercise_id='ex_bw_squat')
        # Tamper: point the session at a non-existent prescription id.
        session = self.client.session
        session['therapist_session'] = {'rx_id': rx.id + 999999}
        session.save()
        resp = self.client.get(_url(0))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/therapist-session/', resp.url)  # back to Today, not a render


class S3OwnPatientScoping(M4Base):
    """S3 — therapist_session_exercise only ever resolves the authenticated
    patient's OWN active link/prescription (via _active_link). Another patient's
    rx_id substituted into the session cannot render that other patient's data."""

    def test_s3_foreign_rx_not_reachable(self):
        # Patient B with their own link + published rx.
        b_user = User.objects.create_user('pt_m4b', password='x')
        b_link = TherapistPatientLink.objects.create(
            therapist=self.therapist, patient=b_user,
            status='active', accepted_at=timezone.now())
        PatientProfile.objects.create(
            patient_id='M4B', name='Bee Bee', phone='9400000002', age=30,
            goals='rehab', user=b_user, therapist_managed=True)
        b_rx = Prescription.objects.create(
            link=b_link, week_number=1, published_at=timezone.now())
        PrescriptionItem.objects.create(
            prescription=b_rx, order=0, exercise_id='ex_bw_squat',
            exercise_name='BEE SECRET EXERCISE', tempo='3-1-2-0', sets=3, reps=10)

        # Patient A authenticated, but session carries B's rx_id.
        a_rx, _ = self.publish_item(exercise_id='ex_bw_squat')
        session = self.client.session
        session['patient_id'] = self.patient.patient_id  # A
        session['therapist_session'] = {'rx_id': b_rx.id}  # foreign
        session.save()
        resp = self.client.get(_url(0))
        # A's active link resolves A's rx; state rx_id (B's) mismatches → redirect.
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn(b'BEE SECRET EXERCISE', resp.content)
