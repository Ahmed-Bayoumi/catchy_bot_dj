"""
Helper utilities for company selection
"""
from apps.core.models import Company


def get_user_company(request):
    """
    Get the company for the current user:
    - Superuser: from session (selected company)
    - Regular users: from user.company
    
    Returns:
        Company object or None
    """
    if not request.user.is_authenticated:
        return None
    
    # Superuser can select any company
    if request.user.is_superuser:
        company_id = request.session.get('selected_company_id')
        if company_id:
            try:
                return Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                # Company deleted - clear session
                request.session.pop('selected_company_id', None)
                return None
        return None  # No company selected
    
    # Regular users use their company
    return request.user.company


def set_selected_company(request, company_id):
    """
    Set the selected company in session (Superuser only)
    
    Args:
        request: HttpRequest object
        company_id: ID of company to select
    
    Returns:
        True if successful, False otherwise
    """
    if not request.user.is_superuser:
        return False
    
    try:
        company = Company.objects.get(pk=company_id)
        request.session['selected_company_id'] = company.id
        return True
    except Company.DoesNotExist:
        return False


def clear_selected_company(request):
    """Clear selected company from session"""
    request.session.pop('selected_company_id', None)
