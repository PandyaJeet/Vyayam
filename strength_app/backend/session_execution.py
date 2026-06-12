"""
SESSION EXECUTION & DAILY FEEDBACK LOOP
Handles daily workout execution and comfort-based progression
"""

from .database_schema import (
    WorkoutSession, ExerciseData, ExerciseProgressionState,
    ExerciseCategory, PrescriptionMode
)
from .form_tracking import FormAnalyzer, PracticeModeCoordinator, VoiceGuidance
from .prescription_engine import PrescriptionEngine
from typing import Dict, List
from datetime import datetime


class SessionExecutor:
    """
    Executes a daily workout session
    Tracks all exercises, form, and patient feedback
    """
    
    def __init__(self):
        self.form_analyzer = FormAnalyzer()
        self.practice_mode = PracticeModeCoordinator()
        self.voice = VoiceGuidance()
    
    
    def execute_workout_session(
        self,
        patient_id: str,
        week_number: int,
        prescription: Dict[str, List[Dict]],
        prescription_mode: PrescriptionMode = PrescriptionMode.AI_AUTO
    ) -> WorkoutSession:
        """
        Execute a complete daily workout
        
        Structure:
        1. Stretching
        2. Strength
        3. Cardio
        """
        
        session = WorkoutSession(
            patient_id=patient_id,
            session_date=datetime.now(),
            week_number=week_number,
            prescription_mode=prescription_mode
        )
        
        start_time = datetime.now()
        
        # 1. STRETCHING
        print("\n" + "=" * 70)
        print("1️⃣  STRETCHING & WARM-UP")
        print("=" * 70)
        
        for stretch_rx in prescription['stretching']:
            exercise_data = self._execute_exercise(
                exercise_prescription=stretch_rx,
                is_stretching=True
            )
            session.stretching_exercises.append(exercise_data)
            session.total_green_reps_all += exercise_data.total_green_reps
        
        # 2. STRENGTH
        print("\n" + "=" * 70)
        print("2️⃣  STRENGTH TRAINING")
        print("=" * 70)
        
        for strength_rx in prescription['strength']:
            exercise_data = self._execute_exercise(
                exercise_prescription=strength_rx,
                is_stretching=False
            )
            session.strength_exercises.append(exercise_data)
            session.total_green_reps_all += exercise_data.total_green_reps
        
        # 3. CARDIO
        print("\n" + "=" * 70)
        print("3️⃣  CARDIO FINISHER")
        print("=" * 70)
        
        for cardio_rx in prescription['cardio']:
            exercise_data = self._execute_exercise(
                exercise_prescription=cardio_rx,
                is_cardio=True
            )
            session.cardio_exercises.append(exercise_data)
        
        # Calculate session totals
        end_time = datetime.now()
        session.total_duration_minutes = int((end_time - start_time).seconds / 60)
        
        all_exercises = (
            session.stretching_exercises +
            session.strength_exercises +
            session.cardio_exercises
        )
        session.total_exercises_completed = len(all_exercises)
        
        # Calculate overall form score
        form_scores = [ex.overall_form_score for ex in all_exercises if ex.overall_form_score and ex.overall_form_score > 0]  # R2-W1-4: None = manual session, no measured form
        if form_scores:
            session.overall_session_form_score = sum(form_scores) / len(form_scores)
        
        return session
    
    
    def _execute_exercise(
        self,
        exercise_prescription: Dict,
        is_stretching: bool = False,
        is_cardio: bool = False
    ) -> ExerciseData:
        """
        Execute a single exercise (all sets)
        """
        
        exercise_data = ExerciseData(
            exercise_id=exercise_prescription['exercise_id'],
            exercise_name=exercise_prescription['exercise_name'],
            category=exercise_prescription['category'],
            prescribed_sets=exercise_prescription['sets'],
            prescribed_reps=exercise_prescription['reps'],
            prescribed_hold_duration=exercise_prescription.get('hold_duration', 0),
            prescribed_rest=exercise_prescription.get('rest', 60)
        )
        
        print(f"\n📋 {exercise_data.exercise_name}")
        print(f"   Prescription: {exercise_data.prescribed_sets} sets × {exercise_data.prescribed_reps} reps")
        
        # Stretching and cardio don't need form tracking
        if is_stretching or is_cardio:
            # Simplified execution (assume completed)
            exercise_data.total_green_reps = exercise_data.prescribed_sets * exercise_data.prescribed_reps
            exercise_data.completion_percentage = 100.0
            exercise_data.overall_form_score = 90.0  # Assume good form for stretching
            print(f"   ✅ Completed!")
            return exercise_data
        
        # STRENGTH EXERCISES - Track form
        for set_num in range(1, exercise_data.prescribed_sets + 1):
            print(f"\n   Set {set_num}/{exercise_data.prescribed_sets}:")
            
            set_data = self.form_analyzer.analyze_set(
                exercise_id=exercise_data.exercise_id,
                set_number=set_num,
                prescribed_reps=exercise_data.prescribed_reps
            )
            
            # Voice guidance for each rep
            for rep in set_data.rep_data:
                self.voice.provide_guidance(rep)
            
            exercise_data.sets_completed.append(set_data)
            exercise_data.total_green_reps += set_data.reps_completed_green
            exercise_data.total_yellow_reps += set_data.reps_yellow
            exercise_data.total_red_reps += set_data.reps_red
            
            # Check if practice mode needed
            if self.form_analyzer.check_if_practice_mode_needed(set_data):
                print("\n   ⚠️  Form issues detected. Entering PRACTICE MODE...")
                
                can_do, practice_reps = self.practice_mode.conduct_practice_session(
                    exercise_id=exercise_data.exercise_id,
                    max_practice_reps=5
                )
                
                exercise_data.practice_mode_entered = True
                exercise_data.practice_reps_done = practice_reps
                
                if not can_do:
                    # Patient can't do this exercise safely
                    exercise_data.went_back_one_level = True
                    print("\n   ⬅️  Exercise too difficult. Should regress to easier variation.")
                    break  # Stop attempting more sets
            
            # Rest between sets
            if set_num < exercise_data.prescribed_sets:
                print(f"   😮‍💨 Rest {exercise_data.prescribed_rest}s...")
        
        # Calculate exercise-level metrics
        total_reps = exercise_data.total_green_reps + exercise_data.total_yellow_reps + exercise_data.total_red_reps
        
        if total_reps > 0:
            all_form_scores = [rep.form_score for s in exercise_data.sets_completed for rep in s.rep_data]
            if all_form_scores:
                exercise_data.overall_form_score = sum(all_form_scores) / len(all_form_scores)
        
        prescribed_total = exercise_data.prescribed_sets * exercise_data.prescribed_reps
        # DA-P4: zero sets/reps (hold-based or malformed prescriptions) must not crash
        if prescribed_total > 0:
            exercise_data.completion_percentage = (exercise_data.total_green_reps / prescribed_total) * 100
        else:
            exercise_data.completion_percentage = 100.0 if exercise_data.total_green_reps else 0.0
        
        print(f"\n   📊 Exercise Summary:")
        print(f"      🟢 Green reps: {exercise_data.total_green_reps}/{prescribed_total}")
        print(f"      📈 Form score: {exercise_data.overall_form_score:.1f}%")
        print(f"      ✅ Completion: {exercise_data.completion_percentage:.1f}%")
        
        return exercise_data


class DailyFeedbackLoop:
    """
    Handles daily feedback and automatic progression/regression
    
    Logic:
    - Not comfortable for 2 days → Go back 1 level
    - Comfortable for whole week → Ask to advance → Advance
    - After advancing, not comfortable → Go back 1 level
    """
    
    def __init__(self):
        self.prescription_engine = PrescriptionEngine()
    
    
    def collect_daily_feedback(
        self,
        patient_id: str,
        session: WorkoutSession
    ) -> Dict:
        """
        Collect patient feedback after session
        """
        
        print("\n" + "=" * 70)
        print("💬 DAILY FEEDBACK")
        print("=" * 70)
        
        # Question 1: Were you comfortable?
        print("\n1. Were you comfortable with today's workout?")
        print("   [1] Yes, felt good")
        print("   [2] No, too difficult")
        
        # Simulate response (in real app: patient clicks button)
        comfortable = True  # Simulated
        
        if comfortable:
            print("   ✅ Patient: Yes, felt good")
        else:
            print("   ⚠️  Patient: No, too difficult")
        
        # Question 2: Difficulty rating
        print("\n2. How difficult was today's session? (1-5)")
        print("   1 = Too easy | 3 = Just right | 5 = Too hard")
        
        difficulty_rating = 3  # Simulated
        print(f"   → Patient rated: {difficulty_rating}/5")
        
        # Question 3: Any notes?
        patient_notes = ""  # In real app: text input
        
        feedback = {
            'patient_comfortable': comfortable,
            'difficulty_rating': difficulty_rating,
            'patient_notes': patient_notes
        }
        
        # Update session
        session.patient_comfortable = comfortable
        session.difficulty_rating = difficulty_rating
        session.patient_notes = patient_notes
        
        return feedback
    
    
    def check_auto_adjustment_needed(
        self,
        patient_id: str,
        progression_states: Dict[str, ExerciseProgressionState],
        latest_feedback: Dict
    ) -> Dict[str, str]:
        """
        Check if any exercises need auto-adjustment
        
        Returns: {exercise_id: action}
        where action = "regress" | "maintain" | "ready_to_advance"
        """
        
        adjustments = {}
        
        for exercise_id, state in progression_states.items():
            # Check regression criteria
            if not latest_feedback['patient_comfortable']:
                state.consecutive_uncomfortable_days += 1
                state.consecutive_comfortable_days = 0
                
                if state.consecutive_uncomfortable_days >= 2:
                    adjustments[exercise_id] = "regress"
                    print(f"\n⬅️  {exercise_id}: Not comfortable for 2 days → REGRESS")
            
            else:
                state.consecutive_comfortable_days += 1
                state.consecutive_uncomfortable_days = 0
                
                # Check advancement criteria
                if state.threshold_met and state.consecutive_comfortable_days >= 7:
                    adjustments[exercise_id] = "ready_to_advance"
                    print(f"\n➡️  {exercise_id}: Comfortable all week + threshold met → READY TO ADVANCE")
        
        return adjustments
    
    
    def apply_adjustments(
        self,
        current_prescription: Dict[str, List[Dict]],
        adjustments: Dict[str, str]
    ) -> Dict[str, List[Dict]]:
        """
        Apply auto-adjustments to prescription
        """
        
        for exercise_id, action in adjustments.items():
            if action == "regress":
                current_prescription = self.prescription_engine.adjust_prescription_for_regression(
                    current_prescription,
                    exercise_id
                )
            
            elif action == "ready_to_advance":
                # Ask patient if ready
                print(f"\n❓ {exercise_id}: You've been comfortable all week.")
                print("   Ready to advance to next level?")
                print("   [1] Yes, advance")
                print("   [2] No, stay at current level")
                
                # Simulate response
                wants_to_advance = True  # Simulated
                
                if wants_to_advance:
                    print("   ✅ Patient: Yes, advance")
                    current_prescription = self.prescription_engine.adjust_prescription_for_advancement(
                        current_prescription,
                        exercise_id
                    )
                else:
                    print("   → Patient: Stay at current level")
        
        return current_prescription


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    from prescription_engine import PrescriptionEngine
    from gate_test_system import GateTestEngine, GateTestCoordinator
    
    print("=" * 70)
    print("SESSION EXECUTION & FEEDBACK LOOP - DEMO")
    print("=" * 70)
    
    # Setup
    executor = SessionExecutor()
    feedback_loop = DailyFeedbackLoop()
    
    # Mock prescription (simplified)
    prescription = {
        'stretching': [
            {
                'exercise_id': 'hamstring_stretch',
                'exercise_name': 'Hamstring Stretch',
                'sets': 2,
                'reps': 1,
                'hold_duration': 30,
                'rest': 30,
                'category': ExerciseCategory.STRETCHING
            }
        ],
        'strength': [
            {
                'exercise_id': 'normal_squat',
                'exercise_name': 'Normal Squat',
                'sets': 3,
                'reps': 10,
                'hold_duration': 0,
                'rest': 60,
                'category': ExerciseCategory.LOWER_BODY
            }
        ],
        'cardio': [
            {
                'exercise_id': 'jogging_light',
                'exercise_name': 'Light Jogging',
                'sets': 1,
                'reps': 1,
                'hold_duration': 600,
                'rest': 0,
                'category': ExerciseCategory.CARDIO
            }
        ]
    }
    
    # Execute session
    print("\n\n🏋️ EXECUTING DAILY WORKOUT...")
    
    session = executor.execute_workout_session(
        patient_id="P001",
        week_number=1,
        prescription=prescription,
        prescription_mode=PrescriptionMode.AI_AUTO
    )
    
    # Collect feedback
    feedback = feedback_loop.collect_daily_feedback(
        patient_id="P001",
        session=session
    )
    
    print("\n\n📊 SESSION COMPLETE!")
    print(f"   Duration: {session.total_duration_minutes} minutes")
    print(f"   Total exercises: {session.total_exercises_completed}")
    print(f"   Total green reps: {session.total_green_reps_all}")
    print(f"   Overall form: {session.overall_session_form_score:.1f}%")
    print(f"   Patient comfortable: {'Yes ✅' if session.patient_comfortable else 'No ⚠️'}")
    
    print("\n" + "=" * 70)
    print("✅ Session Execution System Ready!")
    print("=" * 70)
