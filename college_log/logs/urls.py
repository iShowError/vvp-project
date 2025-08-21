from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('engineer/dashboard/', views.engineer_dashboard, name='engineer_dashboard'),
    path('dept_head/dashboard/', views.dept_head_dashboard, name='dept_head_dashboard'),
]
