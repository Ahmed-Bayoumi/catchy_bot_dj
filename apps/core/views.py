from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta, date
from apps.accounts.decorators import company_required
from .models import Company, LeadSource, LeadStage
from apps.leads.models import Lead


@login_required
@company_required
def dashboard_view(request):
    company = request.user.company
    today = timezone.now().date()

    # Base QuerySet
    # Robustly exclude 'delete'/'deleted' from status and stage
    leads_qs = Lead.objects.filter(company=company) \
        .exclude(status__iexact='delete') \
        .exclude(status__iexact='deleted') \
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

    # Conversion Rate (Leads won / Total Leads)
    # Note: Using 'won' status as conversion for this metric
    won_leads = leads_qs.filter(status='won').count()
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

    # 4. User Performance Statistics
    # These rely on the User model methods which use assigned/converted fields
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


@login_required
@company_required
def company_settings_view(request):

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