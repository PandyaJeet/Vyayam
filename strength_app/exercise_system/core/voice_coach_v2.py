"""
Voice Coach V2 - FIXED VERSION (Correct Indentation)
Prevents "run loop already started" error with singleton pattern

FIXES:
1. Made pyttsx3 import optional
2. Proper indentation throughout
3. Graceful fallback if pyttsx3 not available
"""

# Try to import pyttsx3 (optional dependency)
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("⚠️  pyttsx3 not installed - voice coaching disabled")
    print("   Install with: pip install pyttsx3")

import threading
import queue
import time


class VoiceCoachV2:
    """
    Voice coaching system with atomic sentences and smooth transitions
    
    FIXED: Uses singleton pattern to prevent multiple TTS engine initializations
    FIXED: Made pyttsx3 optional - works even if not installed
    FIXED: Proper indentation throughout
    """
    
    # Class-level TTS engine (shared across all instances)
    _tts_engine = None
    _tts_lock = threading.Lock()
    _engine_initialized = False
    _voice_enabled = PYTTSX3_AVAILABLE  # Disabled if pyttsx3 not available
    
    @classmethod
    def _get_engine(cls):
        """Get or create the shared TTS engine (singleton pattern)"""
        if not cls._voice_enabled:
            return None
        
        with cls._tts_lock:
            if cls._tts_engine is None and not cls._engine_initialized:
                if PYTTSX3_AVAILABLE:
                    try:
                        cls._tts_engine = pyttsx3.init()
                        # Configure engine
                        cls._tts_engine.setProperty('rate', 150)
                        cls._tts_engine.setProperty('volume', 0.9)
                        cls._engine_initialized = True
                    except Exception as e:
                        print(f"⚠️  Voice coach disabled: {e}")
                        cls._voice_enabled = False
                        cls._tts_engine = None
                else:
                    print("⚠️  Voice coach disabled: pyttsx3 not installed")
                    cls._voice_enabled = False
                    cls._tts_engine = None
            
            return cls._tts_engine
    
    def __init__(self):
        """Initialize voice coach (does not create TTS engine yet)"""
        self.message_queue = queue.Queue()
        self.is_speaking = False
        
        # Don't start speech thread if voice is disabled
        if self._voice_enabled:
            self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
            self.speech_thread.start()
        else:
            self.speech_thread = None
    
    def _speech_worker(self):
        """Background thread for processing speech (only runs if voice enabled)"""
        if not self._voice_enabled:
            return
        
        engine = self._get_engine()
        if engine is None:
            return
        
        while True:
            try:
                message = self.message_queue.get(timeout=1)
                
                if message == "STOP":
                    break
                
                # Speak the message
                self.is_speaking = True
                try:
                    engine.say(message)
                    engine.runAndWait()
                except Exception as e:
                    print(f"⚠️  Speech error: {e}")
                finally:
                    self.is_speaking = False
                
                self.message_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️  Speech worker error: {e}")
    
    def say(self, message, priority=False):
        """Alias for speak() — 40 modules call voice.say(), which crashed
        with AttributeError (DA-EX-core)."""
        return self.speak(message, priority=priority)

    def speak(self, message, priority=False):
        """Queue a message for speech (silent if voice disabled).
        priority=True mirrors the old API — clears the queue first so this
        message plays immediately rather than waiting behind others.
        """
        if not self._voice_enabled:
            return
        if priority:
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                except Exception:
                    break
        if self.speech_thread and self.speech_thread.is_alive():
            self.message_queue.put(message)
    
    def speak_immediate(self, message):
        """Speak immediately, clearing queue (silent if voice disabled)"""
        if not self._voice_enabled:
            return
        
        # Clear queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
        
        # Add message
        self.speak(message)
    
    def clear_queue(self):
        """Clear all pending messages"""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
    
    def stop(self):
        """Stop the speech worker"""
        if self.speech_thread and self.speech_thread.is_alive():
            self.message_queue.put("STOP")
            self.speech_thread.join(timeout=2)
    
    # ========================================================================
    # REP COUNTING GUIDANCE
    # ========================================================================
    
    def announce_rep(self, rep_number, target_reps=None, form_score=None):
        """Announce rep completion with quality feedback.

        Every exercise module calls this as (rep_count, target_reps,
        form_score) with a NUMERIC score — the old (rep, 'green'|'yellow')
        2-arg form crashed all 234 modules with a TypeError on the first
        counted rep (DA-C3 follow-on find). Numeric scores map to quality
        bands: ≥85 green, ≥70 yellow, else red.
        """
        quality = form_score
        if isinstance(quality, (int, float)):
            quality = 'green' if quality >= 85 else ('yellow' if quality >= 70 else 'red')

        suffix = f" of {target_reps}" if target_reps else ""
        if quality == "green":
            self.speak(f"Rep {rep_number}{suffix}. Good form.")
        elif quality == "yellow":
            self.speak(f"Rep {rep_number}{suffix}. Watch your form.")
        else:  # red / unknown
            self.speak(f"Rep {rep_number}{suffix}. Poor form. Adjust.")
    
    def announce_set_complete(self, set_number, green_reps, total_reps):
        """Announce set completion"""
        if green_reps == total_reps:
            self.speak(f"Set {set_number} complete. All reps perfect!")
        elif green_reps >= total_reps * 0.8:
            self.speak(f"Set {set_number} complete. {green_reps} good reps. Great work!")
        else:
            self.speak(f"Set {set_number} complete. Focus on form next set.")
    
    def announce_rest(self, rest_seconds):
        """Announce rest period"""
        self.speak(f"Rest for {rest_seconds} seconds.")
    
    def announce_exercise_start(self, exercise_name):
        """Announce exercise start"""
        self.speak(f"Starting {exercise_name}. Get ready.")
    
    # ========================================================================
    # FORM CORRECTION GUIDANCE
    # ========================================================================
    
    def correct_form(self, issue):
        """Provide specific form correction"""
        corrections = {
            'depth': "Go deeper. Lower your hips more.",
            'knees': "Push your knees out. Don't let them cave in.",
            'back': "Keep your back straight. Chest up.",
            'tempo': "Slow down. Control the movement.",
            'stability': "Stay stable. Engage your core.",
            'heels': "Keep your heels down. Don't lift them.",
            'balance': "Find your balance. Take your time.",
            'range': "Full range of motion. Go all the way.",
        }
        
        message = corrections.get(issue, "Adjust your form.")
        self.speak(message)
    
    # ========================================================================
    # ENCOURAGEMENT & MOTIVATION
    # ========================================================================
    
    def encourage(self, phase="middle"):
        """Provide encouragement based on workout phase"""
        if phase == "start":
            messages = [
                "You've got this!",
                "Let's make it count!",
                "Focus and execute.",
            ]
        elif phase == "middle":
            messages = [
                "Keep it up!",
                "You're doing great!",
                "Stay strong!",
                "Excellent work!",
            ]
        else:  # finish
            messages = [
                "Almost there!",
                "Final push!",
                "Finish strong!",
            ]
        
        import random
        self.speak(random.choice(messages))
    
    # ========================================================================
    # PRACTICE MODE GUIDANCE
    # ========================================================================
    
    def guide_practice_mode(self):
        """Provide guidance for practice mode"""
        self.speak("Let's practice the movement. Watch the demo carefully.")
    
    def ask_can_do(self):
        """Ask if patient can do the exercise"""
        self.speak("Can you do this exercise?")
    
    def confirm_ready(self):
        """Confirm patient is ready"""
        self.speak("Ready? Let's begin.")
    
    # ========================================================================
    # COUNTDOWN & TIMING
    # ========================================================================
    
    def countdown(self, seconds):
        """Count down before starting"""
        for i in range(seconds, 0, -1):
            self.speak(str(i))
            time.sleep(1)
        self.speak("Go!")

    # ========================================================================
    # PRACTICE REP & PHASE TRANSITION GUIDANCE
    # ========================================================================

    def announce_practice_rep(self, rep_number, total_practice_reps, form_score=0):
        """Announce a practice rep (before counted reps begin)."""
        status = "Good form!" if form_score >= 85 else ("Almost there." if form_score >= 70 else "Focus on your form.")
        self.speak(f"Practice rep {rep_number} of {total_practice_reps}. {status}")

    def give_atomic_command(self, command_name, priority=False):
        """Give a short phase-transition command."""
        COMMANDS = {
            'start_descent': 'Lower down.',
            'start_lowering': 'Lower down.',
            'reached_bottom': 'Hold.',
            'start_ascent': 'Push up.',
            'start_rising': 'Rise up.',
            'start_flexing': 'Curl up.',
            'reached_top': 'Squeeze.',
            'extending': 'Lower slowly.',
            'start_extending': 'Extend.',
            'straight': 'Lock out.',
            'bent': 'Return.',
            'flexing': 'Pull in.',
            'hinging': 'Hinge at hips.',
            'rising': 'Drive through heels.',
            'lunge': 'Lower into lunge.',
            'airborne': 'Land softly.',
            'landing': 'Absorb the landing.',
            'hopping': 'Stay light.',
            'walking': 'Brace your core.',
            'crawling': 'Keep hips level.',
            'sprinting': 'Drive your arms.',
            'decelerating': 'Decelerate under control.',
            'loaded': 'Load the hips.',
            'skip_right': 'Skip right.',
            'skip_left': 'Skip left.',
            'plank': 'Brace.',
            'tapping': 'Control the tap.',
            'elevated': 'Drop controlled.',
        }
        message = COMMANDS.get(command_name, 'Continue.')
        self.speak(message, priority=priority)

    def announce_phase_transition(self, from_practice_to_counted=False):
        """Announce transition from practice reps to counted reps."""
        if from_practice_to_counted:
            self.speak("Great! Now counting your reps.")
        else:
            self.speak("Moving to next phase.")

    def provide_ar_feedback(self, form_score):
        """Provide voice feedback based on AR overlay form score."""
        if form_score >= 85:
            self.speak("Good form!")
        elif form_score >= 70:
            self.speak("Adjust your form slightly.")
        elif form_score >= 55:
            self.speak("Focus on your form.")
        else:
            self.speak("Stop and reset your form.", priority=True)