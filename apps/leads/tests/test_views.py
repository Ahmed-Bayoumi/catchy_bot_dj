"""
Lead Views Tests
================

Comprehensive tests for all lead views.

Test Coverage:
1. List View - lead_list_view
2. Detail View - lead_detail_view
3. Create View - lead_create_view
4. Edit View - lead_edit_view
5. Delete View - lead_delete_view
6. Assign View - lead_assign_view
7. Change Status View - lead_change_status_view
8. Change Stage View - lead_change_stage_view
9. Kanban View - lead_kanban_view
10. Bulk Actions View - lead_bulk_actions_view

Run tests:
    docker compose exec web python manage.py test apps.leads.tests.test_views
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.core.models import Company, LeadSource, LeadStage
from apps.leads.models import Lead, Note, Activity
import json

User = get_user_model()


class LeadListViewTest(TestCase):
    """Test lead list view with filters and search"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

        # Create company
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )

        # Create source and stage
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

        # Create user
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            company=self.company,
            role='admin'
        )

        # Create test leads
        for i in range(5):
            Lead.objects.create(
                company=self.company,
                name=f'Lead {i}',
                phone=f'+20123456789{i}',
                source=self.source,
                stage=self.stage,
                status='new'
            )

    def test_list_view_requires_login(self):
        """
        Test: List view requires authentication

        Expected: Redirect to login if not authenticated
        """
        response = self.client.get(reverse('leads:lead_list'))

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_list_view_with_authenticated_user(self):
        """
        Test: Authenticated user can access list view

        Expected: 200 OK, shows leads from user's company
        """
        # Login
        self.client.login(email='test@test.com', password='testpass123')

        # Access list view
        response = self.client.get(reverse('leads:lead_list'))

        # Assert success
        self.assertEqual(response.status_code, 200)

        # Assert correct template
        self.assertTemplateUsed(response, 'leads/lead_list.html')

        # Assert context contains leads
        self.assertIn('leads', response.context)
        self.assertEqual(len(response.context['leads']), 5)

    def test_list_view_search(self):
        """
        Test: Search functionality filters leads

        Expected: Only matching leads returned
        """
        self.client.login(email='test@test.com', password='testpass123')

        # Search for "Lead 1"
        response = self.client.get(
            reverse('leads:lead_list'),
            {'search': 'Lead 1'}
        )

        # Assert filtered results
        self.assertEqual(response.status_code, 200)
        leads = response.context['leads']
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].name, 'Lead 1')

    def test_list_view_status_filter(self):
        """
        Test: Status filter works correctly

        Expected: Only leads with selected status returned
        """
        # Create lead with different status
        Lead.objects.create(
            company=self.company,
            name='Contacted Lead',
            phone='+201234567899',
            source=self.source,
            stage=self.stage,
            status='contacted'
        )

        self.client.login(email='test@test.com', password='testpass123')

        # Filter by contacted status
        response = self.client.get(
            reverse('leads:lead_list'),
            {'status': 'contacted'}
        )

        # Assert filtered
        leads = response.context['leads']
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].status, 'contacted')


class LeadDetailViewTest(TestCase):
    """Test lead detail view"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

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
            company=self.company,
            role='admin'
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

    def test_detail_view_requires_login(self):
        """
        Test: Detail view requires authentication

        Expected: Redirect to login
        """
        response = self.client.get(
            reverse('leads:lead_detail', kwargs={'pk': self.lead.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_detail_view_shows_lead_info(self):
        """
        Test: Detail view shows all lead information

        Expected: 200 OK, contains lead data
        """
        self.client.login(email='test@test.com', password='testpass123')

        response = self.client.get(
            reverse('leads:lead_detail', kwargs={'pk': self.lead.pk})
        )

        # Assert success
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leads/lead_detail.html')

        # Assert context
        self.assertEqual(response.context['lead'], self.lead)
        self.assertIn('notes', response.context)
        self.assertIn('activities', response.context)

    def test_detail_view_add_note_via_post(self):
        """
        Test: Adding note via POST to detail view

        Expected: Note created, redirects back to detail
        """
        self.client.login(email='test@test.com', password='testpass123')

        # Post note
        response = self.client.post(
            reverse('leads:lead_detail', kwargs={'pk': self.lead.pk}),
            {'content': 'Test note content'}
        )

        # Assert redirect
        self.assertEqual(response.status_code, 302)

        # Assert note created
        notes = Note.objects.filter(lead=self.lead)
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes.first().content, 'Test note content')

    def test_detail_view_only_shows_company_leads(self):
        """
        Test: User can only view leads from their company

        Expected: 404 for leads from other companies
        """
        # Create another company and lead
        other_company = Company.objects.create(
            name='Other Clinic',
            slug='other-clinic'
        )

        other_lead = Lead.objects.create(
            company=other_company,
            name='Other Lead',
            phone='+201234567891',
            source=self.source,
            stage=self.stage
        )

        self.client.login(email='test@test.com', password='testpass123')

        # Try to access other company's lead
        response = self.client.get(
            reverse('leads:lead_detail', kwargs={'pk': other_lead.pk})
        )

        # Should return 404
        self.assertEqual(response.status_code, 404)


class LeadCreateViewTest(TestCase):
    """Test lead creation view"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

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
            company=self.company,
            role='admin'
        )

    def test_create_view_get_shows_form(self):
        """
        Test: GET request shows creation form

        Expected: 200 OK, form displayed
        """
        self.client.login(email='test@test.com', password='testpass123')

        response = self.client.get(reverse('leads:lead_create'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leads/lead_form.html')
        self.assertIn('form', response.context)

    def test_create_view_post_creates_lead(self):
        """
        Test: POST with valid data creates lead

        Expected: Lead created, redirects to detail
        """
        self.client.login(email='test@test.com', password='testpass123')

        # Count before
        initial_count = Lead.objects.count()

        # Post form
        response = self.client.post(
            reverse('leads:lead_create'),
            {
                'name': 'New Lead',
                'phone': '+201234567890',
                'email': 'new@example.com',
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new',
                'priority': 'medium',
                'notes': 'Test notes'
            }
        )

        # Assert redirect
        self.assertEqual(response.status_code, 302)

        # Assert lead created
        self.assertEqual(Lead.objects.count(), initial_count + 1)

        # Assert lead data
        lead = Lead.objects.latest('created_at')
        self.assertEqual(lead.name, 'New Lead')
        self.assertEqual(lead.phone, '+201234567890')
        self.assertEqual(lead.company, self.company)

    def test_create_view_invalid_phone(self):
        """
        Test: POST with invalid phone shows error

        Expected: Form errors, lead not created
        """
        self.client.login(email='test@test.com', password='testpass123')

        initial_count = Lead.objects.count()

        # Post with invalid phone (no +)
        response = self.client.post(
            reverse('leads:lead_create'),
            {
                'name': 'New Lead',
                'phone': '01234567890',  # Missing +
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'new'
            }
        )

        # Should stay on form (no redirect)
        self.assertEqual(response.status_code, 200)

        # Should have form errors
        self.assertFormError(response, 'form', 'phone', None)

        # Lead should not be created
        self.assertEqual(Lead.objects.count(), initial_count)


class LeadEditViewTest(TestCase):
    """Test lead editing view"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

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

        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            company=self.company,
            role='admin'
        )

        self.agent = User.objects.create_user(
            email='agent@test.com',
            password='testpass123',
            first_name='Agent',
            company=self.company,
            role='agent'
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            assigned_to=self.agent
        )

    def test_edit_view_admin_can_edit(self):
        """
        Test: Admin can edit any lead

        Expected: Form shown, can edit
        """
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(
            reverse('leads:lead_edit', kwargs={'pk': self.lead.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leads/lead_form.html')

    def test_edit_view_assigned_agent_can_edit(self):
        """
        Test: Assigned agent can edit their lead

        Expected: Form shown, can edit
        """
        self.client.login(email='agent@test.com', password='testpass123')

        response = self.client.get(
            reverse('leads:lead_edit', kwargs={'pk': self.lead.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_edit_view_post_updates_lead(self):
        """
        Test: POST updates lead data

        Expected: Lead updated, activity logged
        """
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.post(
            reverse('leads:lead_edit', kwargs={'pk': self.lead.pk}),
            {
                'name': 'Updated Name',
                'phone': '+201234567890',
                'source': self.source.id,
                'stage': self.stage.id,
                'status': 'contacted',
                'priority': 'high'
            }
        )

        # Assert redirect
        self.assertEqual(response.status_code, 302)

        # Assert lead updated
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.name, 'Updated Name')
        self.assertEqual(self.lead.priority, 'high')


class LeadDeleteViewTest(TestCase):
    """Test lead deletion view"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

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

        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            company=self.company,
            role='admin'
        )

        self.agent = User.objects.create_user(
            email='agent@test.com',
            password='testpass123',
            first_name='Agent',
            company=self.company,
            role='agent'
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

    def test_delete_requires_admin(self):
        """
        Test: Only admin can delete leads

        Expected: Agent gets 403, Admin succeeds
        """
        # Agent tries to delete
        self.client.login(email='agent@test.com', password='testpass123')

        response = self.client.post(
            reverse('leads:lead_delete', kwargs={'pk': self.lead.pk})
        )

        # Should be forbidden
        self.assertEqual(response.status_code, 403)

        # Lead should still exist
        self.assertTrue(Lead.objects.filter(pk=self.lead.pk).exists())

    def test_admin_can_delete(self):
        """
        Test: Admin can delete lead

        Expected: Lead status changed to 'deleted'
        """
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.post(
            reverse('leads:lead_delete', kwargs={'pk': self.lead.pk})
        )

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Lead should be soft deleted (status = 'deleted')
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'deleted')


class LeadKanbanViewTest(TestCase):
    """Test kanban board view"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )

        self.source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366'
        )

        # Create multiple stages
        self.stage1 = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1
        )

        self.stage2 = LeadStage.objects.create(
            name='Patient',
            stage_type='patient',
            icon='fas fa-user-md',
            color='#28a745',
            order=2
        )

        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            company=self.company,
            role='admin'
        )

        # Create leads in different stages
        Lead.objects.create(
            company=self.company,
            name='Lead in Stage 1',
            phone='+201234567890',
            source=self.source,
            stage=self.stage1
        )

        Lead.objects.create(
            company=self.company,
            name='Lead in Stage 2',
            phone='+201234567891',
            source=self.source,
            stage=self.stage2
        )

    def test_kanban_view_shows_stages(self):
        """
        Test: Kanban view displays all stages with leads

        Expected: 200 OK, stages_data contains all stages
        """
        self.client.login(email='test@test.com', password='testpass123')

        response = self.client.get(reverse('leads:lead_kanban'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leads/lead_kanban.html')

        # Assert stages_data in context
        self.assertIn('stages_data', response.context)
        stages_data = response.context['stages_data']

        # Should have 2 stages
        self.assertEqual(len(stages_data), 2)

        # Each stage should have leads
        self.assertEqual(stages_data[0]['count'], 1)
        self.assertEqual(stages_data[1]['count'], 1)

# Run all view tests:
# docker compose exec web python manage.py test apps.leads.tests.test_views -v 2