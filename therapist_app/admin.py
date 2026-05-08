from django.contrib import admin

from .models import (
    Prescription,
    PrescriptionItem,
    ProgressReport,
    Therapist,
    TherapistMessage,
    TherapistPatientLink,
)


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'specialization', 'clinic_name', 'seat_limit', 'created_at')
    search_fields = ('full_name', 'user__username', 'clinic_name')


@admin.register(TherapistPatientLink)
class TherapistPatientLinkAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'therapist', 'status', 'primary_condition', 'invited_at')
    list_filter = ('status', 'condition_tone')
    search_fields = ('full_name', 'patient__username', 'therapist__full_name')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('link', 'week_number', 'is_published', 'updated_at')
    list_filter = ('week_number',)
    inlines = [PrescriptionItemInline]


@admin.register(TherapistMessage)
class TherapistMessageAdmin(admin.ModelAdmin):
    list_display = ('link', 'sender', 'sent_at')
    list_filter = ('sent_at',)


@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = ('link', 'title', 'status', 'generated_by', 'created_at')
    list_filter = ('status', 'generated_by')
