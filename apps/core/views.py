from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, date
from apps.accounts.decorators import company_required
from .models import Company, LeadSource, LeadStage


@login_required
@company_required
def dashboard_view(request):
    company = request.user.company

    # Will be updated in Phase 3 with real queries
    total_leads = 0
    new_today = 0
    new_this_week = 0
    new_this_month = 0
    conversion_rate = 0

    # Lead distribution by stage (for charts)
    # Prepare structure for each stage with count, color, icon
    leads_by_stage = []
    stages = LeadStage.objects.filter(is_active=True).order_by('order')
    for stage in stages:
        count = 0  # TODO: Update with Lead.objects.filter(stage=stage).count()
        percentage = (count / total_leads * 100) if total_leads > 0 else 0
        leads_by_stage.append({
            'name': stage.name,
            'count': 0,  # TODO: Update in Phase 3 with Lead.objects.filter(stage=stage).count()
            'color': stage.color,
            'icon': stage.icon,
        })

    # Lead distribution by source
    # Prepare structure for each source with count, color, icon
    leads_by_source = []
    sources = LeadSource.objects.filter(is_active=True).order_by('order')
    for source in sources:
        leads_by_source.append({
            'name': source.name,
            'count': 0,  # TODO: Update in Phase 3 with Lead.objects.filter(source=source).count()
            'color': source.color,
            'icon': source.icon,
        })

    # Current user performance statistics
    # These come from User model (already implemented in Phase 1)
    assigned = request.user.total_leads_assigned
    converted = request.user.total_leads_converted
    won = request.user.total_leads_won

    conversion_percentage = (converted / assigned * 100) if assigned > 0 else 0
    win_percentage = (won / assigned * 100) if assigned > 0 else 0

    user_stats = {
        'assigned': assigned,
        'converted': converted,
        'won': won,
        'conversion_rate': request.user.get_conversion_rate(),
        'win_rate': request.user.get_win_rate(),
        'conversion_percentage': conversion_percentage,
        'win_percentage': win_percentage,
    }

    # Recent activity - Placeholder
    # Will show last 10 leads in Phase 3
    recent_leads = []

    # Date range for charts (last 7 days)
    # Prepare daily data structure for trend charts
    today = date.today()
    last_7_days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        last_7_days.append({
            'date': day.strftime('%Y-%m-%d'),
            'date_label': day.strftime('%d %b'),  # Format: "05 Dec"
            'count': 0,  # TODO: Update in Phase 3 with daily lead counts
        })

    # Prepare context for template
    context = {
        'company': company,
        'total_leads': total_leads,
        'new_today': new_today,
        'new_this_week': new_this_week,
        'new_this_month': new_this_month,
        'conversion_rate': conversion_rate,
        'leads_by_stage': leads_by_stage,
        'leads_by_source': leads_by_source,
        'recent_leads': recent_leads,
        'user_stats': user_stats,
        'last_7_days': last_7_days,
        'active_page': 'dashboard',  # For sidebar highlighting
    }

    return render(request, 'core/dashboard.html', context)


@login_required
@company_required
def company_settings_view(request):
    """
    Company settings page - Admin only

    Allows admin users to view and edit company information.

    Features:
        - View current company settings
        - Edit basic information (name, logo, description)
        - Update contact details (phone, email, website, address)
        - Modify working hours and timezone
        - Toggle active status

    Access Control:
        - Login required
        - Company required
        - Admin only (agents redirected with error message)

    Form Handling:
        - GET: Display current settings
        - POST: Update settings with validation
        - Success message on save
        - Error handling for invalid data

    Context Variables:
        company (Company): Current company instance
        active_page (str): 'settings' for sidebar highlighting

    Template:
        core/company_settings.html

    Security:
        - Only admins can access
        - Users can only edit their own company
        - CSRF protection on form submission

    Note:
        Form implementation will be added after creating CompanyForm.
        Current version only displays settings (no edit functionality yet).
    """

    # Check if user is admin
    # Agents should not access company settings
    if not request.user.is_admin():
        messages.error(request, 'Only admins can access company settings')
        return redirect('core:dashboard')

    # Get current company
    company = request.user.company

    # Handle form submission
    if request.method == 'POST':
        # TODO: Implement form handling
        # Will create CompanyForm and process here
        # For now, just show the page
        pass

    # Prepare context
    context = {
        'company': company,
        'active_page': 'settings',
    }

    return render(request, 'core/company_settings.html', context)