from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, date
from apps.accounts.decorators import company_required
from .models import Company, LeadSource, LeadStage
from apps.leads.models import Lead
from .utils import get_user_company, set_selected_company


@login_required
def company_selector_view(request):
    """
    Company selector for Superuser
    Simple page to choose which company to manage
    """
    # Only superusers can access
    if not request.user.is_superuser:
        return redirect('core:dashboard')
    
    # Handle company selection via GET parameter
    company_id = request.GET.get('company_id')
    if company_id:
        if set_selected_company(request, company_id):
            return redirect('core:dashboard')
    
    # Get all companies
    companies = Company.objects.all().order_by('name')
    
    # Get current selection
    selected_company = get_user_company(request)
    
    context = {
        'companies': companies,
        'selected_company': selected_company,
    }
    
    return render(request, 'core/company_selector.html', context)


@login_required
def dashboard_view(request):
    """
    Main dashboard view
    - Superuser: sees selected company data (or redirected to selector)
    - Admin/Agent: sees their company data
    """
    # Get company (selected for superuser, or user.company for others)
    company = get_user_company(request)
    
    # Superuser without selection → redirect to selector
    if request.user.is_superuser and not company:
        return redirect('core:company_selector')
    
    # Regular user without company → error
    if not company:
        return redirect('login')  # Or show error page
    
    today = timezone.now().date()

    # Base QuerySet - company leads only
    leads_qs = Lead.objects.filter(company=company) \
        .exclude(stage__name__iexact='delete') \
        .exclude(stage__name__iexact='deleted')

    # 1. Key Metrics
    total_leads = leads_qs.count()
    new_today = leads_qs.filter(created_at__date=today).count()
    
    # New this week (starting Monday)
    start_of_week = today - timedelta(days=today.weekday())
    new_this_week = leads_qs.filter(created_at__date__gte=start_of_week).count()
    
    # New this month
    new_this_month = leads_qs.filter(
        created_at__year=today.year, 
        created_at__month=today.month
    ).count()

    # Conversion Rate (Leads in 'won' stage / Total Leads)
    # Find 'won' stage(s) by checking stage_type or name
    won_stages = LeadStage.objects.filter(
        Q(stage_type='won') | Q(name__iexact='won'),
        is_active=True
    )
    won_leads = leads_qs.filter(stage__in=won_stages).count()
    conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0

    # 2. Lead Distribution by Stage
    # Improve performance by fetching counts in one query
    stage_counts = leads_qs.values('stage').annotate(count=Count('id'))
    stage_count_map = {item['stage']: item['count'] for item in stage_counts}
    
    leads_by_stage = []
    stages = LeadStage.objects.filter(is_active=True).order_by('order')
    
    for stage in stages:
        count = stage_count_map.get(stage.id, 0)
        percentage = (count / total_leads * 100) if total_leads > 0 else 0
        leads_by_stage.append({
            'name': stage.name,
            'count': count,
            'percentage': percentage,
            'color': stage.color,
            'icon': stage.icon,
        })

    # 3. Lead Distribution by Source
    source_counts = leads_qs.values('source').annotate(count=Count('id'))
    source_count_map = {item['source']: item['count'] for item in source_counts}

    leads_by_source = []
    sources = LeadSource.objects.filter(is_active=True).order_by('order')
    
    for source in sources:
        count = source_count_map.get(source.id, 0)
        leads_by_source.append({
            'name': source.name,
            'count': count,
            'color': source.color,
            'icon': source.icon,
        })

    # 4. User Performance Statistics (Dynamic - always accurate)
    # Calculate from actual database counts instead of cached fields
    # - Agents: see their own stats
    # - Admins/Superusers: see company-wide stats (in frontend only)
    
    if request.user.is_admin() or request.user.is_superuser:
        # Admins/Superusers see COMPANY-WIDE stats in frontend
        # (Django admin will still show everything for superuser)
        user_assigned_leads = Lead.objects.filter(company=company)
        stats_label = "Company"  # For UI display
    else:
        # Regular agents see THEIR OWN stats
        user_assigned_leads = Lead.objects.filter(
            assigned_to=request.user,
            company=company
        )
        stats_label = "My"  # For UI display
    
    # Count assigned leads
    assigned = user_assigned_leads.count()
    
    # Find "converted" and "won" stages dynamically
    converted_stages = LeadStage.objects.filter(
        Q(stage_type='converted') | Q(name__iexact='converted') | Q(name__iexact='patient'),
        is_active=True
    )
    won_stages = LeadStage.objects.filter(
        Q(stage_type='won') | Q(name__iexact='won'),
        is_active=True
    )
    
    # Count converted and won leads
    converted = user_assigned_leads.filter(stage__in=converted_stages).count()
    won = user_assigned_leads.filter(stage__in=won_stages).count()
    
    # Calculate percentages
    conversion_percentage = (converted / assigned * 100) if assigned > 0 else 0
    win_percentage = (won / assigned * 100) if assigned > 0 else 0

    user_stats = {
        'assigned': assigned,
        'converted': converted,
        'won': won,
        'conversion_rate': conversion_percentage,  # Same as conversion_percentage
        'win_rate': win_percentage,  # Same as win_percentage  
        'conversion_percentage': conversion_percentage,
        'win_percentage': win_percentage,
        'stats_label': stats_label,  # "My" or "Company"
    }

    # 5. Recent Activity
    recent_leads = leads_qs.select_related('source', 'stage').order_by('-created_at')[:10]

    # 6. Daily Trends (Last 7 days)
    # Get counts per day for the last 7 days
    seven_days_ago = today - timedelta(days=6)
    daily_counts = leads_qs.filter(created_at__date__gte=seven_days_ago)\
        .values('created_at__date')\
        .annotate(count=Count('id'))
    
    daily_map = {item['created_at__date']: item['count'] for item in daily_counts}
    
    last_7_days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        last_7_days.append({
            'date': day.strftime('%Y-%m-%d'),
            'date_label': day.strftime('%d %b'),
            'count': daily_map.get(day, 0),
        })

    # Prepare context
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
        'active_page': 'dashboard',
    }

    return render(request, 'core/dashboard.html', context)


from .forms import CompanySettingsForm

@login_required
@company_required
def company_settings_view(request):

    # Check if user is admin
    # Agents should not access company settings
    # Check if user is admin
    # Agents should not access company settings
    if not request.user.is_admin():
        messages.error(request, 'Only admins can access company settings')
        return redirect('core:dashboard')

    # Superuser check: If no company assigned, redirect to Admin Panel
    if request.user.is_superuser and not request.user.company:
        messages.info(request, 'Global Superusers manage settings via the Django Admin Panel.')
        return redirect('admin:index')

    # Get current company
    company = request.user.company

    # Handle form submission
    if request.method == 'POST':
        form = CompanySettingsForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company settings updated successfully.')
            return redirect('core:company_settings')
    else:
        form = CompanySettingsForm(instance=company)

    # Prepare context
    context = {
        'company': company,
        'form': form,
        'active_page': 'settings',
    }

    return render(request, 'core/company_settings.html', context)


@login_required
@company_required
def deactivate_company_view(request):
    """
    Deactivates the company and logs out the user.
    """
    if not request.user.is_admin():
        messages.error(request, 'Only admins can deactivate the company.')
        return redirect('core:dashboard')
        
    # Superuser check
    if request.user.is_superuser and not request.user.company:
        messages.error(request, 'Global superusers cannot deactivate the platform from here.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        confirmation = request.POST.get('confirmation')
        if confirmation == 'CONFIRM':
            company = request.user.company
            company.is_active = False
            company.save()
            
            # Log out the user
            from django.contrib.auth import logout
            logout(request)
            
            # We can't use messages here easily because session is flushed on logout usually,
            # unless we put it in a query param or rely on the login page to handle it.
            # simpler to just redirect to login alone for now.
            return redirect('accounts:login')
        else:
            messages.error(request, 'Incorrect confirmation text.')
            return redirect('core:company_settings')

    return redirect('core:company_settings')