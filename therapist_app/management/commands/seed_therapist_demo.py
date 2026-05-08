"""
Seeds the therapist console demo fixtures.

Idempotent — wipes existing demo therapists / their links / linked
PatientProfiles and recreates.

Usage:
    python manage.py seed_therapist_demo

Test credentials produced:
    THERAPIST CONSOLE (/therapist/login/, Django auth)
      dr_shah  / simple    Dr. Meera Shah, Andheri Sports Clinic
      dr_iyer  / simple    Dr. Karan Iyer, KMC Sports Medicine

    PATIENT PWA (/login/, phone + password against PatientProfile)
      9000000001 / patient   Anika Patel    (dr_shah, active)
      9000000002 / patient   Rohan Gupta    (dr_shah, active, flagged)
      9000000003 / patient   Sara D'Souza   (dr_shah, active)
      9000000004 / patient   Vikram Shetty  (dr_iyer, active — perm test)

    PENDING (no User, no PatientProfile yet)
      Neha Iyer  — accept via Simulate-accept on dr_shah's dashboard

The patient PWA login (strength_app.views.patient_login) authenticates
phone + password directly against PatientProfile.password. To make seeded
patients log in there too, we create a PatientProfile per linked patient
and connect it to the Django User via PatientProfile.user (existing
OneToOneField). Both records use make_password('patient') for the hash —
the Django User's password is what therapists use during dev when they
hit Simulate-accept; the PatientProfile's password is what the PWA
phone-login form checks. They're independent fields and can drift, so
we set both here.
"""

import json
from datetime import date, timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from strength_app.models import PatientProfile

from therapist_app.exercise_catalog import EXERCISES_BY_ID
from therapist_app.models import (
    Prescription,
    PrescriptionItem,
    Therapist,
    TherapistPatientHealthProfile,
    TherapistPatientLink,
)


THERAPISTS = [
    {
        'username': 'dr_shah',
        'password': 'simple',
        'full_name': 'Dr. Meera Shah',
        'specialization': 'Sports Physiotherapy · MPT',
        'registration_number': 'MH-PT-04982',
        'clinic_name': 'Andheri Sports Clinic',
        'email': 'meera.shah@andhericlinic.com',
    },
    {
        'username': 'dr_iyer',
        'password': 'simple',
        'full_name': 'Dr. Karan Iyer',
        'specialization': 'Sports Medicine · MD',
        'registration_number': 'KA-PT-12117',
        'clinic_name': 'KMC Sports Medicine',
        'email': 'karan.iyer@kmcsports.in',
    },
]

DR_SHAH_PATIENTS = [
    {
        'username': 'anika',
        'password': 'patient',
        'full_name': 'Anika Patel',
        'email': 'anika@example.com',
        'phone': '9000000001',
        'patient_id': 'THERA_ANIKA',
        'biological_sex': 'female',
        'age': 29, 'sex': 'F', 'location': 'London (remote)',
        'height_cm': 168.0,
        'weight_kg': 60.5,
        'goals': 'Return to recreational running pain-free in 14 weeks; restore single-leg control and quad strength.',
        'health_profile': {
            'affected_side': 'right',
            'surgery_date': None,
            'pain_medications': 'Paracetamol 500mg PRN (occasional)',
            'other_conditions': 'Mild iron deficiency (managed).',
            'emergency_contact_name': 'Aarav Patel',
            'emergency_contact_phone': '+44 7700 900112',
        },
        'primary_condition': 'Right meniscus tear',
        'condition_tone': 'warn',
        'injury_date': date(2026, 2, 14),
        'program_start': date(2026, 3, 4),
        'total_weeks': 16,
        'status': 'active',
        'metrics': {
            'compliance': 82,
            'sparkline': [1, 1, 0, 1, 1, 1, 0],
            'pain': [3, 3, 4, 4, 2, 3, 2],
            'flags': ['Pain spike on Wed'],
            'last_session': 'Yesterday',
            'next_session': 'Today · 18:00 BST',
            'history': [
                {'date': 'Apr 30', 'name': 'W8 D2 · Lower control', 'complete': 100, 'pain_avg': 2, 'pain_max': 3, 'difficulty': 6, 'duration': '32 min'},
                {'date': 'Apr 28', 'name': 'W8 D1 · Strength build', 'complete': 85,  'pain_avg': 4, 'pain_max': 5, 'difficulty': 7, 'duration': '38 min'},
                {'date': 'Apr 26', 'name': 'W7 D5 · Mobility',       'complete': 100, 'pain_avg': 1, 'pain_max': 2, 'difficulty': 4, 'duration': '22 min'},
                {'date': 'Apr 24', 'name': 'W7 D4 · Lower control',  'complete': 60,  'pain_avg': 5, 'pain_max': 7, 'difficulty': 8, 'duration': '19 min'},
            ],
        },
        'prescription': {
            'week_number': 8,
            'notes_for_patient': "Focus on slow eccentric on the step-ups — 3 seconds down. Stop the side plank if you feel any sharp medial knee pain.",
            'items': [
                {'exercise_id': 'ex_glute_bridge', 'sets': 3, 'reps': 12, 'load': 'BW',         'rest_seconds': 60, 'tempo': '3-1-1', 'notes': 'Squeeze top 2s. Stop if pain >3.'},
                {'exercise_id': 'ex_clamshell',    'sets': 3, 'reps': 15, 'load': 'Light band', 'rest_seconds': 45, 'tempo': '—',     'notes': 'Both sides.'},
                {'exercise_id': 'ex_sl_balance',   'sets': 3, 'reps': 30, 'load': 'BW',         'rest_seconds': 30, 'tempo': 'Hold',  'notes': '30s each side. Eyes open.'},
                {'exercise_id': 'ex_step_up',      'sets': 3, 'reps': 10, 'load': 'BW',         'rest_seconds': 60, 'tempo': '3-0-1', 'notes': '12-inch step. Eccentric focus.'},
                {'exercise_id': 'ex_side_plank',   'sets': 2, 'reps': 30, 'load': 'BW',         'rest_seconds': 45, 'tempo': 'Hold',  'notes': 'Knees bent. 30s each side.'},
            ],
        },
    },
    {
        'username': 'rohan',
        'password': 'patient',
        'full_name': 'Rohan Gupta',
        'email': 'rohan@example.com',
        'phone': '9000000002',
        'patient_id': 'THERA_ROHAN',
        'biological_sex': 'male',
        'age': 22, 'sex': 'M', 'location': 'Mumbai',
        'primary_condition': 'Post-ACL reconstruction',
        'condition_tone': 'warn',
        'injury_date': date(2025, 11, 8),
        'program_start': date(2026, 1, 12),
        'total_weeks': 24,
        'status': 'active',
        'metrics': {
            'compliance': 38,
            'sparkline': [0, 1, 0, 0, 0, 1, 0],
            'pain': [5, 6, 5, 7, 4, 4, 5],
            'flags': ['Missed 3 sessions', 'Pain >5 last week'],
            'last_session': '7 days ago',
            'next_session': 'Tomorrow · 07:00',
        },
    },
    {
        'username': 'sara',
        'password': 'patient',
        'full_name': "Sara D'Souza",
        'email': 'sara@example.com',
        'phone': '9000000003',
        'patient_id': 'THERA_SARA',
        'biological_sex': 'female',
        'age': 30, 'sex': 'F', 'location': 'Pune',
        'primary_condition': 'Chronic low back pain',
        'condition_tone': 'primary',
        'injury_date': None,
        'program_start': date(2026, 2, 20),
        'total_weeks': 12,
        'status': 'active',
        'metrics': {
            'compliance': 95,
            'sparkline': [1, 1, 1, 1, 1, 1, 1],
            'pain': [4, 3, 3, 2, 2, 2, 1],
            'flags': [],
            'last_session': 'Today',
            'next_session': 'Thu · 18:30',
        },
    },
    {
        'username': None,  # No User record yet for the pending invite.
        'full_name': 'Neha Iyer',
        'email': 'neha@example.com',
        'age': 41, 'sex': 'F', 'location': '—',
        'primary_condition': 'Frozen shoulder',
        'condition_tone': 'primary',
        'injury_date': date(2026, 1, 22),
        'program_start': None,
        'total_weeks': 12,
        'status': 'pending',
        'metrics': {},
    },
]

DR_IYER_PATIENTS = [
    {
        'username': 'vikram',
        'password': 'patient',
        'full_name': 'Vikram Shetty',
        'email': 'vikram@example.com',
        'phone': '9000000004',
        'patient_id': 'THERA_VIKRAM',
        'biological_sex': 'male',
        'age': 27, 'sex': 'M', 'location': 'Bangalore',
        'primary_condition': 'Hamstring strain',
        'condition_tone': 'warn',
        'injury_date': date(2026, 3, 1),
        'program_start': date(2026, 3, 20),
        'total_weeks': 8,
        'status': 'active',
        'metrics': {
            'compliance': 78,
            'sparkline': [1, 0, 1, 1, 0, 1, 1],
            'pain': [2, 3, 2, 1, 1, 0, 1],
            'flags': [],
            'last_session': 'Today',
            'next_session': 'Tomorrow · 17:30',
        },
    },
]


class Command(BaseCommand):
    help = 'Seeds the therapist console demo fixtures (idempotent).'

    def handle(self, *args, **options):
        self._wipe()
        therapists = self._seed_therapists()
        self._seed_links(therapists['dr_shah'], DR_SHAH_PATIENTS)
        self._seed_links(therapists['dr_iyer'], DR_IYER_PATIENTS)
        self._seed_anika_prescription(therapists['dr_shah'])

        self.stdout.write(self.style.SUCCESS('\n  Therapist demo seed complete.\n'))
        self.stdout.write('  Therapist console (/therapist/login/):')
        self.stdout.write('    dr_shah / simple    dr_iyer / simple')
        self.stdout.write('  Patient PWA (/login/, phone + password):')
        self.stdout.write('    9000000001 / patient   Anika Patel    (dr_shah)')
        self.stdout.write('    9000000002 / patient   Rohan Gupta    (dr_shah)')
        self.stdout.write("    9000000003 / patient   Sara D'Souza   (dr_shah)")
        self.stdout.write('    9000000004 / patient   Vikram Shetty  (dr_iyer)')
        self.stdout.write('  Pending (no login yet): Neha Iyer — accept via Simulate-accept on dashboard')

    def _wipe(self):
        usernames = ['dr_shah', 'dr_iyer', 'anika', 'rohan', 'sara', 'vikram', 'neha@example.com']
        # Deleting Users cascades to PatientProfile.user (OneToOne CASCADE),
        # so the linked PatientProfile rows go with them. We still defensively
        # wipe any orphaned PatientProfile rows that share our reserved phones
        # or patient_ids — covers the case where a prior failed run left them
        # orphaned, or where the OneToOne wasn't set on an old seed.
        deleted = User.objects.filter(username__in=usernames).delete()
        if deleted[0]:
            self.stdout.write(f'  Wiped {deleted[0]} existing user record(s) + cascades.')

        seed_phones = ['9000000001', '9000000002', '9000000003', '9000000004']
        seed_pids = ['THERA_ANIKA', 'THERA_ROHAN', 'THERA_SARA', 'THERA_VIKRAM']
        orphans = PatientProfile.objects.filter(phone__in=seed_phones).delete()
        orphans2 = PatientProfile.objects.filter(patient_id__in=seed_pids).delete()
        leftover = (orphans[0] or 0) + (orphans2[0] or 0)
        if leftover:
            self.stdout.write(f'  Wiped {leftover} orphan PatientProfile row(s).')

    def _seed_therapists(self):
        out = {}
        for spec in THERAPISTS:
            user, _ = User.objects.get_or_create(
                username=spec['username'],
                defaults={'email': spec['email'], 'first_name': spec['full_name'].split()[1] if len(spec['full_name'].split()) > 1 else ''},
            )
            user.set_password(spec['password'])
            user.email = spec['email']
            user.save()
            therapist, _ = Therapist.objects.update_or_create(
                user=user,
                defaults={
                    'full_name': spec['full_name'],
                    'specialization': spec['specialization'],
                    'registration_number': spec['registration_number'],
                    'clinic_name': spec['clinic_name'],
                    'seat_limit': 12,
                },
            )
            out[spec['username']] = therapist
        return out

    def _seed_links(self, therapist, patients_spec):
        for spec in patients_spec:
            patient_user = self._make_patient_user(spec)
            # Pending invites have no Django User and therefore no
            # PatientProfile yet — they get one only after Simulate-accept
            # (or the real onboarding flow) bridges them in.
            if patient_user is not None and spec.get('phone'):
                self._seed_patient_profile(spec, patient_user)
            metrics = spec.get('metrics') or {}
            notes_payload = json.dumps({'metrics': metrics}) if metrics else ''
            link, _ = TherapistPatientLink.objects.update_or_create(
                therapist=therapist,
                patient=patient_user,
                defaults={
                    'full_name': spec['full_name'],
                    'email': spec['email'],
                    'age': spec.get('age'),
                    'sex': spec.get('sex', ''),
                    'location': spec.get('location', ''),
                    'primary_condition': spec['primary_condition'],
                    'condition_tone': spec['condition_tone'],
                    'injury_date': spec.get('injury_date'),
                    'program_start': spec.get('program_start'),
                    'total_weeks': spec.get('total_weeks', 12),
                    'status': spec['status'],
                    'accepted_at': timezone.now() if spec['status'] == 'active' else None,
                    'notes': notes_payload,
                },
            )
            hp_spec = spec.get('health_profile')
            if hp_spec is not None:
                TherapistPatientHealthProfile.objects.update_or_create(
                    link=link,
                    defaults={
                        'height_cm': spec.get('height_cm'),
                        'weight_kg': spec.get('weight_kg'),
                        'affected_side': hp_spec.get('affected_side', ''),
                        'surgery_date': hp_spec.get('surgery_date'),
                        'pain_medications': hp_spec.get('pain_medications', ''),
                        'other_conditions': hp_spec.get('other_conditions', ''),
                        'emergency_contact_name': hp_spec.get('emergency_contact_name', ''),
                        'emergency_contact_phone': hp_spec.get('emergency_contact_phone', ''),
                        'goals': spec.get('goals', ''),
                    },
                )

    def _make_patient_user(self, spec):
        if not spec.get('username') and not spec.get('email'):
            # Pending placeholders without contact info have no Django User.
            return None
        username = spec.get('username') or spec['email']
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'email': spec['email'], 'first_name': spec['full_name'].split()[0]},
        )
        user.email = spec['email']
        if spec.get('password'):
            user.set_password(spec['password'])
        else:
            user.set_unusable_password()
        user.save()
        return user

    def _seed_patient_profile(self, spec, user):
        """Mirror this Django User into a PatientProfile so the patient PWA
        (which authenticates phone + password against PatientProfile) can log
        them in. The OneToOne ``PatientProfile.user`` ties the two records
        together — that's the bridge used by anything that needs to resolve
        Django User → PatientProfile and vice versa.

        Idempotent: ``_wipe`` removes prior rows first; the User-cascade
        + the explicit phone/patient_id sweep there guarantees no
        unique-constraint collisions on rerun.
        """
        biological_sex = spec.get('biological_sex') or (
            'female' if spec.get('sex', '').upper() == 'F'
            else 'male' if spec.get('sex', '').upper() == 'M'
            else 'not_specified'
        )

        PatientProfile.objects.update_or_create(
            patient_id=spec['patient_id'],
            defaults={
                'user': user,
                'name': spec['full_name'],
                'phone': spec['phone'],
                'email': spec.get('email', ''),
                'password': make_password(spec.get('password') or 'patient'),
                'age': spec['age'],
                'biological_sex': biological_sex,
                'height_cm': spec.get('height_cm'),
                'weight_kg': spec.get('weight_kg'),
                'goals': spec.get('goals', 'Therapist-managed rehabilitation programme.'),
                'goal_type': 'rehabilitation',
                'training_history': 'beginner',
                # B2B2C: skip strength_app onboarding entirely.
                'therapist_managed': True,
                'gate_test_completed': True,
                'prescription_mode': 'therapist_manual',
            },
        )

    def _seed_anika_prescription(self, dr_shah):
        link = TherapistPatientLink.objects.get(therapist=dr_shah, patient__username='anika')
        spec_patient = next(p for p in DR_SHAH_PATIENTS if p.get('username') == 'anika')
        rx_spec = spec_patient['prescription']

        rx, _ = Prescription.objects.update_or_create(
            link=link,
            week_number=rx_spec['week_number'],
            defaults={
                'notes_for_patient': rx_spec['notes_for_patient'],
                'published_at': timezone.now(),
                'draft_json': {},
            },
        )
        rx.items.all().delete()
        for idx, item_spec in enumerate(rx_spec['items']):
            catalog_entry = EXERCISES_BY_ID.get(item_spec['exercise_id'], {})
            PrescriptionItem.objects.create(
                prescription=rx,
                order=idx,
                exercise_id=item_spec['exercise_id'],
                exercise_name=catalog_entry.get('name', item_spec['exercise_id']),
                movement_pattern=catalog_entry.get('movement_pattern', ''),
                sets=item_spec['sets'],
                reps=item_spec['reps'],
                load=item_spec['load'],
                rest_seconds=item_spec['rest_seconds'],
                tempo=item_spec.get('tempo', ''),
                notes=item_spec.get('notes', ''),
            )
