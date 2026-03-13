from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def set_sla_deadlines(issue):
    """Called when an issue is created. Sets response and resolution deadlines."""
    rules = settings.SLA_RULES.get(issue.priority, settings.SLA_RULES['medium'])
    issue.sla_response_deadline = issue.created_at + timedelta(hours=rules['first_response_hours'])
    issue.sla_resolution_deadline = issue.created_at + timedelta(hours=rules['resolution_hours'])
    issue.save(update_fields=['sla_response_deadline', 'sla_resolution_deadline'])


def check_response_sla(issue):
    """Called when the first engineer comment is added. Records response time."""
    if issue.first_response_at:
        return  # already responded
    issue.first_response_at = timezone.now()
    issue.save(update_fields=['first_response_at'])


def check_resolution_sla(issue):
    """Called when issue status changes to resolved/completed. Records resolution time."""
    if issue.resolved_at:
        return  # already recorded
    issue.resolved_at = timezone.now()
    issue.save(update_fields=['resolved_at'])


def get_sla_status(issue):
    """Returns SLA status dict for template display."""
    now = timezone.now()

    # Response SLA
    response_status = 'ok'
    if issue.sla_response_breached:
        response_status = 'breached'
    elif not issue.first_response_at and issue.sla_response_deadline:
        remaining_seconds = (issue.sla_response_deadline - now).total_seconds()
        if remaining_seconds <= 0:
            response_status = 'breached'
        elif remaining_seconds <= 3600:  # less than 1 hour
            response_status = 'warning'

    # Resolution SLA
    resolution_status = 'ok'
    if issue.sla_resolution_breached:
        resolution_status = 'breached'
    elif issue.status not in ('resolved', 'completed', 'closed') and issue.sla_resolution_deadline:
        remaining_seconds = (issue.sla_resolution_deadline - now).total_seconds()
        if remaining_seconds <= 0:
            resolution_status = 'breached'
        elif remaining_seconds <= 7200:  # less than 2 hours
            resolution_status = 'warning'

    # Remaining timedeltas for display
    response_remaining = None
    if issue.sla_response_deadline and not issue.first_response_at:
        response_remaining = issue.sla_response_deadline - now

    resolution_remaining = None
    if issue.sla_resolution_deadline and issue.status not in ('resolved', 'completed', 'closed'):
        resolution_remaining = issue.sla_resolution_deadline - now

    return {
        'response': response_status,
        'resolution': resolution_status,
        'response_deadline': issue.sla_response_deadline,
        'resolution_deadline': issue.sla_resolution_deadline,
        'response_remaining': response_remaining,
        'resolution_remaining': resolution_remaining,
    }
