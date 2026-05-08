"""
Dumbbell Deadlift V2 - Hip hinge exercise

NEW EXERCISE for posterior chain strength

Level: Intermediate
Category: Strength
Target: Hamstrings, glutes, lower back
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class DeadliftDumbbellV2:
    """
    Dumbbell Deadlift - Hip hinge movement
    
    Level: Intermediate
    Category: Strength
    Target: Hamstrings, glutes, erector spinae, core
    
    Reference Video: https://www.youtube.com/watch?v=lJ3QwaXNJfw
    (Dumbbell Deadlift Form - Proper Technique)
    
    Biomechanics:
    - Primary angle: Hip angle (shoulder → hip → knee)
    - Standing: 170-180° (fully extended hips)
    - Bottom: 90-110° (hinge at hips, not knees)
    - Knee angle: 165-175° (slight bend, not a squat; knee bending monitored)
    - Hip hinge depth tracked via shoulder→hip→knee angle
    
    CRITICAL: This is a HIP HINGE, not a squat
    - Movement comes from hips, not knees
    - Back stays straight (never rounds)
    - Knees stay nearly straight
    
    Phases:
    1. Standing (fully upright, hips extended)
    2. Hinging (pushing hips back)
    3. Bottom (dumbbells near ground, back straight)
    4. Rising (driving hips forward)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=lJ3QwaXNJfw"
    
    def __init__(self, target_reps=10):
        self.target_reps = target_reps
        self.rep_count = 0
        self.rejected_count = 0
        
        self.phase = "standing"
        self.last_phase = "standing"
        
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        self.form_scores = []
        self.current_rep_form_scores = []
        
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate hip and back angles"""
        # Joints
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        # Hip angle (shoulder → hip → knee) - PRIMARY for deadlift
        left_hip = analyzer.calculate_angle(ls, lh, lk)
        right_hip = analyzer.calculate_angle(rs, rh, rk)
        
        # NOTE: Spinal alignment cannot be measured with MediaPipe Pose
        # (no landmarks between shoulders and hips). Cues for "back
        # rounding" or thoracolumbar position are not implementable
        # with this hardware. Form analysis here is limited to:
        # knee tracking, depth, foot pressure proxies, hip-knee
        # alignment. Do not add cues that claim to measure spine
        # position without clear documentation of the proxy used.
        #
        # avg_back below is the hip flexion angle (shoulder→hip→knee),
        # NOT spinal curvature. It is retained only for form-score
        # weighting in FormCalculator; do not use it for safety warnings.
        left_back = analyzer.calculate_angle(ls, lh, lk)
        right_back = analyzer.calculate_angle(rs, rh, rk)
        
        # Knee angle (should stay nearly straight)
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
        
        # Smooth
        left_hip = analyzer.smooth_angle(left_hip, 'left')
        right_hip = analyzer.smooth_angle(right_hip, 'right')
        
        # Average
        avg_hip = (left_hip + right_hip) / 2
        avg_back = (left_back + right_back) / 2
        avg_knee = (left_knee + right_knee) / 2
        
        return {
            'left_hip': left_hip,
            'right_hip': right_hip,
            'avg_hip': avg_hip,
            'avg_back': avg_back,
            'avg_knee': avg_knee,
            'joints_coords': {
                'ls': ls, 'rs': rs,
                'lh': lh, 'rh': rh,
                'lk': lk, 'rk': rk,
                'la': la, 'ra': ra
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'standing': {
                'avg_hip': 175,    # Fully extended
                'avg_back': 170,   # Upright
                'avg_knee': 175,   # Nearly straight
                'tolerance': 10
            },
            'hinging': {
                'avg_hip': 130,    # Midway hinge
                'avg_back': 165,   # Still straight!
                'avg_knee': 170,   # Still nearly straight
                'tolerance': 12
            },
            'bottom': {
                'avg_hip': 100,    # Full hinge
                'avg_back': 165,   # MUST stay straight
                'avg_knee': 165,   # Slight bend
                'tolerance': 10
            },
            'rising': {
                'avg_hip': 140,    # Coming back up
                'avg_back': 165,
                'avg_knee': 170,
                'tolerance': 12
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form - CRITICAL: check back stays straight"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Hip angle (primary movement)
        hip_angle = angles.get('avg_hip', 0)
        hip_target = targets['avg_hip']
        
        if abs(hip_angle - hip_target) <= 12:
            feedback['hip'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=hip_angle,
                message="Good hip hinge"
            )
        else:
            feedback['hip'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=hip_angle,
                message="Adjust hip position"
            )
        
        # Knee angle (should NOT bend much)
        knee_angle = angles.get('avg_knee', 0)
        
        if knee_angle < 160:
            feedback['knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="This is not a squat"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good knee position"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update rep counter"""
        rep_done = False
        warnings = []
        
        # State machine based on HIP angle (not knee!)
        if self.phase == "standing" and angle < 165:
            self.phase = "hinging"
            self.tempo_detector.start_phase('hinging')
            voice.speak("Push hips back", priority=False)
        
        elif self.phase == "hinging" and angle < 115:
            self.phase = "bottom"
            self.tempo_detector.start_phase('bottom')
            voice.speak("Hold position", priority=False)
        
        elif self.phase == "bottom" and angle > 125:
            self.phase = "rising"
            self.tempo_detector.start_phase('rising')
            voice.speak("Drive hips forward", priority=False)
        
        elif self.phase == "rising" and angle > 165:
            # Rep complete
            rep_done = True
            self.phase = "standing"
            
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score"""
        if self.current_rep_form_scores:
            avg = sum(self.current_rep_form_scores) / len(self.current_rep_form_scores)
            self.current_rep_form_scores = []
            return avg
        return 85.0
    
    def _handle_rep_completion(self, form_score, voice):
        """Handle rep completion"""
        if self.probation_mode:
            if form_score >= 85:
                self.practice_reps_completed += 1
                voice.announce_practice_rep(
                    self.practice_reps_completed,
                    self.practice_reps_needed,
                    form_score
                )
                
                if self.practice_reps_completed >= self.practice_reps_needed:
                    self.probation_mode = False
                    voice.announce_phase_transition(from_practice_to_counted=True)
            else:
                self.rejected_count += 1
                voice.provide_ar_feedback(form_score)
        else:
            self.rep_count += 1
            self.form_scores.append(form_score)
            voice.announce_rep(self.rep_count, self.target_reps, form_score)
    
    def calculate_real_time_form_score(self, angles, joints_coords):
        """Calculate real-time form score"""
        self.stability_detector.update(joints_coords)
        
        target_angles = self.get_target_poses()[self.phase]
        stability_data = self.stability_detector.get_stability_data()
        tempo_data = self.tempo_detector.check_tempo()
        
        form_score = FormCalculator.calculate_form_score(
            angles=angles,
            target_angles=target_angles,
            stability=stability_data,
            tempo=tempo_data
        )
        
        self.current_rep_form_scores.append(form_score)

        return form_score

    def draw_ar_overlay(self, frame, angles, joints_coords, form_score):
        """Draw AR overlay"""
        if self.probation_mode:
            frame, _ = self.ar.draw_practice_mode(
                frame=frame,
                joints=joints_coords,
                current_angles=angles,
                target_angles=self.get_target_poses()[self.phase],
                form_score=form_score
            )
        else:
            frame = self.ar.draw_counted_mode(
                frame=frame,
                joints=joints_coords,
                form_score=form_score
            )
        
        return frame
    
    def get_stats(self):
        """Get statistics"""
        avg_form = (sum(self.form_scores) / len(self.form_scores) 
                   if self.form_scores else 0)
        
        return {
            'reps_completed': self.rep_count,
            'practice_reps': self.practice_reps_completed,
            'rejected_reps': self.rejected_count,
            'avg_form_score': round(avg_form, 1),
            'form_scores': self.form_scores,
            'target_reps': self.target_reps
        }


if __name__ == "__main__":
    print("DUMBBELL DEADLIFT V2 - Hip hinge exercise")
    print("Posterior chain strength training")
    print("CRITICAL: Back must stay straight!")
    print("Ready to run!")