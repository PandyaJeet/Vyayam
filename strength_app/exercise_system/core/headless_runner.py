"""
HeadlessExerciseRunner
NO Streamlit
NO UI
Pure OpenCV + AR + Voice

FIXED: Corrected class names VoiceCoachV2 and AROverlayV2
"""

import cv2
import time
from .pose_analyzer import PoseAnalyzer
from .voice_coach_v2 import VoiceCoachV2  # ✅ FIXED: Was VoiceCoach
from .visual_overlay import JointHighlighter
from .ar_overlay_v2 import AROverlayV2  # ✅ FIXED: Was AROverlaySystem
from .data_models import FormStatus


class HeadlessExerciseRunner:
    def __init__(self, exercise, enable_voice=True):
        self.exercise = exercise
        self.voice = VoiceCoachV2() if enable_voice else None  # ✅ FIXED: Was VoiceCoach()

        self.analyzer = PoseAnalyzer()
        self.highlighter = JointHighlighter()
        self.ar_system = AROverlayV2()  # ✅ FIXED: Was AROverlaySystem()

        self.start_time = None

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Camera not accessible")

        self.start_time = time.time()
        frame_count = 0
        
        # Announce exercise start
        if self.voice:
            exercise_name = self.exercise.__class__.__name__.replace('V2', '').replace('V1', '')
            # Convert CamelCase to Title Case
            import re
            exercise_name = re.sub(r'([A-Z])', r' \1', exercise_name).strip()
            self.voice.start_exercise(exercise_name, self.exercise.target_reps)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_count += 1

            results = self.analyzer.detect_pose(frame)

            if results.pose_landmarks:
                angles = self.exercise.calculate_angles(
                    self.analyzer, results, frame.shape
                )

                feedback = self.exercise.validate_form(
                    angles, self.exercise.phase
                )

                rep_done, phase, warnings = self._update_rep_counter(
                    angles, feedback
                )

                joints = angles.get("joints_coords", {})

                if self.exercise.probation_mode:
                    targets = self.exercise.get_target_poses().get(self.exercise.phase, {})
                    # Calculate form score for AR coloring
                    form_score = getattr(self.exercise, 'calculate_real_time_form_score', lambda a, j: 85)(angles, joints)
                    frame, position_matched = self.ar_system.draw_practice_mode(
                        frame, joints, angles, targets, form_score
                    )
                else:
                    # Calculate form score for AR coloring
                    form_score = getattr(self.exercise, 'calculate_real_time_form_score', lambda a, j: 85)(angles, joints)
                    frame = self.ar_system.draw_counted_mode(
                        frame, joints, form_score
                    )

                self.highlighter.draw_feedback(frame, feedback, warnings)

                if rep_done and self.exercise.rep_count >= self.exercise.target_reps:
                    break

            cv2.imshow("VYAYAM Exercise", frame)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break

        cap.release()
        cv2.destroyAllWindows()

        duration = time.time() - self.start_time

        return {
            "reps": self.exercise.rep_count,
            "duration": round(duration, 2),
            "rejected": self.exercise.rejected_count,
            "practice_completed": not self.exercise.probation_mode,
        }

    def _get_primary_angle(self, angles):
        for v in angles.values():
            if isinstance(v, (int, float)):
                return v
        return 0

    def _update_rep_counter(self, angles, feedback):
        """Dispatch across the two update_rep_counter conventions.

        ~190 modules take a scalar primary angle; ~30 take the full
        angles dict (DA-EX-core: passing the scalar to those crashed with
        \"'float' object has no attribute 'get'\" on every frame).
        """
        import inspect
        try:
            params = list(inspect.signature(
                self.exercise.update_rep_counter).parameters)
        except (TypeError, ValueError):
            params = []
        wants_dict = bool(params) and params[0] in ('angles', 'angle_dict')
        first_arg = angles if wants_dict else self._get_primary_angle(angles)
        if len(params) >= 3:
            return self.exercise.update_rep_counter(first_arg, feedback, self.voice)
        return self.exercise.update_rep_counter(first_arg, feedback)