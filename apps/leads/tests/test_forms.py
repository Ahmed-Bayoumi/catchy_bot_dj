"""
Lead Forms Tests
================

Tests for all lead forms and validation.

Test Coverage:
1. LeadCreateForm - Creation form validation
2. LeadEditForm - Edit form validation
3. LeadFilterForm - Filter form functionality
4. NoteForm - Note creation validation

Run tests:
    docker compose exec web python manage.py test apps.leads.tests.test_forms
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Company, LeadSource, LeadStage
from apps.accounts.models import User
from apps.leads.models import Lead
from apps.leads.forms import (
    LeadCreateForm,
    LeadEditForm,
    NoteForm,
    LeadFilterForm,
    LeadAssignForm
)


class LeadCreateFormTest(TestCase):
    """Test LeadCreateForm validation"""

    def setUp(self):
        """Setup test data"""
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )

        self.source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366'
        )

        self.stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1
        )

        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            company=self.company
        )

    def test_valid_form(self):
        """
        Test: Form with valid data is valid

        Expected: form.is_valid() returns True
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',
                'email': 'test@example.com',
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new',
                'priority': 'medium'
            },
            company=self.company
        )

        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        """
        Test: Form without required fields is invalid

        Expected: form.is_valid() returns False, errors present
        """
        form = LeadCreateForm(
            data={},
            company=self.company
        )

        self.assertFalse(form.is_valid())

        # Check required fields have errors
        self.assertIn('name', form.errors)
        self.assertIn('phone', form.errors)

    def test_phone_validation_without_plus(self):
        """
        Test: Phone without + sign is invalid

        Expected: Validation error on phone field
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '01234567890',  # Missing +
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_phone_validation_with_plus(self):
        """
        Test: Phone with + sign is valid

        Expected: No validation errors on phone
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',  # Has +
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertTrue(form.is_valid())

    def test_phone_validation_non_numeric(self):
        """
        Test: Phone with non-numeric characters is invalid

        Expected: Validation error
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+20123ABC7890',  # Has letters
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_phone_length_validation(self):
        """
        Test: Phone must be between 10-15 digits

        Expected: Too short/long raises error
        """
        # Too short
        form_short = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+2012345',  # Only 7 digits
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertFalse(form_short.is_valid())
        self.assertIn('phone', form_short.errors)

        # Too long
        form_long = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+20123456789012345',  # 17 digits
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertFalse(form_long.is_valid())
        self.assertIn('phone', form_long.errors)

    def test_email_validation(self):
        """
        Test: Email validation works correctly

        Expected: Invalid emails rejected
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',
                'email': 'invalid-email',  # Invalid format
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_lowercase_conversion(self):
        """
        Test: Email converted to lowercase

        Expected: Email normalized to lowercase
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',
                'email': 'TEST@EXAMPLE.COM',  # Uppercase
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            },
            company=self.company
        )

        self.assertTrue(form.is_valid())

        # Email should be lowercase
        self.assertEqual(
            form.cleaned_data['email'],
            'test@example.com'
        )

    def test_tags_conversion(self):
        """
        Test: Tags string converted to list

        Expected: "tag1, tag2, tag3" → ["tag1", "tag2", "tag3"]
        """
        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new',
                'tags': 'vip, urgent, follow-up'  # String
            },
            company=self.company
        )

        self.assertTrue(form.is_valid())

        # Should be list
        tags = form.cleaned_data['tags']
        self.assertIsInstance(tags, list)
        self.assertEqual(len(tags), 3)
        self.assertIn('vip', tags)
        self.assertIn('urgent', tags)

    def test_follow_up_past_date_validation(self):
        """
        Test: Cannot set follow-up in the past

        Expected: Validation error
        """
        past_date = timezone.now() - timedelta(days=1)

        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new',
                'next_follow_up': past_date.strftime('%Y-%m-%dT%H:%M')
            },
            company=self.company
        )

        self.assertFalse(form.is_valid())
        self.assertIn('next_follow_up', form.errors)

    def test_follow_up_future_date_valid(self):
        """
        Test: Future follow-up date is valid

        Expected: No errors
        """
        future_date = timezone.now() + timedelta(days=1)

        form = LeadCreateForm(
            data={
                'name': 'Test Lead',
                'phone': '+201234567890',
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new',
                'next_follow_up': future_date.strftime('%Y-%m-%dT%H:%M')
            },
            company=self.company
        )

        self.assertTrue(form.is_valid())

    def test_form_filters_agents_by_company(self):
        """
        Test: assigned_to dropdown only shows company agents

        Expected: Other company's users not in queryset
        """
        # Create another company and user
        other_company = Company.objects.create(
            name='Other Clinic',
            slug='other-clinic'
        )

        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            company=other_company
        )

        # Create form with our company
        form = LeadCreateForm(company=self.company)

        # Get assigned_to queryset
        assigned_to_qs = form.fields['assigned_to'].queryset

        # Should contain our user
        self.assertIn(self.user, assigned_to_qs)

        # Should NOT contain other company's user
        self.assertNotIn(other_user, assigned_to_qs)


class LeadEditFormTest(TestCase):
    """Test LeadEditForm"""

    def setUp(self):
        """Setup test data"""
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )

        self.source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366'
        )

        self.stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            status='new'
        )

    def test_edit_form_with_existing_lead(self):
        """
        Test: Edit form populates with existing lead data

        Expected: Form fields contain current values
        """
        form = LeadEditForm(
            instance=self.lead,
            company=self.company
        )

        # Assert fields populated
        self.assertEqual(form.instance, self.lead)
        self.assertEqual(
            form.initial['name'],
            'Test Lead'
        )

    def test_cannot_edit_won_lead_status(self):
        """
        Test: Won/Lost leads have disabled status field

        Expected: Status field disabled
        """
        # Set lead to won
        self.lead.status = 'won'
        self.lead.save()

        form = LeadEditForm(
            instance=self.lead,
            company=self.company
        )

        # Status field should be disabled
        self.assertTrue(
            form.fields['status'].widget.attrs.get('disabled')
        )


class NoteFormTest(TestCase):
    """Test NoteForm"""

    def test_valid_note_form(self):
        """
        Test: Valid note form

        Expected: Form is valid
        """
        form = NoteForm(data={'content': 'Test note'})

        self.assertTrue(form.is_valid())

    def test_empty_note_invalid(self):
        """
        Test: Empty note content is invalid

        Expected: Validation error
        """
        form = NoteForm(data={'content': ''})

        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)


class LeadFilterFormTest(TestCase):
    """Test LeadFilterForm"""

    def setUp(self):
        """Setup test data"""
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )

        self.source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366'
        )

        self.stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1
        )

        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            company=self.company
        )

    def test_all_fields_optional(self):
        """
        Test: All filter fields are optional

        Expected: Empty form is valid
        """
        form = LeadFilterForm(
            data={},
            company=self.company
        )

        self.assertTrue(form.is_valid())

    def test_filters_agents_by_company(self):
        """
        Test: assigned_to only shows company agents

        Expected: Only company users in queryset
        """
        other_company = Company.objects.create(
            name='Other Clinic',
            slug='other-clinic'
        )

        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            company=other_company
        )

        form = LeadFilterForm(company=self.company)

        assigned_to_qs = form.fields['assigned_to'].queryset

        self.assertIn(self.user, assigned_to_qs)
        self.assertNotIn(other_user, assigned_to_qs)


class LeadAssignFormTest(TestCase):
    """Test LeadAssignForm"""

    def setUp(self):
        """Setup test data"""
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )

        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            company=self.company
        )

    def test_valid_assign_form(self):
        """
        Test: Valid assignment form

        Expected: Form is valid
        """
        form = LeadAssignForm(
            data={'assigned_to': self.user.id},
            company=self.company
        )

        self.assertTrue(form.is_valid())

    def test_missing_assigned_to(self):
        """
        Test: assigned_to is required

        Expected: Validation error
        """
        form = LeadAssignForm(
            data={},
            company=self.company
        )

        self.assertFalse(form.is_valid())
        self.assertIn('assigned_to', form.errors)

# Run all form tests:
# docker compose exec web python manage.py test apps.leads.tests.test_forms -v 2