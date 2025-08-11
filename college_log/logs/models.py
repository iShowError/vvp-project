
from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    USER_ROLES = [
        ("engineer", "Engineer"),
        ("dept_head", "Department Head"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=USER_ROLES)
    def __str__(self):
        return f"{self.user.email} ({self.role})"

class Issue(models.Model):
    DEVICE_TYPES = [
        ("Computer", "Computer"),
        ("Printer", "Printer"),
        ("Projector", "Projector"),
        ("Network Switch", "Network Switch"),
        ("Access point", "Access point"),
    ]
    device_type = models.CharField(max_length=30, choices=DEVICE_TYPES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="open")
    dept_head = models.ForeignKey(User, on_delete=models.CASCADE, related_name="issues")
    def __str__(self):
        return f"{self.device_type} - {self.status} ({self.created_at})"

class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="comments")
    engineer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="engineer_comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Comment by {self.engineer.email} on {self.issue}"
from django.db import models

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

    def __str__(self):
        return f"{self.name} ({self.device_type}) - {self.location}"


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
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Log #{self.id} - {self.device.name} - {self.status}"
