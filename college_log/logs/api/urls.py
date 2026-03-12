from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from . import views

urlpatterns = [
    # Auth
    path('auth/token/', obtain_auth_token, name='api_token_auth'),

    # Issues
    path('issues/', views.IssueListCreateView.as_view(), name='api_issue_list'),
    path('issues/<int:pk>/', views.IssueDetailView.as_view(), name='api_issue_detail'),
    path('issues/<int:pk>/comments/', views.CommentListCreateView.as_view(), name='api_issue_comments'),

    # Comments
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='api_comment_detail'),

    # Users
    path('users/me/', views.CurrentUserView.as_view(), name='api_current_user'),

    # Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
