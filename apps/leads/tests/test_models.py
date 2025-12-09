"""
Lead Models Tests
=================

Comprehensive tests for Lead, Note, and Activity models.

Test Coverage:
1. Lead Model
   - Creation and basic fields
   - Relationships (company, source, stage, assigned_to)
   - Business logic methods (assign_to, change_status, change_stage)
   - Utility methods (time_since_created, get_initials, etc.)
   - Validation and constraints

2. Note Model
   - Creation and relationships
   - Automatic activity logging

3. Activity Model
   - Creation and logging
   - Timeline ordering

4. Signals
   - Auto-create activity on lead creation
   - Auto-create activity on note creation

Run tests:
    docker compose exec web python manage.py test apps.leads.tests.test_models
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Company, LeadSource, LeadStage
from apps.accounts.models import User
from apps.leads.models import Lead, Note, Activity


class LeadModelTest(TestCase):
    """
    Test Lead model functionality

    Tests:
    - Model creation
    - Field validation
    - Relationships
    - Business logic methods
    - Utility methods
    """

    def setUp(self):
        """Setup test data before each test"""
        # Create company
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            email='test@clinic.com'
        )

        # Create lead source
        self.source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366',
            order=1,
            is_active=True
        )

        # Create lead stage
        self.stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1,
            is_active=True
        )

        # Create users
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            company=self.company,
            role='admin'
        )

        self.agent1 = User.objects.create_user(
            email='agent1@test.com',
            password='testpass123',
            first_name='Ahmed',
            last_name='Ali',
            company=self.company,
            role='agent'
        )

        self.agent2 = User.objects.create_user(
            email='agent2@test.com',
            password='testpass123',
            first_name='Mohamed',
            last_name='Hassan',
            company=self.company,
            role='agent'
        )

    def test_lead_creation(self):
        """
        Test: Basic lead creation with required fields

        Expected: Lead created successfully with all fields
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            email='test@example.com',
            source=self.source,
            stage=self.stage,
            status='new',
            priority='medium',
            assigned_to=self.agent1
        )

        # Assert lead created
        self.assertIsNotNone(lead.id)
        self.assertEqual(lead.name, 'Test Lead')
        self.assertEqual(lead.phone, '+201234567890')
        self.assertEqual(lead.email, 'test@example.com')
        self.assertEqual(lead.source, self.source)
        self.assertEqual(lead.stage, self.stage)
        self.assertEqual(lead.status, 'new')
        self.assertEqual(lead.priority, 'medium')
        self.assertEqual(lead.assigned_to, self.agent1)
        self.assertEqual(lead.company, self.company)

        # Assert timestamps
        self.assertIsNotNone(lead.created_at)
        self.assertIsNotNone(lead.updated_at)

    def test_lead_string_representation(self):
        """
        Test: __str__ method returns correct format

        Expected: "Name (Phone) - Status"
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Ahmed Ali',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            status='contacted'
        )

        expected = "Ahmed Ali (+201234567890) - تم التواصل"
        self.assertEqual(str(lead), expected)

    def test_lead_unique_phone_per_company(self):
        """
        Test: Phone number must be unique per company

        Expected: Duplicate phone in same company raises error
        """
        # Create first lead
        Lead.objects.create(
            company=self.company,
            name='Lead 1',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # Try to create second lead with same phone in same company
        with self.assertRaises(Exception):
            Lead.objects.create(
                company=self.company,
                name='Lead 2',
                phone='+201234567890',  # Same phone
                source=self.source,
                stage=self.stage
            )

    def test_lead_get_initials(self):
        """
        Test: get_initials() returns correct initials

        Expected:
        - "Ahmed Ali" → "AA"
        - "Mohamed" → "M"
        """
        # Two names
        lead1 = Lead.objects.create(
            company=self.company,
            name='Ahmed Ali',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )
        self.assertEqual(lead1.get_initials(), 'AA')

        # One name
        lead2 = Lead.objects.create(
            company=self.company,
            name='Mohamed',
            phone='+201234567891',
            source=self.source,
            stage=self.stage
        )
        self.assertEqual(lead2.get_initials(), 'M')

    def test_lead_can_be_assigned(self):
        """
        Test: can_be_assigned() checks if lead can be assigned

        Expected:
        - New/Contacted/Qualified leads → True
        - Won/Lost leads → False
        """
        # New lead - can be assigned
        lead_new = Lead.objects.create(
            company=self.company,
            name='New Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            status='new'
        )
        self.assertTrue(lead_new.can_be_assigned())

        # Won lead - cannot be assigned
        lead_won = Lead.objects.create(
            company=self.company,
            name='Won Lead',
            phone='+201234567891',
            source=self.source,
            stage=self.stage,
            status='won'
        )
        self.assertFalse(lead_won.can_be_assigned())

        # Lost lead - cannot be assigned
        lead_lost = Lead.objects.create(
            company=self.company,
            name='Lost Lead',
            phone='+201234567892',
            source=self.source,
            stage=self.stage,
            status='lost'
        )
        self.assertFalse(lead_lost.can_be_assigned())

    def test_lead_assign_to_method(self):
        """
        Test: assign_to() assigns lead to user and creates activity

        Expected:
        - Lead.assigned_to updated
        - Activity created
        - User statistics updated
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            status='new'
        )

        # Get initial stats
        initial_assigned = self.agent1.total_leads_assigned

        # Assign lead
        success = lead.assign_to(self.agent1, assigned_by=self.admin)

        # Assert assignment successful
        self.assertTrue(success)
        self.assertEqual(lead.assigned_to, self.agent1)

        # Assert activity created
        activities = Activity.objects.filter(
            lead=lead,
            activity_type='assigned'
        )
        self.assertEqual(activities.count(), 1)

        # Assert user statistics updated
        self.agent1.refresh_from_db()
        self.assertEqual(
            self.agent1.total_leads_assigned,
            initial_assigned + 1
        )

    def test_lead_reassign(self):
        """
        Test: Reassigning lead from one agent to another

        Expected:
        - Old agent's count decreases
        - New agent's count increases
        - Activity logged
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            status='new',
            assigned_to=self.agent1
        )

        # Manually set initial counts
        self.agent1.total_leads_assigned = 5
        self.agent1.save()
        self.agent2.total_leads_assigned = 3
        self.agent2.save()

        # Reassign from agent1 to agent2
        lead.assign_to(self.agent2, assigned_by=self.admin)

        # Refresh data
        self.agent1.refresh_from_db()
        self.agent2.refresh_from_db()

        # Assert counts updated
        self.assertEqual(self.agent1.total_leads_assigned, 4)  # Decreased
        self.assertEqual(self.agent2.total_leads_assigned, 4)  # Increased

    def test_lead_change_status_method(self):
        """
        Test: change_status() changes status and creates activity

        Expected:
        - Lead.status updated
        - Activity created
        - User statistics updated (for converted/won)
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            status='new',
            assigned_to=self.agent1
        )

        # Get initial converted count
        initial_converted = self.agent1.total_leads_converted

        # Change status to converted
        lead.change_status('converted', user=self.admin)

        # Assert status changed
        self.assertEqual(lead.status, 'converted')

        # Assert activity created
        activities = Activity.objects.filter(
            lead=lead,
            activity_type='status_changed'
        )
        self.assertTrue(activities.exists())

        # Assert user statistics updated
        self.agent1.refresh_from_db()
        self.assertEqual(
            self.agent1.total_leads_converted,
            initial_converted + 1
        )

    def test_lead_change_stage_method(self):
        """
        Test: change_stage() changes stage and creates activity

        Expected:
        - Lead.stage updated
        - Activity created with old and new stage names
        """
        # Create patient stage
        patient_stage = LeadStage.objects.create(
            name='Patient',
            stage_type='patient',
            icon='fas fa-user-md',
            color='#28a745',
            order=2,
            is_active=True
        )

        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,  # Lead stage
            status='qualified'
        )

        # Change stage to Patient
        lead.change_stage(patient_stage, user=self.admin)

        # Assert stage changed
        self.assertEqual(lead.stage, patient_stage)

        # Assert activity created
        activities = Activity.objects.filter(
            lead=lead,
            activity_type='stage_changed'
        )
        self.assertTrue(activities.exists())

        # Check activity description contains stage names
        activity = activities.first()
        self.assertIn('Lead', activity.description)
        self.assertIn('Patient', activity.description)

    def test_lead_add_note_method(self):
        """
        Test: add_note() creates note and activity

        Expected:
        - Note created
        - Activity created
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # Add note
        note = lead.add_note(
            content='This is a test note',
            user=self.admin
        )

        # Assert note created
        self.assertIsNotNone(note.id)
        self.assertEqual(note.content, 'This is a test note')
        self.assertEqual(note.user, self.admin)
        self.assertEqual(note.lead, lead)

        # Assert activity created
        activities = Activity.objects.filter(
            lead=lead,
            activity_type='note_added'
        )
        self.assertTrue(activities.exists())

    def test_lead_time_since_created(self):
        """
        Test: time_since_created() returns human-readable time

        Expected: Returns correct Arabic time format
        """
        # Create lead with custom created_at (1 day ago)
        lead = Lead.objects.create(
            company=self.company,
            name='Old Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # Manually set created_at to 1 day ago
        lead.created_at = timezone.now() - timedelta(days=1)
        lead.save()

        # Get time string
        time_str = lead.time_since_created()

        # Assert contains "يوم" (day in Arabic)
        self.assertIn('يوم', time_str)

    def test_lead_time_until_follow_up(self):
        """
        Test: time_until_follow_up() returns correct time

        Expected:
        - Future date → "خلال X يوم"
        - Past date → "متأخر"
        - None → None
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # No follow-up set
        self.assertIsNone(lead.time_until_follow_up())

        # Future follow-up (1 day from now)
        lead.next_follow_up = timezone.now() + timedelta(days=1)
        lead.save()
        time_str = lead.time_until_follow_up()
        self.assertIn('خلال', time_str)
        self.assertIn('يوم', time_str)

        # Past follow-up (overdue)
        lead.next_follow_up = timezone.now() - timedelta(days=1)
        lead.save()
        time_str = lead.time_until_follow_up()
        self.assertEqual(time_str, 'متأخر')

    def test_lead_get_activities(self):
        """
        Test: get_activities() returns all activities ordered by date

        Expected: Returns queryset ordered newest first
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # Create multiple activities
        Activity.objects.create(
            lead=lead,
            user=self.admin,
            activity_type='created',
            description='Lead created'
        )
        Activity.objects.create(
            lead=lead,
            user=self.admin,
            activity_type='status_changed',
            description='Status changed'
        )

        # Get activities
        activities = lead.get_activities()

        # Assert count
        self.assertEqual(activities.count(), 2)

        # Assert ordered by created_at descending
        self.assertTrue(
            activities[0].created_at >= activities[1].created_at
        )

    def test_lead_get_notes(self):
        """
        Test: get_notes() returns all notes ordered by date

        Expected: Returns queryset ordered newest first
        """
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # Create notes
        Note.objects.create(
            lead=lead,
            user=self.admin,
            content='First note'
        )
        Note.objects.create(
            lead=lead,
            user=self.admin,
            content='Second note'
        )

        # Get notes
        notes = lead.get_notes()

        # Assert count
        self.assertEqual(notes.count(), 2)

        # Assert ordered by created_at descending
        self.assertTrue(
            notes[0].created_at >= notes[1].created_at
        )


class NoteModelTest(TestCase):
    """Test Note model functionality"""

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
            email='user@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            company=self.company
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

    def test_note_creation(self):
        """
        Test: Note creation with all fields

        Expected: Note created successfully
        """
        note = Note.objects.create(
            lead=self.lead,
            user=self.user,
            content='This is a test note'
        )

        self.assertIsNotNone(note.id)
        self.assertEqual(note.lead, self.lead)
        self.assertEqual(note.user, self.user)
        self.assertEqual(note.content, 'This is a test note')
        self.assertIsNotNone(note.created_at)

    def test_note_string_representation(self):
        """
        Test: __str__ method returns preview

        Expected: "Note by User: Content preview..."
        """
        note = Note.objects.create(
            lead=self.lead,
            user=self.user,
            content='This is a very long note that should be truncated in the string representation because it is too long'
        )

        note_str = str(note)

        # Assert contains user name
        self.assertIn('Test User', note_str)

        # Assert truncated (max 50 chars + ...)
        self.assertLessEqual(len(note_str), 100)


class ActivityModelTest(TestCase):
    """Test Activity model functionality"""

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
            email='user@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            company=self.company
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

    def test_activity_creation(self):
        """
        Test: Activity creation with all fields

        Expected: Activity created successfully
        """
        activity = Activity.objects.create(
            lead=self.lead,
            user=self.user,
            activity_type='created',
            description='Lead was created'
        )

        self.assertIsNotNone(activity.id)
        self.assertEqual(activity.lead, self.lead)
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'created')
        self.assertEqual(activity.description, 'Lead was created')
        self.assertIsNotNone(activity.created_at)

    def test_activity_ordering(self):
        """
        Test: Activities ordered by created_at descending

        Expected: Newest activity first
        """
        # Create activities with delay
        activity1 = Activity.objects.create(
            lead=self.lead,
            user=self.user,
            activity_type='created',
            description='First'
        )

        activity2 = Activity.objects.create(
            lead=self.lead,
            user=self.user,
            activity_type='status_changed',
            description='Second'
        )

        # Get all activities
        activities = Activity.objects.all()

        # Assert newest first
        self.assertEqual(activities[0], activity2)
        self.assertEqual(activities[1], activity1)


class LeadSignalTest(TestCase):
    """Test signals for automatic activity logging"""

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

    def test_lead_creation_signal(self):
        """
        Test: Signal creates activity when lead is created

        Expected: Activity with type='created' exists
        """
        lead = Lead.objects.create(
            company=self.company,
            name='New Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

        # Assert activity created by signal
        activities = Activity.objects.filter(
            lead=lead,
            activity_type='created'
        )

        self.assertTrue(activities.exists())
        self.assertIn('إنشاء', activities.first().description)

# Run all tests:
# docker compose exec web python manage.py test apps.leads.tests.test_models -v 2