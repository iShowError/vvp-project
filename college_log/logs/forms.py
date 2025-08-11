from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class RegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=UserProfile.USER_ROLES)

    class Meta:
        model = User
        fields = ('email', 'password')

    def clean_email(self):
        allowed_emails = [
            '23it059.aditya.kiratsata@vvpedulink.ac.in',
            'ithod@vvpedulink.ac.in',
        ]
        email = self.cleaned_data['email']
        if email not in allowed_emails:
            raise forms.ValidationError('Registration is currently limited to authorized college emails only. If you believe this is an error, please contact the administrator.')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please log in or use a different email.')
        return email

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
