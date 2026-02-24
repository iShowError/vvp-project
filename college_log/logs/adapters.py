from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from logs.models import UserProfile
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
            return

        try:
            # Use case-insensitive lookup for existing user
            customer = User.objects.get(email__iexact=user.email)
            sociallogin.connect(request, customer)
            # It's important to raise ImmediateHttpResponse to prevent allauth
            # from continuing to process the login and potentially creating a new user.
            # Here we'll just redirect to a page that can inform the user.
            # For a better UX, you might want to log them in directly.
            messages.info(request, f"Your social account has been connected to your existing account for {customer.email}.")
            raise ImmediateHttpResponse(redirect('login'))

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
