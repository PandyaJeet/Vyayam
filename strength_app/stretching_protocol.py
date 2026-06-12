"""
VYAYAM Pre-Match Stretching Protocol

R2-W2-8 (SB audit "stretch holds" finding): the pre-match protocol is now
DYNAMIC throughout. The previous version opened with 4 × 30 s static holds;
sustained static stretching immediately before explosive work can acutely
reduce power/sprint output (static-stretching performance literature —
commonly cited meta-analyses, e.g. Simic et al. 2013; effect grows with
holds ≥ 60 s, and a dynamic warm-up is the standard pre-match practice).
The former static items are replaced with dynamic, movement-matched
equivalents of the same muscle groups. General-flexibility static holds
(15–30 s × multiple sets, ACSM-style guidance) belong in cooldown /
standalone mobility work, not here.

Order follows joint-to-movement progression:
dynamic mobilisation → isolated activation → integrated movement → full intensity
"""

PRE_MATCH_STRETCHES = [
    {
        'stretch_id': 'hip_flexor_stretch',
        'name': 'Dynamic Hip-Flexor Lunge with Reach',
        'duration_seconds': 30,
        'side': 'left',
        'muscle_group': 'Hip Flexors',
        'coaching_cue': 'Step into a lunge, reach the same-side arm overhead, return to standing. Rhythmic reps — move in and out, no long hold.',
        'icon': '🦵',
    },
    {
        'stretch_id': 'hip_flexor_stretch',
        'name': 'Dynamic Hip-Flexor Lunge with Reach',
        'duration_seconds': 30,
        'side': 'right',
        'muscle_group': 'Hip Flexors',
        'coaching_cue': 'Switch sides. Lunge, reach tall, return. Keep the rhythm — about 2 seconds per rep.',
        'icon': '🦵',
    },
    {
        'stretch_id': 'quadriceps_stretch',
        'name': 'Walking Quad Pulls',
        'duration_seconds': 30,
        'side': 'left',
        'muscle_group': 'Quadriceps',
        'coaching_cue': 'Standing tall, pull your heel to your glute for 2 seconds, release, step, repeat. Brief pulls, not a sustained hold.',
        'icon': '🏃',
    },
    {
        'stretch_id': 'quadriceps_stretch',
        'name': 'Walking Quad Pulls',
        'duration_seconds': 30,
        'side': 'right',
        'muscle_group': 'Quadriceps',
        'coaching_cue': 'Switch legs. 2-second pull, release, repeat. Stand tall throughout.',
        'icon': '🏃',
    },
    {
        'stretch_id': 'hamstring_stretch',
        'name': 'Hamstring Sweeps',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hamstrings',
        'coaching_cue': 'Step one heel forward, toes up, hinge and sweep both hands past the front foot, stand back up. Alternate legs with each rep.',
        'icon': '🧘',
    },
    {
        'stretch_id': 'calf_stretch',
        'name': 'Rocking Calf Stretch',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Calves',
        'coaching_cue': 'Hands on a wall, one leg back. Rock the back heel down for 2 seconds, lift, repeat. Switch legs halfway. Pulsing, not holding.',
        'icon': '🧱',
    },
    {
        'stretch_id': 'hip_circles',
        'name': 'Hip Circles',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hip Rotators',
        'coaching_cue': 'Stand on one leg, lift other knee to hip height and rotate in large circles. 15 seconds each direction.',
        'icon': '🔄',
    },
    {
        'stretch_id': 'knee_circles',
        'name': 'Knee Circles',
        'duration_seconds': 20,
        'side': 'both',
        'muscle_group': 'Knee Joint & Synovial Fluid',
        'coaching_cue': 'Stand with feet together, hands on knees. Circle both knees slowly clockwise for 10 seconds, then counter-clockwise. Lubricates the knee joint.',
        'icon': '🔵',
    },
    {
        'stretch_id': 'butt_kicks',
        'name': 'Butt Kicks',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hamstrings & Knee Flexors',
        'coaching_cue': 'Jog in place kicking heels up toward your glutes. Keep knees pointing down, not forward. Quick rhythm, stay on toes. Mimics the recovery phase of sprinting.',
        'icon': '👟',
    },
    {
        'stretch_id': 'leg_swings',
        'name': 'Dynamic Leg Swings',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Hip Flexors & Hamstrings',
        'coaching_cue': 'Hold wall for balance. Swing one leg forward and back in controlled pendulum motion. Keep core tight.',
        'icon': '⚡',
    },
    {
        'stretch_id': 'ankle_rotations',
        'name': 'Ankle Rotations',
        'duration_seconds': 20,
        'side': 'both',
        'muscle_group': 'Ankles',
        'coaching_cue': 'Lift one foot, rotate ankle in slow circles. 10 seconds clockwise, 10 counter-clockwise.',
        'icon': '🦶',
    },
    {
        'stretch_id': 'high_knees',
        'name': 'High Knees (Dynamic Warm-Up)',
        'duration_seconds': 30,
        'side': 'both',
        'muscle_group': 'Full Lower Body',
        'coaching_cue': 'Jog in place driving knees to hip height. Pump arms opposite to legs. Quick light feet.',
        'icon': '🔥',
    },
]

TOTAL_STRETCHES = len(PRE_MATCH_STRETCHES)
TOTAL_PROTOCOL_DURATION = sum(s['duration_seconds'] for s in PRE_MATCH_STRETCHES)
