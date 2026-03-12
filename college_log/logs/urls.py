from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('registration-pending/', views.registration_pending, name='registration_pending'),
    path('approve/<str:token>/', views.approve_user, name='approve_user'),
    path('reject/<str:token>/', views.reject_user, name='reject_user'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('engineer/dashboard/', views.engineer_dashboard, name='engineer_dashboard'),
    path('dept_head/dashboard/', views.dept_head_dashboard, name='dept_head_dashboard'),
    path('issues/<int:issue_id>/timeline/', views.issue_timeline, name='issue_timeline'),
]
