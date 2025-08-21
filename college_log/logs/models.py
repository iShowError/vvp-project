
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class UserProfile(models.Model):
    USER_ROLES = [
        ("engineer", "Engineer"),
        ("dept_head", "Department Head"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    role = models.CharField(max_length=20, choices=USER_ROLES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} ({self.role})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

class Issue(models.Model):
    DEVICE_TYPES = [
        ("Computer", "Computer"),
        ("Printer", "Printer"),
        ("Projector", "Projector"),
        ("Network Switch", "Network Switch"),
        ("Access point", "Access point"),
    ]
    
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("completed", "Completed"),
        ("closed", "Closed"),
    ]
    
    device_type = models.CharField(max_length=30, choices=DEVICE_TYPES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    dept_head = models.ForeignKey(User, on_delete=models.CASCADE, related_name="issues")
    
    def __str__(self):
        return f"{self.device_type} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def get_comments_count(self):
        return self.comments.count()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Issue"
        verbose_name_plural = "Issues"

class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="comments")
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="engineer_comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Comment by {self.engineer.email} on Issue #{self.issue.id}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

class Device(models.Model):
    DEVICE_TYPES = [
        ("Computer", "Computer"),
        ("Projector", "Projector"),
        ("Printer", "Printer"),
        ("Other", "Other"),
    ]
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    location = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.device_type}) - {self.location}"
    
    class Meta:
        ordering = ['name']
        verbose_name = "Device"
        verbose_name_plural = "Devices"

class Log(models.Model):
    STATUS_CHOICES = [
        ("Open", "Open"),
        ("In Progress", "In Progress"),
        ("Closed", "Closed"),
    ]
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="logs")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Log #{self.id} - {self.device.name} - {self.status}"
    
    def save(self, *args, **kwargs):
        if self.status == "Closed" and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Log"
        verbose_name_plural = "Logs"
