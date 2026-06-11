"""DA-P4 row 11 — data-integrity check command.

Lists rows whose stored values fall outside the current model choices /
validators (legacy rows written before validators were added, e.g.
SessionFeedback.pain_reported values that no longer match PAIN_CHOICES).

Read-only: reports, never mutates.

Usage:
    python manage.py check_data_integrity
"""
from django.core.management.base import BaseCommand

from strength_app.models import (
    ExerciseExecution,
    FoodItem,
    GateTestResult,
    PatientProfile,
    SessionFeedback,
    WorkoutSession,
)


class Command(BaseCommand):
    help = 'Report rows with out-of-choice or out-of-range values (read-only).'

    def handle(self, *args, **options):
        problems = 0

        valid_pain = {c[0] for c in SessionFeedback.PAIN_CHOICES}
        for fb in SessionFeedback.objects.exclude(pain_reported__in=valid_pain):
            problems += 1
            self.stdout.write(
                f'SessionFeedback #{fb.pk}: pain_reported={fb.pain_reported!r} '
                f'not in {sorted(valid_pain)}'
            )

        for fb in SessionFeedback.objects.filter(pain_severity__lt=0) | \
                SessionFeedback.objects.filter(pain_severity__gt=10):
            problems += 1
            self.stdout.write(f'SessionFeedback #{fb.pk}: pain_severity={fb.pain_severity}')

        for p in PatientProfile.objects.filter(age__lt=18) | \
                PatientProfile.objects.filter(age__gt=100):
            problems += 1
            self.stdout.write(f'PatientProfile {p.patient_id}: age={p.age} outside 18-100')

        for fi in FoodItem.objects.filter(calories_per_100g__lt=0):
            problems += 1
            self.stdout.write(f'FoodItem #{fi.pk}: negative calories')

        for ex in ExerciseExecution.objects.filter(prescribed_sets__lt=0) | \
                ExerciseExecution.objects.filter(prescribed_reps__lt=0):
            problems += 1
            self.stdout.write(f'ExerciseExecution #{ex.pk}: negative prescription')

        valid_cat = {c[0] for c in ExerciseExecution.CATEGORY_CHOICES}
        for ex in ExerciseExecution.objects.exclude(category__in=valid_cat):
            problems += 1
            self.stdout.write(f'ExerciseExecution #{ex.pk}: category={ex.category!r}')

        for ws in WorkoutSession.objects.filter(xp_earned__lt=0):
            problems += 1
            self.stdout.write(f'WorkoutSession #{ws.pk}: negative xp_earned')

        for gt in GateTestResult.objects.filter(depth_achieved__lt=0):
            problems += 1
            self.stdout.write(f'GateTestResult #{gt.pk}: negative depth_achieved')

        if problems:
            self.stdout.write(self.style.WARNING(f'{problems} problem row(s) found.'))
        else:
            self.stdout.write(self.style.SUCCESS('All checked rows within model constraints.'))
