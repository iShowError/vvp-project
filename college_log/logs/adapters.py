from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from logs.models import UserProfile
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
            return

        try:
            customer = User.objects.get(email=user.email)
            sociallogin.connect(request, customer)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        email = sociallogin.user.email
        if not email.endswith('@vvpedulink.ac.in'):
            messages.error(request, "Only users with a '@vvpedulink.ac.in' email address can register.")
            raise ImmediateHttpResponse(redirect('login'))

        user = super().save_user(request, sociallogin, form)
        
        username_part = email.split('@')[0]
        valid_depts = ['it', 'ce', 'bt', 'me', 'ch', 'ec', 'cv']
        valid_prefixes = [f'{dept}hod' for dept in valid_depts]
        if any(username_part.startswith(prefix) for prefix in valid_prefixes):
            role = 'dept_head'
        else:
            role = 'engineer'
        
        UserProfile.objects.update_or_create(user=user, defaults={'role': role})
        return user
