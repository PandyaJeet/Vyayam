"""
Seeds a realistic demo patient for offline demonstrations.
Idempotent — deletes and recreates cleanly on every run.

Usage:
    DJANGO_SECRET_KEY='dev-key' DJANGO_DEBUG=True python manage.py seed_demo_patient
Login: phone=0987654321 / password=demo1234
"""
from datetime import date, timedelta, datetime, timezone

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password

from strength_app.models import (
    PatientProfile,
    StrengthProfile,
    PeriodisationState,
    WorkoutSession,
    SessionFeedback,
)

DEMO_ID = 'DEMO001'
DEMO_PHONE = '0987654321'
DEMO_PASSWORD = 'demo1234'

# 12 sessions spread across last 21 days; last 4 are on consecutive days for a 4-day streak.
# Dates are (days_ago, xp_earned, form_score, difficulty_rating)
SESSION_DATA = [
    (21, 38, 72.0, 3),
    (19, 45, 78.0, 3),
    (17, 42, 75.0, 2),
    (15, 55, 82.0, 3),
    (13, 48, 80.0, 3),
    (11, 60, 85.0, 4),
    (9,  52, 79.0, 3),
    (7,  65, 88.0, 4),
    (5,  50, 83.0, 3),
    (3,  58, 86.0, 4),
    (2,  62, 90.0, 4),
    (1,  55, 84.0, 3),
]

# Feedback for 4 of the sessions (indices into SESSION_DATA)
FEEDBACK_DATA = [
    # (session_index, perceived_difficulty, pain_reported, pain_severity, session_rpe, traffic_light, energy_level)
    (2,  'just_right', 'none',     0, 6, 'green',  'good'),
    (5,  'hard',       'mild',     2, 8, 'yellow', 'moderate'),
    (8,  'just_right', 'none',     0, 6, 'green',  'good'),
    (11, 'hard',       'mild',     3, 7, 'yellow', 'moderate'),
]


class Command(BaseCommand):
    help = 'Seeds a realistic demo patient (DEMO001). Deletes and recreates on every run.'

    def handle(self, *args, **options):
        self._wipe_existing()
        patient = self._create_patient()
        self._create_strength_profile(patient)
        self._create_periodisation(patient)
        sessions = self._create_sessions(patient)
        self._create_feedback(patient, sessions)

        total_xp = sum(xp for _, xp, _, _ in SESSION_DATA)
        level = total_xp // 200 + 1
        self.stdout.write(self.style.SUCCESS(
            f'\n  Demo patient ready.\n'
            f'  Phone: {DEMO_PHONE}  |  Password: {DEMO_PASSWORD}\n'
            f'  Total XP: {total_xp}  |  Level: {level}\n'
            f'  Sessions: {len(sessions)}  |  Streak: 4 days\n'
            f'  Asymmetry: hinge/left (mild) — shows asymmetry alert\n'
        ))

    # ── helpers ────────────────────────────────────────────────────────────

    def _wipe_existing(self):
        deleted, _ = PatientProfile.objects.filter(
            patient_id=DEMO_ID
        ).delete()
        # Also remove any stale record that shares the same phone (prevents UNIQUE collision)
        stale, _ = PatientProfile.objects.filter(phone=DEMO_PHONE).exclude(
            patient_id=DEMO_ID
        ).delete()
        total = deleted + stale
        if total:
            self.stdout.write(f'  Wiped {total} existing demo record(s) and related data.')

    def _create_patient(self):
        patient = PatientProfile.objects.create(
            patient_id=DEMO_ID,
            name='Demo Patient',
            phone=DEMO_PHONE,
            email='demo@vyayam.local',
            password=make_password(DEMO_PASSWORD),
            age=28,
            biological_sex='male',
            height_cm=175.0,
            weight_kg=70.0,
            goals='general_strength, injury_prevention',
            goal_type='general_strength',
            goal_secondary='rehabilitation',
            training_history='intermediate',
            training_age_months=24,
            equipment_available_json=['bodyweight', 'dumbbells', 'bands'],
            training_location='home_some',
            session_duration_minutes=45,
            sessions_per_week=4,
            lifestyle='moderately_active',
            sleep_quality='good',
            stress_level='moderate',
            nutrition_quality='regular',
            difficulty_tolerance=6,
            gate_test_completed=True,
            gate_test_completed_at=datetime.now(tz=timezone.utc) - timedelta(days=22),
            status='active',
            data_consent=True,
        )
        self.stdout.write(f'  Created patient {DEMO_ID}: {patient.name}')
        return patient

    def _create_strength_profile(self, patient):
        StrengthProfile.objects.create(
            patient=patient,
            assessment_number=1,
            squat_score=3,
            hinge_score=3,
            push_score=2,
            pull_score=2,
            core_score=4,
            rotate_score=3,
            lunge_score=2,
            # Bilateral values — left hinge is weaker, creating a mild asymmetry
            hinge_left=28,
            hinge_right=32,
            lunge_left=3,
            lunge_right=4,
            rotate_left=4,
            rotate_right=4,
            hinge_asymmetry='mild',
            lunge_asymmetry='none',
            rotate_asymmetry='none',
            weaker_side_hinge='left',
            weaker_side_lunge='',
            weaker_side_rotate='',
        )
        self.stdout.write('  Created StrengthProfile (hinge asymmetry: mild/left)')

    def _create_periodisation(self, patient):
        PeriodisationState.objects.create(
            patient=patient,
            current_phase='hypertrophy',
            current_week=3,
            macrocycle_number=1,
            phase_start_date=date.today() - timedelta(days=14),
            last_deload_date=date.today() - timedelta(days=25),
            weeks_since_deload=3,
            total_sessions_this_cycle=12,
        )
        self.stdout.write('  Created PeriodisationState (hypertrophy / week 3)')

    def _create_sessions(self, patient):
        today = date.today()
        sessions = []
        for i, (days_ago, xp, form_score, difficulty) in enumerate(SESSION_DATA):
            session_date = today - timedelta(days=days_ago)
            week_num = (21 - days_ago) // 7 + 1
            ws = WorkoutSession.objects.create(
                patient=patient,
                week_number=week_num,
                total_duration_minutes=45,
                total_exercises_completed=6,
                total_green_reps_all=48,
                overall_session_form_score=form_score,
                xp_earned=xp,
                patient_comfortable=True,
                difficulty_rating=difficulty,
                patient_notes='',
            )
            # Override auto_now_add timestamp to backdate the session
            WorkoutSession.objects.filter(pk=ws.pk).update(
                session_date=datetime.combine(session_date, datetime.min.time()).replace(
                    hour=8, minute=30, tzinfo=timezone.utc
                )
            )
            sessions.append(ws)
        self.stdout.write(f'  Created {len(sessions)} WorkoutSessions (XP: {sum(x for _,x,_,_ in SESSION_DATA)})')
        return sessions

    def _create_feedback(self, patient, sessions):
        count = 0
        for idx, difficulty, pain, pain_severity, rpe, light, energy in FEEDBACK_DATA:
            SessionFeedback.objects.create(
                session=sessions[idx],
                patient=patient,
                perceived_difficulty=difficulty,
                sleep_last_night='7_to_8',
                pain_reported=pain,
                pain_severity=pain_severity,
                energy_level=energy,
                session_rpe=rpe,
                traffic_light=light,
            )
            count += 1
        self.stdout.write(f'  Created {count} SessionFeedback records')
