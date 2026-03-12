import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from logs.models import Issue

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check for SLA breaches and send email notifications'

    def handle(self, *args, **options):
        now = timezone.now()
        response_count = 0
        resolution_count = 0

        # Response SLA breaches: no first response yet, deadline passed
        response_breached = Issue.objects.filter(
            first_response_at__isnull=True,
            sla_response_deadline__lt=now,
            sla_response_breached=False,
            status='open',
        )
        for issue in response_breached:
            issue.sla_response_breached = True
            issue.save(update_fields=['sla_response_breached'])
            self._send_breach_email(issue, 'response', now)
            response_count += 1

        # Resolution SLA breaches: not resolved, deadline passed
        resolution_breached = Issue.objects.filter(
            status__in=['open', 'in_progress'],
            sla_resolution_deadline__lt=now,
            sla_resolution_breached=False,
        )
        for issue in resolution_breached:
            issue.sla_resolution_breached = True
            issue.save(update_fields=['sla_resolution_breached'])
            self._send_breach_email(issue, 'resolution', now)
            resolution_count += 1

        total = response_count + resolution_count
        self.stdout.write(
            self.style.SUCCESS(f'Done. {total} breach(es) found: {response_count} response, {resolution_count} resolution.')
        )

    def _send_breach_email(self, issue, breach_type, now):
        """Send SLA breach notification to the issue's department head."""
        if not issue.dept_head or not issue.dept_head.email:
            return

        if breach_type == 'response':
            deadline = issue.sla_response_deadline
            sla_type_display = 'First Response'
        else:
            deadline = issue.sla_resolution_deadline
            sla_type_display = 'Resolution'

        overdue_by = now - deadline if deadline else None

        subject = f'[SLA Breach] {sla_type_display} deadline missed — Issue #{issue.id}'
        plain_message = (
            f'SLA Breach Notification\n\n'
            f'An SLA deadline has been missed for one of your issues.\n\n'
            f'Issue #{issue.id}\n'
            f'Device: {issue.device_type}\n'
            f'Priority: {issue.get_priority_display()}\n'
            f'Status: {issue.get_status_display()}\n'
            f'SLA Type: {sla_type_display}\n'
            f'Deadline: {deadline.strftime("%Y-%m-%d %H:%M") if deadline else "N/A"}\n'
            f'Overdue By: {self._format_timedelta(overdue_by) if overdue_by else "N/A"}\n\n'
            f'Please follow up with the engineering team.'
        )

        html_message = render_to_string('emails/sla_breach.html', {
            'issue': issue,
            'sla_type': sla_type_display,
            'deadline': deadline,
            'overdue_by': self._format_timedelta(overdue_by) if overdue_by else 'N/A',
            'breach_type': breach_type,
        })

        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [issue.dept_head.email],
                html_message=html_message,
            )
        except Exception:
            logger.exception(
                'Failed to send SLA breach email for issue=%s type=%s',
                issue.id, breach_type,
            )

    @staticmethod
    def _format_timedelta(td):
        if td is None:
            return ''
        total_seconds = int(abs(td.total_seconds()))
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        if days > 0:
            return f'{days}d {hours}h'
        elif hours > 0:
            return f'{hours}h {minutes}m'
        return f'{minutes}m'
