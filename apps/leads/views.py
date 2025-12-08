from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.utils import timezone

from apps.accounts.decorators import company_required
from .models import Lead, Note, Activity
from .forms import LeadFilterForm, NoteForm
from apps.core.models import LeadSource, LeadStage


@login_required
@company_required
def lead_list_view(request):
    company = request.user.company
    leads = Lead.objects.filter(company=company).select_related(
        'source',
        'stage',
        'assigned_to'
    ).order_by('-created_at')  # Newest first

    search_query = request.GET.get('search', '').strip()

    if search_query:
        # Search in name, phone, or email using Q objects (OR condition)
        leads = leads.filter(
            Q(name__icontains=search_query) |  # Name contains search term
            Q(phone__icontains=search_query) |  # Phone contains search term
            Q(email__icontains=search_query)  # Email contains search term
        )

    filter_form = LeadFilterForm(request.GET, company=company)

    if filter_form.is_valid():
        # Filter by source
        if filter_form.cleaned_data.get('source'):
            leads = leads.filter(source=filter_form.cleaned_data['source'])

        # Filter by stage
        if filter_form.cleaned_data.get('stage'):
            leads = leads.filter(stage=filter_form.cleaned_data['stage'])

        # Filter by status
        if filter_form.cleaned_data.get('status'):
            leads = leads.filter(status=filter_form.cleaned_data['status'])

        # Filter by priority
        if filter_form.cleaned_data.get('priority'):
            leads = leads.filter(priority=filter_form.cleaned_data['priority'])

        # Filter by assigned agent
        if filter_form.cleaned_data.get('assigned_to'):
            leads = leads.filter(assigned_to=filter_form.cleaned_data['assigned_to'])

        # Filter by date range (created_at)
        if filter_form.cleaned_data.get('date_from'):
            # Created on or after this date
            leads = leads.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])

        if filter_form.cleaned_data.get('date_to'):
            # Created on or before this date
            leads = leads.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])

    total_count = leads.count()
    status_counts = {
        'new': leads.filter(status='new').count(),
        'contacted': leads.filter(status='contacted').count(),
        'qualified': leads.filter(status='qualified').count(),
        'converted': leads.filter(status='converted').count(),
        'won': leads.filter(status='won').count(),
        'lost': leads.filter(status='lost').count(),
    }

    paginator = Paginator(leads, 50)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.get_page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        page_obj = paginator.get_page(paginator.num_pages)


    context = {
        'leads': page_obj,
        'filter_form': filter_form,
        'total_count': total_count,
        'status_counts': status_counts,
        'page_obj': page_obj,
        'search_query': search_query,

        # Pagination info
        'is_paginated': page_obj.has_other_pages(),
        'page_range': paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        ),
    }

    return render(request, 'leads/lead_list.html', context)


@login_required
@company_required
def lead_detail_view(request, pk):
    lead = get_object_or_404(
        Lead.objects.select_related(
            'company',
            'source',
            'stage',
            'assigned_to',
            'assigned_to__profile'
        ),
        pk=pk,
        company=request.user.company
    )

    if request.method == 'POST':
        note_form = NoteForm(request.POST)

        if note_form.is_valid():
            note = lead.add_note(
                content=note_form.cleaned_data['content'],
                user=request.user
            )
            messages.success(request, 'تم إضافة الملاحظة بنجاح')

            return redirect('leads:lead_detail', pk=lead.pk)
        else:
            messages.error(request, 'حدث خطأ في إضافة الملاحظة')
    else:
        note_form = NoteForm()


    notes = lead.get_notes()

    activities = lead.get_activities()



    # Can user edit this lead?
    # Rules: User must be admin OR assigned to this lead
    can_edit = (
            request.user.is_admin() or
            lead.assigned_to == request.user
    )

    # Can user delete this lead?
    # Rules: Only admins can delete
    can_delete = request.user.is_admin()

    # Can lead be assigned?
    # Rules: Lead must not be Won/Lost
    can_be_assigned = lead.can_be_assigned()



    context = {
        'lead': lead,
        'notes': notes,
        'activities': activities,
        'note_form': note_form,
        'can_edit': can_edit,
        'can_delete': can_delete,
        'can_be_assigned': can_be_assigned,

        # Counts for tabs
        'notes_count': notes.count(),
        'activities_count': activities.count(),

        # Current tab (from query parameter)
        'active_tab': request.GET.get('tab', 'overview'),
    }

    return render(request, 'leads/lead_detail.html', context)


@login_required
@company_required
def lead_json_view(request, pk):

    try:
        lead = Lead.objects.select_related(
            'source',
            'stage',
            'assigned_to'
        ).get(
            pk=pk,
            company=request.user.company
        )

        data = {
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone,
            'email': lead.email,

            'source': {
                'id': lead.source.id,
                'name': lead.source.name,
                'color': lead.source.color,
                'icon': lead.source.icon,
            },

            # Stage info
            'stage': {
                'id': lead.stage.id,
                'name': lead.stage.name,
                'color': lead.stage.color,
                'icon': lead.stage.icon,
            },

            # Status
            'status': lead.status,
            'status_display': lead.get_status_display(),

            # Priority
            'priority': lead.priority,
            'priority_display': lead.get_priority_display(),

            # Assignment
            'assigned_to': {
                'id': lead.assigned_to.id,
                'name': lead.assigned_to.get_full_name(),
            } if lead.assigned_to else None,

            # Dates
            'next_follow_up': lead.next_follow_up.isoformat() if lead.next_follow_up else None,
            'created_at': lead.created_at.isoformat(),
            'updated_at': lead.updated_at.isoformat(),

            # Additional info
            'notes': lead.notes,
            'tags': lead.tags,

            # Computed fields
            'time_since_created': lead.time_since_created(),
            'time_until_follow_up': lead.time_until_follow_up(),
            'can_be_assigned': lead.can_be_assigned(),
        }

        return JsonResponse(data)

    except Lead.DoesNotExist:
        return JsonResponse(
            {'error': 'Lead not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )


@login_required
@company_required
def lead_activities_view(request, pk):
    try:
        lead = get_object_or_404(
            Lead,
            pk=pk,
            company=request.user.company
        )

        activities = Activity.objects.filter(
            lead=lead
        ).select_related('user').order_by('-created_at')

        page_number = request.GET.get('page', 1)
        per_page = int(request.GET.get('per_page', 20))

        paginator = Paginator(activities, per_page)
        page_obj = paginator.get_page(page_number)

        # Build response
        activities_data = []
        for activity in page_obj:
            activities_data.append({
                'id': activity.id,
                'type': activity.activity_type,
                'type_display': activity.get_activity_type_display(),
                'description': activity.description,
                'user': {
                    'id': activity.user.id,
                    'name': activity.user.get_full_name(),
                    'initials': activity.user.get_initials(),
                } if activity.user else None,
                'created_at': activity.created_at.isoformat(),
                'time_since': activity.created_at,  # Will be formatted in frontend
            })

        data = {
            'activities': activities_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count,
            'page': page_obj.number,
            'num_pages': paginator.num_pages,
        }

        return JsonResponse(data)

    except Lead.DoesNotExist:
        return JsonResponse(
            {'error': 'Lead not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )