"""
Tests for Custom Decorators
============================

Tests all custom decorators to ensure proper access control.

Test Cases:
1. company_required decorator
2. admin_required decorator
3. same_company_required decorator
4. admin_or_owner_required decorator
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from apps.core.models import Company, LeadSource, LeadStage
from apps.leads.models import Lead
from apps.accounts.decorators import (
    company_required,
    admin_required,
    same_company_required,
    admin_or_owner_required
)

User = get_user_model()


class CompanyRequiredDecoratorTest(TestCase):
    """Test @company_required decorator"""
    
    def setUp(self):
        """Setup test data"""
        self.factory = RequestFactory()
        
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )
        
        self.user_with_company = User.objects.create_user(
            email='withcompany@test.com',
            password='testpass123',
            first_name='Ahmed',
            last_name='Ali',
            company=self.company
        )
        
        self.user_without_company = User.objects.create_user(
            email='nocompany@test.com',
            password='testpass123',
            first_name='Mohamed',
            last_name='Hassan'
        )
        
        @company_required
        def dummy_view(request):
            return HttpResponse('Success')
        
        self.dummy_view = dummy_view
    
    def _add_middleware(self, request):
        """Helper to add required middleware"""
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
    
    def test_user_with_company_allowed(self):
        """User with company should be allowed"""
        request = self.factory.get('/test/')
        request.user = self.user_with_company
        self._add_middleware(request)
        
        response = self.dummy_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')
    
    def test_user_without_company_denied(self):
        """User without company should be denied"""
        request = self.factory.get('/test/')
        request.user = self.user_without_company
        self._add_middleware(request)
        
        response = self.dummy_view(request)
        
        self.assertEqual(response.status_code, 302)
        
        messages = list(get_messages(request))
        self.assertTrue(len(messages) > 0)
    
    def test_anonymous_user_redirected(self):
        """Anonymous user should be redirected to login"""
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        self._add_middleware(request)
        
        response = self.dummy_view(request)
        
        self.assertEqual(response.status_code, 302)


class AdminRequiredDecoratorTest(TestCase):
    """Test @admin_required decorator"""
    
    def setUp(self):
        """Setup test data"""
        self.factory = RequestFactory()
        
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            company=self.company,
            role='admin'
        )
        
        self.agent_user = User.objects.create_user(
            email='agent@test.com',
            password='testpass123',
            first_name='Agent',
            company=self.company,
            role='agent'
        )
        
        @admin_required
        def admin_only_view(request):
            return HttpResponse('Admin Access')
        
        self.admin_only_view = admin_only_view
    
    def _add_middleware(self, request):
        """Helper to add required middleware"""
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
    
    def test_admin_user_allowed(self):
        """Admin user should be allowed"""
        request = self.factory.get('/admin-action/')
        request.user = self.admin_user
        
        response = self.admin_only_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Admin Access')
    
    def test_agent_user_denied(self):
        """Agent user should be denied"""
        request = self.factory.get('/admin-action/')
        request.user = self.agent_user
        self._add_middleware(request)  # ← Added middleware
        
        response = self.admin_only_view(request)
        
        # Should redirect to dashboard, not 403
        self.assertEqual(response.status_code, 302)


class SameCompanyRequiredDecoratorTest(TestCase):
    """Test @same_company_required decorator"""
    
    def setUp(self):
        """Setup test data"""
        self.factory = RequestFactory()
        
        self.company_a = Company.objects.create(name='Clinic A', slug='clinic-a')
        self.company_b = Company.objects.create(name='Clinic B', slug='clinic-b')
        
        self.user_a = User.objects.create_user(
            email='usera@test.com',
            password='test123',
            company=self.company_a
        )
        
        self.user_b = User.objects.create_user(
            email='userb@test.com',
            password='test123',
            company=self.company_b
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
        
        self.lead_company_a = Lead.objects.create(
            company=self.company_a,
            name='Lead A',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )
        
        self.lead_company_b = Lead.objects.create(
            company=self.company_b,
            name='Lead B',
            phone='+201234567891',
            source=self.source,
            stage=self.stage
        )
        
        @same_company_required(Lead, pk_param='pk')
        def view_lead(request, pk):
            return HttpResponse(f'Lead {pk}')
        
        self.view_lead = view_lead
    
    def _add_middleware(self, request):
        """Helper to add middleware"""
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        middleware = MessageMiddleware(lambda x: None)
        middleware.process_request(request)
    
    def test_user_can_access_own_company_lead(self):
        """User should access lead from their company"""
        request = self.factory.get(f'/leads/{self.lead_company_a.pk}/')
        request.user = self.user_a
        self._add_middleware(request)
        
        response = self.view_lead(request, pk=self.lead_company_a.pk)
        
        self.assertEqual(response.status_code, 200)
    
    def test_user_cannot_access_other_company_lead(self):
        """User should NOT access lead from different company"""
        request = self.factory.get(f'/leads/{self.lead_company_b.pk}/')
        request.user = self.user_a
        self._add_middleware(request)
        
        # Should raise 404
        with self.assertRaises(Exception):  # Http404
            self.view_lead(request, pk=self.lead_company_b.pk)


class AdminOrOwnerRequiredDecoratorTest(TestCase):
    """Test @admin_or_owner_required decorator"""
    
    def setUp(self):
        """Setup test data"""
        self.factory = RequestFactory()
        
        self.company = Company.objects.create(name='Test Clinic', slug='test-clinic')
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            company=self.company,
            role='admin'
        )
        
        self.agent1 = User.objects.create_user(
            email='agent1@test.com',
            password='test123',
            company=self.company,
            role='agent'
        )
        
        self.agent2 = User.objects.create_user(
            email='agent2@test.com',
            password='test123',
            company=self.company,
            role='agent'
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
        
        self.lead_agent1 = Lead.objects.create(
            company=self.company,
            name='Lead 1',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            assigned_to=self.agent1
        )
        
        @admin_or_owner_required(Lead, field_name='assigned_to')
        def edit_lead(request, pk):
            return HttpResponse(f'Editing {pk}')
        
        self.edit_lead = edit_lead
    
    def test_admin_can_access_any_lead(self):
        """Admin should access any lead"""
        request = self.factory.get(f'/leads/{self.lead_agent1.pk}/edit/')
        request.user = self.admin
        
        response = self.edit_lead(request, pk=self.lead_agent1.pk)
        
        self.assertEqual(response.status_code, 200)
    
    def test_assigned_agent_can_access(self):
        """Assigned agent should access their lead"""
        request = self.factory.get(f'/leads/{self.lead_agent1.pk}/edit/')
        request.user = self.agent1
        
        response = self.edit_lead(request, pk=self.lead_agent1.pk)
        
        self.assertEqual(response.status_code, 200)
    
    def test_non_assigned_agent_cannot_access(self):
        """Non-assigned agent should NOT access"""
        request = self.factory.get(f'/leads/{self.lead_agent1.pk}/edit/')
        request.user = self.agent2
        
        # Should deny access
        with self.assertRaises(Exception):  # PermissionDenied
            self.edit_lead(request, pk=self.lead_agent1.pk)
