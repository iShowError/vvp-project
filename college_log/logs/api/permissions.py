from rest_framework.permissions import BasePermission


class IsEngineer(BasePermission):
    """Allow access only to users with the 'engineer' role."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'userprofile')
            and request.user.userprofile.role == 'engineer'
        )


class IsDeptHead(BasePermission):
    """Allow access only to users with the 'dept_head' role."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'userprofile')
            and request.user.userprofile.role == 'dept_head'
        )


class IsIssueOwner(BasePermission):
    """Allow dept_head to access only their own issues."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.dept_head == request.user


class IsCommentAuthor(BasePermission):
    """Allow engineers to modify only their own comments."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.engineer == request.user


class IssueNotClosed(BasePermission):
    """Block writes on closed/completed issues."""
    message = 'Cannot modify a closed or completed issue.'

    def has_object_permission(self, request, view, obj):
        issue = getattr(obj, 'issue', obj)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return issue.status not in ('closed', 'completed')
