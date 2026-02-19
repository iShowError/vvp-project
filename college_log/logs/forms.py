from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Issue, Device, Comment

class RegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    role = forms.ChoiceField(choices=UserProfile.USER_ROLES)

    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists. Please log in or use a different email.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        
        role = cleaned_data.get('role')
        email = cleaned_data.get('email')

        if email and role:
            # Validate email format based on role
            if role == 'engineer':
                # Engineers: must end with @vvpedulink.ac.in
                if not email.endswith('@vvpedulink.ac.in'):
                    raise forms.ValidationError('Engineers must use an email ending with @vvpedulink.ac.in')
                    
            elif role == 'dept_head':
                # Department Heads: must start with {it,ce,bt,me,ch,ec,cv}hod and end with @vvpedulink.ac.in
                valid_depts = ['it', 'ce', 'bt', 'me', 'ch', 'ec', 'cv']
                valid_prefixes = [f'{dept}hod' for dept in valid_depts]
                
                if not email.endswith('@vvpedulink.ac.in'):
                    raise forms.ValidationError('Department heads must use an email ending with @vvpedulink.ac.in')
                
                username_part = email.split('@')[0]
                if not any(username_part.startswith(prefix) for prefix in valid_prefixes):
                    valid_formats = ', '.join([f'{prefix}@vvpedulink.ac.in' for prefix in valid_prefixes])
                    raise forms.ValidationError(
                        f'Department heads must use an email starting with one of: {valid_formats}'
                    )
        
        return cleaned_data

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class IssueForm(forms.ModelForm):
    """Form for creating new issues with proper choices enforcement"""
    
    class Meta:
        model = Issue
        fields = ['device_type', 'description']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enforce choices at form level using model choices
        self.fields['device_type'] = forms.ChoiceField(
            choices=Issue.DEVICE_TYPES,
            widget=forms.Select(attrs={'class': 'form-control'})
        )
        self.fields['description'] = forms.CharField(
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
        )

class UpdateIssueForm(forms.ModelForm):
    """Form for updating issues with role-based field restrictions"""
    
    class Meta:
        model = Issue
        fields = ['status']
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Get user role
        try:
            user_profile = user.userprofile
            user_role = user_profile.role
        except UserProfile.DoesNotExist:
            user_role = None
        
        # Role-based field restrictions
        if user_role == 'engineer':
            # Engineers can only change status
            self.fields['status'] = forms.ChoiceField(
                choices=[
                    ('open', 'Open'),
                    ('in_progress', 'In Progress'),
                    ('resolved', 'Resolved'),
                ],
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        elif user_role == 'dept_head':
            # Department heads can only mark as completed
            self.fields['status'] = forms.ChoiceField(
                choices=[
                    ('completed', 'Completed'),
                ],
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        else:
            # Default fallback
            self.fields['status'] = forms.ChoiceField(
                choices=[('open', 'Open')],
                widget=forms.Select(attrs={'class': 'form-control'})
            )

class DeviceForm(forms.ModelForm):
    """Form for creating/updating devices with proper choices enforcement"""
    
    class Meta:
        model = Device
        fields = ['name', 'device_type', 'location']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enforce choices at form level using model choices
        self.fields['device_type'] = forms.ChoiceField(
            choices=Device.DEVICE_TYPES,
            widget=forms.Select(attrs={'class': 'form-control'})
        )
        self.fields['name'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'form-control'})
        )
        self.fields['location'] = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'form-control'})
        )

class CommentForm(forms.ModelForm):
    """Form for creating/updating comments"""
    
    class Meta:
        model = Comment
        fields = ['text']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'] = forms.CharField(
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        )
