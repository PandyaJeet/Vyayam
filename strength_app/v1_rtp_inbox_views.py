"""S13 therapist inbox view (RTP). Behind RTP_ENABLED: 404 when off."""
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .rtp import inbox, notify
from .rtp.models import Notification
from .v1_coach_views import coach_required


@coach_required
def rtp_inbox(request):
    data = inbox.inbox_for(request.therapist)
    if data is None:
        raise Http404
    return render(request, 'strength_app/rtp_inbox.html', {**data, 'coach': request.therapist})


@coach_required
@require_POST
def rtp_inbox_read(request, notification_id):
    if inbox.inbox_for(request.therapist) is None:
        raise Http404
    row = get_object_or_404(Notification, pk=notification_id)
    notify.mark_read(row, actor=request.therapist)  # a non-recipient is denied and audited
    return redirect('rtp_inbox')
