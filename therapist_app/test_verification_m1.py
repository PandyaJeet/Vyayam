"""
MODULE 1 VERIFICATION — Foundation: models, auth, cross-tenant access control.

TEST-ONLY. This file adds ZERO application-code changes. Each test proves the
CURRENT behavior of the codebase as of the run date. Where a scenario exposes a
gap, the test asserts and comments the current reality (citing the finding ID)
so a future silent change is flagged — it does NOT fix the gap.

Placement precedent: therapist_app/test_group4.py holds
`test_get_linked_patient_or_404_blocks_other_therapist`; cross-tenant/permission
tests live at the therapist_app ROOT (not a tests/ subdir), so this file sits
alongside it.

Legend in the per-test docstrings:
  PASS    — invariant held, as expected.
  FINDING — documents a current gap; the assertion locks in today's reality.
  (Both are "green" at the Django level — a FINDING test asserts, it does not fail.)

Branch note: the prompt referenced `ship-ready-2026-06`; that branch was merged
& retired 2026-07-18 (CLAUDE.md §4). Verified live against `main`.
"""

import re
from datetime import date, timedelta

from django.contrib.auth.hashers import (
    check_password,
    identify_hasher,
    is_password_usable,
    make_password,
)
from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from strength_app.models import (
    CoachPatientLink,
    FootballProfile,
    PasswordResetToken,
    PatientProfile,
    TherapistProfile,
)
from therapist_app.models import (
    Alert,
    Prescription,
    SessionLog,
    SessionReport,
    Therapist,
    TherapistPatientLink,
)
from therapist_app.permissions import get_linked_patient_or_404


# ---------------------------------------------------------------------------
# Shared factory helpers
# ---------------------------------------------------------------------------

def make_patient_profile(pid, phone, *, password='ValidPass1', age=30,
                         email='', **extra):
    """Create a PatientProfile the same way the views do — via .objects.create
    with a hashed password and NO full_clean() (mirrors the real write paths)."""
    return PatientProfile.objects.create(
        patient_id=pid,
        name=extra.pop('name', 'Test Patient'),
        phone=phone,
        email=email,
        password=make_password(password),
        age=age,
        goals=extra.pop('goals', 'Rehabilitation'),
        **extra,
    )


def make_console_therapist(username, full_name='Dr. Console'):
    """therapist_app.Therapist (console) — User + Therapist record."""
    user = User.objects.create_user(username=username, password='pass')
    therapist = Therapist.objects.create(user=user, full_name=full_name)
    return user, therapist


def make_coach(username, name='Coach One'):
    """strength_app.TherapistProfile (coach/squad) — User + TherapistProfile."""
    user = User.objects.create_user(username=username, password='pass')
    coach = TherapistProfile.objects.create(
        user=user, therapist_id=f'C_{username}', name=name,
        license_number='LIC', specialization='S&C', email='c@x.com', phone='9000000000',
    )
    return user, coach


def assert_is_hashed(testcase, stored, msg=''):
    """Assert `stored` is a recognized Django password hash, not raw plaintext."""
    testcase.assertTrue(is_password_usable(stored), f'{msg}: not a usable hash')
    # identify_hasher raises if the string is not a recognized hash format.
    identify_hasher(stored)  # would raise ValueError on raw plaintext


class M1TestBase(TestCase):
    """Base for every class in this module. The rate_limiter is IP-based on the
    process-wide LocMemCache, which Django does NOT reset between tests — so this
    base clears the cache before AND after every test to (a) isolate our own
    rate-limit assertions and (b) guarantee we never leave 429-tripping counters
    behind that would poison unrelated tests later in the run."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()


# ===========================================================================
# F — FUNCTIONAL / DATA INTEGRITY
# ===========================================================================

class F1ModelValidatorEnforcement(M1TestBase):
    """F1 — Model validators (PatientProfile.age 18-100, biological_sex choices)
    are NOT enforced without full_clean()/ModelForm.

    Verified live: grep across strength_app/views.py, strength_app/v1_coach_views.py,
    therapist_app/views.py finds NO full_clean() and NO forms.ModelForm on any
    PatientProfile write path. Guarded-at-view paths clamp instead:
      - onboarding (v1_onboarding_views.py:457-461) rejects age<18 / >120
      - coach_add_athlete (v1_coach_views.py:595-596) clamps <18 or >100 to 22
    UNGUARDED path: invite_patient parses `int(age_raw)` with NO bounds
    (therapist_app/views.py:662) → link.age; simulate_accept_invite then does
    `'age': link.age or 30` into PatientProfile.objects.get_or_create defaults
    (therapist_app/views.py:726) with no validation.
    """

    def test_f1_orm_create_bypasses_age_validator(self):
        """FINDING: out-of-range age persists silently via .objects.create
        (the way simulate_accept_invite/coach create), while full_clean() would
        have raised. Proves validators are declared but never run on write."""
        p = make_patient_profile('F1LOW', '9110000001', age=5)
        p.refresh_from_db()
        self.assertEqual(p.age, 5)  # < MinValueValidator(18), persisted anyway

        p2 = make_patient_profile('F1HIGH', '9110000002', age=200)
        p2.refresh_from_db()
        self.assertEqual(p2.age, 200)  # > MaxValueValidator(100), persisted anyway

        # The validator EXISTS — full_clean() would have rejected these. This is
        # what the write paths skip.
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_f1_orm_create_bypasses_biological_sex_choices(self):
        """FINDING: an out-of-choices biological_sex persists via .create();
        choices are only enforced by full_clean()."""
        p = make_patient_profile('F1SEX', '9110000003', biological_sex='attack_helicopter')
        p.refresh_from_db()
        self.assertEqual(p.biological_sex, 'attack_helicopter')
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_f1_invite_then_simulate_real_view_path_persists_bad_age(self):
        """FINDING: the real unguarded view chain. invite_patient(age=200) →
        simulate_accept_invite → PatientProfile.age == 200, no validation."""
        user, therapist = make_console_therapist('dr_f1')
        self.client.force_login(user)
        # invite_patient accepts age verbatim (no bounds check).
        self.client.post(reverse('therapist_invite_patient'), data={
            'name': 'Ancient One', 'email': 'ancient@x.com',
            'phone': '9110000900', 'age': '200', 'sex': 'male',
        })
        link = TherapistPatientLink.objects.get(email='ancient@x.com')
        self.assertEqual(link.age, 200)  # TherapistPatientLink.age has no validator
        # simulate_accept_invite creates the PatientProfile from link.age.
        self.client.post(reverse('therapist_simulate_accept', args=[link.id]))
        profile = PatientProfile.objects.get(user_id=link.patient_id)
        self.assertEqual(profile.age, 200)  # out-of-range persisted through the view chain


class F2PasswordHashing(M1TestBase):
    """F2 — Every password write path stores a hash, never raw plaintext.
    Django User.password and PatientProfile.password both."""

    def setUp(self):
        super().setUp()

    def test_f2_change_password_stores_hash(self):
        p = make_patient_profile('F2CP', '9120000001', password='OldPass1')
        session = self.client.session
        session['patient_id'] = p.patient_id
        session.save()
        self.client.post(reverse('change_password'), data={
            'old_password': 'OldPass1',
            'new_password': 'BrandNew9',
            'confirm_password': 'BrandNew9',
        })
        p.refresh_from_db()
        self.assertNotEqual(p.password, 'BrandNew9')
        self.assertTrue(check_password('BrandNew9', p.password))

    def test_f2_reset_password_stores_hash(self):
        p = make_patient_profile('F2RP', '9120000002', email='rp@x.com')
        raw = 'a1b2c3d4resettoken'
        PasswordResetToken.objects.create(patient=p, token=PasswordResetToken.hash_of(raw))
        self.client.post(reverse('reset_password', args=[raw]), data={
            'new_password': 'ResetPass1',
            'confirm_password': 'ResetPass1',
        })
        p.refresh_from_db()
        self.assertNotEqual(p.password, 'ResetPass1')
        self.assertTrue(check_password('ResetPass1', p.password))

    def test_f2_reset_patient_password_stores_hash(self):
        """therapist_app reset_patient_password — server-generated temp pw."""
        user, therapist = make_console_therapist('dr_f2')
        patient_user = User.objects.create_user(username='pf2', password='x')
        link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=patient_user, status='active', phone='9120000003')
        profile = make_patient_profile('F2TR', '9120000003', user=patient_user)
        old_hash = profile.password
        self.client.force_login(user)
        self.client.post(reverse('therapist_reset_patient_password', args=[link.id]))
        profile.refresh_from_db()
        self.assertNotEqual(profile.password, old_hash)
        assert_is_hashed(self, profile.password, 'reset_patient_password')

    def test_f2_simulate_accept_invite_stores_hash_both_models(self):
        """simulate_accept_invite hashes BOTH User.password and
        PatientProfile.password (server-generated temp)."""
        user, therapist = make_console_therapist('dr_f2b')
        self.client.force_login(user)
        self.client.post(reverse('therapist_invite_patient'), data={
            'name': 'Hashme', 'email': 'hashme@x.com', 'phone': '9120000004', 'age': '30',
        })
        link = TherapistPatientLink.objects.get(email='hashme@x.com')
        self.client.post(reverse('therapist_simulate_accept', args=[link.id]))
        link.patient.refresh_from_db()
        profile = PatientProfile.objects.get(user_id=link.patient_id)
        assert_is_hashed(self, link.patient.password, 'simulate User.password')
        assert_is_hashed(self, profile.password, 'simulate PatientProfile.password')

    def test_f2_coach_add_athlete_stores_hash(self):
        user, coach = make_coach('coach_f2')
        self.client.force_login(user)
        self.client.post(reverse('coach_add_athlete'), data={
            'name': 'Athlete F2', 'sport': 'football', 'season_phase': 'in_season', 'age': '22',
        })
        athlete = PatientProfile.objects.filter(athlete_tier_eligible=True).latest('created_at')
        assert_is_hashed(self, athlete.password, 'coach_add_athlete')
        self.assertNotIn(athlete.password, ('', athlete.name))


class F3SessionFixation(M1TestBase):
    """F3 — All three login surfaces rotate the session key on successful login
    (session-fixation prevention). patient login + therapist_login + coach login."""

    def setUp(self):
        super().setUp()

    def _seed_session(self):
        session = self.client.session
        session['seed'] = 'pre-login'
        session.save()
        return session.session_key

    def test_f3_patient_login_rotates_session_key(self):
        make_patient_profile('F3P', '9130000001', password='PatientPw1')
        old = self._seed_session()
        resp = self.client.post(reverse('patient_login'), data={
            'phone': '9130000001', 'password': 'PatientPw1'})
        new = self.client.session.session_key
        self.assertIsNotNone(new)
        self.assertNotEqual(old, new, 'patient login must flush the session key')
        self.assertEqual(resp.status_code, 302)

    def test_f3_therapist_login_rotates_session_key(self):
        make_console_therapist('dr_f3')
        old = self._seed_session()
        resp = self.client.post(reverse('therapist_login'), data={
            'username': 'dr_f3', 'password': 'pass'})
        new = self.client.session.session_key
        self.assertNotEqual(old, new, 'therapist_login must flush the session key')
        self.assertEqual(resp.status_code, 302)

    def test_f3_coach_login_rotates_session_key(self):
        make_coach('coach_f3')
        old = self._seed_session()
        resp = self.client.post(reverse('coach_login'), data={
            'username': 'coach_f3', 'password': 'pass'})
        new = self.client.session.session_key
        self.assertNotEqual(old, new, 'coach_login must flush the session key')
        self.assertEqual(resp.status_code, 302)


class F4MustChangePassword(M1TestBase):
    """F4 — must_change_password after reset_patient_password vs simulate_accept_invite.
    Past audit finding B-5 flagged simulate_accept_invite as NOT setting the flag."""

    def test_f4_reset_patient_password_sets_flag(self):
        """PASS: reset_patient_password sets must_change_password=True
        (therapist_app/views.py:1112)."""
        user, therapist = make_console_therapist('dr_f4a')
        patient_user = User.objects.create_user(username='pf4', password='x')
        link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=patient_user, status='active', phone='9140000001')
        profile = make_patient_profile('F4A', '9140000001', user=patient_user,
                                       must_change_password=False)
        self.client.force_login(user)
        self.client.post(reverse('therapist_reset_patient_password', args=[link.id]))
        profile.refresh_from_db()
        self.assertTrue(profile.must_change_password)

    def test_f4_simulate_accept_invite_sets_flag_b5_now_closed(self):
        """B-5 UPDATE: simulate_accept_invite NOW sets must_change_password=True
        (therapist_app/views.py:731 defaults + :742 update path). The historical
        B-5 gap (flag left False) is CLOSED at this revision. Locking in True so a
        regression that drops the flag is caught."""
        user, therapist = make_console_therapist('dr_f4b')
        self.client.force_login(user)
        self.client.post(reverse('therapist_invite_patient'), data={
            'name': 'Flag F4', 'email': 'flagf4@x.com', 'phone': '9140000002', 'age': '30'})
        link = TherapistPatientLink.objects.get(email='flagf4@x.com')
        self.client.post(reverse('therapist_simulate_accept', args=[link.id]))
        profile = PatientProfile.objects.get(user_id=link.patient_id)
        self.assertTrue(
            profile.must_change_password,
            'B-5 expected CLOSED at this revision — simulate now sets the flag')


class F5InviteUsernameCollision(M1TestBase):
    """F5 — invite_patient username collision across therapists (finding H-13).
    username = email (or phone-based key); User.objects.get_or_create(username=...)
    means two therapists inviting the SAME email share ONE underlying User."""

    def test_f5_same_email_two_therapists_share_one_user(self):
        """FINDING (H-13 still reproducible): Therapist B's link attaches to the
        exact same User row as Therapist A's link. No simulate_accept run on
        either — the shared-User fact is proven and we stop."""
        user_a, therapist_a = make_console_therapist('dr_f5a', 'Dr. A')
        user_b, therapist_b = make_console_therapist('dr_f5b', 'Dr. B')

        self.client.force_login(user_a)
        self.client.post(reverse('therapist_invite_patient'), data={
            'name': 'Alice One', 'email': 'alice@x.com', 'phone': '9150000001', 'age': '30'})
        link_a = TherapistPatientLink.objects.get(therapist=therapist_a, email='alice@x.com')

        self.client.force_login(user_b)
        # DIFFERENT patient name, SAME email — the collision key is the email.
        self.client.post(reverse('therapist_invite_patient'), data={
            'name': 'Bob Two', 'email': 'alice@x.com', 'phone': '9150000002', 'age': '40'})
        link_b = TherapistPatientLink.objects.get(therapist=therapist_b, email='alice@x.com')

        self.assertEqual(
            link_a.patient_id, link_b.patient_id,
            'H-13: both links resolve to the SAME underlying User via get_or_create(username=email)')
        self.assertEqual(User.objects.filter(username='alice@x.com').count(), 1)


class F6ProtectOnDelete(M1TestBase):
    """F6 — PROTECT / deletion behavior on a patient with existing session reports.
    Grep confirms the PROTECT FK: therapist_app/models.py SessionReport.patient →
    strength_app.PatientProfile on_delete=PROTECT (also .link and .session_log
    PROTECT). SessionLog.prescription is also PROTECT."""

    def _build_patient_with_report(self, pid, phone, *, managed):
        user, therapist = make_console_therapist(f'dr_{pid}')
        patient_user = User.objects.create_user(username=f'pu_{pid}', password='x')
        link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=patient_user, status='active', phone=phone)
        rx = Prescription.objects.create(link=link, week_number=1)
        slog = SessionLog.objects.create(link=link, prescription=rx)
        profile = make_patient_profile(
            pid, phone, password='DeleteMe1', user=patient_user, therapist_managed=managed)
        SessionReport.objects.create(
            link=link, session_log=slog, patient=profile,
            report_date=date.today(), report_json={})
        return profile

    def test_f6_direct_orm_delete_raises_protectederror(self):
        """PASS: a direct patient.delete() with a SessionReport pointing at it
        raises ProtectedError (PROTECT FK)."""
        profile = self._build_patient_with_report('F6ORM', '9160000001', managed=False)
        with self.assertRaises(ProtectedError):
            profile.delete()
        self.assertTrue(PatientProfile.objects.filter(pk='F6ORM').exists())

    def test_f6_delete_account_view_catches_and_blocks(self):
        """PASS: delete_account (non-managed) catches ProtectedError, re-renders
        with managed_blocked, and the patient survives
        (strength_app/views.py:1464-1474)."""
        profile = self._build_patient_with_report('F6VIEW', '9160000002', managed=False)
        session = self.client.session
        session['patient_id'] = profile.patient_id
        session.save()
        resp = self.client.post(reverse('delete_account'), data={
            'password': 'DeleteMe1', 'confirm_delete': '1'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get('managed_blocked'))
        self.assertTrue(PatientProfile.objects.filter(pk='F6VIEW').exists())


class F7ChangePasswordPolicy(M1TestBase):
    """F7 — change_password policy vs register/reset policy (finding B-1).
    Live: onboarding (v1_onboarding_views.py:488-494), reset_password
    (views.py:177-180) and change_password (views.py:1519-1522) all enforce the
    IDENTICAL rule: len>=8 AND must mix letters+digits."""

    def setUp(self):
        super().setUp()

    def test_f7_change_password_rejects_weak_b1_now_closed(self):
        """B-1 UPDATE: change_password now REJECTS a 6-char all-digit password
        (len<8), matching register/reset. The historical policy gap is CLOSED.
        Locking in the rejection so a future weakening is caught."""
        p = make_patient_profile('F7', '9170000001', password='OldPass1')
        session = self.client.session
        session['patient_id'] = p.patient_id
        session.save()
        resp = self.client.post(reverse('change_password'), data={
            'old_password': 'OldPass1',
            'new_password': '123456',      # 6 chars, all digits — reset/register reject this
            'confirm_password': '123456',
        })
        p.refresh_from_db()
        # Password unchanged → the weak value was rejected.
        self.assertTrue(check_password('OldPass1', p.password))
        self.assertFalse(check_password('123456', p.password))
        self.assertContains(resp, 'at least 8 characters')


# ===========================================================================
# S — SECURITY
# ===========================================================================

class S1CrossTherapistFirewall(M1TestBase):
    """S1 — get_linked_patient_or_404 firewall + archived-link behavior (H-14).
    Helper hardcodes status='active' (permissions.py:32-40)."""

    def setUp(self):
        _, self.therapist_a = make_console_therapist('dr_s1a', 'Dr. A')
        _, self.therapist_b = make_console_therapist('dr_s1b', 'Dr. B')
        self.patient_user = User.objects.create_user(username='ps1', password='x')

    def test_s1a_other_therapist_link_is_404(self):
        """PASS (light regression): Therapist A cannot reach Therapist B's link."""
        link = TherapistPatientLink.objects.create(
            therapist=self.therapist_b, patient=self.patient_user, status='active')
        with self.assertRaises(Http404):
            get_linked_patient_or_404(self.therapist_a, link.id)

    def test_s1b_own_archived_link_is_404_by_design(self):
        """REGRESSION LOCK (H-14): Therapist A's OWN link, but status='archived',
        still 404s through this helper. The ownership check is intentionally
        conflated with the active-lifecycle filter — a future 'fix' that returns
        archived links here would break the audit-noted design. Lock it in."""
        link = TherapistPatientLink.objects.create(
            therapist=self.therapist_a, patient=self.patient_user, status='archived')
        with self.assertRaises(Http404):
            get_linked_patient_or_404(self.therapist_a, link.id)


class S2CoachMutationIsActive(M1TestBase):
    """S2 — Coach mutation endpoints and the is_active gate (finding A-2).
    A-2 flagged coach_flag_review / coach_set_competition / coach_save_notes as
    omitting is_active. Live: all three now require is_active=True
    (v1_coach_views.py:540, :553, :698)."""

    def setUp(self):
        user, self.coach = make_coach('coach_s2')
        self.patient = make_patient_profile(
            'S2', '9200000001', athlete_tier_eligible=True, athlete_tier_active=True,
            goal_type='athletic', athlete_sport='football')
        FootballProfile.objects.create(patient=self.patient, season_phase='in_season')
        # Link exists but is INACTIVE.
        self.link = CoachPatientLink.objects.create(
            coach=self.coach, patient=self.patient, is_active=False)
        self.client.force_login(user)

    def test_s2_mutations_404_when_link_inactive_a2_now_closed(self):
        """A-2 UPDATE: with the link inactive, all three mutation endpoints 404 —
        the gap is CLOSED at this revision. Control: coach_athlete_detail 404s in
        the identical state, confirming the setup is correct."""
        pid = self.patient.patient_id
        for name in ('coach_flag_review', 'coach_set_competition', 'coach_save_notes'):
            resp = self.client.post(reverse(name, args=[pid]), data={'note': 'x', 'notes': 'x'})
            self.assertEqual(resp.status_code, 404, f'{name} should 404 (A-2 closed)')
        # Comparison control — the already-gated endpoint behaves the same.
        control = self.client.get(reverse('coach_athlete_detail', args=[pid]))
        self.assertEqual(control.status_code, 404, 'control coach_athlete_detail must 404')


class S3RateLimiting(M1TestBase):
    """S3 — Rate limiting on login + change_password surfaces.
    rate_limiter is IP-based (Django cache, POST-only). @rate_limit is present on:
    patient_login (views.py:32), therapist_login (:56), coach_login
    (v1_coach_views.py:172), change_password (views.py:1501)."""

    def setUp(self):
        super().setUp()

    def _hammer(self, url, data, cap=5):
        # Exceed the cap; assert the (cap+1)th POST is blocked with 429.
        for _ in range(cap):
            self.client.post(url, data=data)
        return self.client.post(url, data=data)

    def test_s3_patient_login_rate_limited(self):
        resp = self._hammer(reverse('patient_login'),
                            {'phone': '9999999999', 'password': 'bad'})
        self.assertEqual(resp.status_code, 429)

    def test_s3_therapist_login_rate_limited(self):
        resp = self._hammer(reverse('therapist_login'),
                            {'username': 'nope', 'password': 'bad'})
        self.assertEqual(resp.status_code, 429)

    def test_s3_coach_login_rate_limited(self):
        resp = self._hammer(reverse('coach_login'),
                            {'username': 'nope', 'password': 'bad'})
        self.assertEqual(resp.status_code, 429)

    def test_s3_change_password_rate_limited(self):
        resp = self._hammer(reverse('change_password'),
                            {'old_password': 'a', 'new_password': 'b', 'confirm_password': 'b'})
        self.assertEqual(resp.status_code, 429)


class S4ResetTokenHashed(M1TestBase):
    """S4 — Password-reset token stored hashed, not raw (SECURITY_AUDIT row 17).
    DRIFT: row 17 named the field `hash_of`; live, `hash_of` is a staticmethod and
    the stored field is `PasswordResetToken.token`, holding sha256(raw)."""

    def setUp(self):
        super().setUp()

    def test_s4_stored_token_is_sha256_not_raw(self):
        """PASS: the DB row stores sha256(raw), never the raw emailed token."""
        p = make_patient_profile('S4', '9400000001', email='s4@x.com')
        self.client.post(reverse('forgot_password'), data={'phone': '9400000001'})
        self.assertEqual(len(mail.outbox), 1)
        m = re.search(r'/reset-password/([^/\s]+)/', mail.outbox[0].body)
        self.assertIsNotNone(m, 'reset link with raw token must be in the email')
        raw = m.group(1)
        row = PasswordResetToken.objects.get(patient=p)
        self.assertNotEqual(row.token, raw)
        self.assertEqual(row.token, PasswordResetToken.hash_of(raw))
        self.assertEqual(len(row.token), 64)  # sha256 hex


class S5ResetTokenLifecycle(M1TestBase):
    """S5 — Reset token single-use, expiry, sibling invalidation (regression)."""

    def setUp(self):
        super().setUp()
        self.p = make_patient_profile('S5', '9500000001', email='s5@x.com')

    def _issue_token(self):
        self.client.post(reverse('forgot_password'), data={'phone': '9500000001'})
        raw = re.search(r'/reset-password/([^/\s]+)/', mail.outbox[-1].body).group(1)
        return raw

    def test_s5_single_use(self):
        raw = self._issue_token()
        r1 = self.client.post(reverse('reset_password', args=[raw]), data={
            'new_password': 'FreshPass1', 'confirm_password': 'FreshPass1'})
        self.assertEqual(r1.status_code, 302)  # success → redirect to login
        PasswordResetToken.objects.get(token=PasswordResetToken.hash_of(raw))  # exists, used
        # Reuse the same token → invalid page, no second change.
        r2 = self.client.get(reverse('reset_password', args=[raw]))
        self.assertTrue(r2.context.get('invalid'))

    def test_s5_sibling_invalidation(self):
        raw1 = self._issue_token()
        raw2 = self._issue_token()
        self.client.post(reverse('reset_password', args=[raw2]), data={
            'new_password': 'FreshPass2', 'confirm_password': 'FreshPass2'})
        # Using token2 invalidates all other live tokens (views.py:191-193).
        sibling = PasswordResetToken.objects.get(token=PasswordResetToken.hash_of(raw1))
        self.assertTrue(sibling.used, 'first token must be invalidated after sibling use')

    def test_s5_expiry(self):
        raw = 'expired-raw-token'
        row = PasswordResetToken.objects.create(
            patient=self.p, token=PasswordResetToken.hash_of(raw))
        row.created_at = timezone.now() - timedelta(hours=PasswordResetToken.EXPIRY_HOURS, minutes=1)
        row.save(update_fields=['created_at'])
        self.assertFalse(row.is_valid())


class S6OpenRedirect(M1TestBase):
    """S6 — Open redirect via alert_mark_reviewed's `next` param (finding A-3).
    Live: `redirect(request.POST.get('next') or '/therapist/alerts/')`
    (therapist_app/views.py:461) — no is_safe_url / host validation."""

    def test_s6_next_param_followed_verbatim_a3_open(self):
        """FINDING (A-3 STILL OPEN): an absolute off-site `next` is followed
        verbatim — the redirect Location is the attacker URL."""
        user, therapist = make_console_therapist('dr_s6')
        patient_user = User.objects.create_user(username='ps6', password='x')
        link = TherapistPatientLink.objects.create(
            therapist=therapist, patient=patient_user, status='active')
        alert = Alert.objects.create(link=link, alert_type='pain', message='ow')
        self.client.force_login(user)
        resp = self.client.post(reverse('therapist_alert_reviewed', args=[alert.id]),
                                data={'next': 'https://evil.example/'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, 'https://evil.example/',
            'A-3: off-site next is followed verbatim (open redirect still present)')


class S7AnonymousAccess(M1TestBase):
    """S7 — Anonymous access spot-check: patient / therapist / coach protected
    URLs all redirect to their login, never 200 and never 500."""

    def test_s7_patient_protected_redirects_to_login(self):
        resp = self.client.get(reverse('v1_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_s7_therapist_protected_redirects_to_login(self):
        resp = self.client.get(reverse('therapist_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/therapist/login/', resp.url)

    def test_s7_coach_protected_redirects_to_login(self):
        resp = self.client.get(reverse('coach_squad'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/coach/login/', resp.url)
