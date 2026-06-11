"""Deep audit 2026-06 regression tests.

One test class per Phase-1 C-item (named test_da_c<N>_* so they are
greppable against DEEP_AUDIT_REPORT.md).
"""
from datetime import date, timedelta

from django.test import TestCase

from strength_app.models import PatientProfile, PeriodisationState
from strength_app.v1_gamification import (
    MAX_SESSION_XP,
    XP_PER_SESSION,
    compute_session_xp,
)
from strength_app.v1_safety_logic import check_deload_needed


def _make_patient(pid='DA001', phone='9000009001'):
    return PatientProfile.objects.create(
        patient_id=pid,
        name='Deep Audit Patient',
        phone=phone,
        age=30,
        goals='Strength',
    )


class TestDAC1XpFormGate(TestCase):
    """C1 — XP form-safety gate must not be defeated by a base-XP floor."""

    def test_da_c1_all_unsafe_exercises_earn_zero_xp(self):
        results = [{'form_score': 40}, {'form_score': 30}, {'form_score': 54}]
        self.assertEqual(compute_session_xp(results), 0)

    def test_da_c1_mixed_results_earn_only_passing_xp_no_floor(self):
        # One passing exercise at 60 → base 10 XP, no quality bonus,
        # and no XP_PER_SESSION floor pulling it up to 40.
        results = [{'form_score': 40}, {'form_score': 60}]
        self.assertEqual(compute_session_xp(results), 10)

    def test_da_c1_quality_bonus_above_80(self):
        results = [{'form_score': 85}]
        self.assertEqual(compute_session_xp(results), 15)

    def test_da_c1_empty_results_keep_legacy_fallback(self):
        self.assertEqual(compute_session_xp([]), XP_PER_SESSION)

    def test_da_c1_xp_ceiling(self):
        results = [{'form_score': 90}] * 50
        self.assertEqual(compute_session_xp(results), MAX_SESSION_XP)


class TestDAC2DeloadFallback(TestCase):
    """C2/C11 — mandatory deload gate fires via the correct related_name
    and via calendar time in BOTH branches (state passed or resolved)."""

    def test_da_c2_fallback_resolves_periodisation_related_name(self):
        patient = _make_patient()
        PeriodisationState.objects.create(patient=patient, weeks_since_deload=4)
        needed, reason = check_deload_needed(patient)  # state NOT passed
        self.assertTrue(needed)
        self.assertIn('Mandatory deload', reason)

    def test_da_c2_passed_state_calendar_check(self):
        patient = _make_patient(pid='DA002', phone='9000009002')
        state = PeriodisationState.objects.create(
            patient=patient,
            weeks_since_deload=2,
            last_deload_date=date.today() - timedelta(weeks=5),
        )
        needed, reason = check_deload_needed(patient, periodisation_state=state)
        self.assertTrue(needed)
        self.assertIn('elapsed', reason)

    def test_da_c2_new_patient_no_state_no_crash(self):
        patient = _make_patient(pid='DA003', phone='9000009003')
        needed, reason = check_deload_needed(patient)
        self.assertFalse(needed)

    def test_da_c11_counter_wins_when_ahead_of_calendar(self):
        # Counter 5 but deload 1 week ago: counter is stale-high, but the
        # documented rule is max(counter, calendar) → deload True is the
        # accepted (conservative) outcome.
        patient = _make_patient(pid='DA004', phone='9000009004')
        state = PeriodisationState.objects.create(
            patient=patient,
            weeks_since_deload=5,
            last_deload_date=date.today() - timedelta(weeks=1),
        )
        needed, _ = check_deload_needed(patient, periodisation_state=state)
        self.assertTrue(needed)


class TestDAC5RedFlagAuditTrail(TestCase):
    """C5 — red-flag changes are audited; stop-clearing needs confirmation."""

    def setUp(self):
        self.patient = _make_patient(pid='DAC501', phone='9000009501')
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session.save()

    def _post(self, data):
        from django.urls import reverse
        base = {'surgical_history': '', 'medications': ''}
        base.update(data)
        return self.client.post(reverse('onboarding_red_flags'), data=base)

    def test_da_c5_setting_stop_creates_event(self):
        from strength_app.models import RedFlagEvent
        resp = self._post({'absolute_stop_conditions': ['acute_fracture']})
        self.assertEqual(resp.status_code, 200)  # stopped screen
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.absolute_stop)
        event = RedFlagEvent.objects.get(patient=self.patient)
        self.assertEqual(event.change_type, 'absolute_stop_set')
        self.assertTrue(event.new_stop)

    def test_da_c5_clear_without_confirmation_blocked(self):
        from strength_app.models import RedFlagEvent
        self._post({'absolute_stop_conditions': ['acute_fracture']})
        RedFlagEvent.objects.all().delete()

        resp = self._post({})  # uncheck everything, no confirmation
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'confirm_stop_clear')
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.absolute_stop)  # NOT cleared
        self.assertEqual(RedFlagEvent.objects.count(), 0)

    def test_da_c5_clear_with_confirmation_audited_and_noted(self):
        from strength_app.models import (
            CoachPatientLink, RedFlagEvent, TherapistProfile,
        )
        from django.contrib.auth.models import User

        coach_user = User.objects.create_user('dacoach', password='x')
        coach = TherapistProfile.objects.create(
            user=coach_user, name='Coach DA', email='c@x.com',
        )
        link = CoachPatientLink.objects.create(
            coach=coach, patient=self.patient, is_active=True,
        )

        self._post({'absolute_stop_conditions': ['acute_fracture']})
        resp = self._post({'confirm_stop_clear': '1'})
        self.assertEqual(resp.status_code, 302)  # continues to lifestyle

        self.patient.refresh_from_db()
        self.assertFalse(self.patient.absolute_stop)
        event = RedFlagEvent.objects.filter(
            patient=self.patient, change_type='absolute_stop_cleared',
        ).get()
        self.assertTrue(event.old_stop)
        self.assertFalse(event.new_stop)
        link.refresh_from_db()
        self.assertIn('cleared absolute stop', link.notes)

    def test_da_c5_flag_update_creates_event(self):
        from strength_app.models import RedFlagEvent
        resp = self._post({'red_flags': ['hernia']})
        self.assertEqual(resp.status_code, 302)
        event = RedFlagEvent.objects.get(patient=self.patient)
        self.assertEqual(event.change_type, 'flags_updated')
        self.assertEqual(event.new_flags, ['hernia'])


class TestDAC6EmergencyScreening(TestCase):
    """C6 — emergency screens (cauda equina/DVT/cardiac/systemic patterns)
    hard-stop with urgent-care copy, audit event, and engine refusal."""

    def setUp(self):
        self.patient = _make_patient(pid='DAC601', phone='9000009601')
        session = self.client.session
        session['patient_id'] = self.patient.patient_id
        session.save()

    def test_da_c6_each_new_option_stops_with_urgent_copy(self):
        from django.urls import reverse
        from strength_app.models import RedFlagEvent
        from strength_app.v1_onboarding_views import URGENT_STOP_IDS
        from strength_app.v1_prescription_engine import generate_v1_session

        self.assertEqual(len(URGENT_STOP_IDS), 5)
        for stop_id in sorted(URGENT_STOP_IDS):
            with self.subTest(stop_id=stop_id):
                resp = self.client.post(reverse('onboarding_red_flags'), data={
                    'absolute_stop_conditions': [stop_id],
                    'surgical_history': '', 'medications': '',
                })
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, 'seek urgent medical care')

                self.patient.refresh_from_db()
                self.assertTrue(self.patient.absolute_stop)
                # Internal ID must not leak into patient-facing copy (R4)
                self.assertNotIn(stop_id, self.patient.absolute_stop_reason)

                # Engine refuses to generate a session
                data = generate_v1_session(self.patient)
                self.assertEqual(data['status'], 'stopped')

                # Reset for next subtest (confirmation required to clear)
                self.client.post(reverse('onboarding_red_flags'), data={
                    'confirm_stop_clear': '1',
                    'surgical_history': '', 'medications': '',
                })
                self.patient.refresh_from_db()
                self.assertFalse(self.patient.absolute_stop)

        # Audit events recorded for every set + clear
        self.assertGreaterEqual(
            RedFlagEvent.objects.filter(patient=self.patient).count(), 10
        )

    def test_da_c6_classic_stop_keeps_generic_copy(self):
        from django.urls import reverse
        resp = self.client.post(reverse('onboarding_red_flags'), data={
            'absolute_stop_conditions': ['acute_fracture'],
            'surgical_history': '', 'medications': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Consult Your Clinician')
        self.assertNotContains(resp, 'seek urgent medical care')


class TestDAC4AcwrRemoved(TestCase):
    """C4 — ACWR (discredited metric, standing decision R2) fully removed."""

    def test_da_c4_engine_has_no_acwr(self):
        import strength_app.v1_prescription_engine as engine
        self.assertFalse(hasattr(engine, '_compute_acwr'))

    def test_da_c4_athlete_session_generates_without_acwr_meta(self):
        from strength_app.models import FootballProfile, StrengthProfile
        from strength_app.v1_prescription_engine import generate_v1_session

        patient = PatientProfile.objects.create(
            patient_id='DAATH1',
            name='Audit Athlete',
            phone='9100000099',
            age=22,
            goals='Coach-onboarded football athlete',
            goal_type='athletic',
            sport_type='football',
            training_history='intermediate',
            sessions_per_week=4,
            gate_test_completed=True,
            athlete_tier_eligible=True,
            athlete_tier_active=True,
            athlete_sport='football',
        )
        StrengthProfile.objects.create(
            patient=patient, assessment_number=1,
            squat_score=3, hinge_score=3, push_score=3,
            pull_score=3, core_score=3, rotate_score=3, lunge_score=3,
        )
        FootballProfile.objects.create(patient=patient)

        data = generate_v1_session(patient)
        self.assertIsInstance(data, dict)
        meta = data.get('meta', {})
        for key in meta:
            self.assertNotIn('acwr', key.lower())
        notes = ' '.join(meta.get('modifier_notes', []) or [])
        self.assertNotIn('ACWR', notes)
        self.assertNotIn('P31', notes)


class TestDAC7RealReportNumbers(TestCase):
    """C7 — progress reports compute real aggregates, never fabricate."""

    def test_da_c7_report_matches_db_aggregates(self):
        from strength_app.models import WorkoutSession
        from strength_app.utils import generate_progress_report

        patient = _make_patient(pid='DAC701', phone='9000009701')
        patient.sessions_per_week = 3
        patient.save(update_fields=['sessions_per_week'])
        for score, greens in [(70.0, 10), (80.0, 12), (90.0, 15)]:
            WorkoutSession.objects.create(
                patient=patient,
                total_green_reps_all=greens,
                overall_session_form_score=score,
            )

        report = generate_progress_report(patient, weeks=4)
        self.assertEqual(report.total_sessions_completed, 3)
        self.assertEqual(report.total_sessions_prescribed, 12)  # 3/wk × 4
        self.assertEqual(report.overall_adherence_rate, 25.0)
        self.assertEqual(report.total_green_reps_period, 37)
        self.assertEqual(report.average_form_score_period, 80.0)
        self.assertEqual(report.form_improvement, 20.0)

    def test_da_c7_zero_sessions_insufficient_data_not_75pct(self):
        from strength_app.utils import generate_progress_report

        patient = _make_patient(pid='DAC702', phone='9000009702')
        report = generate_progress_report(patient, weeks=4)
        self.assertEqual(report.total_sessions_completed, 0)
        self.assertEqual(report.overall_adherence_rate, 0.0)
        self.assertIn('Insufficient data', report.recommended_next_steps)

    def test_da_c7_view_uses_real_generator(self):
        from django.urls import reverse
        from strength_app.models import ProgressReport

        patient = _make_patient(pid='DAC703', phone='9000009703')
        session = self.client.session
        session['patient_id'] = patient.patient_id
        session.save()

        resp = self.client.get(reverse('generate_report'))
        self.assertEqual(resp.status_code, 302)
        report = ProgressReport.objects.get(patient=patient)
        # The old broken path fabricated 75.0 adherence / 20 prescribed.
        self.assertEqual(report.overall_adherence_rate, 0.0)
        self.assertNotEqual(report.total_sessions_prescribed, 20)


class TestDAC3SquatFormScoring(TestCase):
    """C3 — correct deep squats must not be penalized by hip-flexion targets."""

    def test_da_c3_perfect_deep_squat_scores_green(self):
        """C3 — a synthetically perfect deep squat must average ≥85.

        Before the fix, get_target_poses() scored avg_back (hip flexion,
        shoulder→hip→knee) against 155° at the bottom of the squat. A
        CORRECT deep squat reads ~50–90° there, so the component scored 0
        and dragged every correct rep down ~25 points.
        """
        try:
            from strength_app.exercise_system.exercises.full_squat_v2 import (
                FullSquatsV2,
            )
        except ImportError:
            self.skipTest('CV stack (mediapipe/cv2) not available')

        ex = FullSquatsV2()
        joints = {
            'lh': (300, 400), 'lk': (300, 500), 'la': (300, 600),
            'rh': (340, 400), 'rk': (340, 500), 'ra': (340, 600),
            'ls': (300, 250), 'rs': (340, 250),
        }

        def frames():
            # 175 → 90 → 175, ~20 frames each way; avg_back tracks a
            # realistic hip-flexion curve (172 standing → 75 at depth).
            down = [175 - i * (85 / 19) for i in range(20)]
            up = list(reversed(down))[1:]
            for knee in down + up:
                t = (175 - knee) / 85.0
                yield knee, 172 - t * 97

        scores = []
        for _ in range(5):  # several reps: 3 practice + counted
            for knee, back in frames():
                angles = {'avg_knee': knee, 'avg_back': back}
                score = ex.calculate_real_time_form_score(angles, joints)
                scores.append(score)
                ex.update_rep_counter(knee, {}, ex.voice)

        mean_score = sum(scores) / len(scores)
        self.assertGreaterEqual(mean_score, 85.0)
        self.assertGreaterEqual(ex.rep_count + ex.practice_reps_completed, 1)
