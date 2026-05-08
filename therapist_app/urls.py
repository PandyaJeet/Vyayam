from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path('login/', views.therapist_login, name='therapist_login'),
    path('logout/', views.therapist_logout, name='therapist_logout'),

    # Top-level pages
    path('', views.dashboard, name='therapist_root'),
    path('dashboard/', views.dashboard, name='therapist_dashboard'),
    path('patients/', views.patient_list, name='therapist_patient_list'),
    path('library/', views.library, name='therapist_library'),
    path('reports/', views.reports, name='therapist_reports'),
    path('settings/', views.settings_page, name='therapist_settings'),

    # Invite + accept
    path('patients/invite/', views.invite_patient, name='therapist_invite_patient'),
    path('patients/<uuid:link_id>/accept/', views.simulate_accept_invite, name='therapist_simulate_accept'),

    # Patient detail (tab via ?tab=)
    path('patient/<uuid:link_id>/', views.patient_detail, name='therapist_patient_detail'),
    path('patient/<uuid:link_id>/onboarding/save/', views.save_onboarding, name='therapist_save_onboarding'),
    path('patient/<uuid:link_id>/program/save/', views.save_program, name='therapist_save_program'),
    path('patient/<uuid:link_id>/messages/send/', views.send_message, name='therapist_send_message'),
    path('patient/<uuid:link_id>/reports/generate/', views.generate_report, name='therapist_generate_report'),
]
