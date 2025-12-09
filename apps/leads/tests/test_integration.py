"""
Integration Tests for Leads App
================================

Tests complete user flows and integration with other apps.

Test Scenarios:
1. Complete lead lifecycle (Create → Assign → Contact → Convert → Win)
2. Multi-user scenarios (Admin and Agent interactions)
3. Integration with Core app (Company, Sources, Stages)
4. Permissions and security
5. Full CRUD flow with UI

Run tests:
    docker compose exec web python manage.py test apps.leads.tests.test_integration
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.core.models import Company, LeadSource, LeadStage
from apps.leads.models import Lead, Note, Activity

User = get_user_model()


class LeadLifecycleIntegrationTest(TestCase):
    """
    Test complete lead lifecycle from creation to won

    Flow:
    1. Admin creates lead
    2. Admin assigns to agent
    3. Agent contacts lead
    4. Agent qualifies lead
    5. Agent converts lead
    6. Admin marks as won
    """

    def setUp(self):
        """Setup test environment"""
        self.client = Client()

        # Create company
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            email='test@clinic.com',
            phone='+201234567890'
        )

        # Create sources
        self.whatsapp_source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366',
            order=1,
            is_active=True
        )

        # Create stages
        self.lead_stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1,
            is_active=True
        )

        self.patient_stage = LeadStage.objects.create(
            name='Patient',
            stage_type='patient',
            icon='fas fa-user-md',
            color='#28a745',
            order=2,
            is_active=True
        )

        self.won_stage = LeadStage.objects.create(
            name='Won',
            stage_type='won',
            icon='fas fa-trophy',
            color='#ffc107',
            order=3,
            is_active=True
        )

        # Create users
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            company=self.company,
            role='admin'
        )

        self.agent = User.objects.create_user(
            email='agent@test.com',
            password='agent123',
            first_name='Agent',
            last_name='User',
            company=self.company,
            role='agent'
        )

    def test_complete_lead_lifecycle(self):
        """
        Test: Complete flow from lead creation to won

        Steps:
        1. Admin creates lead ✓
        2. Admin assigns to agent ✓
        3. Agent adds note ✓
        4. Agent changes status to contacted ✓
        5. Agent qualifies lead ✓
        6. Agent converts to patient ✓
        7. Admin marks as won ✓

        Expected: All steps succeed, activities logged
        """

        # ===== Step 1: Admin creates lead =====
        self.client.login(email='admin@test.com', password='admin123')

        response = self.client.post(
            reverse('leads:lead_create'),
            {
                'name': 'Ahmed Ali',
                'phone': '+201234567890',
                'email': 'ahmed@example.com',
                'source': self.whatsapp_source.id,
                'stage': self.lead_stage.id,
                'status': 'new',
                'priority': 'high',
                'notes': 'Interested in teeth whitening'
            }
        )

        # Assert redirect (success)
        self.assertEqual(response.status_code, 302)

        # Get created lead
        lead = Lead.objects.latest('created_at')
        self.assertEqual(lead.name, 'Ahmed Ali')
        self.assertEqual(lead.status, 'new')

        # Assert creation activity logged
        creation_activity = Activity.objects.filter(
            lead=lead,
            activity_type='created'
        )
        self.assertTrue(creation_activity.exists())

        # ===== Step 2: Admin assigns to agent =====
        response = self.client.post(
            reverse('leads:lead_assign', kwargs={'pk': lead.pk}),
            {'assigned_to': self.agent.id}
        )

        # Refresh lead
        lead.refresh_from_db()

        # Assert assigned
        self.assertEqual(lead.assigned_to, self.agent)

        # Assert assignment activity
        assignment_activity = Activity.objects.filter(
            lead=lead,
            activity_type='assigned'
        )
        self.assertTrue(assignment_activity.exists())

        # Assert agent statistics updated
        self.agent.refresh_from_db()
        self.assertGreater(self.agent.total_leads_assigned, 0)

        # ===== Step 3: Agent adds note =====
        self.client.logout()
        self.client.login(email='agent@test.com', password='agent123')

        response = self.client.post(
            reverse('leads:lead_detail', kwargs={'pk': lead.pk}),
            {'content': 'Called patient, interested in appointment'}
        )

        # Assert note created
        notes = Note.objects.filter(lead=lead)
        self.assertEqual(notes.count(), 1)
        self.assertIn('Called patient', notes.first().content)

        # ===== Step 4: Agent changes status to contacted =====
        response = self.client.post(
            reverse('leads:lead_change_status', kwargs={'pk': lead.pk}),
            {'status': 'contacted'}
        )

        lead.refresh_from_db()
        self.assertEqual(lead.status, 'contacted')

        # ===== Step 5: Agent qualifies lead =====
        response = self.client.post(
            reverse('leads:lead_change_status', kwargs={'pk': lead.pk}),
            {'status': 'qualified'}
        )

        lead.refresh_from_db()
        self.assertEqual(lead.status, 'qualified')

        # ===== Step 6: Agent converts to patient =====
        response = self.client.post(
            reverse('leads:lead_change_status', kwargs={'pk': lead.pk}),
            {'status': 'converted'}
        )

        lead.refresh_from_db()
        self.assertEqual(lead.status, 'converted')

        # Assert agent converted count increased
        self.agent.refresh_from_db()
        self.assertGreater(self.agent.total_leads_converted, 0)

        # Change stage to Patient
        response = self.client.post(
            reverse('leads:lead_change_stage', kwargs={'pk': lead.pk}),
            {'stage': self.patient_stage.id}
        )

        lead.refresh_from_db()
        self.assertEqual(lead.stage, self.patient_stage)

        # ===== Step 7: Admin marks as won =====
        self.client.logout()
        self.client.login(email='admin@test.com', password='admin123')

        response = self.client.post(
            reverse('leads:lead_change_status', kwargs={'pk': lead.pk}),
            {'status': 'won'}
        )

        lead.refresh_from_db()
        self.assertEqual(lead.status, 'won')

        # Assert agent won count increased
        self.agent.refresh_from_db()
        self.assertGreater(self.agent.total_leads_won, 0)

        # ===== Verify complete activity log =====
        activities = Activity.objects.filter(lead=lead)

        # Should have multiple activities
        self.assertGreaterEqual(activities.count(), 6)

        # Verify activity types present
        activity_types = activities.values_list('activity_type', flat=True)
        self.assertIn('created', activity_types)
        self.assertIn('assigned', activity_types)
        self.assertIn('note_added', activity_types)
        self.assertIn('status_changed', activity_types)


class MultiUserPermissionTest(TestCase):
    """
    Test permissions and multi-user scenarios

    Scenarios:
    1. Admin can do everything
    2. Agent can only edit assigned leads
    3. Agent cannot delete leads
    4. Users from different companies are isolated
    """

    def setUp(self):
        """Setup test environment"""
        self.client = Client()

        # Company 1
        self.company1 = Company.objects.create(
            name='Clinic 1',
            slug='clinic-1'
        )

        # Company 2
        self.company2 = Company.objects.create(
            name='Clinic 2',
            slug='clinic-2'
        )

        # Source and Stage
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

        # Company 1 users
        self.admin1 = User.objects.create_user(
            email='admin1@test.com',
            password='test123',
            first_name='Admin1',
            company=self.company1,
            role='admin'
        )

        self.agent1 = User.objects.create_user(
            email='agent1@test.com',
            password='test123',
            first_name='Agent1',
            company=self.company1,
            role='agent'
        )

        # Company 2 users
        self.admin2 = User.objects.create_user(
            email='admin2@test.com',
            password='test123',
            first_name='Admin2',
            company=self.company2,
            role='admin'
        )

        # Leads
        self.lead1 = Lead.objects.create(
            company=self.company1,
            name='Lead 1',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            assigned_to=self.agent1
        )

        self.lead2 = Lead.objects.create(
            company=self.company2,
            name='Lead 2',
            phone='+201234567891',
            source=self.source,
            stage=self.stage
        )

    def test_company_isolation(self):
        """
        Test: Users can only see leads from their company

        Expected:
        - Company 1 users see only Company 1 leads
        - Company 2 users see only Company 2 leads
        """
        # Admin 1 sees only company 1 leads
        self.client.login(email='admin1@test.com', password='test123')
        response = self.client.get(reverse('leads:lead_list'))

        leads = response.context['leads']
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0], self.lead1)

        # Admin 2 sees only company 2 leads
        self.client.logout()
        self.client.login(email='admin2@test.com', password='test123')
        response = self.client.get(reverse('leads:lead_list'))

        leads = response.context['leads']
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0], self.lead2)

    def test_agent_cannot_access_other_company_lead(self):
        """
        Test: Agent from Company 1 cannot access Company 2 leads

        Expected: 404 error
        """
        self.client.login(email='agent1@test.com', password='test123')

        # Try to access Company 2's lead
        response = self.client.get(
            reverse('leads:lead_detail', kwargs={'pk': self.lead2.pk})
        )

        # Should get 404
        self.assertEqual(response.status_code, 404)

    def test_agent_can_edit_assigned_lead(self):
        """
        Test: Agent can edit lead assigned to them

        Expected: Access granted
        """
        self.client.login(email='agent1@test.com', password='test123')

        response = self.client.get(
            reverse('leads:lead_edit', kwargs={'pk': self.lead1.pk})
        )

        # Should succeed
        self.assertEqual(response.status_code, 200)

    def test_agent_cannot_delete_lead(self):
        """
        Test: Agent cannot delete leads (admin only)

        Expected: 403 Forbidden
        """
        self.client.login(email='agent1@test.com', password='test123')

        response = self.client.post(
            reverse('leads:lead_delete', kwargs={'pk': self.lead1.pk})
        )

        # Should be forbidden
        self.assertEqual(response.status_code, 403)

        # Lead should still exist
        self.assertTrue(Lead.objects.filter(pk=self.lead1.pk).exists())

    def test_admin_can_delete_lead(self):
        """
        Test: Admin can delete leads

        Expected: Lead soft deleted (status='deleted')
        """
        self.client.login(email='admin1@test.com', password='test123')

        response = self.client.post(
            reverse('leads:lead_delete', kwargs={'pk': self.lead1.pk})
        )

        # Should redirect (success)
        self.assertEqual(response.status_code, 302)

        # Lead should be soft deleted
        self.lead1.refresh_from_db()
        self.assertEqual(self.lead1.status, 'deleted')


class KanbanIntegrationTest(TestCase):
    """
    Test Kanban board functionality and drag-drop
    """

    def setUp(self):
        """Setup test environment"""
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

        # Create stages
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
            password='test123',
            first_name='Test',
            company=self.company,
            role='admin'
        )

        # Create lead in stage 1
        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage1
        )

    def test_move_lead_between_stages(self):
        """
        Test: Moving lead from stage1 to stage2 via API

        Expected: Lead stage updated, activity logged
        """
        self.client.login(email='test@test.com', password='test123')

        # Move to stage 2
        response = self.client.post(
            reverse('leads:lead_change_stage', kwargs={'pk': self.lead.pk}),
            {'stage': self.stage2.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'  # AJAX request
        )

        # Assert success
        self.assertEqual(response.status_code, 200)

        # Assert stage changed
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.stage, self.stage2)

        # Assert activity logged
        stage_change = Activity.objects.filter(
            lead=self.lead,
            activity_type='stage_changed'
        )
        self.assertTrue(stage_change.exists())

# Run all integration tests:
# docker compose exec web python manage.py test apps.leads.tests.test_integration -v 2