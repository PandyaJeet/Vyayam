"""
VYAYAM NUTRITION ENGINE
Goal-based macro calculator with Indian food focus.
"""

from datetime import date, timedelta

# ── Goal macro ratios ──────────────────────────────────────────────────────────
# Each entry: (calorie_multiplier_from_tdee, protein_ratio, carbs_ratio, fat_ratio)
# protein/carbs/fat ratios are % of total calories.
GOAL_NUTRITION = {
    'weight_loss': {
        'calorie_factor': 0.80,   # 20% deficit
        'protein_pct': 0.35,
        'carbs_pct':   0.35,
        'fat_pct':     0.30,
        'label': 'Weight Loss',
        'note': 'High protein to preserve muscle during deficit.',
    },
    'muscle_gain': {
        'calorie_factor': 1.10,   # 10% surplus
        'protein_pct': 0.30,
        'carbs_pct':   0.45,
        'fat_pct':     0.25,
        'label': 'Muscle Gain',
        'note': 'Moderate surplus with high carbs to fuel training.',
    },
    'maintenance': {
        'calorie_factor': 1.00,
        'protein_pct': 0.30,
        'carbs_pct':   0.40,
        'fat_pct':     0.30,
        'label': 'Maintenance',
        'note': 'Balanced nutrition to support your training.',
    },
    'lean_muscle': {
        'calorie_factor': 1.05,
        'protein_pct': 0.35,
        'carbs_pct':   0.40,
        'fat_pct':     0.25,
        'label': 'Lean Muscle',
        'note': 'Slight surplus with high protein for lean gains.',
    },
    'performance': {
        'calorie_factor': 1.10,
        'protein_pct': 0.25,
        'carbs_pct':   0.50,
        'fat_pct':     0.25,
        'label': 'Performance',
        'note': 'High carb for training output and recovery.',
    },
    'endurance': {
        'calorie_factor': 1.05,
        'protein_pct': 0.20,
        'carbs_pct':   0.55,
        'fat_pct':     0.25,
        'label': 'Endurance',
        'note': 'High carbohydrate to fuel endurance training.',
    },
    'athletic_performance': {
        'calorie_factor': 1.05,
        'protein_pct': 0.28,
        'carbs_pct':   0.52,
        'fat_pct':     0.20,
        'label': 'Athletic Performance',
        'note': 'Carb-forward to support high-intensity training.',
    },
    'rehabilitation': {
        'calorie_factor': 0.95,
        'protein_pct': 0.32,
        'carbs_pct':   0.43,
        'fat_pct':     0.25,
        'label': 'Rehabilitation / Recovery',
        'note': 'Slight deficit with elevated protein to support tissue repair.',
    },
}

# Map training goal keys → nutrition goal keys
TRAINING_TO_NUTRITION_GOAL = {
    'fat_loss':          'weight_loss',
    'hypertrophy':       'muscle_gain',
    'general_strength':  'maintenance',
    'endurance':         'endurance',
    'strength_endurance':'maintenance',
    'calisthenics':      'lean_muscle',
    'female_physique':   'weight_loss',
    'athletic':          'performance',
    'rehabilitation':    'rehabilitation',
    'mobility':          'maintenance',
    'posture':           'maintenance',
    'healthy_ageing':    'maintenance',
}

ACTIVITY_MULTIPLIERS = {
    'sedentary':        1.2,
    'lightly_active':   1.375,
    'moderately_active': 1.55,
    'very_active':      1.725,
    'extra_active':     1.9,
}


def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor BMR formula."""
    if sex == 'female':
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Total Daily Energy Expenditure."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return bmr * multiplier


def calculate_macro_targets(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity_level: str,
    goal: str,
    medical_conditions: list = None,
) -> dict:
    """
    Returns {calories, protein_g, carbs_g, fat_g, notes}.
    Applies red-flag adjustments for known medical conditions.
    """
    medical_conditions = medical_conditions or []
    # Auto-map from training goal if nutrition goal not set or not found
    if not goal or goal not in GOAL_NUTRITION:
        goal = TRAINING_TO_NUTRITION_GOAL.get(goal, 'maintenance')
    goal_cfg = GOAL_NUTRITION.get(goal, GOAL_NUTRITION['maintenance'])

    bmr = calculate_bmr(weight_kg, height_cm, age, sex)
    tdee = calculate_tdee(bmr, activity_level)
    target_cal = tdee * goal_cfg['calorie_factor']

    protein_cal = target_cal * goal_cfg['protein_pct']
    carbs_cal   = target_cal * goal_cfg['carbs_pct']
    fat_cal     = target_cal * goal_cfg['fat_pct']

    protein_g = protein_cal / 4
    carbs_g   = carbs_cal   / 4
    fat_g     = fat_cal     / 9

    notes = [goal_cfg['note']]

    # Red-flag medical adjustments
    cond_lower = [c.lower() for c in medical_conditions]

    if any('kidney' in c or 'renal' in c for c in cond_lower):
        cap = weight_kg * 0.8   # 0.8 g/kg protein cap for kidney disease
        if protein_g > cap:
            saved_cal = (protein_g - cap) * 4
            protein_g = cap
            carbs_g += saved_cal / 4   # redistribute to carbs
        notes.append('Protein capped at 0.8 g/kg due to kidney condition.')

    if any('hypertension' in c or 'high blood pressure' in c for c in cond_lower):
        notes.append('Limit sodium: avoid processed foods, papad, pickles, extra salt.')

    if any('diabetes' in c or 'diabetic' in c for c in cond_lower):
        notes.append('Prefer complex carbs (brown rice, oats, dal) and limit refined sugars.')

    if any('osteoporosis' in c or 'bone' in c for c in cond_lower):
        notes.append('Include calcium-rich foods: ragi, paneer, milk, sesame seeds.')

    return {
        'calories':  round(target_cal),
        'protein_g': round(protein_g),
        'carbs_g':   round(carbs_g),
        'fat_g':     round(fat_g),
        'bmr':       round(bmr),
        'tdee':      round(tdee),
        'notes':     notes,
    }


def get_daily_nutrition_summary(patient, log_date: date = None) -> dict:
    """
    Returns totals + remaining macros for a given date.
    """
    from .models import DailyFoodLog, NutritionProfile

    if log_date is None:
        log_date = date.today()

    logs = DailyFoodLog.objects.filter(patient=patient, log_date=log_date)

    total_cal  = sum(l.calories_logged for l in logs)
    total_pro  = sum(l.protein_logged  for l in logs)
    total_carb = sum(l.carbs_logged    for l in logs)
    total_fat  = sum(l.fat_logged      for l in logs)

    needs_setup = False
    try:
        np = patient.nutrition_profile
        target_cal  = np.target_calories
        target_pro  = np.target_protein_g
        target_carb = np.target_carbs_g
        target_fat  = np.target_fat_g
    except NutritionProfile.DoesNotExist:
        target_cal = target_pro = target_carb = target_fat = 0

    pct_cal = round(total_cal / target_cal * 100) if target_cal else 0

    # DA-C10: no targets set is a SETUP state, not a red light — a brand
    # new patient must not open the app to a red nutrition warning.
    if not target_cal:
        needs_setup = True
        traffic_light = 'none'
    else:
        traffic_light = 'green'
        if pct_cal < 60:
            traffic_light = 'red'
        elif pct_cal < 80:
            traffic_light = 'yellow'

    # Group by meal
    by_meal = {}
    for log in logs:
        meal = log.meal_type
        if meal not in by_meal:
            by_meal[meal] = []
        by_meal[meal].append({
            'food': log.food_item.name,
            'qty_g': log.quantity_g,
            'calories': log.calories_logged,
            'protein': log.protein_logged,
        })

    return {
        'date': log_date,
        'total_calories': round(total_cal, 1),
        'total_protein':  round(total_pro,  1),
        'total_carbs':    round(total_carb, 1),
        'total_fat':      round(total_fat,  1),
        'target_calories': target_cal,
        'target_protein':  target_pro,
        'target_carbs':    target_carb,
        'target_fat':      target_fat,
        'remaining_calories': max(0, target_cal - round(total_cal)),
        'remaining_protein':  max(0, target_pro  - round(total_pro)),
        'pct_calories': pct_cal,
        'traffic_light': traffic_light,
        'needs_setup': needs_setup,
        'by_meal': by_meal,
        'log_count': logs.count(),
    }


def generate_mess_guidance(food_items, nutrition_profile) -> str:
    """
    Given a list of FoodItem objects available in the mess today,
    return portion guidance text tailored to the patient's macro targets.
    """
    if not nutrition_profile:
        return "Log your portions as usual. Aim for 1–2 servings of protein, 1 serving of carbs, and a side of vegetables."

    goal = nutrition_profile.nutrition_goal
    target_protein = nutrition_profile.target_protein_g
    target_cal = nutrition_profile.target_calories

    # Classify available items
    proteins  = [f for f in food_items if f.protein_per_100g >= 8]
    carbs     = [f for f in food_items if f.carbs_per_100g  >= 20]
    veggies   = [f for f in food_items if f.category == 'vegetable']

    lines = []

    if goal in ('muscle_gain', 'athletic_performance'):
        lines.append("Today's mess — Muscle/Performance Mode:")
        if proteins:
            lines.append(f"  • Protein: Eat a full serving of {proteins[0].name}"
                         + (f" + {proteins[1].name}" if len(proteins) > 1 else "") + ".")
        if carbs:
            lines.append(f"  • Carbs: Take 1.5× normal serving of {carbs[0].name}.")
        if veggies:
            lines.append(f"  • Veggies: Add {veggies[0].name} freely — no restriction.")
        lines.append(f"  • Target for this meal: ~{round(target_cal * 0.35)} kcal.")

    elif goal == 'weight_loss':
        lines.append("Today's mess — Weight Loss Mode:")
        if proteins:
            lines.append(f"  • Protein first: Fill half your plate with {proteins[0].name}.")
        if veggies:
            lines.append(f"  • Veggies: Quarter plate of {veggies[0].name}.")
        if carbs:
            lines.append(f"  • Carbs: Keep {carbs[0].name} to one small serving.")
        lines.append(f"  • Target for this meal: ~{round(target_cal * 0.30)} kcal.")

    else:  # maintenance / rehabilitation
        lines.append("Today's mess — Balanced Mode:")
        if proteins:
            lines.append(f"  • Include {proteins[0].name} for protein.")
        if carbs:
            lines.append(f"  • Normal serving of {carbs[0].name} for energy.")
        if veggies:
            lines.append(f"  • Add {veggies[0].name} for micronutrients.")
        lines.append(f"  • Target for this meal: ~{round(target_cal * 0.33)} kcal.")

    if not lines:
        return "Eat a balanced plate: protein + carbs + vegetables in equal portions."

    return "\n".join(lines)
