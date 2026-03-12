from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from logs.models import Issue, Comment, UserProfile
from .serializers import (
    IssueListSerializer,
    IssueDetailSerializer,
    IssueCreateSerializer,
    IssueUpdateSerializer,
    CommentSerializer,
    UserProfileSerializer,
)
from .permissions import IsEngineer, IsDeptHead, IsCommentAuthor, IssueNotClosed
from .filters import IssueFilter


# ── helpers ───────────────────────────────────────────────────────────────────

def _visible_issues(user):
    """Return the queryset of issues a user is allowed to see."""
    if user.is_superuser:
        return Issue.objects.all()
    role = getattr(getattr(user, 'userprofile', None), 'role', None)
    if role == 'dept_head':
        return Issue.objects.filter(dept_head=user)
    if role == 'engineer':
        return Issue.objects.filter(
            Q(status__in=['open', 'in_progress', 'resolved'])
            | Q(comments__engineer=user)
        ).distinct()
    return Issue.objects.none()


# ── Issues ────────────────────────────────────────────────────────────────────

class IssueListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/issues/   — list issues visible to the current user
    POST /api/issues/   — dept_head creates a new issue
    """
    filterset_class = IssueFilter
    search_fields = ['description']
    ordering_fields = ['created_at', 'priority', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return IssueCreateSerializer
        return IssueListSerializer

    def get_queryset(self):
        return _visible_issues(self.request.user)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsDeptHead()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        from logs.sla import set_sla_deadlines
        issue = serializer.save(dept_head=self.request.user)
        set_sla_deadlines(issue)


class IssueDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/issues/<pk>/   — issue detail
    PATCH /api/issues/<pk>/   — update status/priority
    """
    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return IssueUpdateSerializer
        return IssueDetailSerializer

    def get_queryset(self):
        return _visible_issues(self.request.user)

    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT'):
            return [permissions.IsAuthenticated(), IssueNotClosed()]
        return [permissions.IsAuthenticated()]


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/issues/<pk>/comments/  — list comments on an issue
    POST /api/issues/<pk>/comments/  — engineer adds a comment
    """
    serializer_class = CommentSerializer

    def get_queryset(self):
        issue_pk = self.kwargs['pk']
        return Comment.objects.filter(issue_id=issue_pk).order_by('-created_at')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsEngineer()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        from logs.sla import check_response_sla
        from django.utils import timezone

        issue = Issue.objects.get(pk=self.kwargs['pk'])
        if issue.status in ('closed', 'completed', 'resolved'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Cannot comment on a closed/completed/resolved issue.')

        comment = serializer.save(issue=issue, engineer=self.request.user)

        # Track first response for SLA
        if not issue.first_response_at:
            issue.first_response_at = timezone.now()
            issue.save(update_fields=['first_response_at'])
            check_response_sla(issue)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/comments/<pk>/  — single comment
    PATCH  /api/comments/<pk>/  — edit own comment
    DELETE /api/comments/<pk>/  — delete own comment
    """
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()

    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT', 'DELETE'):
            return [permissions.IsAuthenticated(), IsCommentAuthor(), IssueNotClosed()]
        return [permissions.IsAuthenticated()]


# ── User profile ──────────────────────────────────────────────────────────────

class CurrentUserView(APIView):
    """GET /api/users/me/ — current user profile + role."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response({'detail': 'No profile found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
