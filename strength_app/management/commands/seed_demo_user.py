"""
Seeds the Ideathon demo patient (DEMO_USER01).
Idempotent — deletes and recreates on every run.

Usage:
    python manage.py seed_demo_user

Login: phone=1234567890 / password=simple
"""
from datetime import date, timedelta, datetime, timezone

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password

from strength_app.models import PatientProfile, StrengthProfile, PeriodisationState, WorkoutSession

DEMO_ID    = 'DEMO_USER01'
DEMO_PHONE = '1234567890'
DEMO_PASS  = 'simple'


class Command(BaseCommand):
    help = 'Seeds the Ideathon demo patient (DEMO_USER01). Idempotent.'

    def handle(self, *args, **options):
        self._wipe()
        patient = self._create_patient()
        self._create_profile(patient)
        self._create_periodisation(patient)
        self._create_sessions(patient)

        self.stdout.write(self.style.SUCCESS(
            f'\n  Demo user ready.\n'
            f'  Phone: {DEMO_PHONE}  |  Password: {DEMO_PASS}\n'
            f'  Patient ID: {DEMO_ID}\n'
            f'  Session: partial_squat (warmup) → full_squats (main)\n'
        ))

    def _wipe(self):
        deleted, _ = PatientProfile.objects.filter(patient_id=DEMO_ID).delete()
        stale, _   = PatientProfile.objects.filter(phone=DEMO_PHONE).exclude(patient_id=DEMO_ID).delete()
        total = deleted + stale
        if total:
            self.stdout.write(f'  Wiped {total} existing record(s).')

    def _create_patient(self):
        patient = PatientProfile.objects.create(
            patient_id=DEMO_ID,
            name='Demo User',
            phone=DEMO_PHONE,
            email='demo_user@vyayam.local',
            password=make_password(DEMO_PASS),
            age=28,
            biological_sex='male',
            height_cm=175.0,
            weight_kg=75.0,
            goals='general_strength',
            goal_type='general_strength',
            training_history='beginner',
            training_age_months=6,
            equipment_available_json=['bodyweight'],
            training_location='home_some',
            session_duration_minutes=30,
            sessions_per_week=3,
            lifestyle='moderately_active',
            sleep_quality='good',
            stress_level='low',
            nutrition_quality='regular',
            difficulty_tolerance=5,
            gate_test_completed=True,
            gate_test_completed_at=datetime.now(tz=timezone.utc) - timedelta(days=7),
            status='active',
            data_consent=True,
        )
        self.stdout.write(f'  Created patient {DEMO_ID}: {patient.name}')
        return patient

    def _create_profile(self, patient):
        StrengthProfile.objects.create(
            patient=patient,
            assessment_number=1,
            squat_score=3,
            hinge_score=3,
            push_score=3,
            pull_score=3,
            core_score=3,
            rotate_score=3,
            lunge_score=3,
            hinge_left=30,
            hinge_right=30,
            lunge_left=3,
            lunge_right=3,
            rotate_left=3,
            rotate_right=3,
            hinge_asymmetry='none',
            lunge_asymmetry='none',
            rotate_asymmetry='none',
        )
        self.stdout.write('  Created StrengthProfile (band 3 across all patterns, no asymmetry)')

    def _create_periodisation(self, patient):
        PeriodisationState.objects.create(
            patient=patient,
            current_phase='hypertrophy',
            current_week=1,
            macrocycle_number=1,
            phase_start_date=date.today() - timedelta(days=7),
            last_deload_date=None,
            weeks_since_deload=0,
            total_sessions_this_cycle=3,
        )
        self.stdout.write('  Created PeriodisationState (hypertrophy / week 1)')

    def _create_sessions(self, patient):
        today = date.today()
        session_days = [7, 5, 3]
        for days_ago in session_days:
            ws = WorkoutSession.objects.create(
                patient=patient,
                week_number=1,
                total_duration_minutes=25,
                total_exercises_completed=1,
                overall_session_form_score=80.0,
                xp_earned=45,
                patient_comfortable=True,
                difficulty_rating=3,
            )
            session_date = today - timedelta(days=days_ago)
            WorkoutSession.objects.filter(pk=ws.pk).update(
                session_date=datetime.combine(session_date, datetime.min.time()).replace(
                    hour=9, minute=0, tzinfo=timezone.utc
                )
            )
        self.stdout.write(f'  Created {len(session_days)} WorkoutSessions')
