from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from .models import Lead, Note
from apps.core.models import LeadSource, LeadStage
from apps.accounts.models import User
import re


class LeadCreateForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'phone', 'email', 'source', 'stage', 'status', 'priority', 'assigned_to', 'next_follow_up', 'notes']
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ahmed Ali Mohamed', 'autofocus': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+201234567890 or 01234567890', 'dir': 'ltr'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com', 'dir': 'ltr'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'next_follow_up': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add any notes here...'}),
        }
        
        help_texts = {
            'phone': 'Phone number in international format (e.g. +201234567890) or local (01234567890)',
            'email': 'Email address (optional)',
            'assigned_to': 'Agent responsible for this lead',
            'next_follow_up': 'Next follow-up date and time',
        }
        
        error_messages = {
            'name': {'required': 'Name is required', 'max_length': 'Name is too long (max 200 characters)'},
            'phone': {'required': 'Phone number is required'},
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if self.company:
            self.fields['assigned_to'].queryset = User.objects.filter(company=self.company, is_active=True).order_by('first_name', 'last_name')
        
        self.fields['assigned_to'].empty_label = "Unassigned"
        
        if not self.instance.pk:
            try:
                default_stage = LeadStage.objects.filter(stage_type='lead', is_active=True).order_by('order').first()
                self.fields['stage'].initial = default_stage
            except:
                pass
            
            self.fields['status'].initial = 'new'
            self.fields['priority'].initial = 'medium'
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()

        if phone.startswith('0'):
            phone = '+2' + phone
        elif not phone.startswith('+'):
            raise ValidationError('Phone must start with + or 0')
        
        phone_digits = phone[1:]
        if not phone_digits.isdigit():
            raise ValidationError('Phone number must contain only digits after +')
        
        if len(phone_digits) < 10 or len(phone_digits) > 15:
            raise ValidationError('Phone number must be between 10 and 15 digits')
        
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            return email
        return None
    
    def clean_next_follow_up(self):
        next_follow_up = self.cleaned_data.get('next_follow_up')
        if next_follow_up:
            if next_follow_up < timezone.now():
                raise ValidationError('Follow-up date cannot be in the past')
        return next_follow_up


class LeadEditForm(LeadCreateForm):
    class Meta(LeadCreateForm.Meta):
        pass
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.status in ['won', 'lost']:
            self.fields['status'].widget.attrs['disabled'] = True
            self.fields['stage'].widget.attrs['disabled'] = True
            self.fields['status'].help_text = 'Cannot change status for closed leads (won/lost)'


class LeadQuickEditForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'phone', 'email', 'priority', 'next_follow_up']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'next_follow_up': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class LeadAssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none(), label='Assign To', required=True, empty_label='Select agent', widget=forms.Select(attrs={'class': 'form-select'}))
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['assigned_to'].queryset = User.objects.filter(company=company, is_active=True).order_by('first_name', 'last_name')


class LeadStatusChangeForm(forms.Form):
    status = forms.ChoiceField(choices=Lead.STATUS_CHOICES, label='New Status', required=True, widget=forms.Select(attrs={'class': 'form-select'}))


class LeadStageChangeForm(forms.Form):
    stage = forms.ModelChoiceField(queryset=LeadStage.objects.filter(is_active=True).order_by('order'), label='New Stage', required=True, empty_label=None, widget=forms.Select(attrs={'class': 'form-select'}))


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your note here...', 'autofocus': True})}
        labels = {'content': 'Note'}
        error_messages = {'content': {'required': 'Note content is required'}}


class LeadFilterForm(forms.Form):
    search = forms.CharField(required=False, label='Search', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name, phone, or email...'}))
    source = forms.ModelChoiceField(queryset=LeadSource.objects.filter(is_active=True).order_by('order'), required=False, label='Source', empty_label='All Sources', widget=forms.Select(attrs={'class': 'form-select'}))
    stage = forms.ModelChoiceField(queryset=LeadStage.objects.filter(is_active=True).order_by('order'), required=False, label='Stage', empty_label='All Stages', widget=forms.Select(attrs={'class': 'form-select'}))
    status = forms.ChoiceField(choices=[('', 'All Statuses')] + Lead.STATUS_CHOICES, required=False, label='Status', widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(choices=[('', 'All Priorities')] + Lead.PRIORITY_CHOICES, required=False, label='Priority', widget=forms.Select(attrs={'class': 'form-select'}))
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none(), required=False, label='Assigned To', empty_label='All', widget=forms.Select(attrs={'class': 'form-select'}))
    date_from = forms.DateField(required=False, label='From Date', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_to = forms.DateField(required=False, label='To Date', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['assigned_to'].queryset = User.objects.filter(company=company, is_active=True).order_by('first_name', 'last_name')


class LeadImportForm(forms.Form):
    file = forms.FileField(label='Data File', help_text='Excel file (.xlsx, .xls) or CSV (.csv) - Max 5MB', widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls,.csv'}))
    source = forms.ModelChoiceField(queryset=LeadSource.objects.filter(is_active=True).order_by('order'), label='Source', help_text='This source will be assigned to all imported leads', widget=forms.Select(attrs={'class': 'form-select'}))
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none(), required=False, label='Assign To (Optional)', empty_label='No assignment', widget=forms.Select(attrs={'class': 'form-select'}))
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['assigned_to'].queryset = User.objects.filter(company=company, is_active=True).order_by('first_name', 'last_name')
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            file_name = file.name.lower()
            valid_extensions = ['.xlsx', '.xls', '.csv']
            if not any(file_name.endswith(ext) for ext in valid_extensions):
                raise ValidationError('Unsupported file type. Please upload Excel (.xlsx, .xls) or CSV (.csv) file')
            
            max_size = getattr(settings, 'LEAD_IMPORT_MAX_FILE_SIZE', 5 * 1024 * 1024)
            if file.size > max_size:
                max_mb = max_size / (1024 * 1024)
                raise ValidationError(f'File size is too large. Maximum {max_mb:.0f}MB allowed')
        return file


class LeadBulkActionForm(forms.Form):
    """Form for bulk operations on multiple leads"""
    
    ACTION_CHOICES = [
        ('assign', 'Assign to agent'),
        ('change_status', 'Change status'),
        ('change_stage', 'Change stage'),
        ('set_priority', 'Set priority'),
        ('delete', 'Delete'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, label='Action', widget=forms.Select(attrs={'class': 'form-select', 'id': 'bulk-action-select'}))
    lead_ids = forms.CharField(widget=forms.HiddenInput(), required=True)
    
    # Conditional fields (shown based on action)
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none(), required=False, label='Assign To', widget=forms.Select(attrs={'class': 'form-select'}))
    status = forms.ChoiceField(choices=Lead.STATUS_CHOICES, required=False, label='Status', widget=forms.Select(attrs={'class': 'form-select'}))
    stage = forms.ModelChoiceField(queryset=LeadStage.objects.filter(is_active=True).order_by('order'), required=False, label='Stage', widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(choices=Lead.PRIORITY_CHOICES, required=False, label='Priority', widget=forms.Select(attrs={'class': 'form-select'}))
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['assigned_to'].queryset = User.objects.filter(company=company, is_active=True).order_by('first_name', 'last_name')
    
    def clean_lead_ids(self):
        lead_ids = self.cleaned_data.get('lead_ids', '')
        try:
            id_list = [int(id.strip()) for id in lead_ids.split(',') if id.strip()]
            if not id_list:
                raise ValidationError('No leads selected')
            return id_list
        except ValueError:
            raise ValidationError('Invalid lead IDs')
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        # Validate required fields based on action
        if action == 'assign' and not cleaned_data.get('assigned_to'):
            raise ValidationError({'assigned_to': 'Please select an agent'})
        elif action == 'change_status' and not cleaned_data.get('status'):
            raise ValidationError({'status': 'Please select a status'})
        elif action == 'change_stage' and not cleaned_data.get('stage'):
            raise ValidationError({'stage': 'Please select a stage'})
        elif action == 'set_priority' and not cleaned_data.get('priority'):
            raise ValidationError({'priority': 'Please select a priority'})
        
        return cleaned_data


class FollowUpReminderForm(forms.Form):

    next_follow_up = forms.DateTimeField(label='Follow-up Date & Time', widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}), help_text='When should you follow up with this lead?')
    
    reminder_before = forms.ChoiceField(choices=getattr(settings, 'LEAD_REMINDER_OPTIONS', [('1hour', '1 hour before')]), label='Remind Me', widget=forms.Select(attrs={'class': 'form-select'}), help_text='When should you receive a reminder?')
    
    send_email = forms.BooleanField(required=False, initial=True, label='Email Reminder', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    send_sms = forms.BooleanField(required=False, initial=False, label='SMS Reminder', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    notes = forms.CharField(required=False, label='Reminder Notes', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes for this follow-up...'}), help_text='Optional notes to include in the reminder')
    
    def clean_next_follow_up(self):
        next_follow_up = self.cleaned_data.get('next_follow_up')
        if next_follow_up:
            if next_follow_up < timezone.now():
                raise ValidationError('Follow-up date cannot be in the past')
        return next_follow_up
    
    def clean(self):
        cleaned_data = super().clean()
        send_email = cleaned_data.get('send_email')
        send_sms = cleaned_data.get('send_sms')
        
        if not send_email and not send_sms:
            raise ValidationError('Please select at least one reminder method (Email or SMS)')
        
        return cleaned_data
