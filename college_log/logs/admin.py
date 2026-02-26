from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import Device, Log, Issue, Comment, UserProfile

# Inline for UserProfile to be edited alongside User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

# Custom User Admin with UserProfile inline
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'userprofile__role')
    
    def get_role(self, obj):
        try:
            return obj.userprofile.role
        except UserProfile.DoesNotExist:
            return "No Role"
    get_role.short_description = 'Role'

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Device)
class DeviceAdmin(SimpleHistoryAdmin):
    list_display = ("id", "name", "device_type", "location")
    search_fields = ("name", "device_type", "location")
    list_filter = ("device_type",)

@admin.register(Log)
class LogAdmin(SimpleHistoryAdmin):
    list_display = ("id", "device", "status", "created_at", "closed_at")
    list_filter = ("status", "device__device_type", "created_at")
    search_fields = ("description", "device__name")
    date_hierarchy = 'created_at'

@admin.register(Issue)
class IssueAdmin(SimpleHistoryAdmin):
    list_display = ("id", "device_type", "status", "dept_head_email", "created_at")
    list_filter = ("status", "device_type", "created_at")
    search_fields = ("description", "dept_head__email", "dept_head__username")
    readonly_fields = ("created_at",)
    date_hierarchy = 'created_at'
    list_per_page = 20
    
    def dept_head_email(self, obj):
        return obj.dept_head.email
    dept_head_email.short_description = 'Department Head'

@admin.register(Comment)
class CommentAdmin(SimpleHistoryAdmin):
    list_display = ("id", "issue_short", "engineer", "text_preview", "created_at")
    list_filter = ("created_at", "updated_at", "engineer")
    search_fields = ("text", "engineer__email", "engineer__username", "issue__description")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = 'created_at'
    list_per_page = 20
    
    def issue_short(self, obj):
        return f"{obj.issue.device_type} - {obj.issue.status}"
    issue_short.short_description = 'Issue'
    
    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comment Text'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "user_email", "user_date_joined")
    list_filter = ("role",)
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def user_date_joined(self, obj):
        return obj.user.date_joined
    user_date_joined.short_description = 'Date Joined'
