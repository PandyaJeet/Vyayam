"""
Form Calculator - Real-time form scoring system
Calculates actual form scores (not stuck at 100%)

SCORING BREAKDOWN:
- Angle Accuracy: 50% weight
- Stability: 30% weight  
- Tempo Control: 20% weight

Final Score: 0-100
"""

import numpy as np
from typing import Dict, Tuple, Optional


class FormCalculator:
    """
    Calculates real-time form scores based on multiple factors
    
    Usage:
        form_score = FormCalculator.calculate_form_score(
            angles={'avg_knee': 85},
            target_angles={'avg_knee': 90, 'tolerance': 8},
            stability={'wobble_amount': 2.5, 'wild_movement': False},
            tempo={'too_fast': False, 'too_slow': False}
        )
    """
    
    # Scoring thresholds
    ANGLE_PERFECT_THRESHOLD = 5      # Within 5° = perfect
    ANGLE_GOOD_THRESHOLD = 10        # Within 10° = good
    ANGLE_ACCEPTABLE_THRESHOLD = 15  # Within 15° = acceptable
    
    STABILITY_WOBBLE_THRESHOLD = 5   # Wobble amount threshold
    
    @staticmethod
    def calculate_angle_accuracy(angles: Dict[str, float],
                                 target_angles: Dict[str, float]) -> float:
        """
        Calculate angle accuracy score (0-100)
        
        Args:
            angles: Current measured angles {'avg_knee': 85, 'avg_hip': 95, ...}
            target_angles: Target angles {'avg_knee': 90, 'avg_hip': 100, 'tolerance': 8}
        
        Returns:
            Angle accuracy score 0-100
        """
        if not angles or not target_angles:
            return 100.0  # No angles to check = perfect by default
        
        angle_scores = []
        tolerance = target_angles.get('tolerance', 8)  # Custom tolerance or default
        
        for angle_name, target_value in target_angles.items():
            if angle_name == 'tolerance':
                continue  # Skip tolerance key

            current_value = angles.get(angle_name)

            if current_value is None:
                continue  # Skip if angle not measured

            if isinstance(target_value, bool) or isinstance(target_value, str):
                continue  # Boolean/string hints are not scoreable angles

            # Band target (lo, hi): for MOVING phases (descending/ascending)
            # the joint legitimately sweeps a range, so any angle inside the
            # band is correct and error is distance to the nearest bound.
            # Static phases keep scalar targets. (DA-C3)
            if isinstance(target_value, (tuple, list)):
                lo, hi = min(target_value), max(target_value)
                if lo <= current_value <= hi:
                    error = 0.0
                else:
                    error = lo - current_value if current_value < lo else current_value - hi
            else:
                # Calculate error
                error = abs(current_value - target_value)
            
            # DA-H1: piecewise curve parameterized by the exercise's OWN
            # tolerance, so a tighter tolerance means stricter scoring.
            # The old fixed 5/10/15° thresholds made any tolerance ≤ 15
            # meaningless (errors up to 15° always scored ≥ 70 even when
            # the exercise asked ±8) and the (tolerance - 15) divisor was
            # a degenerate slope for small tolerances.
            #
            #   error ≤ tol/4      → 100            (perfect zone)
            #   error ≤ tol        → 100 → 70 linear (acceptable)
            #   error ≤ 2·tol      → 70 → 30 linear  (poor)
            #   beyond 2·tol       → 30 → 0 at 3·tol (failing)
            tol = tolerance if tolerance and tolerance > 0 else 8.0
            perfect_zone = tol / 4.0

            if error <= perfect_zone:
                score = 100.0
            elif error <= tol:
                score = 100.0 - 30.0 * (error - perfect_zone) / (tol - perfect_zone)
            elif error <= 2 * tol:
                score = 70.0 - 40.0 * (error - tol) / tol
            else:
                score = max(0.0, 30.0 - 30.0 * (error - 2 * tol) / tol)

            angle_scores.append(score)
        
        # Average all angle scores
        if not angle_scores:
            return 100.0
        
        return sum(angle_scores) / len(angle_scores)
    
    @staticmethod
    def calculate_stability_score(stability_data: Dict) -> float:
        """
        Calculate stability score (0-100)
        
        Args:
            stability_data: {
                'wobble_amount': float (0-10, lower is better),
                'wild_movement': bool,
                'balance_lost': bool
            }
        
        Returns:
            Stability score 0-100
        """
        if not stability_data:
            return 100.0  # No stability data = perfect by default
        
        base_score = 100.0
        
        # Wobble penalty
        wobble_amount = stability_data.get('wobble_amount', 0)
        if wobble_amount > 0:
            # Each point of wobble = -10 points, capped
            wobble_penalty = min(wobble_amount * 10, 50)  # Max 50 point penalty
            base_score -= wobble_penalty
        
        # Wild movement penalty
        if stability_data.get('wild_movement', False):
            base_score -= 20  # Significant penalty for wild movements
        
        # Balance lost penalty
        if stability_data.get('balance_lost', False):
            base_score -= 30  # Major penalty for losing balance
        
        return max(0, base_score)
    
    @staticmethod
    def calculate_tempo_score(tempo_data: Dict) -> float:
        """
        Calculate tempo control score (0-100)
        
        Args:
            tempo_data: {
                'too_fast': bool,
                'too_slow': bool,
                'phase_time': float (optional - actual time in phase),
                'target_time': float (optional - target time for phase)
            }
        
        Returns:
            Tempo score 0-100
        """
        if not tempo_data:
            return 100.0  # No tempo data = perfect by default
        
        # Simple boolean checks
        too_fast = tempo_data.get('too_fast', False)
        too_slow = tempo_data.get('too_slow', False)
        
        if too_fast:
            return 60.0  # Going too fast = 60/100
        elif too_slow:
            return 80.0  # Going too slow = 80/100 (less penalty)
        
        # Optional: More precise tempo scoring if time data available
        phase_time = tempo_data.get('phase_time')
        target_time = tempo_data.get('target_time')
        
        if phase_time is not None and target_time is not None and target_time > 0:
            # Calculate timing accuracy
            time_ratio = phase_time / target_time
            
            # Ideal: 0.9 - 1.1 (within 10% of target)
            if 0.9 <= time_ratio <= 1.1:
                return 100.0
            
            # Good: 0.7 - 1.3 (within 30%)
            elif 0.7 <= time_ratio <= 1.3:
                return 90.0
            
            # Acceptable: 0.5 - 1.5
            elif 0.5 <= time_ratio <= 1.5:
                return 75.0
            
            # Poor: outside acceptable range
            else:
                return 60.0
        
        # Default: perfect tempo
        return 100.0
    
    @staticmethod
    def calculate_form_score(angles: Dict[str, float],
                            target_angles: Dict[str, float],
                            stability: Dict,
                            tempo: Dict) -> float:
        """
        MAIN METHOD: Calculate overall form score
        
        Args:
            angles: Current measured angles
            target_angles: Target angles for current phase
            stability: Stability measurements
            tempo: Tempo measurements
        
        Returns:
            Overall form score 0-100
        
        Example:
            >>> form_score = FormCalculator.calculate_form_score(
            ...     angles={'avg_knee': 88, 'avg_hip': 98},
            ...     target_angles={'avg_knee': 90, 'avg_hip': 100, 'tolerance': 8},
            ...     stability={'wobble_amount': 1.5, 'wild_movement': False},
            ...     tempo={'too_fast': False, 'too_slow': False}
            ... )
            >>> print(f"Form Score: {form_score:.1f}%")
            Form Score: 94.5%
        """
        
        # Calculate component scores
        angle_score = FormCalculator.calculate_angle_accuracy(angles, target_angles)
        stability_score = FormCalculator.calculate_stability_score(stability)
        tempo_score = FormCalculator.calculate_tempo_score(tempo)
        
        # Weighted average
        # Angle accuracy: 50%
        # Stability: 30%
        # Tempo: 20%
        final_score = (
            angle_score * 0.5 +
            stability_score * 0.3 +
            tempo_score * 0.2
        )
        
        # Clamp to 0-100
        final_score = max(0, min(100, final_score))
        
        return round(final_score, 1)
    
    @staticmethod
    def get_form_color(form_score: float) -> Tuple[int, int, int]:
        """
        Get color (BGR) based on form score for AR overlay
        
        Args:
            form_score: Score 0-100
        
        Returns:
            BGR color tuple
            
        GREEN (≥85): Excellent form
        YELLOW (70-84): Needs adjustment
        RED (<70): Incorrect form
        """
        if form_score >= 85:
            return (0, 255, 0)      # Green
        elif form_score >= 70:
            return (0, 255, 255)    # Yellow
        else:
            return (0, 0, 255)      # Red
    
    @staticmethod
    def get_form_feedback(form_score: float) -> str:
        """
        Get text feedback based on form score
        
        Args:
            form_score: Score 0-100
        
        Returns:
            Feedback string
        """
        if form_score >= 95:
            return "Perfect form!"
        elif form_score >= 85:
            return "Excellent"
        elif form_score >= 75:
            return "Good - minor adjustments"
        elif form_score >= 70:
            return "Watch your form"
        elif form_score >= 60:
            return "Fix form - significant issues"
        else:
            return "Stop - incorrect form"


# ============================================================================
# HELPER CLASS: Stability Detector
# ============================================================================

class StabilityDetector:
    """
    Detects stability issues from pose data
    Works with existing pose_analyzer
    """
    
    def __init__(self, history_size: int = 10):
        """
        Args:
            history_size: Number of frames to track for stability
        """
        self.joint_history = {}  # Track joint positions over time
        self.history_size = history_size
    
    def update(self, joints: Dict[str, Tuple[int, int]]):
        """
        Update joint history with new frame
        
        Args:
            joints: Current joint positions {'lk': (x, y), 'rk': (x, y), ...}
        """
        for joint_name, position in joints.items():
            if joint_name not in self.joint_history:
                self.joint_history[joint_name] = []
            
            self.joint_history[joint_name].append(position)
            
            # Keep only recent history
            if len(self.joint_history[joint_name]) > self.history_size:
                self.joint_history[joint_name].pop(0)
    
    def calculate_wobble(self, joint_name: str = 'lk') -> float:
        """
        Calculate wobble amount for a joint
        
        Args:
            joint_name: Joint to check (default: left knee)
        
        Returns:
            Wobble amount 0-10 (lower is more stable)
        """
        if joint_name not in self.joint_history:
            return 0.0
        
        history = self.joint_history[joint_name]
        
        if len(history) < 3:
            return 0.0  # Not enough data
        
        # Calculate standard deviation of positions
        positions = np.array(history)
        x_std = np.std(positions[:, 0])
        y_std = np.std(positions[:, 1])
        
        # Average standard deviation
        avg_std = (x_std + y_std) / 2
        
        # Scale to 0-10 range (rough calibration)
        # 0-5 pixels = stable (score 0-2)
        # 5-15 pixels = moderate wobble (score 2-5)
        # 15+ pixels = high wobble (score 5-10)
        wobble_score = min(avg_std / 3, 10)
        
        return wobble_score
    
    def check_wild_movement(self, threshold: float = 50) -> bool:
        """
        Check if any joint moved wildly between frames
        
        Args:
            threshold: Pixel movement threshold
        
        Returns:
            True if wild movement detected
        """
        for joint_name, history in self.joint_history.items():
            if len(history) < 2:
                continue
            
            # Check last two positions
            prev_pos = np.array(history[-2])
            curr_pos = np.array(history[-1])
            
            # Calculate distance moved
            distance = np.linalg.norm(curr_pos - prev_pos)
            
            if distance > threshold:
                return True  # Wild movement detected
        
        return False
    
    def get_stability_data(self) -> Dict:
        """
        Get complete stability data for form calculator
        
        Returns:
            Dict with stability metrics
        """
        # Calculate wobble for key joints
        knee_wobble = self.calculate_wobble('lk')
        hip_wobble = self.calculate_wobble('lh')
        
        avg_wobble = (knee_wobble + hip_wobble) / 2
        
        return {
            'wobble_amount': avg_wobble,
            'wild_movement': self.check_wild_movement(),
            'balance_lost': False  # Set externally if balance lost
        }


# ============================================================================
# HELPER CLASS: Tempo Detector
# ============================================================================

class TempoDetector:
    """
    Detects if exercise tempo is correct
    Works with phase tracking
    """
    
    def __init__(self):
        self.phase_start_time = None
        self.current_phase = None
        self.phase_durations = {
            'descending': (2.0, 4.0),  # Min 2s, max 4s
            'bottom': (0.5, 2.0),      # Min 0.5s, max 2s
            'ascending': (1.5, 3.0),   # Min 1.5s, max 3s
            'holding': None            # No time limit for static holds
        }
    
    def get_phase_duration(self) -> float:
        """Seconds elapsed in the current phase (0.0 before any phase).

        DA-EX-core: 13 modules call this; it did not exist — AttributeError
        on every rep of those exercises.
        """
        import time
        if self.phase_start_time is None:
            return 0.0
        return time.time() - self.phase_start_time

    def start_phase(self, phase_name: str):
        """
        Mark start of new phase

        Args:
            phase_name: Phase name ('descending', 'bottom', 'ascending', 'holding')
        """
        import time
        self.phase_start_time = time.time()
        self.current_phase = phase_name
    
    def check_tempo(self) -> Dict:
        """
        Check if current tempo is correct
        
        Returns:
            Tempo data dict for form calculator
        """
        if self.phase_start_time is None or self.current_phase is None:
            return {'too_fast': False, 'too_slow': False}
        
        import time
        elapsed = time.time() - self.phase_start_time
        
        # Get target duration for this phase
        duration_range = self.phase_durations.get(self.current_phase)
        
        if duration_range is None:
            # No tempo check for this phase
            return {'too_fast': False, 'too_slow': False}
        
        min_duration, max_duration = duration_range
        
        # Check if too fast or too slow
        too_fast = elapsed < min_duration and elapsed > 0.5  # Give 0.5s grace
        too_slow = elapsed > max_duration
        
        return {
            'too_fast': too_fast,
            'too_slow': too_slow,
            'phase_time': elapsed,
            'target_time': (min_duration + max_duration) / 2
        }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("FORM CALCULATOR EXAMPLES")
    print("="*70)
    
    # Example 1: Perfect form
    print("\n1. PERFECT FORM")
    print("-" * 70)
    
    form_score = FormCalculator.calculate_form_score(
        angles={'avg_knee': 90, 'avg_hip': 100},
        target_angles={'avg_knee': 90, 'avg_hip': 100, 'tolerance': 8},
        stability={'wobble_amount': 0.5, 'wild_movement': False},
        tempo={'too_fast': False, 'too_slow': False}
    )
    
    color = FormCalculator.get_form_color(form_score)
    feedback = FormCalculator.get_form_feedback(form_score)
    
    print(f"Form Score: {form_score}%")
    print(f"Color: {'GREEN' if color == (0, 255, 0) else 'YELLOW' if color == (0, 255, 255) else 'RED'}")
    print(f"Feedback: {feedback}")
    
    # Example 2: Good form with slight wobble
    print("\n2. GOOD FORM (slight wobble)")
    print("-" * 70)
    
    form_score = FormCalculator.calculate_form_score(
        angles={'avg_knee': 88, 'avg_hip': 98},
        target_angles={'avg_knee': 90, 'avg_hip': 100, 'tolerance': 8},
        stability={'wobble_amount': 2.5, 'wild_movement': False},
        tempo={'too_fast': False, 'too_slow': False}
    )
    
    color = FormCalculator.get_form_color(form_score)
    feedback = FormCalculator.get_form_feedback(form_score)
    
    print(f"Form Score: {form_score}%")
    print(f"Color: {'GREEN' if color == (0, 255, 0) else 'YELLOW' if color == (0, 255, 255) else 'RED'}")
    print(f"Feedback: {feedback}")
    
    # Example 3: Needs adjustment (yellow)
    print("\n3. NEEDS ADJUSTMENT (angles off, going too fast)")
    print("-" * 70)
    
    form_score = FormCalculator.calculate_form_score(
        angles={'avg_knee': 78, 'avg_hip': 95},  # 12° off
        target_angles={'avg_knee': 90, 'avg_hip': 100, 'tolerance': 8},
        stability={'wobble_amount': 1.0, 'wild_movement': False},
        tempo={'too_fast': True, 'too_slow': False}
    )
    
    color = FormCalculator.get_form_color(form_score)
    feedback = FormCalculator.get_form_feedback(form_score)
    
    print(f"Form Score: {form_score}%")
    print(f"Color: {'GREEN' if color == (0, 255, 0) else 'YELLOW' if color == (0, 255, 255) else 'RED'}")
    print(f"Feedback: {feedback}")
    
    # Example 4: Incorrect form (red)
    print("\n4. INCORRECT FORM (way off + wild movement)")
    print("-" * 70)
    
    form_score = FormCalculator.calculate_form_score(
        angles={'avg_knee': 65, 'avg_hip': 85},  # 25° off
        target_angles={'avg_knee': 90, 'avg_hip': 100, 'tolerance': 8},
        stability={'wobble_amount': 6.0, 'wild_movement': True},
        tempo={'too_fast': True, 'too_slow': False}
    )
    
    color = FormCalculator.get_form_color(form_score)
    feedback = FormCalculator.get_form_feedback(form_score)
    
    print(f"Form Score: {form_score}%")
    print(f"Color: {'GREEN' if color == (0, 255, 0) else 'YELLOW' if color == (0, 255, 255) else 'RED'}")
    print(f"Feedback: {feedback}")
    
    print("\n" + "="*70)