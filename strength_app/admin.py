"""
VYAYAM STRENGTH TRAINING - DJANGO ADMIN
Admin interface configuration
"""

from django.contrib import admin
from .models import (
    PatientProfile, GateTestResult, WorkoutSession,
    ExerciseExecution, TherapistProfile, TherapistPrescription,
    ExerciseProgressionState, ProgressReport, StretchSession,
    StrengthProfile, PeriodisationState, SessionFeedback, AnonymisedSessionLog,
    CoachPatientLink, NutritionProfile, FoodItem, DailyFoodLog, MessEntry,
    FootballProfile, RedFlagEvent,
)


@admin.register(RedFlagEvent)
class RedFlagEventAdmin(admin.ModelAdmin):
    """DA-C5 audit trail — read-only: audit records must never be edited."""
    list_display = ['patient', 'change_type', 'source', 'old_stop', 'new_stop', 'changed_at']
    list_filter = ['change_type', 'source']
    search_fields = ['patient__name', 'patient__patient_id']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'name', 'age', 'lifestyle', 'prescription_mode', 'current_week', 'status', 'created_at']
    list_filter = ['prescription_mode', 'lifestyle', 'status', 'goal_type']
    search_fields = ['patient_id', 'name', 'phone', 'email']
    readonly_fields = ['patient_id', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('patient_id', 'name', 'phone', 'email', 'age', 'created_at')
        }),
        ('8 Clusteral Parameters', {
            'fields': (
                'fitness_level_json', 'goals', 'goal_type', 'biomechanics',
                'difficulty_tolerance', 'lifestyle', 'occupation',
                'compliance_proven', 'adherence_rate', 'timeline'
            )
        }),
        ('Medical Information', {
            'fields': ('medical_conditions_json', 'contraindications_json')
        }),
        ('Program Details', {
            'fields': (
                'prescription_mode', 'assigned_therapist', 'current_week',
                'program_start_date', 'program_end_date', 'status'
            )
        }),
    )


@admin.register(GateTestResult)
class GateTestResultAdmin(admin.ModelAdmin):
    list_display = ['patient', 'category', 'capability_level', 'reps_completed', 'difficulty_reported', 'test_date']
    list_filter = ['category', 'capability_level', 'test_date']
    search_fields = ['patient__name', 'patient__patient_id']
    readonly_fields = ['test_date']


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'week_number', 'session_date', 'total_green_reps_all', 'overall_session_form_score', 'patient_comfortable']
    list_filter = ['week_number', 'session_date', 'patient_comfortable', 'prescription_mode']
    search_fields = ['patient__name', 'patient__patient_id']
    readonly_fields = ['session_date']


@admin.register(ExerciseExecution)
class ExerciseExecutionAdmin(admin.ModelAdmin):
    list_display = ['session', 'exercise_name', 'category', 'total_green_reps', 'overall_form_score']
    list_filter = ['category']
    search_fields = ['exercise_name', 'session__patient__name']


@admin.register(TherapistProfile)
class TherapistProfileAdmin(admin.ModelAdmin):
    list_display = ['therapist_id', 'name', 'license_number', 'specialization', 'email']
    search_fields = ['therapist_id', 'name', 'license_number', 'email']


@admin.register(TherapistPrescription)
class TherapistPrescriptionAdmin(admin.ModelAdmin):
    list_display = ['prescription_id', 'patient', 'therapist', 'created_date', 'active', 'completed']
    list_filter = ['active', 'completed', 'created_date']
    search_fields = ['prescription_id', 'patient__name', 'therapist__name']
    readonly_fields = ['created_date']


@admin.register(ExerciseProgressionState)
class ExerciseProgressionStateAdmin(admin.ModelAdmin):
    list_display = ['patient', 'exercise_category', 'current_level', 'current_sets', 'current_reps', 'threshold_met']
    list_filter = ['exercise_category', 'threshold_met', 'ready_to_advance']
    search_fields = ['patient__name', 'patient__patient_id']


@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'report_period', 'report_date', 'overall_adherence_rate', 'average_form_score_period']
    list_filter = ['report_date', 'continue_current_program']
    search_fields = ['patient__name', 'patient__patient_id']
    readonly_fields = ['report_date']


@admin.register(StretchSession)
class StretchSessionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'protocol_name', 'session_date', 'stretches_completed', 'total_stretches', 'camera_used']
    list_filter = ['session_date', 'camera_used']
    search_fields = ['patient__name', 'patient__patient_id']
    readonly_fields = ['session_date']


@admin.register(StrengthProfile)
class StrengthProfileAdmin(admin.ModelAdmin):
    list_display = ['patient', 'assessment_number', 'assessed_at', 'squat_score', 'hinge_score', 'push_score', 'pull_score', 'core_score', 'rotate_score', 'lunge_score']
    list_filter = ['assessed_at']
    search_fields = ['patient__name', 'patient__patient_id']


@admin.register(PeriodisationState)
class PeriodisationStateAdmin(admin.ModelAdmin):
    list_display = ['patient', 'current_phase', 'current_week', 'macrocycle_number', 'weeks_since_deload']
    list_filter = ['current_phase']
    search_fields = ['patient__name']


@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = ['patient', 'perceived_difficulty', 'sleep_last_night', 'pain_reported', 'traffic_light', 'created_at']
    list_filter = ['traffic_light', 'perceived_difficulty', 'pain_reported']
    search_fields = ['patient__name']


@admin.register(AnonymisedSessionLog)
class AnonymisedSessionLogAdmin(admin.ModelAdmin):
    list_display = ['age_bracket', 'biological_sex', 'goal_type', 'session_phase', 'traffic_light', 'created_at']
    list_filter = ['biological_sex', 'goal_type', 'session_phase', 'traffic_light']
    readonly_fields = ['created_at']


@admin.register(CoachPatientLink)
class CoachPatientLinkAdmin(admin.ModelAdmin):
    list_display = ['coach', 'patient', 'linked_at', 'is_active']
    list_filter = ['is_active']
    search_fields = ['coach__name', 'patient__name', 'patient__patient_id']
    readonly_fields = ['linked_at']


@admin.register(NutritionProfile)
class NutritionProfileAdmin(admin.ModelAdmin):
    list_display = ['patient', 'nutrition_goal', 'activity_level', 'target_calories', 'target_protein_g', 'target_carbs_g', 'target_fat_g', 'mess_mode']
    list_filter = ['nutrition_goal', 'activity_level', 'mess_mode']
    search_fields = ['patient__name', 'patient__patient_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_hindi', 'category', 'calories_per_100g', 'protein_per_100g', 'carbs_per_100g', 'fat_per_100g', 'serving_size_g', 'is_mess_common', 'is_active']
    list_filter = ['category', 'is_mess_common', 'is_active']
    search_fields = ['name', 'name_hindi']


@admin.register(DailyFoodLog)
class DailyFoodLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'food_item', 'log_date', 'meal_type', 'quantity_g', 'calories_logged', 'protein_logged']
    list_filter = ['log_date', 'meal_type']
    search_fields = ['patient__name', 'food_item__name']
    readonly_fields = ['logged_at', 'calories_logged', 'protein_logged', 'carbs_logged', 'fat_logged']


@admin.register(MessEntry)
class MessEntryAdmin(admin.ModelAdmin):
    list_display = ['patient', 'entry_date', 'meal_type', 'logged_at']
    list_filter = ['entry_date', 'meal_type']
    search_fields = ['patient__name', 'raw_description']
    readonly_fields = ['logged_at']


@admin.register(FootballProfile)
class FootballProfileAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'football_level', 'fv_tendency', 'lsi_flag',
        'hsr_current_phase', 'plyometric_cleared', 'assessed_at',
    ]
    list_filter = ['football_level', 'fv_tendency', 'lsi_flag', 'plyometric_cleared', 'hsr_current_phase']
    search_fields = ['patient__name', 'patient__patient_id']
    readonly_fields = ['assessed_at', 'updated_at']
