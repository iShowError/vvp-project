from django.contrib import admin
from .models import Device, Log, Issue, Comment, UserProfile

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "device_type", "location")
    search_fields = ("name", "device_type", "location")

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "status", "created_at", "closed_at")
    list_filter = ("status", "device__device_type")
    search_fields = ("description", "device__name")

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("id", "device_type", "status", "created_at", "dept_head")
    list_filter = ("status", "device_type", "created_at")
    search_fields = ("description", "device_type")
    readonly_fields = ("created_at",)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "issue", "engineer", "created_at", "text")
    list_filter = ("created_at", "engineer")
    search_fields = ("text", "engineer__email")
    readonly_fields = ("created_at", "updated_at")

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__email", "user__username")
