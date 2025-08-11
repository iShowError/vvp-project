from django.contrib import admin
from .models import Device, Log

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "device_type", "location")
    search_fields = ("name", "device_type", "location")

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "status", "created_at", "closed_at")
    list_filter = ("status", "device__device_type")
    search_fields = ("description", "device__name")
