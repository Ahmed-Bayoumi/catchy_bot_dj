# Views in this file:
# 1. Authentication: login, logout
# 2. Profile: view, edit
# 3. Password: change, reset
# 4. User Management: list, detail, create, edit, delete
#
# View types:
# - Function-based views (FBV) - simple and clear
# - Uses Django's built-in authentication system


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from .models import User, UserProfile
from .forms import (
    LoginForm,
    UserProfileForm,
    UserEditForm,
    UserCreateForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm
)
from .decorators import admin_required


# HELPER FUNCTIONS
def get_client_ip(request):
    """
    Get user's IP address from request

    Checks X-Forwarded-For header first (for proxies/load balancers)
    Falls back to REMOTE_ADDR
    Example:
        ip = get_client_ip(request)
        user.last_login_ip = ip
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs (proxy chain)
        # First one is the original client IP
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Direct connection (no proxy)
        ip = request.META.get('REMOTE_ADDR')
    return ip



# AUTHENTICATION VIEWS
@never_cache
def login_view(request):
    """
    User login page

    GET: Display login form
    POST: Process login credentials

    Features:
    - Email + password authentication
    - Remember me checkbox (30 days vs session)
    - Redirect to 'next' parameter or dashboard
    - Track login count and IP
    - Show error messages for invalid credentials

    URL: /accounts/login/
    Template: templates/accounts/login.html
    """
    # If already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember = form.cleaned_data.get('remember', False)

            # Authenticate user (check email + password)
            # Returns User object if valid, None if invalid
            user = authenticate(request, username=email, password=password)

            if user is not None:
                # Check if user is active
                if not user.is_active:
                    messages.error(
                        request,
                        _('Your account is inactive. Please contact administrator.')
                    )
                    return render(request, 'accounts/login.html', {'form': form})

                # Login user (creates session)
                login(request, user)

                if remember:
                    # Session expires in 30 days
                    request.session.set_expiry(30 * 24 * 60 * 60)
                else:
                    # Session expires when browser closes
                    request.session.set_expiry(0)

                # Track login activity
                ip_address = get_client_ip(request)
                user.increment_login_count(ip_address=ip_address)

                # Success message
                messages.success(
                    request,
                    _('Welcome back, {}!').format(user.get_full_name())
                )

                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('core:dashboard')

            else:
                # Invalid credentials
                messages.error(
                    request,
                    _('Invalid email or password. Please try again.')
                )
        else:
            # Form validation errors
            messages.error(request, _('Please correct the errors below.'))

    else:
        # GET request - show empty form
        form = LoginForm()

    context = {
        'form': form,
        'page_title': _('Login'),
    }

    return render(request, 'accounts/login.html', context)


@login_required
def logout_view(request):
    """
    Logs out current user and redirects to login page

    Features:
    - Clears session data
    - Shows success message
    - Redirects to login

    URL: /accounts/logout/

    Security:
    - Requires login (cannot logout if not logged in)
    - CSRF protection (should be POST in production)
    """
    # Store user name before logout (for message)
    user_name = request.user.get_full_name()

    # Logout user (clears session)
    logout(request)

    # Success message
    messages.success(
        request,
        _('You have been logged out successfully. See you soon, {}!').format(user_name)
    )

    # Redirect to login page
    return redirect('accounts:login')



# PROFILE VIEWS
@login_required
def profile_view(request):
    """
    User profile page

    Features:
    - Personal information
    - Profile details
    - Performance statistics
    - Activity tracking
    - Edit button

    URL: /accounts/profile/
    Template: templates/accounts/profile.html
    """
    user = request.user
    profile = user.profile

    # Calculate performance metrics
    conversion_rate = user.get_conversion_rate()
    win_rate = user.get_win_rate()
    performance_score = user.get_performance_score()

    context = {
        'user': user,
        'profile': profile,
        'conversion_rate': conversion_rate,
        'win_rate': win_rate,
        'performance_score': performance_score,
        'page_title': _('My Profile'),
    }

    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """
    Features:
    - Edit personal information (name, phone, etc.)
    - Update profile details (bio, address, etc.)
    - Change avatar
    - Update preferences (theme, language, notifications)

    URL: /accounts/profile/edit/
    Template: templates/accounts/profile_edit.html

    Forms:
    - UserEditForm: User model fields
    - UserProfileForm: Profile model fields

    Validation:
    - Email uniqueness
    - Phone format
    - Avatar file size/type
    """
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        # Two forms: one for User, one for Profile
        user_form = UserEditForm(
            request.POST,
            request.FILES,
            instance=user
        )
        profile_form = UserProfileForm(
            request.POST,
            instance=profile
        )

        # Validate both forms
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(
                request,
                _('Your profile has been updated successfully!')
            )
            return redirect('accounts:profile')

        else:
            messages.error(
                request,
                _('Please correct the errors below.')
            )

    else:
        # GET request - show forms with current data
        user_form = UserEditForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user': user,
        'profile': profile,
        'page_title': _('Edit Profile'),
    }

    return render(request, 'accounts/profile_edit.html', context)


# PASSWORD MANAGEMENT VIEWS
@login_required
def password_change_view(request):
    """
    GET: Display password change form
    POST: Process password change

    Features:
    - Verify old password
    - Validate new password
    - Password strength requirements
    - Keep user logged in after change

    URL: /accounts/password/change/
    Template: templates/accounts/password_change.html
    """
    if request.method == 'POST':
        # Django's built-in password change form
        form = PasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()

            # Update session (keep user logged in)
            update_session_auth_hash(request, user)
            messages.success(
                request,
                _('Your password has been changed successfully!')
            )
            return redirect('accounts:profile')

        else:
            messages.error(
                request,
                _('Please correct the errors below.')
            )

    else:
        # GET request - show empty form
        form = PasswordChangeForm(user=request.user)

    context = {
        'form': form,
        'page_title': _('Change Password'),
    }

    return render(request, 'accounts/password_change.html', context)


@never_cache
def password_reset_request_view(request):          #################################################
    """
    Password reset request (for logged-out users)

    GET: Display email input form
    POST: Send reset email

    Features:
    - Enter email address
    - Send reset link via email
    - Secure token generation
    - Token expires in 24 hours

    URL: /accounts/password/reset/
    Template: templates/accounts/password_reset.html

    Flow:
    1. User enters email
    2. System checks if email exists
    3. Generates secure token
    4. Sends email with reset link
    5. Link format: /accounts/password/reset/<uid>/<token>/

    Security:
    - Rate limiting (prevent spam)
    - Same message for valid/invalid email (prevent email enumeration)
    - Token expires after use or 24 hours

    Example POST data:
    {
        'email': 'ahmed@clinic.com'
    }

    Note: Will be fully implemented in Phase 9 (Email Configuration)
    For now, shows success message but doesn't send actual email
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            # Check if user exists
            try:
                user = User.objects.get(email=email, is_active=True)

                # TODO: Generate reset token and send email
                # This will be implemented in Phase 9
                # from django.contrib.auth.tokens import default_token_generator
                # from django.utils.http import urlsafe_base64_encode
                # from django.utils.encoding import force_bytes

                # token = default_token_generator.make_token(user)
                # uid = urlsafe_base64_encode(force_bytes(user.pk))
                # reset_url = request.build_absolute_uri(
                #     reverse('accounts:password_reset_confirm',
                #             kwargs={'uidb64': uid, 'token': token})
                # )

                # Send email with reset_url
                # send_password_reset_email(user, reset_url)

                pass  # Placeholder

            except User.DoesNotExist:
                # Don't reveal if email exists or not (security)
                pass

            # Always show success message (even if email doesn't exist)
            # This prevents email enumeration attacks
            messages.success(
                request,
                _('If an account exists with this email, you will receive '
                  'password reset instructions shortly.')
            )

            return redirect('accounts:login')

    else:
        # GET request - show form
        form = PasswordResetRequestForm()

    context = {
        'form': form,
        'page_title': _('Reset Password'),
    }

    return render(request, 'accounts/password_reset.html', context)


@never_cache
def password_reset_confirm_view(request, uidb64, token):             ##########################################################
    """
    Password reset confirmation (from email link)

    GET: Display new password form
    POST: Set new password

    Features:
    - Verify reset token
    - Set new password
    - Token expires after use
    - Auto-login after reset

    URL: /accounts/password/reset/<uidb64>/<token>/
    Template: templates/accounts/password_reset_confirm.html

    Parameters:
    - uidb64: Base64 encoded user ID
    - token: Password reset token

    Example URL:
    /accounts/password/reset/MQ/5xz-abc123def456/

    Security:
    - Token valid only once
    - Token expires in 24 hours
    - CSRF protection

    Note: Will be fully implemented in Phase 9
    """
    # TODO: Implement token verification
    # from django.contrib.auth.tokens import default_token_generator
    # from django.utils.http import urlsafe_base64_decode

    # Verify token
    # try:
    #     uid = urlsafe_base64_decode(uidb64).decode()
    #     user = User.objects.get(pk=uid)
    # except (TypeError, ValueError, OverflowError, User.DoesNotExist):
    #     user = None

    # if user and default_token_generator.check_token(user, token):
    #     # Token valid
    #     ...
    # else:
    #     # Token invalid or expired
    #     messages.error(request, 'Invalid or expired reset link.')
    #     return redirect('accounts:password_reset')

    messages.info(
        request,
        _('Password reset feature coming soon in Phase 9.')
    )
    return redirect('accounts:login')


# USER MANAGEMENT VIEWS (Admin Only)
@login_required
@admin_required
def user_list_view(request):             #################################################
    """
    List all users in company (Admin only)

    Features:
    - Paginated list
    - Search by name, email, phone
    - Filter by role, status
    - Sort by various fields
    - Quick actions (activate/deactivate)

    URL: /accounts/users/
    Template: templates/accounts/user_list.html

    Query parameters:
    - q: Search query
    - role: Filter by role (admin/agent)
    - status: Filter by status (active/inactive)
    - sort: Sort field (name/email/joined)
    - page: Page number
    """
    company = request.user.company

    queryset = User.objects.filter(company=company)

    # Search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter in ['admin', 'agent']:
        queryset = queryset.filter(role=role_filter)

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)

    # Sort
    sort_by = request.GET.get('sort', '-date_joined')
    valid_sort_fields = ['first_name', 'email', 'date_joined', 'login_count']
    if sort_by.lstrip('-') in valid_sort_fields:
        queryset = queryset.order_by(sort_by)

    # Statistics
    total_users = queryset.count()
    active_users = queryset.filter(is_active=True).count()
    inactive_users = queryset.filter(is_active=False).count()

    # Pagination (25 per page)
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'page_title': _('Users'),
    }

    return render(request, 'accounts/user_list.html', context)


@login_required
def user_detail_view(request, pk):
    """
    View detailed information about a user
    """
    viewed_user = get_object_or_404(User, pk=pk)

    # Permission check
    if not request.user.is_admin() and viewed_user != request.user:
        messages.error(
            request,
            _('You do not have permission to view this user.')
        )
        return redirect('accounts:profile')

    # Check if user belongs to same company (for admins)
    if request.user.is_admin() and viewed_user.company != request.user.company:
         messages.error(
             request,
             _('User not found.')
         )
         return redirect('accounts:user_list')

    profile = viewed_user.profile

    # Performance metrics
    conversion_rate = viewed_user.get_conversion_rate()
    win_rate = viewed_user.get_win_rate()
    performance_score = viewed_user.get_performance_score()

    context = {
        'viewed_user': viewed_user,
        'profile': profile,
        'conversion_rate': conversion_rate,
        'win_rate': win_rate,
        'performance_score': performance_score,
        'page_title': viewed_user.get_full_name(),
    }

    return render(request, 'accounts/user_detail.html', context)

@login_required
@admin_required
def user_create_view(request):
    """
    Create new user (Admin only)

    Features:
    - Set user role (admin/agent)
    - Set initial password (user can change later)
    - Auto-assign to admin's company
    - Send welcome email (Phase 9)

    URL: /accounts/users/create/
    Template: templates/accounts/user_form.html

    Form fields:
    - email
    - first_name
    - last_name
    - phone
    - role
    - password1
    - password2

    Validation:
    - Email uniqueness
    - Password strength
    - Required fields
    """
    if request.method == 'POST':
        form = UserCreateForm(request.POST)

        if form.is_valid():
            # Create user (don't save yet)
            user = form.save(commit=False)

            # Assign to admin's company
            # user.company = request.user.company

            # Save user
            user.save()

            # Success message
            messages.success(
                request,
                _('User {} has been created successfully!').format(user.get_full_name())
            )

            # TODO: Send welcome email (Phase 9)

            # Redirect to user detail
            return redirect('accounts:user_detail', pk=user.pk)

        else:
            messages.error(request, _('Please correct the errors below.'))

    else:
        form = UserCreateForm()

    context = {
        'form': form,
        'form_title': _('Create User'),
        'submit_text': _('Create'),
        'page_title': _('Create User'),
    }

    return render(request, 'accounts/user_form.html', context)


@login_required
def user_edit_view(request, pk):
    """
    Edit user (Admin or own profile)

    Access control:
    - Admin: Can edit any user in company
    - Agent: Can only edit own profile

    URL: /accounts/users/<pk>/edit/
    Template: templates/accounts/user_form.html

    Restrictions:
    - Agents cannot change role
    - Agents cannot activate/deactivate
    - Cannot change email (security)
    """
    user = get_object_or_404(User, pk=pk)

    # Permission check
    can_edit_all_fields = request.user.is_admin()
    can_edit = can_edit_all_fields or user == request.user

    if not can_edit:
        return HttpResponseForbidden(_('You do not have permission to edit this user.'))

    # Check company
    # if request.user.is_admin() and user.company != request.user.company:
    #     return HttpResponseForbidden(_('User not found.'))

    if request.method == 'POST':
        form = UserEditForm(
            request.POST,
            request.FILES,
            instance=user,
            can_edit_all_fields=can_edit_all_fields
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                _('User has been updated successfully!')
            )

            return redirect('accounts:user_detail', pk=user.pk)

        else:
            messages.error(request, _('Please correct the errors below.'))

    else:
        form = UserEditForm(
            instance=user,
            can_edit_all_fields=can_edit_all_fields
        )

    context = {
        'form': form,
        'form_title': _('Edit User'),
        'submit_text': _('Update'),
        'user': user,
        'page_title': _('Edit {}').format(user.get_full_name()),
    }

    return render(request, 'accounts/user_form.html', context)


@login_required
@admin_required
@require_http_methods(['POST'])
def user_delete_view(request, pk):
    """
    Delete user (Admin only, POST only)

    Security:
    - Cannot delete self
    - Cannot delete superuser (unless you're superuser)
    - Requires confirmation
    - TODO: Reassign leads before deletion (Phase 3)

    URL: /accounts/users/<pk>/delete/
    Method: POST only (for security)
    """
    user = get_object_or_404(User, pk=pk)

    # Cannot delete self
    if user == request.user:
        messages.error(request, _('You cannot delete yourself.'))
        return redirect('accounts:user_list')

    # Cannot delete superuser (unless you're superuser)
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, _('You cannot delete a superuser.'))
        return redirect('accounts:user_list')

    # Check company
    # if user.company != request.user.company:
    #     return HttpResponseForbidden(_('User not found.'))

    # Store name for message
    user_name = user.get_full_name()

    # TODO: Reassign leads (Phase 3)
    # from apps.leads.models import Lead
    # Lead.objects.filter(assigned_to=user).update(assigned_to=request.user)

    # Delete user
    user.delete()

    messages.success(
        request,
        _('User {} has been deleted successfully.').format(user_name)
    )

    return redirect('accounts:user_list')



# AJAX VIEWS (for dynamic features)
@login_required
@require_http_methods(['POST'])
def toggle_user_status(request, pk):
    """
    Toggle user active status via AJAX

    Quick activate/deactivate without page reload

    URL: /accounts/users/<pk>/toggle-status/
    Method: POST
    Returns: JSON response
    """
    if not request.user.is_admin():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    user = get_object_or_404(User, pk=pk)

    # Cannot deactivate self
    if user == request.user:
        return JsonResponse({'success': False, 'error': 'Cannot deactivate yourself'})

    # Cannot deactivate superuser
    if user.is_superuser and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Cannot deactivate superuser'})

    # Toggle status
    user.is_active = not user.is_active
    user.save()

    status_text = _('activated') if user.is_active else _('deactivated')

    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': _('User {}').format(status_text)
    })


# ERROR HANDLERS (Optional)
# Custom 403 handler for accounts app
def custom_403(request, exception=None):
    """
    Custom 403 Forbidden page

    Shown when user tries to access restricted page
    """
    return render(request, 'accounts/403.html', status=403)

