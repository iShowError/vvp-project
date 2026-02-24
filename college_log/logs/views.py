import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import IntegrityError, DatabaseError, transaction
from django.db.models import Q
from .models import Issue, Comment, UserProfile, Device, Log
from .forms import RegistrationForm, LoginForm, IssueForm, UpdateIssueForm, CommentForm
from django.utils import timezone


logger = logging.getLogger(__name__)


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _login_throttle_key(email, ip_address):
    return f"login_fail:{email}:{ip_address}"


def _is_login_locked(email, ip_address):
    max_attempts = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
    key = _login_throttle_key(email, ip_address)
    failures = cache.get(key, 0)
    return failures >= max_attempts


def _record_failed_login(email, ip_address):
    lockout_seconds = getattr(settings, 'LOGIN_LOCKOUT_SECONDS', 900)
    key = _login_throttle_key(email, ip_address)
    failures = cache.get(key, 0) + 1
    cache.set(key, failures, timeout=lockout_seconds)
    return failures


def _clear_failed_logins(email, ip_address):
    key = _login_throttle_key(email, ip_address)
    cache.delete(key)


def _engineer_visible_issues(user):
    return Issue.objects.filter(
        Q(status__in=['open', 'in_progress', 'resolved']) |
        Q(comments__engineer=user)
    ).distinct()

def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        profile = request.user.userprofile
        if profile.role.lower() == 'engineer':
            return redirect('engineer_dashboard')
        elif profile.role.lower() == 'dept_head':
            return redirect('dept_head_dashboard')
        return redirect('logout')
    except UserProfile.DoesNotExist:
        return redirect('login')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                    )
                    UserProfile.objects.create(user=user, role=role)
            except IntegrityError:
                logger.warning(
                    "Registration conflict for email=%s; likely duplicate submission or race condition.",
                    email,
                )
                form.add_error('email', 'An account with this email already exists. Please log in instead.')
                messages.error(request, 'We could not create your account because this email is already registered.')
            except DatabaseError:
                logger.exception("Registration failed due to a database error for email=%s", email)
                form.add_error(None, 'We could not create your account right now. Please try again in a moment.')
                messages.error(request, 'We could not create your account right now. Please try again in a moment.')
            else:
                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            password = form.cleaned_data['password']
            ip_address = _get_client_ip(request)

            if _is_login_locked(email, ip_address):
                error_message = 'Too many failed login attempts. Please try again in 15 minutes.'
                logger.warning('Blocked login attempt for email=%s from ip=%s due to lockout.', email, ip_address)
                return render(request, 'login.html', {'form': form, 'error_message': error_message})

            user = authenticate(request, username=email, password=password)
            if user is not None:
                _clear_failed_logins(email, ip_address)
                login(request, user)
                return redirect('home')
            else:
                failures = _record_failed_login(email, ip_address)
                max_attempts = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
                if failures >= max_attempts:
                    error_message = 'Too many failed login attempts. Please try again in 15 minutes.'
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
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect('logout')
    if profile.role != 'engineer':
        return redirect('dept_head_dashboard')

    # Handle add, edit, delete comment
    if request.method == 'POST':
        issue_id = request.POST.get('issue_id')
        comment_text = request.POST.get('comment')
        edit_id = request.POST.get('edit_id')
        delete_id = request.POST.get('delete_id')
        
        if comment_text and issue_id:
            issue = get_object_or_404(_engineer_visible_issues(request.user), id=issue_id)
            if issue.status not in ['closed', 'completed']:
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
            else:
                messages.error(request, 'Cannot add comment to a closed issue.')
            return redirect('engineer_dashboard')
            
        if edit_id:
            comment = get_object_or_404(Comment, id=edit_id, engineer=request.user)
            new_text = request.POST.get('edit_text')
            if new_text:
                comment.text = new_text
                comment.save()
                messages.success(request, 'Comment updated successfully.')
            return redirect('engineer_dashboard')
            
        if delete_id:
            comment = get_object_or_404(Comment, id=delete_id, engineer=request.user)
            comment.delete()
            messages.success(request, 'Comment deleted successfully.')
            return redirect('engineer_dashboard')

    issues_list = _engineer_visible_issues(request.user).order_by('-created_at')
    paginator = Paginator(issues_list, 5)  # 5 issues per page
    page_number = request.GET.get('page')
    issues = paginator.get_page(page_number)
    return render(request, 'engineer_dashboard.html', {'issues': issues})


@login_required
def dept_head_dashboard(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect('logout')
    if profile.role != 'dept_head':
        return redirect('engineer_dashboard')

    if request.method == 'POST':
        if 'issue_submit' in request.POST:
            form = IssueForm(request.POST)
            if form.is_valid():
                issue = form.save(commit=False)
                issue.dept_head = request.user
                issue.save()
                messages.success(request, 'Issue submitted successfully!')
                return redirect('dept_head_dashboard')
        elif 'update_issue_id' in request.POST:
            update_issue_id = request.POST.get('update_issue_id')
            issue = get_object_or_404(Issue, id=update_issue_id, dept_head=request.user)
            form = UpdateIssueForm(request.user, request.POST, instance=issue)
            if form.is_valid():
                old_status = issue.status
                issue = form.save()
                if issue.status == 'completed':
                    messages.success(request, 'Issue closed successfully.')
                else:
                    messages.success(request, f'Issue status updated from "{old_status}" to "{issue.status}".')
                # Send email notification for status update
                send_mail(
                    subject='Issue Status Updated',
                    message=f'An issue status has been updated.\n\nDevice: {issue.device_type}\nDescription: {issue.description}\nStatus changed from "{old_status}" to "{issue.status}"\nBy: {issue.dept_head.email}',
                    from_email=None,
                    recipient_list=['adityakiratsata@gmail.com'],
                    fail_silently=True,
                )
            return redirect('dept_head_dashboard')

    issues_list = Issue.objects.filter(dept_head=request.user).order_by('-created_at')
    paginator = Paginator(issues_list, 5)  # 5 issues per page
    page_number = request.GET.get('page')
    issues = paginator.get_page(page_number)
    form = IssueForm()
    return render(request, 'dept_head_dashboard.html', {'issues': issues, 'form': form})
