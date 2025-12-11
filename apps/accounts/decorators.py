# Decorators in this file:
# 1. admin_required - Only admins can access
# 2. agent_required - Only agents can access
# 3. company_required - User must belong to a company
# 4. ajax_required - Only AJAX requests allowed
#
# Why decorators?
# - Clean code (no repeated permission checks)
# - Easy to apply (@decorator before function)
# - Reusable across views
# - Better security
# ==============================================================================

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied


# ROLE-BASED DECORATORS
def admin_required(view_func):
    """
    Decorator: Only admins can access this view

    Checks:
    1. User is authenticated (logged in)
    2. User role is 'admin' OR is superuser

    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated (should be checked by @login_required)
        if not request.user.is_authenticated:
            messages.error(request, _('Please login to continue.'))
            return redirect('accounts:login')

        # Check if user is admin or superuser
        if request.user.is_admin() or request.user.is_superuser:
            # User is admin → allow access
            return view_func(request, *args, **kwargs)

        # User is not admin → deny access
        messages.error(
            request,
            _('You do not have permission to access this page. Admin access required.')
        )

        # Redirect to dashboard or show 403
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request → return JSON error
            return JsonResponse({
                'success': False,
                'error': 'Admin access required'
            }, status=403)
        else:
            # Regular request → redirect
            return redirect('core:dashboard')

    return wrapper


def agent_required(view_func):
    """
    Checks:
    1. User is authenticated
    2. User role is 'agent'
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('Please login to continue.'))
            return redirect('accounts:login')

        # Check if user is agent
        if request.user.is_agent():
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            _('This page is only accessible to agents.')
        )
        return redirect('core:dashboard')

    return wrapper


def role_required(*allowed_roles):
    """
    Decorator: Only specific roles can access

    Flexible decorator that accepts multiple roles

    Args:
        *allowed_roles: Tuple of allowed role names

    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, _('Please login to continue.'))
                return redirect('accounts:login')

            # Check if user's role is in allowed roles
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                _('You do not have permission to access this page.')
            )
            return redirect('core:dashboard')

        return wrapper

    return decorator



# COMPANY-BASED DECORATORS
def company_required(view_func):
    """
    Checks:
    1. User is authenticated
    2. User has company assigned


    Why needed?
    - Some users might not have company (superusers, etc.)
    - Multi-tenancy requires company context
    - Prevents errors when accessing user.company

    Example flow:
    User without company tries to access
    → @company_required checks user.company
    → user.company = None → ❌ Access denied
    → Shows error + redirects
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('Please login to continue.'))
            return redirect('accounts:login')

        # Check if user has company OR is superuser
        if request.user.company or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            _('You must be assigned to a company to access this page.')
        )
        return redirect('core:dashboard')

    return wrapper


def same_company_required(model_class, pk_param='pk'):
    """
    Decorator: Verify accessed object belongs to user's company

    Multi-tenancy security: Users can only access their company's data

    Args:
        model_class: Model class to verify (e.g., Lead, Contact)
        pk_param: URL parameter name for primary key (default: 'pk')

    Usage:
        @login_required
        @company_required
        @same_company_required(Lead, pk_param='pk')
        def lead_detail_view(request, pk):
            # Object is guaranteed to belong to user's company
            lead = get_object_or_404(Lead, pk=pk)
            return render(request, 'lead_detail.html', {'lead': lead})

    How it works:
    1. Gets pk from URL parameters
    2. Verifies object exists AND belongs to user's company
    3. If object from different company → 404 (not 403, to hide existence)
    4. If object belongs to user's company → Allow access

    Security benefits:
    - Prevents cross-company data access
    - Returns 404 instead of 403 (hides existence of other company's data)
    - Automatic multi-tenancy enforcement

    Example:
        Company A user tries to access Company B's lead:
        GET /leads/123/ → Lead 123 belongs to Company B
        → Decorator checks: lead.company == user.company?
        → NO → Returns 404 (as if lead doesn't exist)
        → Result: Company A user can't even know Lead 123 exists
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check authentication
            if not request.user.is_authenticated:
                messages.error(request, _('Please login to continue.'))
                return redirect('accounts:login')

            # Check company
            if not request.user.company:
                messages.error(
                    request,
                    _('You must be assigned to a company to access this page.')
                )
                return redirect('core:dashboard')

            # Get object pk from URL parameters
            pk = kwargs.get(pk_param)
            
            if not pk:
                # No pk provided, let view handle it
                return view_func(request, *args, **kwargs)

            try:
                # Verify object exists AND belongs to user's company
                # This is the key security check!
                obj = model_class.objects.get(
                    pk=pk,
                    company=request.user.company  # ⭐ Multi-tenancy filter
                )
                
                # Object belongs to user's company ✅
                # Continue to view
                return view_func(request, *args, **kwargs)

            except model_class.DoesNotExist:
                # Object doesn't exist OR belongs to different company
                # Return 404 (not 403) to hide existence
                from django.http import Http404
                raise Http404(
                    f"{model_class.__name__} not found or you don't have access to it."
                )

        return wrapper

    return decorator


# REQUEST TYPE DECORATORS
def ajax_required(view_func):
    """
    Decorator: Only AJAX requests allowed

    Checks if request is AJAX (XMLHttpRequest)

    Usage:
    @ajax_required
    def api_endpoint(request):
        # Only AJAX requests reach here
        data = {'status': 'success'}
        return JsonResponse(data)

    Why needed?
    - Some views should only be called via JavaScript
    - Prevents direct URL access
    - Security for API endpoints

    Example:
    Direct browser access → ❌ 403 Forbidden
    jQuery.ajax() → ✅ Allowed
    fetch() → ✅ Allowed

    How it detects AJAX:
    - Checks X-Requested-With header
    - Modern AJAX libraries set this automatically
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if request is AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return view_func(request, *args, **kwargs)

        # Not AJAX → forbidden
        return HttpResponseForbidden('AJAX requests only')

    return wrapper


def post_required(view_func):
    """
    Decorator: Only POST requests allowed

    Usage:
    @post_required
    def delete_user(request):
        # Only POST requests (secure)
        user.delete()
        return redirect('user_list')

    Why needed?
    - Security: Destructive actions (delete, update) should be POST
    - GET requests can be triggered by bots, crawlers
    - CSRF protection works with POST

    Example:
    GET /delete/5/ → ❌ 405 Method Not Allowed
    POST /delete/5/ → ✅ Allowed

    Note:
    Django has @require_http_methods(['POST']) built-in
    This is a simplified educational version
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            return view_func(request, *args, **kwargs)

        return JsonResponse({
            'success': False,
            'error': 'POST requests only'
        }, status=405)

    return wrapper


# ==============================================================================
# PERMISSION DECORATORS
# ==============================================================================

def permission_required(*permissions):
    """
    Decorator: Check Django permissions

    Args:
        *permissions: Permission codenames

    Usage:
    @login_required
    @permission_required('accounts.add_user', 'accounts.change_user')
    def create_user(request):
        # User must have both permissions
        pass

    Permissions format:
    'app_label.permission_codename'
    Examples:
    - 'accounts.add_user'
    - 'accounts.change_user'
    - 'accounts.delete_user'
    - 'leads.view_lead'

    How Django permissions work:
    - Auto-created for each model (add, change, delete, view)
    - Can assign to users or groups
    - Check with: user.has_perm('accounts.add_user')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Check all permissions
            has_all_perms = all(
                request.user.has_perm(perm) for perm in permissions
            )

            if has_all_perms or request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Missing permissions
            raise PermissionDenied

        return wrapper

    return decorator


def ownership_required(model_class, pk_param='pk', field_name='user'):
    """
    Decorator: Check object ownership

    Verify that object belongs to current user

    Args:
        model_class: Model class to check
        pk_param: URL parameter name for primary key
        field_name: Field name that contains user reference

    Usage:
    @login_required
    @ownership_required(Lead, pk_param='lead_id', field_name='assigned_to')
    def edit_lead(request, lead_id):
        # User can only edit their own leads
        pass

    How it works:
    1. Gets pk from URL parameters
    2. Fetches object from database
    3. Checks: object.assigned_to == request.user
    4. If not → 403 Forbidden

    Example:
    URL: /leads/5/edit/
    User ID: 10
    Lead 5's assigned_to: User 10 → ✅ Allowed
    Lead 5's assigned_to: User 15 → ❌ Forbidden
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Get object pk from URL parameters
            pk = kwargs.get(pk_param)

            try:
                # Fetch object
                obj = model_class.objects.get(pk=pk)

                # Check ownership
                owner = getattr(obj, field_name, None)

                if owner == request.user or request.user.is_admin():
                    return view_func(request, *args, **kwargs)

                # Not owner
                raise PermissionDenied

            except model_class.DoesNotExist:
                # Object not found
                raise PermissionDenied

        return wrapper

    return decorator


# ==============================================================================
# COMBINING DECORATORS
# ==============================================================================

def admin_or_owner_required(model_class, pk_param='pk', field_name='user'):
    """
    Decorator: Admin OR owner can access

    Flexible access: Either admin or object owner

    Usage:
    @login_required
    @admin_or_owner_required(Lead, field_name='assigned_to')
    def view_lead(request, pk):
        # Admins can view any lead
        # Agents can only view their own leads
        pass

    Access matrix:
    User Type | Own Object | Other's Object
    ----------|------------|---------------
    Admin     | ✅         | ✅
    Agent     | ✅         | ❌
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Admin has full access
            if request.user.is_admin():
                return view_func(request, *args, **kwargs)

            # Check ownership
            pk = kwargs.get(pk_param)

            try:
                obj = model_class.objects.get(pk=pk)
                owner = getattr(obj, field_name, None)

                if owner == request.user:
                    return view_func(request, *args, **kwargs)

                raise PermissionDenied

            except model_class.DoesNotExist:
                raise PermissionDenied

        return wrapper

    return decorator


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================

"""
EXAMPLE 1: Admin-only view
==========================
from django.contrib.auth.decorators import login_required
from .decorators import admin_required

@login_required
@admin_required
def user_management(request):
    users = User.objects.all()
    return render(request, 'users.html', {'users': users})


EXAMPLE 2: Multi-decorator
===========================
@login_required           # Must be logged in
@company_required         # Must have company
@admin_required           # Must be admin
def company_settings(request):
    company = request.user.company
    return render(request, 'settings.html', {'company': company})


EXAMPLE 3: AJAX endpoint
=========================
@login_required
@ajax_required
@post_required
def delete_lead(request):
    lead_id = request.POST.get('lead_id')
    # ... delete logic
    return JsonResponse({'success': True})


EXAMPLE 4: Permission-based
============================
@login_required
@permission_required('accounts.add_user', 'accounts.change_user')
def bulk_create_users(request):
    # Only users with both permissions
    pass


EXAMPLE 5: Ownership check
===========================
@login_required
@ownership_required(Lead, pk_param='lead_id', field_name='assigned_to')
def edit_my_lead(request, lead_id):
    # User can only edit leads assigned to them
    lead = get_object_or_404(Lead, pk=lead_id)
    # ... edit logic


EXAMPLE 6: Flexible access
===========================
@login_required
@admin_or_owner_required(Lead, field_name='assigned_to')
def view_lead_detail(request, pk):
    # Admins see any lead
    # Agents see only their leads
    lead = get_object_or_404(Lead, pk=pk)
    return render(request, 'lead_detail.html', {'lead': lead})


EXAMPLE 7: Multi-tenancy security
===================================
from apps.leads.models import Lead

@login_required
@company_required
@same_company_required(Lead, pk_param='pk')
def lead_detail_view(request, pk):
    # Automatic company verification
    # If lead belongs to different company → 404
    # If lead belongs to user's company → Allow
    lead = get_object_or_404(Lead, pk=pk)
    return render(request, 'lead_detail.html', {'lead': lead})


EXAMPLE 8: Combined security layers
=====================================
@login_required                          # Layer 1: Authentication
@company_required                        # Layer 2: Has company
@same_company_required(Lead)             # Layer 3: Company match
@admin_or_owner_required(Lead, 'assigned_to')  # Layer 4: Admin or assigned
def lead_edit_view(request, pk):
    # Maximum security:
    # 1. ✅ User logged in
    # 2. ✅ User has company
    # 3. ✅ Lead belongs to user's company
    # 4. ✅ User is admin OR assigned to lead
    lead = get_object_or_404(Lead, pk=pk)
    # ... edit logic
"""

# ==============================================================================
# TESTING DECORATORS
# ==============================================================================

"""
Test decorators in Django shell:

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.accounts.decorators import admin_required

User = get_user_model()

# Create test request
factory = RequestFactory()
request = factory.get('/test/')

# Test with admin
admin = User.objects.get(role='admin')
request.user = admin

@admin_required
def test_view(request):
    return 'Success'

result = test_view(request)  # Should work

# Test with agent
agent = User.objects.get(role='agent')
request.user = agent
result = test_view(request)  # Should fail
"""

# ==============================================================================
# DECORATOR BEST PRACTICES
# ==============================================================================

"""
1. Order matters:
   @login_required       ← First (outermost)
   @company_required     ← Second
   @admin_required       ← Third (innermost)
   def view(request):
       pass

2. Use @wraps:
   - Preserves original function name
   - Preserves docstring
   - Helps debugging

3. Clear error messages:
   - Tell user WHY access denied
   - Suggest what to do

4. Consistent behavior:
   - AJAX → JSON response
   - Regular → redirect with message

5. Security first:
   - Always check authentication
   - Fail securely (deny by default)
   - Log access attempts

6. Performance:
   - Cache permission checks when possible
   - Don't query database in every decorator
   - Use select_related for ownership checks
"""