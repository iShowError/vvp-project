from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import IntegrityError
from .models import Issue, Comment, UserProfile, Device, Log
from .forms import RegistrationForm, LoginForm, IssueForm, UpdateIssueForm, CommentForm
from django.utils import timezone

def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        profile = request.user.userprofile
        if profile.role == 'engineer':
            return redirect('engineer_dashboard')
        elif profile.role == 'dept_head':
            return redirect('dept_head_dashboard')
        return redirect('logout')
    except UserProfile.DoesNotExist:
        return redirect('login')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            user = User.objects.create_user(username=email, email=email, password=password)
            UserProfile.objects.create(user=user, role=role)
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
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
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
            issue = get_object_or_404(Issue, id=issue_id)
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

    issues_list = Issue.objects.all().order_by('-created_at')
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
