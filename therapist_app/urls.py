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
    path('reports/<int:report_id>/download/', views.download_report, name='therapist_download_report'),
    path('patient/<uuid:link_id>/reset-password/', views.reset_patient_password, name='therapist_reset_patient_password'),  # R2-U1
    path('patient/<uuid:link_id>/session-reports/<int:report_id>/', views.session_report_detail, name='therapist_session_report_detail'),  # R3
    path('patient/<uuid:link_id>/session-reports/<int:report_id>/pdf/', views.session_report_pdf, name='therapist_session_report_pdf_dl'),  # 2026-07 P1
    path('alerts/', views.alerts_inbox, name='therapist_alerts'),                                                            # R2-T2
    path('alerts/<int:alert_id>/reviewed/', views.alert_mark_reviewed, name='therapist_alert_reviewed'),                     # R2-T2
    path('patient/<uuid:link_id>/program/copy-week/', views.copy_previous_week, name='therapist_copy_week'),                 # R2-T3
    path('patient/<uuid:link_id>/notes/add/', views.add_visit_note, name='therapist_add_visit_note'),                        # R2-T7

    # 2026-07 dark camera coaches — QA surface (therapist-only, writes nothing)
    path('qa/dark-coaches/', views.qa_dark_coaches, name='therapist_qa_dark_coaches'),
    path('qa/dark-coaches/<str:key>/run/', views.qa_dark_coach_run, name='therapist_qa_dark_coach_run'),
]
