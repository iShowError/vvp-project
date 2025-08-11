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
