"""
Therapist console permission gating.

- @therapist_required: Allows authenticated users with a Therapist record;
  rejects authenticated patients with 403; redirects logged-out users to login.
- get_linked_patient_or_404(therapist, link_id): Returns the
  TherapistPatientLink (status='active') or raises 404. All patient data
  reads MUST go through this helper to enforce the cross-therapist firewall.
"""

from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect

from .models import TherapistPatientLink


def therapist_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('therapist_login')
        if not hasattr(request.user, 'therapist'):
            return HttpResponseForbidden(
                "Therapist console is for licensed therapists only."
            )
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_linked_patient_or_404(therapist, link_id):
    """Returns the active TherapistPatientLink for this therapist + link_id,
    or raises 404. Used as the cross-therapist firewall."""
    return get_object_or_404(
        TherapistPatientLink,
        id=link_id,
        therapist=therapist,
        status='active',
    )
