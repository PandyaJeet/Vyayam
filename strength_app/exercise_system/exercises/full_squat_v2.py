"""
Full Squats V2 - Deep squat exercise

NEW EXERCISE for advanced strength training

Level: Intermediate-Advanced
Category: Strength
Target: Quadriceps, glutes, hamstrings, core
"""

import cv2
import time
from ..core.pose_analyzer import PoseAnalyzer
from ..core.voice_coach_v2 import VoiceCoachV2
from ..core.ar_overlay_v2 import AROverlayV2
from ..core.form_calculator import FormCalculator, StabilityDetector, TempoDetector
from ..core.data_models import FormStatus, JointFeedback


class FullSquatsV2:
    """
    Full Squats - Deep squat to 90° or below
    
    Level: Intermediate-Advanced
    Category: Strength
    Target: Quadriceps, glutes, hamstrings, core stability
    
    Reference Video: https://www.youtube.com/watch?v=aclHkVaku9U
    (Full Squat Technique - Proper Form Tutorial)
    
    Biomechanics:
    - Primary angle: Knee flexion (hip → knee → ankle)
    - Standing: 170-180° (nearly straight)
    - Target depth: 85-95° (full depth, thighs parallel or below)
    - Hip angle: <90° at bottom
    - Knee tracking: valgus (inward collapse) monitored via knee-over-ankle alignment
    
    Key differences from Partial Squats:
    - Deeper range of motion (90° vs 120°)
    - Requires better mobility and strength
    - Higher difficulty level
    
    Phases:
    1. Standing (ready position)
    2. Descending (controlled descent)
    3. Bottom (hold at full depth)
    4. Ascending (drive back up)
    """
    
    # YouTube reference video
    REFERENCE_VIDEO_URL = "https://www.youtube.com/watch?v=aclHkVaku9U"
    
    def __init__(self, target_reps=10, target_depth=90):
        # Exercise parameters
        self.target_reps = target_reps
        self.target_depth = target_depth  # 85-95° for full squats
        self.rep_count = 0
        self.rejected_count = 0
        
        # Phase tracking
        self.phase = "standing"
        self.last_phase = "standing"
        
        # Practice mode
        self.probation_mode = True
        self.practice_reps_needed = 3
        self.practice_reps_completed = 0
        
        # Form tracking
        self.form_scores = []
        self.current_rep_form_scores = []
        
        # Detectors
        self.stability_detector = StabilityDetector(history_size=10)
        self.tempo_detector = TempoDetector()
        
        # Voice and AR
        self.voice = VoiceCoachV2()
        self.ar = AROverlayV2()
        # Exercise announcement moved to runner
    def calculate_angles(self, analyzer, results, shape):
        """Calculate knee and back angles"""
        # Extract joints
        lh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_HIP, shape)
        lk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_KNEE, shape)
        la = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_ANKLE, shape)
        
        rh = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_HIP, shape)
        rk = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_KNEE, shape)
        ra = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_ANKLE, shape)
        
        ls = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.LEFT_SHOULDER, shape)
        rs = analyzer.get_coords(results, analyzer.mp_pose.PoseLandmark.RIGHT_SHOULDER, shape)
        
        # Calculate angles
        left_knee = analyzer.calculate_angle(lh, lk, la)
        right_knee = analyzer.calculate_angle(rh, rk, ra)
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

        # Smooth
        left_knee = analyzer.smooth_angle(left_knee, 'left')
        right_knee = analyzer.smooth_angle(right_knee, 'right')

        # Average
        avg_knee = (left_knee + right_knee) / 2
        avg_back = (left_back + right_back) / 2  # hip flexion angle — see note above
        
        return {
            'left_knee': left_knee,
            'right_knee': right_knee,
            'avg_knee': avg_knee,
            'avg_back': avg_back,
            'joints_coords': {
                'lh': lh, 'lk': lk, 'la': la,
                'rh': rh, 'rk': rk, 'ra': ra,
                'ls': ls, 'rs': rs
            }
        }
    
    def get_target_poses(self):
        """Target angles for each phase"""
        return {
            'standing': {
                'avg_knee': 175,
                'avg_back': 165,
                'tolerance': 10
            },
            'descending': {
                'avg_knee': 130,
                'avg_back': 160,
                'tolerance': 15
            },
            'bottom': {
                'avg_knee': self.target_depth,  # 90° full depth
                'avg_back': 155,
                'tolerance': 10
            },
            'ascending': {
                'avg_knee': 140,
                'avg_back': 160,
                'tolerance': 15
            }
        }
    
    def validate_form(self, angles, phase):
        """Validate form"""
        feedback = {}
        targets = self.get_target_poses()[phase]
        
        # Knee angle
        knee_angle = angles.get('avg_knee', 0)
        knee_target = targets['avg_knee']
        knee_tolerance = targets['tolerance']
        
        if abs(knee_angle - knee_target) <= knee_tolerance:
            feedback['knee'] = JointFeedback(
                status=FormStatus.CORRECT,
                angle=knee_angle,
                message="Good depth"
            )
        elif abs(knee_angle - knee_target) <= knee_tolerance * 1.5:
            feedback['knee'] = JointFeedback(
                status=FormStatus.NEEDS_ADJUSTMENT,
                angle=knee_angle,
                message="Adjust depth"
            )
        else:
            feedback['knee'] = JointFeedback(
                status=FormStatus.INCORRECT,
                angle=knee_angle,
                message="Check depth"
            )
        
        return feedback
    
    def update_rep_counter(self, angle, feedback, voice):
        """Update rep counter with state machine"""
        rep_done = False
        warnings = []
        
        # State machine
        if self.phase == "standing" and angle < 160:
            self.phase = "descending"
            self.tempo_detector.start_phase('descending')
            voice.give_atomic_command('start_descent', priority=False)
        
        elif self.phase == "descending" and angle < (self.target_depth + 10):
            self.phase = "bottom"
            self.tempo_detector.start_phase('bottom')
            voice.give_atomic_command('reached_bottom', priority=False)
        
        elif self.phase == "bottom" and angle > (self.target_depth + 20):
            self.phase = "ascending"
            self.tempo_detector.start_phase('ascending')
            voice.give_atomic_command('start_ascent', priority=False)
        
        elif self.phase == "ascending" and angle > 165:
            # Rep complete
            rep_done = True
            self.phase = "standing"
            
            form_score = self._calculate_rep_form_score()
            self._handle_rep_completion(form_score, voice)
        
        if self.phase != self.last_phase:
            self.last_phase = self.phase
        
        return rep_done, self.phase, warnings
    
    def _calculate_rep_form_score(self):
        """Calculate form score for completed rep"""
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
    print("FULL SQUATS V2 - Deep squat exercise (90° depth)")
    print("Advanced strength training")
    print("Ready to run!")