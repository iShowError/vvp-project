from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.mail import send_mail
from django.template.loader import render_to_string
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
    list_display = ("id", "device_type", "priority", "status", "sla_response_breached", "sla_resolution_breached", "dept_head_email", "created_at")
    list_filter = ("status", "priority", "device_type", "sla_response_breached", "sla_resolution_breached", "created_at")
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
    list_display = ("user", "role", "approval_status", "user_email", "user_date_joined")
    list_filter = ("role", "approval_status")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    actions = ['approve_selected_users', 'reject_selected_users']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def user_date_joined(self, obj):
        return obj.user.date_joined
    user_date_joined.short_description = 'Date Joined'

    @admin.action(description='Approve selected users')
    def approve_selected_users(self, request, queryset):
        count = 0
        for profile in queryset.filter(approval_status='pending'):
            user = profile.user
            user.is_active = True
            user.save(update_fields=['is_active'])
            profile.approval_status = 'approved'
            profile.save(update_fields=['approval_status'])
            try:
                login_url = request.build_absolute_uri('/login/')
                html_message = render_to_string('emails/user_approved.html', {
                    'email': user.email,
                    'login_url': login_url,
                })
                send_mail(
                    '[Issue Management System] Your account has been approved!',
                    f'Hello,\n\nYour account ({user.email}) has been approved by an administrator.\nYou can now log in and access your dashboard.\n\nThank you!',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                )
            except Exception:
                pass
            count += 1
        self.message_user(request, f'{count} user(s) approved and notified.')

    @admin.action(description='Reject selected users')
    def reject_selected_users(self, request, queryset):
        count = 0
        for profile in queryset.filter(approval_status='pending'):
            user = profile.user
            email = user.email
            profile.approval_status = 'rejected'
            profile.save(update_fields=['approval_status'])
            try:
                html_message = render_to_string('emails/user_rejected.html', {
                    'email': email,
                })
                send_mail(
                    '[Issue Management System] Registration not approved',
                    f'Hello,\n\nWe regret to inform you that your registration ({email}) was not approved by an administrator.\n\nIf you believe this was a mistake, please contact the admin directly.\n\nThank you.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                )
            except Exception:
                pass
            # user.delete() # Rejection should not be a destructive action
            count += 1
        self.message_user(request, f'{count} user(s) rejected and notified.')
