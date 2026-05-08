"""
VYAYAM STRENGTH TRAINING - APP URLS
Complete URL patterns for the strength training app
Fixed to match template expectations
"""

from django.urls import path
from django.conf import settings
from django.views.static import serve as static_serve
from . import views
from . import v1_onboarding_views as views_onboard
from . import v1_football_views as views_football
from . import v1_session_views as views_session
from . import v1_progress_views as views_progress
from . import v1_coach_views as views_coach
from . import v1_nutrition_views as views_nutrition
from . import v1_therapist_session_views as views_thrx

urlpatterns = [

    # PWA service worker — must be served from root scope
    path('sw.js', static_serve, {
        'path': 'strength_app/sw.js',
        'document_root': settings.BASE_DIR / 'strength_app' / 'static',
    }, name='service_worker'),

    # ========================================================================
    # V1 ONBOARDING (14 patterns — 10-screen clinical assessment)
    # ========================================================================
    path('onboarding/start/',                                          views_onboard.onboarding_start,                name='onboarding_start'),
    path('onboarding/identity/',                                       views_onboard.onboarding_identity,             name='onboarding_identity'),
    path('onboarding/training-history/',                               views_onboard.onboarding_training_history,     name='onboarding_training_history'),
    path('onboarding/strength-test/',                                  views_onboard.onboarding_strength_test,        name='onboarding_strength_test'),
    path('onboarding/strength-test-execute/<int:test_index>/',         views_onboard.onboarding_strength_test_execute, name='onboarding_strength_test_execute'),
    path('onboarding/save-test-result/',                               views_onboard.onboarding_save_test_result,     name='onboarding_save_test_result'),
    path('onboarding/asymmetry/',                                      views_onboard.onboarding_asymmetry,            name='onboarding_asymmetry'),
    path('onboarding/goals/',                                          views_onboard.onboarding_goals,                name='onboarding_goals'),
    path('onboarding/equipment/',                                      views_onboard.onboarding_equipment,            name='onboarding_equipment'),
    path('onboarding/hormonal/',                                       views_onboard.onboarding_hormonal,             name='onboarding_hormonal'),
    path('onboarding/red-flags/',                                      views_onboard.onboarding_red_flags,            name='onboarding_red_flags'),
    path('onboarding/lifestyle/',                                      views_onboard.onboarding_lifestyle,            name='onboarding_lifestyle'),
    path('onboarding/mind-muscle/',                                    views_onboard.onboarding_mind_muscle,          name='onboarding_mind_muscle'),
    path('onboarding/nutrition/',                                      views_onboard.onboarding_nutrition,            name='onboarding_nutrition'),
    path('onboarding/complete/',                                       views_onboard.onboarding_complete,             name='onboarding_complete'),

    # ========================================================================
    # FOOTBALL / ATHLETE TIER
    # ========================================================================
    path('football/sport-select/',                                     views_football.football_sport_select,           name='football_sport_select'),
    path('football/assessment/',                                       views_football.football_assessment,             name='football_assessment'),
    path('football/assessment/<int:test_index>/',                      views_football.football_assessment_execute,     name='football_assessment_execute'),
    path('football/save-test-result/',                                 views_football.football_save_test_result,       name='football_save_test_result'),
    path('football/results/',                                          views_football.football_assessment_results,     name='football_assessment_results'),
    path('football/matches/',                                          views_football.match_calendar,                  name='match_calendar'),
    path('football/matches/add/',                                      views_football.match_add,                       name='match_add'),
    path('football/matches/delete/<int:match_id>/',                    views_football.match_delete,                    name='match_delete'),

    # ========================================================================
    # V1 SESSION EXECUTION (8 patterns)
    # ========================================================================
    path('v1/dashboard/',                                   views_session.v1_dashboard,             name='v1_dashboard'),
    path('v1/session/',                                     views_session.v1_session_overview,      name='v1_session_overview'),
    path('v1/session/warmup/',                              views_session.v1_warmup,                    name='v1_warmup'),
    path('v1/session/warmup/exercise/<int:warmup_index>/', views_session.v1_execute_warmup_exercise,   name='v1_execute_warmup_exercise'),
    path('v1/session/exercise/<int:exercise_index>/',       views_session.v1_execute_exercise,          name='v1_execute_exercise'),
    path('v1/session/save-exercise/',                       views_session.v1_save_exercise_result,  name='v1_save_exercise_result'),
    path('v1/session/cooldown/',                            views_session.v1_cooldown,              name='v1_cooldown'),
    path('v1/session/conditioning/',                        views_session.v1_conditioning_session,  name='v1_conditioning_session'),
    path('v1/session/feedback/',                            views_session.v1_post_session_feedback, name='v1_post_session_feedback'),
    path('v1/session/complete/',                            views_session.v1_session_complete,      name='v1_session_complete'),
    path('v1/progress/',                                    views_progress.v1_progress_dashboard,   name='v1_progress'),
    path('v1/progress/api/',                                views_progress.v1_progress_api,         name='v1_progress_api'),
    path('v1/profile/',                                     views_progress.v1_profile,              name='v1_profile'),
    path('v1/test-exercises/',                              views_session.v1_test_list,             name='v1_test_list'),
    path('v1/test-exercise/<str:exercise_id>/',             views_session.v1_test_exercise,         name='v1_test_exercise'),
    path('api/analyze-frame/',                              views.analyze_frame,                    name='analyze_frame'),

    # ========================================================================
    # COACH DASHBOARD
    # ========================================================================
    path('coach/login/',                                              views_coach.coach_login,                    name='coach_login'),
    path('coach/logout/',                                             views_coach.coach_logout,                   name='coach_logout'),
    path('coach/squad/',                                              views_coach.coach_squad,                    name='coach_squad'),
    path('coach/athlete/<str:patient_id>/',                           views_coach.coach_athlete_detail,           name='coach_athlete_detail'),
    path('coach/athlete/<str:patient_id>/override/',                  views_coach.coach_override_prescription,    name='coach_override_prescription'),
    path('coach/athlete/<str:patient_id>/flag/',                      views_coach.coach_flag_review,              name='coach_flag_review'),
    path('coach/athlete/<str:patient_id>/competition/',               views_coach.coach_set_competition,          name='coach_set_competition'),
    path('coach/athlete/<str:patient_id>/notes/',                     views_coach.coach_save_notes,               name='coach_save_notes'),
    path('coach/add-athlete/',                                        views_coach.coach_add_athlete,              name='coach_add_athlete'),

    # ========================================================================
    # HOME & AUTHENTICATION
    # ========================================================================
    path('', views.home, name='home'),
    path('register/', views.patient_register, name='patient_register'),
    path('login/', views.patient_login, name='patient_login'),
    path('logout/', views.patient_logout, name='patient_logout'),
    
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ========================================================================
    # LEGACY — re-enabled (templates reference these routes)
    # ========================================================================
    path('gate-testing/', views.gate_testing, name='gate_testing'),
    path('execute-gate-test/<int:family_index>/<int:level_index>/', views.execute_gate_test, name='execute_gate_test'),
    path('save-gate-test-result/', views.save_gate_test_result, name='save_gate_test_result'),
    path('gate-test-results/', views.gate_test_results, name='gate_test_results'),
    path('prescription/', views.prescription, name='prescription'),
    path('daily-workout/', views.daily_workout, name='daily_workout'),
    path('execute-exercise/<int:exercise_index>/', views.execute_exercise, name='execute_exercise'),
    # path('save-exercise-results/', views.save_exercise_results, name='save_exercise_results'),
    path('workout-complete/', views.workout_complete, name='workout_complete'),
    path('progress-reports/', views.progress_reports, name='progress_reports'),
    path('generate-report/', views.generate_report, name='generate_report'),
    path('view-report/<int:report_id>/', views.view_report, name='view_report'),
    path('download-report/<int:report_id>/', views.download_report, name='download_report'),
    
    # ========================================================================
    # LEGAL PAGES
    # ========================================================================
    path('privacy/',        views.privacy_policy,   name='privacy_policy'),
    path('terms/',          views.terms_of_service, name='terms_of_service'),
    path('disclaimer/',     views.disclaimer,        name='disclaimer'),
    path('delete-account/', views.delete_account,   name='delete_account'),

    # ========================================================================
    # EXERCISE LIBRARY
    # ========================================================================
    path('exercises/', views.exercise_library, name='exercise_library'),
    path('exercises/<str:exercise_id>/', views.exercise_detail, name='exercise_detail'),
    path('exercises/<str:exercise_id>/execute/', views.exercise_execute, name='exercise_execute'),

    # ========================================================================
    # THERAPIST-DRIVEN PATIENT SESSION (B2B2C)
    # ========================================================================
    path('therapist-session/today/',                 views_thrx.therapist_session_today,     name='therapist_session_today'),
    path('therapist-session/start/',                 views_thrx.therapist_session_start,     name='therapist_session_start'),
    path('therapist-session/exercise/<int:idx>/',    views_thrx.therapist_session_exercise,  name='therapist_session_exercise'),
    path('therapist-session/feedback/<int:idx>/',    views_thrx.therapist_session_feedback,  name='therapist_session_feedback'),
    path('therapist-session/complete/',              views_thrx.therapist_session_complete,  name='therapist_session_complete'),
    path('therapist-session/finished/',              views_thrx.therapist_session_finished,  name='therapist_session_finished'),
    path('therapist-session/progress/',              views_thrx.therapist_session_progress,  name='therapist_session_progress'),
    path('therapist-session/profile/',               views_thrx.therapist_session_profile,   name='therapist_session_profile'),

    # ========================================================================
    # NUTRITION MODULE
    # ========================================================================
    path('nutrition/',                   views_nutrition.v1_nutrition_dashboard, name='v1_nutrition_dashboard'),
    path('nutrition/log/',               views_nutrition.v1_food_log,            name='v1_food_log'),
    path('nutrition/mess/',              views_nutrition.v1_mess_mode,           name='v1_mess_mode'),
    path('nutrition/api/search/',        views_nutrition.v1_food_search_api,     name='v1_food_search_api'),
    path('nutrition/api/quick-log/',     views_nutrition.v1_quick_log_api,       name='v1_quick_log_api'),

    # ========================================================================
    # PRE-MATCH STRETCHING
    # ========================================================================
    path('stretch-protocol/', views.stretch_protocol, name='stretch_protocol'),
    path('stretch-execute/<int:stretch_index>/', views.stretch_execute, name='stretch_execute'),
    path('save-stretch-result/', views.save_stretch_result, name='save_stretch_result'),
    path('stretch-complete/', views.stretch_complete, name='stretch_complete'),
    path('stretch-download-pdf/<int:session_id>/', views.stretch_download_pdf, name='stretch_download_pdf'),
]