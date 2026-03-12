import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.db import IntegrityError, DatabaseError, transaction
from django.db.models import Q
from .models import Issue, Comment, UserProfile, Device, Log
from .forms import RegistrationForm, LoginForm, IssueForm, UpdateIssueForm
from .sla import set_sla_deadlines, check_response_sla, check_resolution_sla
from django.utils import timezone


ITEMS_PER_PAGE = 10

logger = logging.getLogger(__name__)


signer = TimestampSigner()


def _generate_approval_token(user_id, action):
    return signer.sign(f'{user_id}:{action}')


def _verify_approval_token(token, max_age=7 * 24 * 3600):
    try:
        value = signer.unsign(token, max_age=max_age)
        user_id_str, action = value.rsplit(':', 1)
        return int(user_id_str), action
    except (BadSignature, SignatureExpired, ValueError):
        return None, None


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
    # Atomically add key if not exists (returns True), otherwise create it
    if cache.add(key, 1, timeout=lockout_seconds):
        return 1
    # If key exists, atomically increment
    try:
        return cache.incr(key)
    except ValueError:
        # Key might have expired between add() and incr()
        cache.set(key, 1, timeout=lockout_seconds)
        return 1


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
    
    # Redirect admins to the admin panel
    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin:index')
    
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
                    user.is_active = False
                    user.save(update_fields=['is_active'])
                    UserProfile.objects.create(user=user, role=role, approval_status='pending')
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
                # Email all superusers with approve/reject links
                _send_approval_email_to_admins(request, user, role)

                # Store pending info in session for the pending page
                request.session['pending_email'] = email
                request.session['pending_role'] = role
                return redirect('registration_pending')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def _send_approval_email_to_admins(request, user, role):
    approve_token = _generate_approval_token(user.id, 'approve')
    reject_token = _generate_approval_token(user.id, 'reject')

    base_url = request.build_absolute_uri('/')[:-1]  # e.g. http://127.0.0.1:8000
    approve_url = f"{base_url}/approve/{approve_token}/"
    reject_url = f"{base_url}/reject/{reject_token}/"

    role_display = 'Engineer' if role == 'engineer' else 'Department Head'
    subject = f'[Issue Management System] New registration: {user.email}'
    plain_message = (
        f'A new user has registered and is awaiting your approval.\n\n'
        f'Email: {user.email}\n'
        f'Role: {role_display}\n'
        f'Registered at: {user.date_joined.strftime("%Y-%m-%d %H:%M")}\n\n'
        f'Approve: {approve_url}\n\n'
        f'Reject: {reject_url}\n\n'
        f'This link expires in 7 days.'
    )
    html_message = render_to_string('emails/admin_approval_request.html', {
        'email': user.email,
        'role': role_display,
        'registered_at': user.date_joined.strftime('%Y-%m-%d %H:%M'),
        'approve_url': approve_url,
        'reject_url': reject_url,
    })

    admin_emails = list(
        User.objects.filter(is_superuser=True)
        .values_list('email', flat=True)
        .exclude(email='')
    )
    if admin_emails:
        try:
            send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, admin_emails, html_message=html_message)
        except Exception:
            logger.exception("Failed to send approval email to admins for user=%s", user.email)


def registration_pending(request):
    email = request.session.pop('pending_email', None)
    role = request.session.pop('pending_role', None)
    if not email:
        return redirect('register')
    role_display = 'Engineer' if role == 'engineer' else 'Department Head'
    return render(request, 'registration_pending.html', {
        'email': email,
        'role': role_display,
    })


def approve_user(request, token):
    user_id, action = _verify_approval_token(token)
    if user_id is None or action != 'approve':
        return render(request, 'approval_result.html', {
            'success': False,
            'message': 'This approval link is invalid or has expired.',
        })

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return render(request, 'approval_result.html', {
            'success': False,
            'message': 'The user account no longer exists.',
        })

    profile = user.userprofile
    if profile.approval_status == 'approved':
        return render(request, 'approval_result.html', {
            'success': True,
            'message': f'{user.email} has already been approved.',
        })

    user.is_active = True
    user.save(update_fields=['is_active'])
    profile.approval_status = 'approved'
    profile.save(update_fields=['approval_status'])

    # Notify the user
    try:
        plain_message = (
            f'Hello,\n\n'
            f'Your account ({user.email}) has been approved by an administrator.\n'
            f'You can now log in and access your dashboard.\n\n'
            f'Thank you!'
        )
        html_message = render_to_string('emails/user_approved.html', {
            'email': user.email,
            'login_url': request.build_absolute_uri('/login/'),
        })
        send_mail(
            '[Issue Management System] Your account has been approved!',
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
        )
    except Exception:
        logger.exception("Failed to send approval notification to user=%s", user.email)

    return render(request, 'approval_result.html', {
        'success': True,
        'message': f'{user.email} has been approved and notified via email.',
    })


def reject_user(request, token):
    user_id, action = _verify_approval_token(token)
    if user_id is None or action != 'reject':
        return render(request, 'approval_result.html', {
            'success': False,
            'message': 'This rejection link is invalid or has expired.',
        })

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return render(request, 'approval_result.html', {
            'success': False,
            'message': 'The user account no longer exists.',
        })

    profile = user.userprofile
    if profile.approval_status == 'rejected':
        return render(request, 'approval_result.html', {
            'success': True,
            'message': f'{user.email} has already been rejected.',
        })

    email = user.email
    profile.approval_status = 'rejected'
    profile.save(update_fields=['approval_status'])

    # Notify the user before deleting
    try:
        plain_message = (
            f'Hello,\n\n'
            f'We regret to inform you that your registration ({email}) '
            f'was not approved by an administrator.\n\n'
            f'If you believe this was a mistake, please contact the admin directly.\n\n'
            f'Thank you.'
        )
        html_message = render_to_string('emails/user_rejected.html', {
            'email': email,
        })
        send_mail(
            '[Issue Management System] Registration not approved',
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=html_message,
        )
    except Exception:
        logger.exception("Failed to send rejection notification to user=%s", email)

    user.delete()

    return render(request, 'approval_result.html', {
        'success': True,
        'message': f'{email} has been rejected and notified via email.',
    })


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
                # Check if this is a pending/rejected user (inactive account)
                try:
                    inactive_user = User.objects.get(username=email, is_active=False)
                    profile = getattr(inactive_user, 'userprofile', None)
                    if profile and profile.approval_status == 'pending':
                        error_message = 'Your account is pending admin approval. Please wait for the confirmation email.'
                    elif profile and profile.approval_status == 'rejected':
                        error_message = 'Your registration was not approved. Please contact the administrator.'
                    else:
                        error_message = 'Your account is inactive. Please contact the administrator.'
                except User.DoesNotExist:
                    pass

                if not error_message:
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
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return redirect('home')

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
            if issue.status not in ['closed', 'completed', 'resolved']:
                Comment.objects.create(issue=issue, engineer=request.user, text=comment_text)
                # Track first response for SLA
                if not issue.first_response_at:
                    check_response_sla(issue)
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
            if comment.issue.status in ['closed', 'completed', 'resolved']:
                messages.error(request, 'Cannot edit a comment on a closed issue.')
                return redirect('engineer_dashboard')
            new_text = request.POST.get('edit_text')
            if new_text:
                comment.text = new_text
                comment.save()
                messages.success(request, 'Comment updated successfully.')
            return redirect('engineer_dashboard')
            
        if delete_id:
            comment = get_object_or_404(Comment, id=delete_id, engineer=request.user)
            if comment.issue.status in ['closed', 'completed', 'resolved']:
                messages.error(request, 'Cannot delete a comment on a closed issue.')
                return redirect('engineer_dashboard')
            comment.delete()
            messages.success(request, 'Comment deleted successfully.')
            return redirect('engineer_dashboard')

    issues_list = _engineer_visible_issues(request.user).order_by('-created_at').prefetch_related('comments__engineer')
    paginator = Paginator(issues_list, ITEMS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'engineer_dashboard.html', {'page_obj': page_obj, 'show_navbar': True})


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
                set_sla_deadlines(issue)
                messages.success(request, 'Issue submitted successfully!')
                return redirect('dept_head_dashboard')
        elif 'update_issue_id' in request.POST:
            update_issue_id = request.POST.get('update_issue_id')
            issue = get_object_or_404(Issue, id=update_issue_id, dept_head=request.user)
            if issue.status in ['completed', 'closed']:
                messages.error(request, 'This issue is already closed and cannot be updated.')
                return redirect('dept_head_dashboard')
            form = UpdateIssueForm(request.user, request.POST, instance=issue)
            if form.is_valid():
                old_status = issue.status
                issue = form.save()
                # Track resolution for SLA
                if issue.status in ('resolved', 'completed') and old_status not in ('resolved', 'completed', 'closed'):
                    check_resolution_sla(issue)
                if issue.status == 'completed':
                    messages.success(request, 'Issue closed successfully.')
                else:
                    messages.success(request, f'Issue status updated from "{old_status}" to "{issue.status}".')
                # Send email notification for status update
                send_mail(
                    subject='Issue Status Updated',
                    message=f'An issue status has been updated.\n\nDevice: {issue.device_type}\nDescription: {issue.description}\nStatus changed from "{old_status}" to "{issue.status}"\nBy: {issue.dept_head.email if issue.dept_head else "Deleted User"}',
                    from_email=None,
                    recipient_list=['adityakiratsata@gmail.com'],
                    fail_silently=True,
                )
            return redirect('dept_head_dashboard')

    issues_list = Issue.objects.filter(dept_head=request.user).order_by('-created_at').prefetch_related('comments__engineer')
    paginator = Paginator(issues_list, ITEMS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    form = IssueForm()
    return render(request, 'dept_head_dashboard.html', {'page_obj': page_obj, 'form': form, 'show_navbar': True})
