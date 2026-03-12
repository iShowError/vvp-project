from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('logs.api.urls')),
    path('', include('logs.urls')),
    path('accounts/', include('allauth.urls')),
]
