"""
VYAYAM STRENGTH TRAINING - DJANGO MODELS
All data structures as Django ORM models
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


# ============================================================================
# PATIENT PROFILE - The 8 Parameters + All Data
# ============================================================================

class PatientProfile(models.Model):
    """
    Complete patient health profile with all 8 clusteral dimensions
    """
    # Link to Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Basic Information
    patient_id = models.CharField(max_length=20, unique=True, primary_key=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    password = models.CharField(max_length=128, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 8 CLUSTERAL DIMENSIONS
    # 1. Age
    age = models.IntegerField(validators=[MinValueValidator(13), MaxValueValidator(100)])

    # Biological Context
    BIOLOGICAL_SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('not_specified', 'Prefer not to say'),
    ]
    biological_sex = models.CharField(max_length=15, choices=BIOLOGICAL_SEX_CHOICES, default='not_specified')
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)

    # 2. Fitness Level (stored as JSON)
    fitness_level_json = models.JSONField(default=dict, blank=True)
    # Example: {'lower_body': 'manageable', 'upper_body': 'easy'}
    
    # 3. Goals
    goals = models.TextField()
    GOAL_TYPES = [
        ('general_strength', 'General Strength'),
        ('hypertrophy', 'Build Muscle'),
        ('endurance', 'Endurance'),
        ('strength_endurance', 'Strength + Endurance'),
        ('calisthenics', 'Calisthenics Skills'),
        ('fat_loss', 'Fat Loss'),
        ('female_physique', 'Female Physique'),
        ('athletic', 'Athletic Performance'),
        ('rehabilitation', 'Rehabilitation'),
        ('mobility', 'Mobility and Movement'),
        ('posture', 'Posture Correction'),
        ('healthy_ageing', 'Healthy and Active (50+)'),
    ]
    goal_type = models.CharField(max_length=25, choices=GOAL_TYPES, default='general_strength')
    goal_secondary = models.CharField(max_length=25, choices=GOAL_TYPES, blank=True, default='')
    sport_type = models.CharField(max_length=50, blank=True, default='')
    competition_date = models.DateField(null=True, blank=True)
    
    # 4. Biomechanics
    biomechanics = models.CharField(max_length=100, blank=True)
    activity_pattern = models.CharField(max_length=50, blank=True)
    
    # 5. Difficulty Tolerance (Pain Tolerance)
    difficulty_tolerance = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    # 6. Lifestyle
    LIFESTYLE_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('moderately_active', 'Moderately Active'),
        ('active', 'Active'),
        ('very_active', 'Very Active'),
    ]
    lifestyle = models.CharField(max_length=30, choices=LIFESTYLE_CHOICES, default='sedentary')
    occupation = models.CharField(max_length=200, blank=True)
    daily_sitting_hours = models.IntegerField(default=0)

    # Lifestyle expansion
    sleep_quality = models.CharField(max_length=20, blank=True, default='good')  # poor/moderate/good/variable
    stress_level = models.CharField(max_length=20, blank=True, default='moderate')  # low/moderate/high/very_high
    nutrition_quality = models.CharField(max_length=30, blank=True, default='regular')  # skip_meals/regular/good/managed

    # Training History
    TRAINING_HISTORY_CHOICES = [
        ('never', 'Never Trained'),
        ('tried', 'Tried but stopped'),
        ('beginner', '1-6 months'),
        ('intermediate', '6 months - 2 years'),
        ('advanced', '2+ years'),
    ]
    training_history = models.CharField(max_length=20, choices=TRAINING_HISTORY_CHOICES, default='never')
    training_age_months = models.IntegerField(default=0)
    TRAINING_TYPES = [
        ('gym_machines', 'Gym Machines'),
        ('free_weights', 'Free Weights'),
        ('calisthenics', 'Calisthenics'),
        ('yoga', 'Yoga'),
        ('running', 'Running'),
        ('sports', 'Sports'),
        ('home_workouts', 'Home Workouts'),
        ('nothing', 'Nothing'),
    ]
    training_types_json = models.JSONField(default=list, blank=True)
    last_trained = models.CharField(max_length=20, blank=True, default='never')

    # Equipment
    EQUIPMENT_CHOICES = [
        ('none', 'Bodyweight Only'),
        ('bands', 'Resistance Bands'),
        ('dumbbells', 'Dumbbells'),
        ('kettlebell', 'Kettlebell'),
        ('pullup_bar', 'Pull-up Bar'),
        ('barbell', 'Barbell and Plates'),
        ('bench', 'Bench'),
        ('full_gym', 'Full Gym Access'),
    ]
    equipment_available_json = models.JSONField(default=list, blank=True)
    raw_test_data_json = models.JSONField(default=dict, blank=True)
    TRAINING_LOCATION_CHOICES = [
        ('home_none', 'Home — No Equipment'),
        ('home_some', 'Home — Some Equipment'),
        ('gym', 'Gym'),
        ('outdoor', 'Outdoor'),
        ('mixed', 'Mixed'),
    ]
    training_location = models.CharField(max_length=20, choices=TRAINING_LOCATION_CHOICES, default='home_none')
    session_duration_minutes = models.IntegerField(default=45)
    sessions_per_week = models.IntegerField(default=3)

    # 7. Compliance
    compliance_proven = models.BooleanField(default=False)
    adherence_rate = models.FloatField(default=0.0)  # Percentage
    
    # 8. Timeline
    TIMELINE_CHOICES = [
        ('no_rush', 'No Rush'),
        ('moderate', 'Moderate'),
        ('urgent', 'Urgent'),
    ]
    timeline = models.CharField(max_length=20, choices=TIMELINE_CHOICES, default='no_rush')
    target_weeks = models.IntegerField(default=12)
    
    # Medical History
    medical_conditions_json = models.JSONField(default=list, blank=True)
    contraindications_json = models.JSONField(default=list, blank=True)

    # Red Flags
    red_flags_json = models.JSONField(default=list, blank=True)
    surgical_history_json = models.JSONField(default=list, blank=True)
    medications_json = models.JSONField(default=list, blank=True)
    absolute_stop = models.BooleanField(default=False)
    absolute_stop_reason = models.TextField(blank=True, default='')

    # Female Hormonal Integration (only relevant if biological_sex == 'female')
    cycle_tracking_enabled = models.BooleanField(default=False)
    cycle_length_days = models.IntegerField(null=True, blank=True)
    last_period_start = models.DateField(null=True, blank=True)
    hormonal_contraceptive = models.BooleanField(default=False)
    menstrual_pain_level = models.CharField(max_length=20, blank=True, default='')  # minimal/moderate/significant/severe

    # Mind-Muscle Connection Baseline
    MIND_MUSCLE_CHOICES = [
        ('clear', 'Yes, clearly'),
        ('slight', 'Slightly'),
        ('none', 'Cannot isolate'),
    ]
    mind_muscle_glute = models.CharField(max_length=10, choices=MIND_MUSCLE_CHOICES, blank=True, default='')
    mind_muscle_vmo = models.CharField(max_length=10, choices=MIND_MUSCLE_CHOICES, blank=True, default='')

    # Prescription Mode
    PRESCRIPTION_MODES = [
        ('ai_auto', 'AI Auto-Prescription'),
        ('therapist_manual', 'Therapist Manual'),
    ]
    prescription_mode = models.CharField(
        max_length=20,
        choices=PRESCRIPTION_MODES,
        default='ai_auto'
    )
    # B2B2C: when True, the patient was created by a therapist via therapist_app.
    # Patient PWA login skips strength_app onboarding and routes to the
    # therapist-driven session today page instead.
    therapist_managed = models.BooleanField(default=False)
    assigned_therapist = models.ForeignKey(
        'TherapistProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Current Status
    current_week = models.IntegerField(default=0)
    program_start_date = models.DateTimeField(null=True, blank=True)
    program_end_date = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # ── Health Profile State (persists across sessions) ──────────────────────
    # Tracks whether gate tests have been completed so the dashboard always
    # shows the correct state, even after server restarts.
    gate_test_completed = models.BooleanField(default=False)
    gate_test_completed_at = models.DateTimeField(null=True, blank=True)

    # The current generated prescription stored in DB so it survives session loss.
    # Same structure as what generate_prescription() returns, serialised as JSON.
    current_prescription_json = models.JSONField(default=dict, blank=True)
    prescription_generated_at = models.DateTimeField(null=True, blank=True)

    # V2 data foundation — anonymised data collection consent
    data_consent = models.BooleanField(default=False)
    data_consent_date = models.DateTimeField(null=True, blank=True)

    # Athlete tier
    athlete_tier_eligible = models.BooleanField(default=False)
    athlete_tier_active = models.BooleanField(default=False)
    athlete_sport = models.CharField(max_length=30, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.patient_id})"
    
    @property
    def medical_conditions(self):
        return self.medical_conditions_json
    
    @property
    def contraindications(self):
        return self.contraindications_json
    
    @property
    def fitness_level(self):
        return self.fitness_level_json


# ============================================================================
# STRENGTH PROFILE — 7-test assessment radar chart
# ============================================================================

class MatchDate(models.Model):
    """Monthly match calendar for in-season microcycle management (P29)."""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='match_dates')
    match_date = models.DateField()
    opponent = models.CharField(max_length=100, blank=True, default='')
    notes = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['match_date']
        unique_together = ['patient', 'match_date']

    def __str__(self):
        return f"{self.patient.name} — Match {self.match_date}"


class StrengthProfile(models.Model):
    """7-test strength assessment producing a radar chart strength profile."""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='strength_profiles')
    assessed_at = models.DateTimeField(auto_now_add=True)
    assessment_number = models.IntegerField(default=1)

    # 7 pattern scores (1-5 capability)
    squat_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    hinge_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    push_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    pull_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    core_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    rotate_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    lunge_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])

    # Bilateral test details (left/right scores for asymmetry)
    hinge_left = models.IntegerField(default=0)
    hinge_right = models.IntegerField(default=0)
    lunge_left = models.IntegerField(default=0)
    lunge_right = models.IntegerField(default=0)
    rotate_left = models.IntegerField(default=0)
    rotate_right = models.IntegerField(default=0)

    # Asymmetry flags
    ASYMMETRY_CHOICES = [
        ('none', 'None'),
        ('mild', 'Mild (gap 1)'),
        ('moderate', 'Moderate (gap 2)'),
        ('significant', 'Significant (gap 3+)'),
    ]
    hinge_asymmetry = models.CharField(max_length=15, choices=ASYMMETRY_CHOICES, default='none')
    lunge_asymmetry = models.CharField(max_length=15, choices=ASYMMETRY_CHOICES, default='none')
    rotate_asymmetry = models.CharField(max_length=15, choices=ASYMMETRY_CHOICES, default='none')
    weaker_side_hinge = models.CharField(max_length=5, blank=True, default='')
    weaker_side_lunge = models.CharField(max_length=5, blank=True, default='')
    weaker_side_rotate = models.CharField(max_length=5, blank=True, default='')

    # Subcutaneous fat asymmetry (self-report)
    fat_asymmetry_visible = models.CharField(max_length=20, blank=True, default='none')
    fat_asymmetry_location = models.CharField(max_length=30, blank=True, default='')
    fat_asymmetry_side = models.CharField(max_length=10, blank=True, default='')

    # Pattern priority assignment (computed from scores)
    pattern_priority_json = models.JSONField(default=dict, blank=True)

    # Raw test data (JSON for flexibility)
    raw_test_data_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-assessed_at']

    def __str__(self):
        return f"{self.patient.name} — Assessment #{self.assessment_number} ({self.assessed_at.strftime('%Y-%m-%d')})"


# ============================================================================
# PERIODISATION STATE
# ============================================================================

class PeriodisationState(models.Model):
    """Tracks the patient's current position in the periodisation macrocycle."""
    patient = models.OneToOneField(PatientProfile, on_delete=models.CASCADE, related_name='periodisation')

    PHASE_CHOICES = [
        ('anatomical_adaptation_iso', 'Anatomical Adaptation — Isometric'),
        ('anatomical_adaptation_ecc', 'Anatomical Adaptation — Eccentric'),
        ('hypertrophy', 'Hypertrophy'),
        ('hypertrophy_volume', 'Hypertrophy — Increased Volume'),
        ('strength', 'Strength'),
        ('deload', 'Deload'),
    ]
    current_phase = models.CharField(max_length=30, choices=PHASE_CHOICES, default='anatomical_adaptation_iso')
    current_week = models.IntegerField(default=1)
    macrocycle_number = models.IntegerField(default=1)
    phase_start_date = models.DateField(null=True, blank=True)
    last_deload_date = models.DateField(null=True, blank=True)
    weeks_since_deload = models.IntegerField(default=0)

    anatomical_adaptation_weeks = models.IntegerField(default=4)
    total_sessions_this_cycle = models.IntegerField(default=0)

    class Meta:
        pass

    def __str__(self):
        return f"{self.patient.name} — {self.get_current_phase_display()} (Week {self.current_week})"


# ============================================================================
# GATE TEST RESULTS
# ============================================================================

class GateTestResult(models.Model):
    """Results from a single gate test — one record per exercise family"""

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='gate_tests')

    # ── Exercise Family (new progression-based system) ──────────────────────
    exercise_family = models.CharField(
        max_length=50, default='',
        help_text='e.g. squat_family, hip_hinge_family, lunge_family, ...'
    )
    family_name = models.CharField(max_length=100, default='')

    # Legacy category field kept for backwards compatibility
    CATEGORY_CHOICES = [
        ('lower_body', 'Lower Body'),
        ('posterior_chain', 'Posterior Chain'),
        ('upper_body', 'Upper Body'),
        ('cardio', 'Cardio'),
        ('push', 'Push Pattern'),
        ('balance', 'Balance & Stability'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='lower_body')

    # The specific exercise the patient was tested at their final level
    test_exercise = models.CharField(max_length=100)          # exercise_id tested
    test_date = models.DateTimeField(auto_now_add=True)

    # ── Level reached ────────────────────────────────────────────────────────
    level_index = models.IntegerField(default=0, help_text='0-based index in the progression chain')
    levels_advanced_through = models.IntegerField(default=0, help_text='How many "Too Easy" advances before settling')

    # ── The exact exercise to prescribe ─────────────────────────────────────
    prescribed_exercise_id = models.CharField(max_length=100, default='')
    prescribed_exercise_name = models.CharField(max_length=200, default='')

    # ── Performance at final level ───────────────────────────────────────────
    reps_completed = models.IntegerField(default=0)
    depth_achieved = models.FloatField(default=0.0)   # For squats only
    difficulty_reported = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    pain_during = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )

    # ── Capability Classification ─────────────────────────────────────────────
    CAPABILITY_CHOICES = [
        ('cannot_do', 'Cannot Do'),
        ('struggling', 'Struggling'),
        ('manageable', 'Manageable'),
        ('easy', 'Easy'),
    ]
    capability_level = models.CharField(max_length=20, choices=CAPABILITY_CHOICES, default='manageable')

    # ── Prescription Determined ───────────────────────────────────────────────
    starting_sets = models.IntegerField(default=3)
    starting_reps = models.IntegerField(default=10)
    starting_phase = models.CharField(max_length=30, default='phase_1_standard')

    # ── Numeric Capability Level (1-5 Progressive Loading System) ────────────
    # 1=Unable, 2=Partial/Assisted, 3=Basic/Building, 4=Comfortable, 5=Advanced
    capability_numeric = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='1=Unable, 2=Partial, 3=Basic, 4=Comfortable, 5=Advanced'
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = models.TextField(blank=True)
    went_to_practice_mode = models.BooleanField(default=False)
    advancement_from_gate = models.IntegerField(default=0)

    class Meta:
        ordering = ['-test_date']

    def __str__(self):
        return f"{self.patient.name} — {self.family_name or self.category} ({self.capability_level})"


# ============================================================================
# PATIENT FAMILY CAPABILITY — tracks current level per exercise family
# This is the live "health profile" state that updates after each reassessment
# ============================================================================

class PatientFamilyCapability(models.Model):
    """
    Stores the patient's current capability level (1-5) for each exercise family.
    Updated every time a gate test or weekly reassessment is completed.
    This is the source of truth for the prescription engine.
    """
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE,
        related_name='family_capabilities'
    )
    family_id = models.CharField(max_length=50, help_text='e.g. squat_family, cardio_family')
    family_name = models.CharField(max_length=100, default='')

    # Current position on the ladder
    current_level_index = models.IntegerField(
        default=0,
        help_text='0-based index in progression chain (which exercise)'
    )
    current_exercise_id = models.CharField(max_length=100, default='')
    current_exercise_name = models.CharField(max_length=200, default='')

    # 5-level capability at current ladder position
    capability_numeric = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='1=Unable, 2=Partial, 3=Basic, 4=Comfortable, 5=Advanced/Ready to progress'
    )
    capability_string = models.CharField(
        max_length=20, default='manageable',
        help_text='cannot_do | struggling | manageable | easy'
    )

    # Prescription from latest assessment
    prescribed_sets = models.IntegerField(default=3)
    prescribed_reps = models.IntegerField(default=10)
    prescribed_hold_duration = models.IntegerField(default=0)

    # Progression tracking
    weeks_at_current_level = models.IntegerField(default=0)
    sessions_at_current_level = models.IntegerField(default=0)
    consecutive_comfortable_sessions = models.IntegerField(default=0)
    ready_to_advance = models.BooleanField(default=False)

    # Timestamps
    first_assessed = models.DateTimeField(auto_now_add=True)
    last_assessed = models.DateTimeField(auto_now=True)
    last_advancement_date = models.DateTimeField(null=True, blank=True)

    # History (JSON log of all level changes)
    progression_history_json = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ['patient', 'family_id']
        ordering = ['family_id']

    def __str__(self):
        return (
            f"{self.patient.name} | {self.family_name or self.family_id} | "
            f"L{self.current_level_index + 1} | Cap={self.capability_numeric}"
        )

    def to_summary_dict(self):
        """Serialisable summary for session / prescription use."""
        return {
            'family_id': self.family_id,
            'family_name': self.family_name,
            'current_level_index': self.current_level_index,
            'current_exercise_id': self.current_exercise_id,
            'capability_numeric': self.capability_numeric,
            'capability_string': self.capability_string,
            'prescribed_sets': self.prescribed_sets,
            'prescribed_reps': self.prescribed_reps,
            'prescribed_hold_duration': self.prescribed_hold_duration,
            'weeks_at_current_level': self.weeks_at_current_level,
            'ready_to_advance': self.ready_to_advance,
        }


# ============================================================================
# WORKOUT SESSIONS
# ============================================================================

class WorkoutSession(models.Model):
    """Complete daily workout session"""
    
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='workout_sessions')
    session_date = models.DateTimeField(auto_now_add=True)
    week_number = models.IntegerField(default=1)
    
    # Session-level metrics
    total_duration_minutes = models.IntegerField(default=0)
    total_exercises_completed = models.IntegerField(default=0)
    total_green_reps_all = models.IntegerField(default=0)
    overall_session_form_score = models.FloatField(default=0.0)
    
    # XP earned this session (persisted so total_xp reflects variable form-based scoring)
    xp_earned = models.IntegerField(default=0)

    # Daily Feedback
    patient_comfortable = models.BooleanField(default=True)
    difficulty_rating = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    patient_notes = models.TextField(blank=True)
    
    # Prescription info
    prescription_mode = models.CharField(max_length=20, default='ai_auto')
    prescribed_by_therapist = models.ForeignKey(
        'TherapistProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-session_date']
    
    def __str__(self):
        return f"{self.patient.name} - Week {self.week_number} - {self.session_date.strftime('%Y-%m-%d')}"


class SessionFeedback(models.Model):
    """Post-session check-in data — feeds traffic light load management."""
    session = models.OneToOneField(WorkoutSession, on_delete=models.CASCADE, related_name='feedback')
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='session_feedbacks')
    created_at = models.DateTimeField(auto_now_add=True)

    PERCEIVED_DIFFICULTY_CHOICES = [
        ('too_easy', 'Too Easy'),
        ('just_right', 'Just Right'),
        ('hard', 'Hard'),
        ('too_hard', 'Too Hard'),
    ]
    perceived_difficulty = models.CharField(max_length=15, choices=PERCEIVED_DIFFICULTY_CHOICES, default='just_right')

    SLEEP_CHOICES = [
        ('under_5', '< 5 hours'),
        ('5_to_6', '5-6 hours'),
        ('7_to_8', '7-8 hours'),
        ('over_8', '8+ hours'),
    ]
    sleep_last_night = models.CharField(max_length=10, choices=SLEEP_CHOICES, default='7_to_8')

    PAIN_CHOICES = [
        ('none', 'None'),
        ('mild', 'Mild Discomfort'),
        ('moderate', 'Moderate Pain'),
        ('severe', 'Severe Pain'),
    ]
    pain_reported = models.CharField(max_length=20, choices=PAIN_CHOICES, default='none')
    pain_location = models.CharField(max_length=100, blank=True, default='')
    pain_exercise = models.CharField(max_length=100, blank=True, default='')
    pain_severity = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)])

    ENERGY_CHOICES = [
        ('good', 'Good'),
        ('moderate', 'Moderate'),
        ('low', 'Low'),
    ]
    energy_level = models.CharField(max_length=10, choices=ENERGY_CHOICES, blank=True, default='')
    hormonal_phase = models.CharField(max_length=20, blank=True, default='')

    # Session RPE for ACWR calculation (P31)
    session_rpe = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Session RPE 1-10: How hard was this session overall?'
    )

    TRAFFIC_LIGHT_CHOICES = [
        ('green', 'Green — Safe to progress'),
        ('yellow', 'Yellow — Maintain, do not progress'),
        ('red', 'Red — Reduce load, assess'),
    ]
    traffic_light = models.CharField(max_length=10, choices=TRAFFIC_LIGHT_CHOICES, default='green')

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Always recompute traffic light on save
        from .v1_safety_logic import compute_traffic_light
        self.traffic_light = compute_traffic_light(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient.name} — {self.traffic_light} ({self.created_at.strftime('%Y-%m-%d')})"


class ExerciseExecution(models.Model):
    """Data for a single exercise in a workout"""
    
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='exercises')
    
    exercise_id = models.CharField(max_length=100)
    exercise_name = models.CharField(max_length=200)
    
    CATEGORY_CHOICES = [
        ('lower_body', 'Lower Body'),
        ('posterior_chain', 'Posterior Chain'),
        ('upper_body', 'Upper Body'),
        ('cardio', 'Cardio'),
        ('stretching', 'Stretching'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Prescription
    prescribed_sets = models.IntegerField()
    prescribed_reps = models.IntegerField()
    prescribed_hold_duration = models.FloatField(default=0.0)
    prescribed_rest = models.IntegerField(default=60)
    
    # Execution
    total_green_reps = models.IntegerField(default=0)
    total_yellow_reps = models.IntegerField(default=0)
    total_red_reps = models.IntegerField(default=0)
    
    # Metrics
    overall_form_score = models.FloatField(default=0.0)
    completion_percentage = models.FloatField(default=0.0)
    
    # Practice Mode
    practice_mode_entered = models.BooleanField(default=False)
    practice_reps_done = models.IntegerField(default=0)
    went_back_one_level = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.exercise_name} - {self.session}"


# ============================================================================
# THERAPIST PROFILE
# ============================================================================

class TherapistProfile(models.Model):
    """Licensed therapist who can manually prescribe"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    therapist_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100)
    specialization = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Dashboard preferences
    show_ai_suggestions = models.BooleanField(default=True)
    auto_generate_reports = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Dr. {self.name} ({self.therapist_id})"
    
    @property
    def assigned_patients(self):
        return PatientProfile.objects.filter(assigned_therapist=self)


class TherapistPrescription(models.Model):
    """Manual prescription by therapist"""
    
    prescription_id = models.CharField(max_length=50, unique=True)
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    
    # Prescribed exercises (stored as JSON)
    exercises_json = models.JSONField(default=list)
    
    # Prescription details
    duration_weeks = models.IntegerField(default=1)
    frequency_per_week = models.IntegerField(default=7)
    
    # Notes
    clinical_reasoning = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Status
    active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.prescription_id} - {self.patient.name} by {self.therapist.name}"
    
    @property
    def exercises(self):
        return self.exercises_json


# ============================================================================
# EXERCISE PROGRESSION STATE
# ============================================================================

class ExerciseProgressionState(models.Model):
    """Track progression for a specific exercise category"""
    
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='progression_states')
    
    CATEGORY_CHOICES = [
        ('lower_body', 'Lower Body'),
        ('posterior_chain', 'Posterior Chain'),
        ('upper_body', 'Upper Body'),
        ('cardio', 'Cardio'),
    ]
    exercise_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    current_exercise_id = models.CharField(max_length=100)
    current_level = models.CharField(max_length=100)
    
    # Current prescription
    current_sets = models.IntegerField(default=3)
    current_reps = models.IntegerField(default=10)
    
    # Progression tracking
    weeks_at_current_level = models.IntegerField(default=0)
    threshold_met = models.BooleanField(default=False)
    ready_to_advance = models.BooleanField(default=False)
    
    # Comfort tracking
    consecutive_uncomfortable_days = models.IntegerField(default=0)
    consecutive_comfortable_days = models.IntegerField(default=0)
    
    # History
    last_advancement_date = models.DateTimeField(null=True, blank=True)
    last_regression_date = models.DateTimeField(null=True, blank=True)
    progression_history_json = models.JSONField(default=list, blank=True)
    
    class Meta:
        unique_together = ['patient', 'exercise_category']
    
    def __str__(self):
        return f"{self.patient.name} - {self.exercise_category}: {self.current_level}"
    
    @property
    def progression_history(self):
        return self.progression_history_json


# ============================================================================
# PROGRESS REPORTS
# ============================================================================

class ProgressReport(models.Model):
    """Professional physiotherapy progress report"""
    
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='reports')
    report_date = models.DateTimeField(auto_now_add=True)
    report_period = models.CharField(max_length=50)  # "Week 1-4"
    
    # Overall Outcomes (stored as metrics)
    total_sessions_completed = models.IntegerField(default=0)
    total_sessions_prescribed = models.IntegerField(default=0)
    overall_adherence_rate = models.FloatField(default=0.0)
    total_green_reps_period = models.IntegerField(default=0)
    average_form_score_period = models.FloatField(default=0.0)
    form_improvement = models.FloatField(default=0.0)
    
    # Data (stored as JSON for flexibility)
    initial_fitness_levels_json = models.JSONField(default=dict, blank=True)
    current_fitness_levels_json = models.JSONField(default=dict, blank=True)
    exercises_advanced_json = models.JSONField(default=list, blank=True)
    exercises_current_levels_json = models.JSONField(default=dict, blank=True)
    volume_by_exercise_json = models.JSONField(default=dict, blank=True)
    
    # Clinical Notes
    therapist_notes = models.TextField(blank=True)
    patient_feedback_summary = models.TextField(blank=True)
    
    # Recommendations
    continue_current_program = models.BooleanField(default=True)
    recommended_next_steps = models.TextField(blank=True)
    
    # Metadata
    prescribed_by = models.CharField(max_length=200, default="VYAYAM AI System")
    reason_for_prescription = models.TextField(default="Strength training program")
    
    class Meta:
        ordering = ['-report_date']
    
    def __str__(self):
        return f"{self.patient.name} - Report {self.report_period}"
    
    @property
    def initial_fitness_levels(self):
        return self.initial_fitness_levels_json
    
    @property
    def current_fitness_levels(self):
        return self.current_fitness_levels_json
    
    @property
    def exercises_advanced(self):
        return self.exercises_advanced_json
    
    @property
    def exercises_current_levels(self):
        return self.exercises_current_levels_json
    
    @property
    def volume_by_exercise(self):
        return self.volume_by_exercise_json


# ============================================================================
# STRETCH SESSION
# ============================================================================

class AnonymisedSessionLog(models.Model):
    """V2 data foundation — anonymised session data for Bayesian engine training."""
    created_at = models.DateTimeField(auto_now_add=True)
    age_bracket = models.CharField(max_length=10)
    biological_sex = models.CharField(max_length=15)
    goal_type = models.CharField(max_length=25)
    training_history = models.CharField(max_length=20)
    session_phase = models.CharField(max_length=30)
    exercises_json = models.JSONField(default=list)
    feedback_difficulty = models.CharField(max_length=15, blank=True)
    feedback_pain = models.CharField(max_length=20, blank=True)
    feedback_pain_location = models.CharField(max_length=100, blank=True)
    traffic_light = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AnonLog [{self.age_bracket} {self.biological_sex} {self.session_phase}] {self.created_at.strftime('%Y-%m-%d')}"


class CoachPatientLink(models.Model):
    """Links a coach/therapist to their athletes for squad dashboard access."""
    coach = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name='athletes')
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='coaches')
    linked_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('coach', 'patient')
        ordering = ['patient__name']

    def __str__(self):
        return f"{self.coach.name} → {self.patient.name}"


class StretchSession(models.Model):
    """Pre-match stretching protocol session"""
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='stretch_sessions'
    )
    session_date = models.DateTimeField(auto_now_add=True)
    protocol_name = models.CharField(max_length=100, default='Pre-Football Stretching')
    total_stretches = models.IntegerField(default=12)
    stretches_completed = models.IntegerField(default=0)
    total_duration_seconds = models.IntegerField(default=0)
    stretch_results_json = models.JSONField(default=list, blank=True)
    posture_notes = models.TextField(blank=True)
    camera_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-session_date']

    def __str__(self):
        return f"{self.patient.name} — {self.protocol_name} ({self.session_date.strftime('%Y-%m-%d')})"


class NutritionProfile(models.Model):
    """Optional nutrition profile — stores goal-based macro targets for a patient"""
    GOAL_CHOICES = [
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('maintenance', 'Maintenance'),
        ('athletic_performance', 'Athletic Performance'),
        ('rehabilitation', 'Rehabilitation / Recovery'),
    ]
    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary (desk job, little exercise)'),
        ('lightly_active', 'Lightly Active (1–3 days/week)'),
        ('moderately_active', 'Moderately Active (3–5 days/week)'),
        ('very_active', 'Very Active (6–7 days/week)'),
        ('extra_active', 'Extra Active (athlete / physical job)'),
    ]

    patient = models.OneToOneField(
        PatientProfile, on_delete=models.CASCADE, related_name='nutrition_profile'
    )
    nutrition_goal = models.CharField(max_length=30, choices=GOAL_CHOICES, default='maintenance')
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='moderately_active')

    # Body stats (optional — used for BMR)
    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    biological_sex = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], default='male')

    # Computed targets (updated by engine on save / re-calc)
    target_calories = models.IntegerField(default=0)
    target_protein_g = models.IntegerField(default=0)
    target_carbs_g = models.IntegerField(default=0)
    target_fat_g = models.IntegerField(default=0)

    # Hostel / mess mode toggle
    mess_mode = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.name} — Nutrition ({self.nutrition_goal})"


class FoodItem(models.Model):
    """Curated Indian food database"""
    CATEGORY_CHOICES = [
        ('grain', 'Grains & Rice'),
        ('dal', 'Dal & Legumes'),
        ('vegetable', 'Vegetables'),
        ('fruit', 'Fruits'),
        ('dairy', 'Dairy'),
        ('non_veg', 'Non-Vegetarian'),
        ('snack', 'Snacks & Street Food'),
        ('beverage', 'Beverages'),
        ('oil_fat', 'Oils & Fats'),
        ('sweet', 'Sweets & Desserts'),
        ('mess', 'Mess / Canteen Common'),
    ]

    name = models.CharField(max_length=100)
    name_hindi = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Per 100g values
    calories_per_100g = models.FloatField()
    protein_per_100g = models.FloatField(default=0)
    carbs_per_100g = models.FloatField(default=0)
    fat_per_100g = models.FloatField(default=0)
    fiber_per_100g = models.FloatField(default=0)

    # Typical serving size
    serving_size_g = models.FloatField(default=100)
    serving_description = models.CharField(max_length=80, blank=True, help_text="e.g. '1 medium bowl', '2 rotis'")

    is_mess_common = models.BooleanField(default=False, help_text="Commonly served in hostel mess")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"

    @property
    def calories_per_serving(self):
        return round(self.calories_per_100g * self.serving_size_g / 100, 1)

    @property
    def protein_per_serving(self):
        return round(self.protein_per_100g * self.serving_size_g / 100, 1)

    @property
    def carbs_per_serving(self):
        return round(self.carbs_per_100g * self.serving_size_g / 100, 1)

    @property
    def fat_per_serving(self):
        return round(self.fat_per_100g * self.serving_size_g / 100, 1)


class DailyFoodLog(models.Model):
    """One food entry logged by the patient for a given date"""
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='food_logs'
    )
    food_item = models.ForeignKey(
        FoodItem, on_delete=models.CASCADE, related_name='log_entries'
    )
    log_date = models.DateField()
    quantity_g = models.FloatField(default=100, help_text="Grams consumed")
    meal_type = models.CharField(
        max_length=15,
        choices=[
            ('breakfast', 'Breakfast'),
            ('lunch', 'Lunch'),
            ('snack', 'Snack'),
            ('dinner', 'Dinner'),
            ('pre_workout', 'Pre-Workout'),
            ('post_workout', 'Post-Workout'),
        ],
        default='lunch'
    )
    logged_at = models.DateTimeField(auto_now_add=True)

    # Cached macros at time of logging (avoids re-calc if FoodItem changes)
    calories_logged = models.FloatField(default=0)
    protein_logged = models.FloatField(default=0)
    carbs_logged = models.FloatField(default=0)
    fat_logged = models.FloatField(default=0)

    class Meta:
        ordering = ['log_date', 'meal_type', 'logged_at']

    def save(self, *args, **kwargs):
        factor = self.quantity_g / 100
        self.calories_logged = round(self.food_item.calories_per_100g * factor, 1)
        self.protein_logged = round(self.food_item.protein_per_100g * factor, 1)
        self.carbs_logged = round(self.food_item.carbs_per_100g * factor, 1)
        self.fat_logged = round(self.food_item.fat_per_100g * factor, 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient.name} — {self.food_item.name} {self.quantity_g}g ({self.log_date})"


class MessEntry(models.Model):
    """Hostel mess mode: patient records what was served; app returns portion guidance"""
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name='mess_entries'
    )
    entry_date = models.DateField()
    meal_type = models.CharField(
        max_length=15,
        choices=[('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('snack', 'Snack'), ('dinner', 'Dinner')],
        default='lunch'
    )
    # Comma-separated list of food item IDs served in the mess
    food_items_served = models.ManyToManyField(FoodItem, blank=True, related_name='mess_appearances')
    # Free-text note from patient ("biryani, dal, salad")
    raw_description = models.TextField(blank=True)
    # Guidance text generated by the engine
    guidance_text = models.TextField(blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', 'meal_type']

    def __str__(self):
        return f"{self.patient.name} — Mess {self.meal_type} ({self.entry_date})"


# ============================================================================
# FOOTBALL PROFILE — athlete tier performance data
# ============================================================================

class FootballProfile(models.Model):
    """
    Stores the football assessment battery results and derived performance
    metrics for an athlete-tier patient. One profile per patient.
    """
    patient = models.OneToOneField(
        PatientProfile, on_delete=models.CASCADE, related_name='football_profile'
    )
    assessed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Assessment scores (0-5) ──────────────────────────────────────────────
    hop_score = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    nordic_score = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    sprint_score = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    pogo_score = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    cod_score = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    ybalance_score = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    # ── Raw test data ────────────────────────────────────────────────────────
    hop_left_cm = models.FloatField(null=True, blank=True)
    hop_right_cm = models.FloatField(null=True, blank=True)
    nordic_seconds = models.FloatField(null=True, blank=True)
    sprint_seconds = models.FloatField(null=True, blank=True)
    pogo_clean_reps = models.IntegerField(null=True, blank=True)
    cod_left_seconds = models.FloatField(null=True, blank=True)
    cod_right_seconds = models.FloatField(null=True, blank=True)
    ybalance_left_pct = models.FloatField(null=True, blank=True)
    ybalance_right_pct = models.FloatField(null=True, blank=True)

    # ── Derived fields ───────────────────────────────────────────────────────
    football_level = models.IntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    fv_tendency = models.CharField(
        max_length=20,
        choices=[
            ('force_dominant', 'Force-Dominant'),
            ('velocity_dominant', 'Velocity-Dominant'),
            ('balanced', 'Balanced'),
        ],
        default='balanced',
    )
    lsi_flag = models.BooleanField(default=False)   # True if any LSI < 90 %

    SEASON_PHASE_CHOICES = [
        ('off_season', 'Off-Season'),
        ('pre_season', 'Pre-Season'),
        ('in_season', 'In-Season'),
        ('post_season', 'Post-Season'),
    ]
    season_phase = models.CharField(
        max_length=20,
        choices=SEASON_PHASE_CHOICES,
        default='in_season',
    )

    hop_lsi_pct = models.FloatField(null=True, blank=True)
    cod_lsi_pct = models.FloatField(null=True, blank=True)
    ybalance_lsi_pct = models.FloatField(null=True, blank=True)
    hsr_current_phase = models.CharField(
        max_length=20,
        choices=[
            ('hsr_phase_1', 'HSR Phase 1'),
            ('hsr_phase_2', 'HSR Phase 2'),
            ('hsr_phase_3', 'HSR Phase 3'),
        ],
        default='hsr_phase_1',
    )
    plyometric_cleared = models.CharField(
        max_length=20,
        choices=[
            ('none', 'Not Cleared'),
            ('low_load', 'Low-Load'),
            ('moderate_load', 'Moderate-Load'),
            ('high_load', 'High-Load'),
        ],
        default='none',
    )
    hsr_weeks_completed = models.IntegerField(default=0)
    last_reassessment = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-assessed_at']

    def __str__(self):
        return f"{self.patient.name} — Football L{self.football_level} ({self.fv_tendency})"

    # ── Computation methods ──────────────────────────────────────────────────

    def compute_level(self):
        """Weakest-link: football_level = min of all 6 test scores (floor 1)."""
        scores = [
            self.hop_score, self.nordic_score, self.sprint_score,
            self.pogo_score, self.cod_score, self.ybalance_score,
        ]
        valid = [s for s in scores if s > 0]
        self.football_level = max(1, min(valid)) if valid else 1
        return self.football_level

    def compute_lsi(self):
        """
        Compute Limb Symmetry Index for bilateral tests.
        LSI = (weaker / stronger) × 100.  Sets lsi_flag if any LSI < 90 %.
        """
        flag = False

        if self.hop_left_cm and self.hop_right_cm:
            stronger = max(self.hop_left_cm, self.hop_right_cm)
            weaker = min(self.hop_left_cm, self.hop_right_cm)
            self.hop_lsi_pct = round((weaker / stronger) * 100, 1)
            if self.hop_lsi_pct < 90:
                flag = True

        if self.cod_left_seconds and self.cod_right_seconds:
            # Lower time = better; weaker side is the slower (higher) time
            faster = min(self.cod_left_seconds, self.cod_right_seconds)
            slower = max(self.cod_left_seconds, self.cod_right_seconds)
            self.cod_lsi_pct = round((faster / slower) * 100, 1)
            if self.cod_lsi_pct < 90:
                flag = True

        if self.ybalance_left_pct and self.ybalance_right_pct:
            stronger = max(self.ybalance_left_pct, self.ybalance_right_pct)
            weaker = min(self.ybalance_left_pct, self.ybalance_right_pct)
            self.ybalance_lsi_pct = round((weaker / stronger) * 100, 1)
            if self.ybalance_lsi_pct < 90:
                flag = True

        self.lsi_flag = flag
        return flag

    def compute_fv_tendency(self):
        """
        Force-velocity tendency from hop_score vs sprint_score.
        hop_score proxy for force; sprint_score proxy for velocity.
        """
        diff = self.hop_score - self.sprint_score
        if diff > 1:
            self.fv_tendency = 'force_dominant'
        elif diff < -1:
            self.fv_tendency = 'velocity_dominant'
        else:
            self.fv_tendency = 'balanced'
        return self.fv_tendency

    def check_plyometric_gate(self, pain_nrs=0):
        """
        Return the highest plyometric tier the athlete has cleared.
        pain_nrs: current pain numeric rating scale (0-10).
        """
        from .v1_football_constants import PLYOMETRIC_GATES

        cleared = 'none'

        low = PLYOMETRIC_GATES['low_load']['requirements']
        if (
            self.football_level >= low['min_football_level']
            and (self.hop_lsi_pct or 100) >= low['lsi_min_pct']
            and self.hop_score >= low['hop_score_min']
            and pain_nrs <= low['pain_nrs_max']
        ):
            cleared = 'low_load'

        mod = PLYOMETRIC_GATES['moderate_load']['requirements']
        if (
            cleared == 'low_load'
            and self.football_level >= mod['min_football_level']
            and (self.hop_lsi_pct or 100) >= mod['lsi_min_pct']
            and self.hop_score >= mod['hop_score_min']
            and self.nordic_score >= mod.get('nordic_score_min', 0)
            and pain_nrs <= mod['pain_nrs_max']
        ):
            cleared = 'moderate_load'

        hi = PLYOMETRIC_GATES['high_load']['requirements']
        if (
            cleared == 'moderate_load'
            and self.football_level >= hi['min_football_level']
            and (self.hop_lsi_pct or 100) >= hi['lsi_min_pct']
            and self.hop_score >= hi['hop_score_min']
            and self.nordic_score >= hi.get('nordic_score_min', 0)
            and self.sprint_score >= hi.get('sprint_score_min', 0)
            and pain_nrs <= hi['pain_nrs_max']
        ):
            cleared = 'high_load'

        self.plyometric_cleared = cleared
        return cleared