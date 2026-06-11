"""
VYAYAM V1 — Nutrition Views
"""

import json
import logging
from datetime import date, timedelta

from django.db.models import Q
from django.http import JsonResponse

logger = logging.getLogger(__name__)
from .rate_limiter import rate_limit
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import PatientProfile, NutritionProfile, FoodItem, DailyFoodLog, MessEntry
from .v1_nutrition_engine import (
    calculate_macro_targets,
    get_daily_nutrition_summary,
    generate_mess_guidance,
    GOAL_NUTRITION,
    ACTIVITY_MULTIPLIERS,
)


def _require_patient(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None, redirect('patient_login')
    try:
        return PatientProfile.objects.get(patient_id=pid), None
    except PatientProfile.DoesNotExist:
        request.session.flush()
        return None, redirect('patient_login')


# ── Dashboard ─────────────────────────────────────────────────────────────────

def v1_nutrition_dashboard(request):
    patient, err = _require_patient(request)
    if err:
        return err

    today = date.today()
    yesterday = today - timedelta(days=1)

    summary_today = get_daily_nutrition_summary(patient, today)
    summary_yesterday = get_daily_nutrition_summary(patient, yesterday)

    try:
        np = patient.nutrition_profile
    except NutritionProfile.DoesNotExist:
        np = None

    # Last 7 days for mini trend (calories only)
    trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        s = get_daily_nutrition_summary(patient, d)
        trend.append({'date': d.strftime('%a'), 'calories': s['total_calories'], 'target': s['target_calories']})

    return render(request, 'strength_app/v1_nutrition_dashboard.html', {
        'patient': patient,
        'np': np,
        'summary': summary_today,
        'summary_yesterday': summary_yesterday,
        'trend': trend,
        'today': today,
        'goal_label': GOAL_NUTRITION.get(np.nutrition_goal if np else 'maintenance', {}).get('label', 'Maintenance'),
    })


# ── Food Log ──────────────────────────────────────────────────────────────────

def v1_food_log(request):
    patient, err = _require_patient(request)
    if err:
        return err

    selected_date_str = request.GET.get('date', str(date.today()))
    try:
        selected_date = date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = date.today()

    if request.method == 'POST':
        food_id    = request.POST.get('food_id')
        meal_type  = request.POST.get('meal_type', 'lunch')
        try:
            quantity_g = float(request.POST.get('quantity_g') or 100)
            if quantity_g <= 0 or quantity_g > 5000:
                quantity_g = 100
        except (ValueError, TypeError):
            quantity_g = 100
        log_date   = request.POST.get('log_date', str(date.today()))

        try:
            food_item = FoodItem.objects.get(id=food_id, is_active=True)
            DailyFoodLog.objects.create(
                patient=patient,
                food_item=food_item,
                log_date=log_date,
                quantity_g=quantity_g,
                meal_type=meal_type,
            )
        except (FoodItem.DoesNotExist, ValueError):
            pass

        from django.urls import reverse
        return redirect(f"{reverse('v1_food_log')}?date={log_date}")

    summary  = get_daily_nutrition_summary(patient, selected_date)
    top_foods = FoodItem.objects.filter(is_active=True, is_mess_common=True).order_by('category', 'name')[:20]

    return render(request, 'strength_app/v1_food_log.html', {
        'patient': patient,
        'summary': summary,
        'selected_date': selected_date,
        'top_foods': top_foods,
        'meal_types': ['breakfast', 'lunch', 'snack', 'dinner'],
    })


# ── Mess Mode ─────────────────────────────────────────────────────────────────

def v1_mess_mode(request):
    patient, err = _require_patient(request)
    if err:
        return err

    try:
        np = patient.nutrition_profile
    except NutritionProfile.DoesNotExist:
        np = None

    guidance = None
    selected_items = []

    if request.method == 'POST':
        meal_type    = request.POST.get('meal_type', 'lunch')
        food_ids     = request.POST.getlist('food_ids')
        raw_desc     = request.POST.get('raw_description', '').strip()
        entry_date   = date.today()

        foods = FoodItem.objects.filter(id__in=food_ids, is_active=True)
        guidance = generate_mess_guidance(list(foods), np)

        entry = MessEntry.objects.create(
            patient=patient,
            entry_date=entry_date,
            meal_type=meal_type,
            raw_description=raw_desc,
            guidance_text=guidance,
        )
        entry.food_items_served.set(foods)

        selected_items = list(foods)

    mess_foods = FoodItem.objects.filter(is_mess_common=True, is_active=True).order_by('category', 'name')
    recent = MessEntry.objects.filter(patient=patient).order_by('-entry_date')[:5]

    return render(request, 'strength_app/v1_mess_mode.html', {
        'patient': patient,
        'np': np,
        'mess_foods': mess_foods,
        'guidance': guidance,
        'selected_items': selected_items,
        'recent': recent,
        'meal_types': ['breakfast', 'lunch', 'snack', 'dinner'],
    })


# ── API: Food Search ──────────────────────────────────────────────────────────

def v1_food_search_api(request):
    if not request.session.get('patient_id'):
        return JsonResponse({'error': 'Authentication required'}, status=401)

    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'results': []})

    items = FoodItem.objects.filter(
        Q(name__icontains=q) | Q(name_hindi__icontains=q),
        is_active=True,
    )[:15]

    results = [{
        'id': f.id,
        'name': f.name,
        'name_hindi': f.name_hindi,
        'category': f.get_category_display(),
        'cal_per_100g': f.calories_per_100g,
        'protein_per_100g': f.protein_per_100g,
        'carbs_per_100g': f.carbs_per_100g,
        'fat_per_100g': f.fat_per_100g,
        'serving_g': f.serving_size_g,
        'serving_desc': f.serving_description,
        'cal_per_serving': f.calories_per_serving,
        'protein_per_serving': f.protein_per_serving,
    } for f in items]

    return JsonResponse({'results': results})


# ── API: Quick Log ────────────────────────────────────────────────────────────

@require_POST
@rate_limit(max_attempts=60, window_seconds=60, key_prefix='quick_log')  # DA-P6
def v1_quick_log_api(request):
    patient, err = _require_patient(request)
    if err:
        return JsonResponse({'ok': False, 'error': 'Not logged in'}, status=401)

    try:
        data = json.loads(request.body)

        food_id = int(data['food_id'])
        if food_id <= 0:
            return JsonResponse({'ok': False, 'error': 'Invalid food item.'}, status=400)

        qty_g = float(data.get('quantity_g', 100))
        if qty_g <= 0 or qty_g > 5000:
            return JsonResponse({'ok': False, 'error': 'Quantity must be between 1 and 5000 grams.'}, status=400)

        ALLOWED_MEALS = {'breakfast', 'lunch', 'snack', 'dinner', 'pre_workout', 'post_workout'}
        meal_type = data.get('meal_type', 'lunch')
        if meal_type not in ALLOWED_MEALS:
            meal_type = 'lunch'

        from datetime import datetime as _dt
        log_date_str = data.get('log_date', str(date.today()))
        try:
            log_date = _dt.strptime(log_date_str, '%Y-%m-%d').date()
            if log_date > date.today() or (date.today() - log_date).days > 7:
                log_date = date.today()
        except ValueError:
            log_date = date.today()

    except (KeyError, ValueError, json.JSONDecodeError):
        logger.exception('Error in quick_log_api')
        return JsonResponse({'ok': False, 'error': 'Could not log food. Please check your input and try again.'}, status=400)

    try:
        food = FoodItem.objects.get(id=food_id, is_active=True)
    except FoodItem.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Food not found'}, status=404)

    log = DailyFoodLog.objects.create(
        patient=patient,
        food_item=food,
        log_date=log_date,
        quantity_g=qty_g,
        meal_type=meal_type,
    )

    summary = get_daily_nutrition_summary(patient, log_date)

    return JsonResponse({
        'ok': True,
        'logged': {
            'id': log.id,
            'food': food.name,
            'qty_g': qty_g,
            'calories': log.calories_logged,
            'protein': log.protein_logged,
        },
        'summary': {
            'total_calories': summary['total_calories'],
            'total_protein':  summary['total_protein'],
            'pct_calories':   summary['pct_calories'],
            'traffic_light':  summary['traffic_light'],
        },
    })
