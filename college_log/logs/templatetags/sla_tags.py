from django import template

from logs.sla import get_sla_status

register = template.Library()


@register.simple_tag
def get_issue_sla(issue):
    """Returns SLA status dict for use in templates via {% get_issue_sla issue as sla %}."""
    return get_sla_status(issue)


@register.filter
def format_td(td):
    """Format a timedelta for compact display (e.g. '2d 3h', '4h 15m', '23m')."""
    if td is None:
        return ''
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        total_seconds = abs(total_seconds)

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days > 0:
        return f'{days}d {hours}h'
    elif hours > 0:
        return f'{hours}h {minutes}m'
    else:
        return f'{minutes}m'
