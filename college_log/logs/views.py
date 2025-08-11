from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Issue, Comment, UserProfile
from .forms import RegistrationForm, LoginForm
from django.utils import timezone

def index(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # Only dept_head can submit complaints
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect('logout')
    if profile.role != 'dept_head':
        # Redirect engineers to their dashboard
        return redirect('engineer_dashboard')
    if request.method == 'POST':
        device_type = request.POST.get('device')
        description = request.POST.get('description')
        if device_type and description:
            issue = Issue.objects.create(
                device_type=device_type,
                description=description,
                dept_head=request.user
            )
            # Send email notification
            send_mail(
                subject='New Issue Created',
                message=f'A new issue has been created.\n\nDevice: {issue.device_type}\nDescription: {issue.description}\nBy: {issue.dept_head.email}',
                from_email=None,
                recipient_list=['adityakiratsata@gmail.com'],
                fail_silently=True,
            )
            return redirect('dept_head_dashboard')
    device_types = [dt[0] for dt in Issue.DEVICE_TYPES]
    return render(request, "index.html", {"device_types": device_types})

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            user = User.objects.create_user(username=email, email=email, password=password)
            UserProfile.objects.create(user=user, role=role)
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                # Redirect to dashboard based on role
                try:
                    profile = user.userprofile
                    if profile.role == 'engineer':
                        return redirect('engineer_dashboard')
                    elif profile.role == 'dept_head':
                        return redirect('dept_head_dashboard')
                except UserProfile.DoesNotExist:
                    error_message = "Your account is missing a role. Please contact the administrator."
            else:
                error_message = "The email or password you entered is incorrect. Please try again."
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form, 'error_message': error_message})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def engineer_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect('logout')
    if profile.role != 'engineer':
        return redirect('dept_head_dashboard')

    # Handle add, edit, delete comment
    if request.method == 'POST':
        issue_id = request.GET.get('issue_id')
        comment_text = request.POST.get('comment')
        edit_id = request.POST.get('edit_id')
        delete_id = request.POST.get('delete_id')
        if comment_text and issue_id:
            issue = Issue.objects.filter(id=issue_id).first()
            if issue:
                Comment.objects.create(issue=issue, engineer=request.user, text=comment_text)
                messages.success(request, 'Comment added successfully.')
                # Send email notification for new comment
                send_mail(
                    subject='New Comment Added',
                    message=f'A new comment was added to issue (Device: {issue.device_type}).\n\nComment: {comment_text}\nBy: {request.user.email}',
                    from_email=None,
                    recipient_list=['adityakiratsata@gmail.com'],
                    fail_silently=True,
                )
            return redirect('engineer_dashboard')
        if edit_id:
            comment = Comment.objects.filter(id=edit_id, engineer=request.user).first()
            if comment:
                new_text = request.POST.get('edit_text')
                if new_text:
                    comment.text = new_text
                    comment.save()
                    messages.success(request, 'Comment updated successfully.')
            return redirect('engineer_dashboard')
        if delete_id:
            comment = Comment.objects.filter(id=delete_id, engineer=request.user).first()
            if comment:
                comment.delete()
                messages.success(request, 'Comment deleted successfully.')
            return redirect('engineer_dashboard')

    issues_list = Issue.objects.all().order_by('-created_at')
    paginator = Paginator(issues_list, 5)  # 5 issues per page
    page_number = request.GET.get('page')
    issues = paginator.get_page(page_number)
    return render(request, 'engineer_dashboard.html', {'issues': issues})

@login_required
def dept_head_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect('logout')
    if profile.role != 'dept_head':
        return redirect('engineer_dashboard')

    # Handle close issue
    if request.method == 'POST':
        close_issue_id = request.GET.get('close_issue_id')
        if close_issue_id:
            issue = Issue.objects.filter(id=close_issue_id, dept_head=request.user).first()
            if issue and issue.status == 'open':
                issue.status = 'closed'
                issue.save()
                messages.success(request, 'Issue closed successfully.')
                # Send email notification for closed issue
                send_mail(
                    subject='Issue Closed',
                    message=f'An issue has been closed.\n\nDevice: {issue.device_type}\nDescription: {issue.description}\nBy: {issue.dept_head.email}',
                    from_email=None,
                    recipient_list=['adityakiratsata@gmail.com'],
                    fail_silently=True,
                )
            return redirect('dept_head_dashboard')

    issues_list = Issue.objects.filter(dept_head=request.user).order_by('-created_at')
    paginator = Paginator(issues_list, 5)  # 5 issues per page
    page_number = request.GET.get('page')
    issues = paginator.get_page(page_number)
    return render(request, 'dept_head_dashboard.html', {'issues': issues})
