from django.shortcuts import render, redirect
from .models import Device, Log
from django.utils import timezone

def index(request):
    devices = Device.objects.all()

    if request.method == "POST":
        device_id = request.POST.get("device")
        description = request.POST.get("description")
        device = Device.objects.get(id=device_id)

        Log.objects.create(
            device=device,
            description=description,
            created_at=timezone.now()
        )
        return redirect("index")

    return render(request, "index.html", {"devices": devices})
