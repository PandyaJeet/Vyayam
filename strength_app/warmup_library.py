"""
VYAYAM V1 - Warm-up and Cool-down Exercise Library
Structured by the 5-phase session model: Elevate → Mobilise → Activate → Prime → [Work] → Cool-down
"""

# ============================================================================
# PHASE 1: ELEVATE (raise core temperature, 3-5 min)
# ============================================================================

ELEVATE_EXERCISES = [
    {
        'id': 'marching_on_spot',
        'name': 'Marching on Spot',
        'duration_seconds': 60,
        'equipment': 'none',
        'instructions': 'March in place with high knees, pumping arms. Gradually increase pace.',
        'cues': ['Drive knees to hip height', 'Pump arms opposite to legs', 'Stay on balls of feet'],
    },
    {
        'id': 'jumping_jacks_light',
        'name': 'Jumping Jacks (Light)',
        'duration_seconds': 60,
        'equipment': 'none',
        'instructions': 'Standard jumping jacks at an easy, controlled pace. Land softly.',
        'cues': ['Soft landing - bend knees on contact', 'Arms reach above head fully', 'Controlled rhythm, no rushing'],
    },
    {
        'id': 'arm_circles_large',
        'name': 'Large Arm Circles',
        'duration_seconds': 45,
        'equipment': 'none',
        'instructions': 'Stand tall, extend arms out to sides. Make the largest circles possible, 10 forward then 10 backward.',
        'cues': ['Full shoulder range - reach back behind you', 'Keep neck relaxed', 'Gradually increase speed each rep'],
    },
    {
        'id': 'skip_in_place',
        'name': 'Skip in Place',
        'duration_seconds': 45,
        'equipment': 'none',
        'instructions': 'Skip in place with an exaggerated arm swing. Light and bouncy.',
        'cues': ['Light heel kick back on each skip', 'Tall posture - do not hunch', 'Rhythmic and relaxed'],
    },
    {
        'id': 'butt_kicks_light',
        'name': 'Butt Kicks (Light)',
        'duration_seconds': 45,
        'equipment': 'none',
        'instructions': 'Jog in place, kicking heels up toward glutes with each step. Easy pace.',
        'cues': ['Keep hips under you - do not lean forward', 'Light arm swing', 'Focus on the hamstring contraction'],
    },
    {
        'id': 'high_knees_light',
        'name': 'High Knees (Light)',
        'duration_seconds': 45,
        'equipment': 'none',
        'instructions': 'Jog in place driving knees to waist height at a comfortable pace.',
        'cues': ['Knees to waist - not just ankle flicks', 'Stay on balls of feet', 'Upright torso'],
    },
    {
        'id': 'lateral_shuffle',
        'name': 'Lateral Shuffle',
        'duration_seconds': 60,
        'equipment': 'none',
        'instructions': 'Step-shuffle side to side over a 2–3 metre distance, staying low in a quarter-squat. Keep weight on balls of feet.',
        'cues': ['Hip-width stance throughout', 'Do NOT cross feet', 'Low hips - think athletic stance'],
    },
    {
        'id': 'star_jumps_light',
        'name': 'Star Jumps (Light)',
        'duration_seconds': 45,
        'equipment': 'none',
        'instructions': 'Jump feet out and arms overhead simultaneously, then return. Slower and lower intensity than full star jumps.',
        'cues': ['Soft knees on landing', 'Arms fully extended overhead at top', 'Controlled pace - this is a warm-up'],
    },
]

# ============================================================================
# PHASE 2: MOBILISE (CARs and joint prep, 4-6 min)
# Mapped to movement patterns - system selects based on today's session
# ============================================================================

MOBILISE_EXERCISES = {
    'squat_day': [
        {
            'id': 'hip_cars',
            'name': 'Hip CARs',
            'reps': 5,
            'side': 'each',
            'instructions': 'Standing, lift knee to hip height, rotate outward in largest circle possible, return. Reverse direction.',
            'cues': ['Biggest circle possible', 'Pelvis stays still', 'Control the entire range'],
        },
        {
            'id': 'ankle_circles',
            'name': 'Ankle Circles',
            'reps': 10,
            'side': 'each',
            'instructions': 'Seated or standing on one foot. Draw the largest circle possible with your toes. 10 clockwise, 10 anti-clockwise per ankle.',
            'cues': ['Move from the ankle - not the whole leg', 'Full range: point and flex fully', 'Slow and deliberate'],
        },
        {
            'id': '90_90_hip_switch',
            'name': '90/90 Hip Switch',
            'reps': 5,
            'side': 'each',
            'instructions': 'Sit on floor, both knees bent at 90°. Rotate hips to switch legs from one 90/90 position to the other. Keep torso upright.',
            'cues': ['Transition slowly', 'Both knees try to reach the floor', 'Tall spine throughout'],
        },
        {
            'id': 'thoracic_rotation_seated',
            'name': 'Thoracic Rotation (Seated)',
            'reps': 8,
            'side': 'each',
            'instructions': 'Sit cross-legged or on a chair. Place hands on opposite shoulders. Rotate upper body as far as possible each side without moving hips.',
            'cues': ['Hips stay square', 'Look as far as you rotate', 'Exhale as you rotate'],
        },
    ],
    'hinge_day': [
        {
            'id': 'hip_cars_hinge',
            'name': 'Hip CARs',
            'reps': 5,
            'side': 'each',
            'instructions': 'Standing, lift knee to hip height, rotate outward in largest circle possible, return. Reverse direction.',
            'cues': ['Biggest circle possible', 'Pelvis stays still', 'Control the entire range'],
        },
        {
            'id': 'cat_cow',
            'name': 'Cat–Cow',
            'reps': 8,
            'side': None,
            'instructions': 'On hands and knees. Inhale - drop belly, lift head and tailbone (Cow). Exhale - round spine fully, tuck chin and pelvis (Cat). Move slowly.',
            'cues': ['Full range in both directions', 'Breathe drives the movement', 'Feel each segment of the spine move'],
        },
        {
            'id': 'hip_flexor_rock',
            'name': 'Hip Flexor Rock',
            'reps': 8,
            'side': 'each',
            'instructions': 'In a half-kneeling lunge position. Gently rock forward until you feel a stretch in the front of the back-leg hip. Rock back. Repeat.',
            'cues': ['Tuck tailbone under (posterior pelvic tilt)', 'Forward knee stays over toes', 'Keep torso upright'],
        },
        {
            'id': 'hamstring_nerve_floss',
            'name': 'Hamstring Nerve Floss',
            'reps': 8,
            'side': 'each',
            'instructions': 'Seated on edge of chair or floor. Extend one leg out. Flex foot toward you and straighten knee, then point foot and bend knee. Slow alternation.',
            'cues': ['This is NOT a stretch - it is a nerve glide', 'Move within comfortable range', 'If sharp pain, reduce range'],
        },
    ],
    'push_pull_day': [
        {
            'id': 'shoulder_cars',
            'name': 'Shoulder CARs',
            'reps': 5,
            'side': 'each direction',
            'instructions': 'Standing, one arm at a time. Slowly rotate arm through the largest possible circle: forward, overhead, behind, back down. Reverse.',
            'cues': ['Maximum range in every position', 'Other hand on shoulder to feel any hitching', 'Slow and controlled - 5 seconds per revolution'],
        },
        {
            'id': 'wrist_circles',
            'name': 'Wrist Circles',
            'reps': 10,
            'side': 'each',
            'instructions': 'Extend arms forward, make fists. Rotate wrists in full circles - 10 clockwise, 10 anti-clockwise.',
            'cues': ['Full range - avoid shortcuts at the top and bottom', 'Forearms stay still', 'Follow with finger extension stretches'],
        },
        {
            'id': 'thoracic_rotation',
            'name': 'Thoracic Rotation (Side-lying)',
            'reps': 8,
            'side': 'each',
            'instructions': 'Side-lying, knees bent and stacked at 90°. Top arm reaches across chest then opens fully to the back, following with your eyes. Return.',
            'cues': ['Knees stay stacked - only upper body rotates', 'Follow your hand with your gaze', 'Breathe out as you open'],
        },
        {
            'id': 'neck_semicircle',
            'name': 'Neck Semicircle',
            'reps': 5,
            'side': 'each',
            'instructions': 'Standing tall. Slowly drop right ear to right shoulder, roll chin down to chest, then to left shoulder. Do NOT roll head backward.',
            'cues': ['Gravity does the work - no forcing', 'Front semicircle ONLY - no backward roll', 'Slow: 5 seconds each arc'],
        },
    ],
    'lunge_day': [
        {
            'id': 'hip_cars_lunge',
            'name': 'Hip CARs',
            'reps': 5,
            'side': 'each',
            'instructions': 'Standing, lift knee to hip height, rotate outward in largest circle possible, return. Reverse direction.',
            'cues': ['Biggest circle possible', 'Pelvis stays still', 'Control the entire range'],
        },
        {
            'id': 'ankle_circles_lunge',
            'name': 'Ankle Circles',
            'reps': 10,
            'side': 'each',
            'instructions': 'Seated or standing on one foot. Draw the largest circle possible with your toes.',
            'cues': ['Move from the ankle - not the whole leg', 'Full range: point and flex fully', 'Slow and deliberate'],
        },
        {
            'id': 'lateral_hip_opener',
            'name': 'Lateral Hip Opener',
            'reps': 8,
            'side': 'each',
            'instructions': 'Stand with feet wide. Lunge to one side, bending that knee and keeping the opposite leg straight. Shift side to side.',
            'cues': ['Bent-knee foot stays flat', 'Straight-leg toes point forward or slightly up', 'Slow shift, pause at end range'],
        },
        {
            'id': 'adductor_rock',
            'name': 'Adductor Rock',
            'reps': 8,
            'side': 'each',
            'instructions': 'On all fours, extend one leg straight to the side, toes on floor. Rock your hips back toward your heel, feeling inner thigh stretch. Rock forward.',
            'cues': ['Leg stays straight', 'Keep hips level', 'Rock slowly - feel the inner thigh lengthen'],
        },
    ],
    'rotate_day': [
        {
            'id': 'thoracic_rotation_rotate',
            'name': 'Thoracic Rotation (Side-lying)',
            'reps': 8,
            'side': 'each',
            'instructions': 'Side-lying, knees bent at 90°. Top arm opens fully to the back. Return.',
            'cues': ['Knees stay stacked', 'Follow your hand with your gaze', 'Breathe out as you open'],
        },
        {
            'id': 'hip_cars_rotate',
            'name': 'Hip CARs',
            'reps': 5,
            'side': 'each',
            'instructions': 'Standing, rotate hip through the largest circle possible in both directions.',
            'cues': ['Biggest circle possible', 'Pelvis stays still', 'Control the entire range'],
        },
        {
            'id': 'cat_cow_rotate',
            'name': 'Cat–Cow',
            'reps': 8,
            'side': None,
            'instructions': 'On hands and knees. Inhale - drop belly (Cow). Exhale - round spine fully (Cat).',
            'cues': ['Full range both ways', 'Breath drives the movement', 'Feel every spinal segment'],
        },
        {
            'id': 'lateral_flexion',
            'name': 'Lateral Flexion',
            'reps': 8,
            'side': 'each',
            'instructions': 'Stand tall, feet hip-width. Reach one arm overhead and bend sideways, sliding opposite hand down the leg. Return. Alternate sides.',
            'cues': ['Do not lean forward or back - pure side bend', 'Reach up and over - elongate first', 'Breathe out at end range'],
        },
    ],
}

# ============================================================================
# PHASE 3: ACTIVATE (wake up inhibited muscles, 4-5 min)
# Selected based on strength profile weaknesses
# ============================================================================

ACTIVATE_EXERCISES = {
    'glute_activation': [
        {
            'id': 'clamshell_activation',
            'name': 'Clamshells (Activation)',
            'sets': 2, 'reps': 12, 'side': 'each',
            'instructions': 'Side-lying, knees bent 90°, open top knee without rolling pelvis.',
            'cues': ['Feel the squeeze in outer glute', 'Pelvis does NOT roll back', 'Slow and controlled'],
            'when': 'Before any hinge, squat, or lunge session',
        },
        {
            'id': 'glute_bridge_activation',
            'name': 'Glute Bridge (Activation)',
            'sets': 2, 'reps': 10, 'side': None,
            'instructions': 'Lie on back, feet flat, hip-width. Drive hips up, squeeze glutes at top for 2 seconds. Lower with control.',
            'cues': ['Squeeze HARD at the top', 'Don\'t arch lower back - ribs stay down', '2-second hold every rep'],
            'when': 'Before any hinge, squat, or lunge session',
        },
        {
            'id': 'side_lying_hip_abduction',
            'name': 'Side-Lying Hip Abduction (Activation)',
            'sets': 2, 'reps': 10, 'side': 'each',
            'instructions': 'Side-lying, body in a straight line. Lift top leg to 45° with toes pointing slightly down, then lower.',
            'cues': ['Toes point slightly toward floor (not ceiling)', 'Pelvis stays still - no rolling', 'Feel it in outer hip, not lower back'],
            'when': 'Before any squat, lunge, or hinge session',
        },
        {
            'id': 'fire_hydrant',
            'name': 'Fire Hydrant (Activation)',
            'sets': 2, 'reps': 10, 'side': 'each',
            'instructions': 'On all fours. Lift one knee out to the side (like a dog at a fire hydrant) keeping the knee bent at 90°. Lower with control.',
            'cues': ['Hips stay square - do NOT rotate', 'Feel the outer glute working', 'Slow on the way down'],
            'when': 'Before any squat, lunge, or hinge session',
        },
    ],
    'vmo_activation': [
        {
            'id': 'tke_activation',
            'name': 'Terminal Knee Extension (Activation)',
            'sets': 2, 'reps': 15,
            'side': None,
            'instructions': 'Band around knee, slight bend, press knee to full extension.',
            'cues': ['Feel the muscle just above inner knee', 'Full lockout', 'Hold 1 second at top'],
            'when': 'Before any squat or lunge session',
        },
        {
            'id': 'vmo_squeeze_seated',
            'name': 'VMO Squeeze (Seated)',
            'sets': 2, 'reps': 10, 'side': None,
            'instructions': 'Sit on chair, feet flat. Place a rolled towel or small ball between knees. Squeeze for 3 seconds, release.',
            'cues': ['Feel the squeeze at inner lower quad', '3-second hold every rep', 'Do not hold breath'],
            'when': 'Before any squat or lunge session',
        },
    ],
    'scapular_activation': [
        {
            'id': 'prone_y_t_w_activation',
            'name': 'Prone Y-T-W (Activation)',
            'sets': 1, 'reps': 8, 'side': None,
            'instructions': 'Face down, lift arms in Y shape, then T shape, then W shape. 8 of each.',
            'cues': ['Squeeze shoulder blades together', 'Thumbs up in Y position', 'Lift from upper back'],
            'when': 'Before any push or pull session',
        },
        {
            'id': 'wall_slide',
            'name': 'Wall Slide (Activation)',
            'sets': 2, 'reps': 10, 'side': None,
            'instructions': 'Stand against wall, elbows at 90° pressed to wall. Slide arms overhead keeping everything in contact with wall. Lower with control.',
            'cues': ['Lower back, elbows, wrists all touch wall', 'If you can\'t - that\'s the mobility goal', 'Slow: 3 seconds up, 3 seconds down'],
            'when': 'Before any push or pull session',
        },
        {
            'id': 'band_pull_apart_activation',
            'name': 'Band Pull Apart (Activation)',
            'sets': 2, 'reps': 15, 'side': None,
            'instructions': 'Hold a light band in front, arms at shoulder height. Pull band apart until arms are fully extended to sides. Control the return.',
            'cues': ['Squeeze shoulder blades together at full pull', 'Keep arms at shoulder height', 'Do not shrug'],
            'when': 'Before any push or pull session',
        },
    ],
    'deep_core_activation': [
        {
            'id': 'dead_bug_activation',
            'name': 'Dead Bug (Activation)',
            'sets': 1, 'reps': 5, 'side': 'each',
            'instructions': 'Back flat, knees at 90°. Lower opposite arm and leg slowly. Back stays flat.',
            'cues': ['BACK STAYS FLAT on floor', 'Slow controlled movement', 'Breathe throughout'],
            'when': 'Before any core-intensive session',
        },
        {
            'id': 'pallof_press_activation',
            'name': 'Pallof Press Isometric Hold (Activation)',
            'sets': 3, 'hold_seconds': 10, 'side': 'each',
            'instructions': 'Band anchored at chest height to side. Stand perpendicular. Press hands out in front, hold for 10 seconds resisting rotation. Return.',
            'cues': ['Resist the pull - do NOT rotate', 'Tall spine, engaged core', 'Breathe normally during the hold'],
            'when': 'Before any rotation, carry, or loaded carry session',
        },
    ],
}

# ============================================================================
# PHASE 5: COOL-DOWN (8-10 min)
# ============================================================================

COOLDOWN_LIGHT_MOVEMENT = [
    {
        'id': 'slow_walk',
        'name': 'Slow Walking',
        'duration_seconds': 120,
        'instructions': 'Walk slowly, letting heart rate gradually come down.',
        'cues': ['Long slow strides', 'Swing arms naturally', 'Breathe through nose if possible'],
    },
    {
        'id': 'gentle_arm_swings',
        'name': 'Gentle Arm Swings',
        'duration_seconds': 60,
        'instructions': 'Stand tall, let arms swing loosely forward and backward like pendulums. Gradually let the swing die down.',
        'cues': ['Completely relaxed arms - no muscular control', 'Let gravity do the work', 'Eyes closed if balance allows'],
    },
    {
        'id': 'easy_hip_circles',
        'name': 'Easy Hip Circles',
        'duration_seconds': 60,
        'instructions': 'Stand with hands on hips. Make slow, large circles with your hips - 30 seconds each direction.',
        'cues': ['Slow and smooth', 'Imagine drawing a large circle with your tailbone', 'Relaxed, not forced'],
    },
    {
        'id': 'shoulder_rolls',
        'name': 'Shoulder Rolls',
        'duration_seconds': 60,
        'instructions': 'Roll shoulders forward in large slow circles for 30 seconds, then backward for 30 seconds.',
        'cues': ['Exaggerate the motion - lift high, pull back, drop fully', 'Neck stays long and relaxed', 'Breathe slowly'],
    },
    {
        'id': 'neck_rolls_gentle',
        'name': 'Gentle Neck Rolls',
        'duration_seconds': 60,
        'instructions': 'Drop chin to chest and slowly roll head from side to side (front half only). Pause where tight.',
        'cues': ['Front semicircle only - no backward roll', 'Gravity is doing the work', 'Pause on tight spots - breathe into them'],
    },
    {
        'id': 'slow_tai_chi_sway',
        'name': 'Slow Tai Chi Sway',
        'duration_seconds': 90,
        'instructions': 'Stand with feet shoulder-width. Gently shift weight left and right in a slow rhythmic sway. Arms hang loose or rise gently with each shift.',
        'cues': ['No urgency', 'Feel weight transfer fully to each foot', 'Close eyes if comfortable'],
    },
]

COOLDOWN_STATIC_STRETCHES = {
    # R2-W2-8: holds capped at 30 s per ACSM-style flexibility guidance
    # (15-30 s x 2-4 repeats); the UI copy says "repeat if time allows".
    # Post-workout statics are fine — the pre-match protocol is dynamic-only.
    'squat_day': [
        {
            'id': 'quad_stretch_standing',
            'name': 'Standing Quad Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Stand, grab ankle behind, pull heel to glute. Keep knees together.',
            'cues': ['Upright torso', 'Knees together', 'Push hip slightly forward'],
        },
        {
            'id': 'hip_flexor_stretch_kneeling',
            'name': 'Kneeling Hip Flexor Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Half-kneeling position. Tuck pelvis under and shift weight forward until you feel a stretch at the front of the back-leg hip. Hold.',
            'cues': ['Tuck tailbone - this activates the stretch', 'Upright torso', 'Breathe and relax into it'],
        },
        {
            'id': 'calf_stretch_wall',
            'name': 'Wall Calf Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Hands on wall, one leg back, heel flat. Lean into wall until calf stretches. Also perform with slight knee bend for soleus.',
            'cues': ['Back heel stays DOWN', 'Slight bend at knee to target soleus', 'Do both versions'],
        },
        {
            'id': 'adductor_stretch_wide_squat',
            'name': 'Wide-Stance Adductor Stretch',
            'hold': 30, 'side': None,
            'instructions': 'Stand with feet wide (wider than squat stance), toes out 45°. Sink into a deep squat, elbows pressing knees out. Hold at bottom.',
            'cues': ['Elbows press knees wide', 'Heels stay down', 'Upright torso'],
        },
    ],
    'hinge_day': [
        {
            'id': 'hamstring_stretch_standing',
            'name': 'Standing Hamstring Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Stand, extend one leg forward with heel on a slightly elevated surface or flat. Hinge from hips forward until you feel the hamstring stretch. Keep back straight.',
            'cues': ['Hinge from HIPS - not rounding the back', 'Toes pulled back (dorsiflex)', 'Hold at the point of tension - don\'t force'],
        },
        {
            'id': 'glute_stretch_figure4',
            'name': 'Figure-4 Glute Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Lying on back. Cross right ankle over left knee. Pull left knee to chest, feeling stretch in right glute. Hold.',
            'cues': ['Flex the top foot (protect knee)', 'The closer the knee to chest, the deeper', 'Breathe and let the glute release'],
        },
        {
            'id': 'hip_flexor_stretch_hinge',
            'name': 'Kneeling Hip Flexor Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Half-kneeling. Tuck pelvis and shift forward until stretch felt in front of back-leg hip.',
            'cues': ['Tuck tailbone', 'Upright torso', 'Breathe steadily'],
        },
        {
            'id': 'lower_back_rotation',
            'name': 'Supine Lumbar Rotation',
            'hold': 30, 'side': 'each',
            'instructions': 'Lying on back, knees bent. Let both knees drop to one side, keep shoulders flat. Hold, then switch.',
            'cues': ['Shoulders stay flat on floor', 'Relax completely into the position', 'Breathe into the rotation'],
        },
    ],
    'push_pull_day': [
        {
            'id': 'doorway_chest_stretch',
            'name': 'Doorway Chest Stretch',
            'hold': 30, 'side': None,
            'instructions': 'Stand in a doorway, forearms vertical on door frame, elbows at 90°. Step one foot forward, lean through door until you feel the chest opening.',
            'cues': ['Forearms stay on frame', 'Do NOT shrug', 'Lean until mild stretch - not pain'],
        },
        {
            'id': 'lat_stretch_overhead',
            'name': 'Overhead Lat Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Reach one arm overhead, place hand on a wall or door frame. Lean away while keeping that arm extended. Feel the lat stretch along the side body.',
            'cues': ['Think "armpit to ceiling"', 'Ribs down - don\'t flare', 'Increase lean slowly'],
        },
        {
            'id': 'tricep_stretch',
            'name': 'Overhead Tricep Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Raise one arm, bend elbow so hand drops behind head. Use opposite hand to gently press the elbow back. Hold.',
            'cues': ['Keep neck long', 'Press the elbow gently - no forcing', 'Feel it down the back of the upper arm'],
        },
        {
            'id': 'forearm_flexor_stretch',
            'name': 'Forearm Flexor Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Extend arm in front, palm facing away from you. Use other hand to gently pull fingers back toward you. Hold.',
            'cues': ['Elbow stays fully extended', 'Gentle pressure - this can feel intense', 'Great after grip-heavy pulling sessions'],
        },
    ],
    'lunge_day': [
        {
            'id': 'hip_flexor_stretch_deep',
            'name': 'Deep Kneeling Hip Flexor Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Half-kneeling. Tuck pelvis and shift weight forward. For a deeper stretch, raise the arm on the kneeling-leg side overhead and lean slightly away.',
            'cues': ['Tailbone tucked hard', 'Raise arm = deeper stretch', 'Breathe slowly into front of hip'],
        },
        {
            'id': 'quad_stretch_prone',
            'name': 'Prone Quad Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Lie face down. Bend one knee and reach back to hold the ankle (or use a towel). Gently pull heel toward glute.',
            'cues': ['Hips stay flat on floor', 'Feel it in the quad, not just knee', 'Relax the leg you are stretching'],
        },
        {
            'id': 'adductor_stretch_lunge',
            'name': 'Wide-Stance Adductor Stretch',
            'hold': 30, 'side': None,
            'instructions': 'Wide stance, toes out. Sink into deep squat, elbows pressing out on knees. Hold at bottom.',
            'cues': ['Elbows press knees wide', 'Heels stay down', 'Upright torso'],
        },
        {
            'id': 'it_band_stretch',
            'name': 'IT Band / TFL Stretch (Standing)',
            'hold': 30, 'side': 'each',
            'instructions': 'Stand near a wall. Cross one leg behind the other and lean hips toward the wall on the side of the front leg. Feel stretch on outer thigh/hip.',
            'cues': ['Lean hips sideways - not backward', 'Keep crossed leg straight', 'Subtle stretch - not dramatic'],
        },
    ],
    'rotate_day': [
        {
            'id': 'trunk_rotation_lying',
            'name': 'Supine Trunk Rotation',
            'hold': 30, 'side': 'each',
            'instructions': 'Lying on back, knees bent. Lower both knees to one side while keeping shoulders flat. Breathe into the rotation.',
            'cues': ['Shoulders stay flat', 'Relax completely', 'Extend the hold as your body unwinds'],
        },
        {
            'id': 'childs_pose',
            'name': "Child's Pose",
            'hold': 30, 'side': None,
            'instructions': 'Kneel and sit back on heels, extending arms forward along floor. Breathe into the lower back and lats.',
            'cues': ['Walk hands further forward to increase stretch', 'Try arms wide (like a Y) for lat focus', 'Let the spine decompress with each exhale'],
        },
        {
            'id': 'cat_cow_slow',
            'name': 'Cat–Cow (Slow)',
            'reps': 8, 'side': None,
            'instructions': 'On hands and knees, move very slowly between full spinal flexion and extension. Synchronise with breath.',
            'cues': ['Maximum range each direction', 'Full exhale in cat, full inhale in cow', '5 seconds each position'],
        },
        {
            'id': 'lateral_flexion_stretch',
            'name': 'Standing Lateral Flexion Stretch',
            'hold': 30, 'side': 'each',
            'instructions': 'Stand, reach one arm overhead, bend sideways keeping hips square. Hold at end range.',
            'cues': ['Pure side bend - don\'t rotate', 'Reach the arm long to increase stretch', 'Breathe into the stretched side'],
        },
    ],
}

COOLDOWN_BREATHING = [
    {
        'id': 'diaphragmatic_4_4_6',
        'name': 'Diaphragmatic Breathing - 4-4-6',
        'duration_seconds': 180,  # ~10 breaths
        'instructions': 'Inhale through nose 4 counts. Hold 4 counts. Exhale through mouth 6 counts. Repeat 10 times.',
        'cues': ['Belly expands on inhale (not chest)', 'Slow exhale activates parasympathetic system', 'Close eyes if comfortable'],
        'purpose': 'Activates parasympathetic nervous system. Reduces cortisol. Accelerates recovery.',
    },
    {
        'id': 'box_breathing_4_4_4_4',
        'name': 'Box Breathing - 4-4-4-4',
        'duration_seconds': 180,
        'instructions': 'Inhale 4 counts. Hold 4 counts. Exhale 4 counts. Hold empty 4 counts. Repeat for 3 minutes.',
        'cues': ['Equal sides of the box', 'Stay relaxed during the holds', 'If light-headed, reduce holds to 2 counts'],
        'purpose': 'Balances sympathetic and parasympathetic. Used by high-performance athletes for nervous system reset.',
    },
    {
        'id': 'extended_exhale_4_7_8',
        'name': '4-7-8 Breathing',
        'duration_seconds': 180,
        'instructions': 'Inhale through nose for 4 counts. Hold for 7 counts. Exhale through mouth (pursed lips, audible whoosh) for 8 counts.',
        'cues': ['Tongue behind upper front teeth during hold and exhale', 'Exhale is the longest phase', 'Do not exceed 4 cycles to start'],
        'purpose': 'Deep parasympathetic activation. Promotes sleep onset if done post-session.',
    },
    {
        'id': 'resonant_breathing_5_5',
        'name': 'Resonant / Coherent Breathing - 5-5',
        'duration_seconds': 300,
        'instructions': 'Inhale gently through nose for 5 counts. Exhale gently for 5 counts. Aim for approximately 6 breaths per minute for 5 minutes.',
        'cues': ['No holds - smooth wave of breath', 'Both inhale and exhale are gentle and equal', 'Maximises heart rate variability (HRV)'],
        'purpose': 'Scientifically validated protocol for maximising HRV. Ideal end-of-session practice for recovery tracking.',
    },
]


# ============================================================================
# FIFA 11+ NEUROMUSCULAR WARMUP (P32)
# For football athletes only. Replaces standard warmup.
# 3 parts, 3 progressive levels per part.
# Research: Soligard 2008 (BMJ), Silvers-Granelli 2015 (AJSM). 30-46% injury reduction.
# ============================================================================

FIFA_11_PART1_RUNNING = {
    # Part 1: Running exercises — 8 minutes
    'level_1': [
        {'id': 'fifa_straight_run', 'name': 'Straight Running', 'duration_seconds': 60,
         'instructions': 'Jog straight across the field at an easy pace. Focus on relaxed upright posture.',
         'cues': ['Relaxed shoulders', 'Light foot contact', 'Upright torso']},
        {'id': 'fifa_hip_out', 'name': 'Hip Out (External Rotation Run)', 'duration_seconds': 60,
         'instructions': 'Jog forward. Every 3 steps, lift one knee and rotate it outward, opening the hip. Alternate legs.',
         'cues': ['Knee to hip height', 'Rotate outward from the hip, not the ankle', 'Stay balanced']},
        {'id': 'fifa_hip_in', 'name': 'Hip In (Internal Rotation Run)', 'duration_seconds': 60,
         'instructions': 'Jog forward. Every 3 steps, lift one knee and rotate it inward across the body. Alternate legs.',
         'cues': ['Controlled rotation', 'Do not twist the trunk', 'Light and rhythmic']},
        {'id': 'fifa_circling_partner', 'name': 'Circling Partner', 'duration_seconds': 60,
         'instructions': 'Jog side by side with a partner or imaginary partner. At a cone, shuffle around each other and continue. If alone, jog to a marker, circle it, jog back.',
         'cues': ['Stay low during the circle', 'Keep hips square', 'Quick feet around the turn']},
        {'id': 'fifa_shoulder_contact', 'name': 'Shoulder Contact Run', 'duration_seconds': 60,
         'instructions': 'Jog with a partner. At each cone, lean into each other shoulder to shoulder briefly, then continue. If alone, jog and perform a lateral lean every 5 steps.',
         'cues': ['Brace core on contact', 'Stay balanced through the bump', 'Keep running rhythm']},
    ],
    'level_2': [
        {'id': 'fifa_straight_run', 'name': 'Straight Running', 'duration_seconds': 60,
         'instructions': 'Jog at moderate pace with higher knees than Level 1.',
         'cues': ['Knees higher', 'Faster arm drive', 'Light ground contact']},
        {'id': 'fifa_hip_out', 'name': 'Hip Out Run (Faster)', 'duration_seconds': 60,
         'instructions': 'Same as Level 1 but at a faster jog and every 2 steps.',
         'cues': ['Quicker hip rotation', 'Maintain speed', 'Balanced landing']},
        {'id': 'fifa_hip_in', 'name': 'Hip In Run (Faster)', 'duration_seconds': 60,
         'instructions': 'Same as Level 1 but faster, every 2 steps.',
         'cues': ['Speed with control', 'Core tight', 'Smooth rhythm']},
        {'id': 'fifa_circling_partner', 'name': 'Circling Partner (Quick)', 'duration_seconds': 60,
         'instructions': 'Same movement at higher speed. Circle tighter and faster.',
         'cues': ['Low centre of gravity', 'Quick direction change', 'Explosive out of the circle']},
        {'id': 'fifa_quick_forwards_back', 'name': 'Quick Forwards and Back', 'duration_seconds': 60,
         'instructions': 'Sprint forward 5m, backpedal 3m, sprint forward again. Continuous for 60 seconds.',
         'cues': ['Explosive first step', 'Stay low on backpedal', 'Quick transition']},
    ],
    'level_3': [
        {'id': 'fifa_straight_run', 'name': 'Straight Running (Fast)', 'duration_seconds': 45,
         'instructions': 'Run at 75% speed. Near-sprint effort.',
         'cues': ['Aggressive arm drive', 'High knee lift', 'Short ground contact time']},
        {'id': 'fifa_hip_out', 'name': 'Hip Out Run (Sprint Pace)', 'duration_seconds': 45,
         'instructions': 'Same movement at sprint speed. Every 2 steps.',
         'cues': ['Maximum hip range', 'Do not slow down for the rotation', 'Power through']},
        {'id': 'fifa_hip_in', 'name': 'Hip In Run (Sprint Pace)', 'duration_seconds': 45,
         'instructions': 'Same movement at sprint speed.',
         'cues': ['Fast and controlled', 'Brace on each rotation', 'Athletic posture']},
        {'id': 'fifa_bounding_run', 'name': 'Bounding Run', 'duration_seconds': 60,
         'instructions': 'Exaggerated running strides. Push off each foot with maximum extension. Cover distance with each bound.',
         'cues': ['Triple extension: hip, knee, ankle', 'Arms drive hard', 'Land softly, push explosively']},
        {'id': 'fifa_plant_and_cut', 'name': 'Plant and Cut', 'duration_seconds': 60,
         'instructions': 'Sprint 5m, plant outside foot hard, cut 90 degrees, sprint 5m. Alternate directions.',
         'cues': ['Low hips on the cut', 'Outside foot plants firm', 'Explode out of the cut']},
    ],
}

FIFA_11_PART2_STRENGTH = {
    # Part 2: Strength, plyometrics, balance — 10 minutes
    'level_1': [
        {'id': 'planks', 'name': 'Front Plank', 'duration_seconds': 30, 'sets': 3,
         'instructions': 'Hold a front plank on forearms and toes. Body straight from head to heels.',
         'cues': ['No hip sag', 'Squeeze glutes', 'Breathe normally']},
        {'id': 'side_plank', 'name': 'Side Plank', 'duration_seconds': 20, 'sets': 2,
         'instructions': 'Side plank on forearm. Hold each side.',
         'cues': ['Hips stacked', 'Top arm on hip', 'Do not rotate forward']},
        {'id': 'nordic_hamstring_curl', 'name': 'Nordic Hamstring Curl (Partial)', 'sets': 3, 'reps': 3,
         'instructions': 'Kneel with ankles anchored. Slowly lower chest toward floor, catching yourself with hands. Only go as far as you can control.',
         'cues': ['Hips stay extended', 'Slow descent — 5 seconds minimum', 'Catch with hands, push back up']},
        {'id': 'single_leg_balance', 'name': 'Single Leg Balance (Eyes Open)', 'duration_seconds': 30, 'sets': 2,
         'instructions': 'Stand on one leg. Hold for 30 seconds each side.',
         'cues': ['Fix eyes on a point ahead', 'Slight knee bend', 'Hip level — do not drop']},
        {'id': 'partial_squats', 'name': 'Bodyweight Squats', 'sets': 2, 'reps': 10,
         'instructions': 'Bodyweight squat to parallel. Controlled descent and ascent.',
         'cues': ['Knees track over toes', 'Chest up', 'Full depth to parallel']},
    ],
    'level_2': [
        {'id': 'planks', 'name': 'Front Plank (Leg Lift)', 'duration_seconds': 40, 'sets': 3,
         'instructions': 'Front plank, alternating lifting one leg 15cm off the ground every 5 seconds.',
         'cues': ['No hip shift when leg lifts', 'Keep core braced', 'Slow controlled lifts']},
        {'id': 'side_plank_hip_dip', 'name': 'Side Plank with Hip Dip', 'duration_seconds': 30, 'sets': 2,
         'instructions': 'Side plank. Lower hip toward floor, then raise back to straight line. Each side.',
         'cues': ['Controlled dip — do not collapse', 'Full hip extension at top', 'Core tight throughout']},
        {'id': 'nordic_hamstring_curl', 'name': 'Nordic Hamstring Curl (Deeper)', 'sets': 3, 'reps': 5,
         'instructions': 'Same movement but lower further before catching. Aim for 60% of full range.',
         'cues': ['5-second controlled descent', 'Hips extended — no hip flexion', 'Hamstrings control the lowering']},
        {'id': 'single_leg_balance', 'name': 'Single Leg Balance (Eyes Closed)', 'duration_seconds': 20, 'sets': 2,
         'instructions': 'Single leg balance with eyes closed. 20 seconds each side.',
         'cues': ['Close eyes gently', 'Activate foot muscles', 'Small corrections at the ankle']},
        {'id': 'jump_squats', 'name': 'Jump Squats (Controlled)', 'sets': 2, 'reps': 8,
         'instructions': 'Squat to parallel, explode upward. Land softly with bent knees.',
         'cues': ['Soft landing — absorb through hips and knees', 'No knee valgus on landing', 'Arms drive the jump']},
    ],
    'level_3': [
        {'id': 'planks', 'name': 'Front Plank (Opposite Arm-Leg Lift)', 'duration_seconds': 45, 'sets': 3,
         'instructions': 'Front plank. Lift right arm and left leg simultaneously. Hold 3 seconds. Alternate.',
         'cues': ['Zero hip rotation', 'Reach long through fingertips and heel', 'Brace hard before each lift']},
        {'id': 'copenhagen_plank', 'name': 'Copenhagen Plank', 'duration_seconds': 20, 'sets': 2,
         'instructions': 'Side plank with top leg on a bench, bottom leg unsupported. Hold each side.',
         'cues': ['Squeeze adductors to hold', 'Hips stacked and elevated', 'Brutal — scale time if needed']},
        {'id': 'nordic_hamstring_curl', 'name': 'Nordic Hamstring Curl (Full Range)', 'sets': 3, 'reps': 5,
         'instructions': 'Full Nordic curl. Lower all the way to the floor under control. Push up and repeat.',
         'cues': ['6-second eccentric', 'Hips MUST stay extended the entire time', 'This is the gold standard hamstring exercise']},
        {'id': 'single_leg_balance', 'name': 'Single Leg Squat Touch', 'duration_seconds': 30, 'sets': 2,
         'instructions': 'Stand on one leg. Squat down and touch the floor with opposite hand. Return to standing.',
         'cues': ['Knee tracks over toe', 'Hip stays level', 'Control the entire range']},
        {'id': 'jump_squats', 'name': 'Tuck Jumps', 'sets': 2, 'reps': 8,
         'instructions': 'Jump and pull knees to chest at the peak. Land softly. Immediately repeat.',
         'cues': ['Knees to chest, not chest to knees', 'Land soft and reload instantly', 'Maximum height every rep']},
    ],
}

FIFA_11_PART3_RUNNING_ADVANCED = {
    # Part 3: Advanced running — 2 minutes
    'level_1': [
        {'id': 'fifa_high_knees_accel', 'name': 'High Knees into Acceleration', 'duration_seconds': 40,
         'instructions': '10 high knees on the spot, then sprint 10m. Walk back. Repeat 3 times.',
         'cues': ['Knees to waist', 'Explode into the sprint from the last high knee', 'Full sprint effort for 10m']},
        {'id': 'fifa_bounding_short', 'name': 'Bounding (Short)', 'duration_seconds': 40,
         'instructions': 'Exaggerated skipping strides across 15m. Walk back. Repeat 3 times.',
         'cues': ['Drive knee high', 'Push off forcefully', 'Cover ground with each bound']},
    ],
    'level_2': [
        {'id': 'fifa_high_knees_accel', 'name': 'High Knees into Sprint', 'duration_seconds': 40,
         'instructions': '10 high knees then sprint 15m. Walk back. Repeat 3 times. Faster than Level 1.',
         'cues': ['Transition from knees to sprint must be instant', 'Arms drive hard', 'Sprint at 90% effort']},
        {'id': 'fifa_plant_and_cut', 'name': 'Plant and Cut (Moderate)', 'duration_seconds': 40,
         'instructions': 'Sprint 8m, plant and cut 45 degrees, sprint 8m. Alternate sides. 4 reps.',
         'cues': ['Lower hips into the cut', 'Push off outside foot', 'Accelerate out of every cut']},
    ],
    'level_3': [
        {'id': 'fifa_high_knees_accel', 'name': 'High Knees into Max Sprint', 'duration_seconds': 40,
         'instructions': '8 rapid high knees then all-out sprint 20m. Walk back. Repeat 3 times.',
         'cues': ['Maximum knee frequency', 'Explosive transition', '100% sprint effort']},
        {'id': 'fifa_plant_and_cut', 'name': 'Plant and Cut (Max Speed)', 'duration_seconds': 40,
         'instructions': 'Sprint 10m at maximum speed, plant and cut 90 degrees, sprint 10m. 4 reps alternating.',
         'cues': ['Full speed into the cut', 'Decelerate, plant, explode — no stutter steps', 'This is match-intensity']},
    ],
}
