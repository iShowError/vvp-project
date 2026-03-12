from .models import Comment


# Display-friendly labels for history fields
STATUS_LABELS = dict([("open", "Open"), ("in_progress", "In Progress"), ("resolved", "Resolved"), ("completed", "Completed"), ("closed", "Closed")])
PRIORITY_LABELS = dict([("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")])

# Fields we care about when diffing issue history
TRACKED_ISSUE_FIELDS = {
    'status': ('bi-arrow-repeat', 'info', STATUS_LABELS),
    'priority': ('bi-exclamation-triangle', 'warning', PRIORITY_LABELS),
}


def get_issue_timeline(issue):
    """Build a chronological timeline of all events for an issue using django-simple-history."""
    timeline = []

    # --- Issue history ---
    history_records = list(issue.history.all().order_by('history_date'))
    prev = None
    for record in history_records:
        if record.history_type == '+':
            timeline.append({
                'type': 'created',
                'icon': 'bi-plus-circle-fill',
                'color': 'primary',
                'user': record.history_user,
                'message': f'Issue created — {record.device_type}',
                'timestamp': record.history_date,
            })
        elif record.history_type == '~' and prev:
            delta = record.diff_against(prev)
            for change in delta.changes:
                if change.field in TRACKED_ISSUE_FIELDS:
                    icon, color, labels = TRACKED_ISSUE_FIELDS[change.field]
                    old_label = labels.get(change.old, change.old)
                    new_label = labels.get(change.new, change.new)
                    timeline.append({
                        'type': f'{change.field}_change',
                        'icon': icon,
                        'color': color,
                        'user': record.history_user,
                        'message': f'{change.field.replace("_", " ").title()} changed from {old_label} → {new_label}',
                        'timestamp': record.history_date,
                    })
        prev = record

    # --- Comment history (existing comments) ---
    for comment in issue.comments.all():
        comment_history = list(comment.history.all().order_by('history_date'))
        for crecord in comment_history:
            if crecord.history_type == '+':
                text = crecord.text or ''
                preview = f'"{text[:80]}…"' if len(text) > 80 else f'"{text}"'
                timeline.append({
                    'type': 'comment_added',
                    'icon': 'bi-chat-dots-fill',
                    'color': 'secondary',
                    'user': crecord.history_user,
                    'message': f'Comment added: {preview}',
                    'timestamp': crecord.history_date,
                })
            elif crecord.history_type == '~':
                timeline.append({
                    'type': 'comment_edited',
                    'icon': 'bi-pencil',
                    'color': 'muted',
                    'user': crecord.history_user,
                    'message': 'Comment edited',
                    'timestamp': crecord.history_date,
                })

    # --- Deleted comments (no longer in DB, but in history) ---
    existing_comment_ids = set(issue.comments.values_list('id', flat=True))
    deleted_records = (
        Comment.history
        .filter(issue_id=issue.id, history_type='-')
        .exclude(id__in=existing_comment_ids)
        .order_by('history_date')
    )
    for dc in deleted_records:
        timeline.append({
            'type': 'comment_deleted',
            'icon': 'bi-trash',
            'color': 'danger',
            'user': dc.history_user,
            'message': 'Comment deleted',
            'timestamp': dc.history_date,
        })

    timeline.sort(key=lambda x: x['timestamp'])
    return timeline
