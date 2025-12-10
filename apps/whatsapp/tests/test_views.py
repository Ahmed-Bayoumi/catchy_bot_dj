
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.core.models import Company, LeadSource, LeadStage
from apps.leads.models import Lead
from apps.whatsapp.models import WoztellConfig, Message, Channel

User = get_user_model()


class WebhookReceiverTest(TestCase):


    def setUp(self):
        """
        Set up test data
        """
        # Create company
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            email='test@clinic.com',
            is_active=True
        )

        # Create WoztellConfig
        self.config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_api_key',
            api_secret='test_api_secret',
            channel_id='CH_TEST',
            webhook_secret='my_secret_key_123',
            is_active=True
        )

        # Create lead source
        self.whatsapp_source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366',
            order=1,
            is_active=True
        )

        # Create lead stage
        self.lead_stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1,
            is_active=True
        )

        # Create test client
        self.client = Client()

        # Build webhook URL
        self.webhook_url = reverse(
            'whatsapp:webhook_receiver',
            kwargs={'webhook_secret': self.config.webhook_secret}
        )

    def test_webhook_with_new_lead(self):
        """
        Test webhook creates new lead when phone doesn't exist
        """
        # Prepare payload
        payload = {
            'phone': '+201234567890',
            'name': 'Ahmed Ali',
            'message': 'السلام عليكم، عايز أحجز كشف',
            'message_id': 'woztell_msg_123'
        }

        # Send webhook
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertTrue(response_data['data']['lead_created'])
        self.assertTrue(response_data['data']['channel_created'])

        # Verify lead created
        lead = Lead.objects.get(phone='+201234567890')
        self.assertEqual(lead.name, 'Ahmed Ali')
        self.assertEqual(lead.company, self.company)
        self.assertEqual(lead.source, self.whatsapp_source)

        # Verify message created
        message = Message.objects.get(lead=lead)
        self.assertEqual(message.content, 'السلام عليكم، عايز أحجز كشف')
        self.assertEqual(message.direction, Message.DIRECTION_INCOMING)
        self.assertEqual(message.status, Message.STATUS_DELIVERED)

        # Verify channel created
        channel = Channel.objects.get(lead=lead)
        self.assertEqual(channel.channel_type, Channel.TYPE_WHATSAPP)
        self.assertEqual(channel.unread_count, 1)
        self.assertIsNotNone(channel.last_message_at)

    def test_webhook_with_existing_lead(self):
        """
        Test webhook uses existing lead when phone exists
        """
        # Create existing lead
        existing_lead = Lead.objects.create(
            company=self.company,
            name='Existing Lead',
            phone='+201234567890',
            source=self.whatsapp_source,
            stage=self.lead_stage,
            status='new'
        )

        # Prepare payload
        payload = {
            'phone': '+201234567890',
            'name': 'Updated Name',
            'message': 'رسالة تانية'
        }

        # Send webhook
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertFalse(response_data['data']['lead_created'])  # NOT created

        # Verify lead updated
        existing_lead.refresh_from_db()
        self.assertEqual(existing_lead.name, 'Updated Name')  # Name updated

        # Verify message count
        message_count = Message.objects.filter(lead=existing_lead).count()
        self.assertEqual(message_count, 1)

    def test_webhook_invalid_secret(self):
        """
        Test webhook rejects invalid secret
        """
        # Build URL with wrong secret
        wrong_url = reverse(
            'whatsapp:webhook_receiver',
            kwargs={'webhook_secret': 'wrong_secret'}
        )

        payload = {
            'phone': '+201234567890',
            'message': 'test'
        }

        # Send webhook
        response = self.client.post(
            wrong_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 401)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Invalid webhook secret', response_data['message'])

    def test_webhook_missing_phone(self):
        """
        Test webhook rejects payload without phone
        """
        payload = {
            'name': 'Test User',
            'message': 'test message'
            # phone missing
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Phone number is required', response_data['message'])

    def test_webhook_missing_message_and_media(self):
        """
        Test webhook rejects payload without message or media
        """
        payload = {
            'phone': '+201234567890',
            # message and media_url missing
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Message content or media is required', response_data['message'])

    def test_webhook_invalid_json(self):
        """
        Test webhook rejects invalid JSON
        """
        response = self.client.post(
            self.webhook_url,
            data='invalid json{',
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Invalid JSON', response_data['message'])

    def test_webhook_with_media(self):
        """
        Test webhook handles media messages
        """
        payload = {
            'phone': '+201234567890',
            'name': 'Test User',
            'message': '',  # Empty text
            'media_url': 'https://example.com/image.jpg',
            'media_type': 'image'
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify message with media
        lead = Lead.objects.get(phone='+201234567890')
        message = Message.objects.get(lead=lead)

        self.assertEqual(message.content, '[Media]')
        self.assertEqual(message.media_url, 'https://example.com/image.jpg')
        self.assertEqual(message.media_type, 'image')

    def test_webhook_increments_unread(self):
        """
        Test webhook increments channel unread count
        """
        # Create lead and channel
        lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.whatsapp_source,
            stage=self.lead_stage
        )

        channel = Channel.objects.create(
            company=self.company,
            lead=lead,
            channel_type=Channel.TYPE_WHATSAPP,
            unread_count=2  # Already has 2 unread
        )

        # Send webhook
        payload = {
            'phone': '+201234567890',
            'message': 'new message'
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check unread incremented
        channel.refresh_from_db()
        self.assertEqual(channel.unread_count, 3)  # 2 + 1


class WebhookTestViewTest(TestCase):
    """
    Test suite for webhook_test view

    Tests:
    - Valid secret returns success
    - Invalid secret returns error
    """

    def setUp(self):
        """
        Set up test data
        """
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            is_active=True
        )

        self.config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_key',
            api_secret='test_secret',
            channel_id='CH_TEST',
            webhook_secret='valid_secret',
            is_active=True
        )

        self.client = Client()

    def test_webhook_test_valid_secret(self):
        """
        Test webhook test endpoint with valid secret
        """
        url = reverse(
            'whatsapp:webhook_test',
            kwargs={'webhook_secret': 'valid_secret'}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Test Clinic', response.content.decode())

    def test_webhook_test_invalid_secret(self):
        """
        Test webhook test endpoint with invalid secret
        """
        url = reverse(
            'whatsapp:webhook_test',
            kwargs={'webhook_secret': 'invalid_secret'}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid', response.content.decode())


class SendMessageAPITest(TestCase):
    """
    Test suite for send_message_api view

    Tests:
    - Successful message send
    - Authentication required
    - Permission checks (agent vs admin)
    - Invalid lead
    - Missing fields
    - API failure handling
    """

    def setUp(self):
        """
        Set up test data
        """
        # Create company
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            is_active=True
        )

        # Create WoztellConfig
        self.config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_key',
            api_secret='test_secret',
            channel_id='CH_TEST',
            webhook_secret='secret',
            is_active=True
        )

        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            company=self.company,
            role='admin'
        )

        # Create agent user
        self.agent_user = User.objects.create_user(
            email='agent@test.com',
            password='testpass123',
            company=self.company,
            role='agent'
        )

        # Create lead source and stage
        self.source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            order=1
        )

        self.stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            order=1
        )

        # Create test lead
        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            assigned_to=self.agent_user
        )

        self.client = Client()
        self.url = reverse('whatsapp:send_message')

    @patch('apps.whatsapp.views.send_whatsapp_message')
    def test_send_message_success(self, mock_send):
        """
        Test successful message send
        """
        # Mock successful send
        mock_send.return_value = (True, None)

        # Login as admin
        self.client.login(email='admin@test.com', password='testpass123')

        # Prepare payload
        payload = {
            'lead_id': self.lead.id,
            'message': 'Test message'
        }

        # Send request
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('message_id', response_data['data'])

        # Verify message created
        message = Message.objects.get(id=response_data['data']['message_id'])
        self.assertEqual(message.lead, self.lead)
        self.assertEqual(message.user, self.admin_user)
        self.assertEqual(message.direction, Message.DIRECTION_OUTGOING)
        self.assertEqual(message.content, 'Test message')

    def test_send_message_authentication_required(self):
        """
        Test send message requires authentication
        """
        payload = {
            'lead_id': self.lead.id,
            'message': 'Test'
        }

        # Not logged in
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    @patch('apps.whatsapp.views.send_whatsapp_message')
    def test_agent_can_send_to_assigned_lead(self, mock_send):
        """
        Test agent can send message to assigned lead
        """
        mock_send.return_value = (True, None)

        # Login as agent
        self.client.login(email='agent@test.com', password='testpass123')

        payload = {
            'lead_id': self.lead.id,
            'message': 'Test'
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should succeed
        self.assertEqual(response.status_code, 200)

    def test_agent_cannot_send_to_unassigned_lead(self):
        """
        Test agent cannot send to lead not assigned to them
        """
        # Create another lead not assigned to agent
        other_lead = Lead.objects.create(
            company=self.company,
            name='Other Lead',
            phone='+201111111111',
            source=self.source,
            stage=self.stage
            # assigned_to not set
        )

        # Login as agent
        self.client.login(email='agent@test.com', password='testpass123')

        payload = {
            'lead_id': other_lead.id,
            'message': 'Test'
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should be forbidden
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')

    @patch('apps.whatsapp.views.send_whatsapp_message')
    def test_admin_can_send_to_any_lead(self, mock_send):
        """
        Test admin can send to any lead in company
        """
        mock_send.return_value = (True, None)

        # Create unassigned lead
        unassigned_lead = Lead.objects.create(
            company=self.company,
            name='Unassigned',
            phone='+201111111111',
            source=self.source,
            stage=self.stage
        )

        # Login as admin
        self.client.login(email='admin@test.com', password='testpass123')

        payload = {
            'lead_id': unassigned_lead.id,
            'message': 'Test'
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should succeed
        self.assertEqual(response.status_code, 200)

    def test_send_message_missing_lead_id(self):
        """
        Test send message with missing lead_id
        """
        self.client.login(email='admin@test.com', password='testpass123')

        payload = {
            'message': 'Test'
            # lead_id missing
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertIn('Lead ID is required', response_data['message'])

    def test_send_message_missing_content(self):
        """
        Test send message without message or media
        """
        self.client.login(email='admin@test.com', password='testpass123')

        payload = {
            'lead_id': self.lead.id
            # message and media_url missing
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    def test_send_message_invalid_lead(self):
        """
        Test send message with non-existent lead
        """
        self.client.login(email='admin@test.com', password='testpass123')

        payload = {
            'lead_id': 99999,  # Doesn't exist
            'message': 'Test'
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    @patch('apps.whatsapp.views.send_whatsapp_message')
    def test_send_message_api_failure(self, mock_send):
        """
        Test send message when API fails
        """
        # Mock API failure
        mock_send.return_value = (False, 'Network error')

        self.client.login(email='admin@test.com', password='testpass123')

        payload = {
            'lead_id': self.lead.id,
            'message': 'Test'
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should return error
        self.assertEqual(response.status_code, 500)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Network error', response_data['message'])


class GetMessagesAPITest(TestCase):
    """
    Test suite for get_messages_api view

    Tests:
    - Successful message retrieval
    - Authentication required
    - Permission checks
    - Invalid lead
    - Mark as read functionality
    """

    def setUp(self):
        """
        Set up test data
        """
        # Create company
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            is_active=True
        )

        # Create users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            company=self.company,
            role='admin'
        )

        self.agent_user = User.objects.create_user(
            email='agent@test.com',
            password='testpass123',
            company=self.company,
            role='agent'
        )

        # Create lead source and stage
        self.source = LeadSource.objects.create(name='WhatsApp', order=1)
        self.stage = LeadStage.objects.create(name='Lead', stage_type='lead', order=1)

        # Create lead
        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage,
            assigned_to=self.agent_user
        )

        # Create messages
        self.message1 = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='First message',
            status=Message.STATUS_DELIVERED
        )

        self.message2 = Message.objects.create(
            lead=self.lead,
            user=self.admin_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Reply message',
            status=Message.STATUS_SENT
        )

        # Create channel
        self.channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP,
            unread_count=5
        )

        self.client = Client()

    def test_get_messages_success(self):
        """
        Test successful message retrieval
        """
        self.client.login(email='admin@test.com', password='testpass123')

        url = reverse('whatsapp:get_messages', kwargs={'lead_id': self.lead.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')

        # Check lead data
        lead_data = response_data['data']['lead']
        self.assertEqual(lead_data['id'], self.lead.id)
        self.assertEqual(lead_data['name'], self.lead.name)

        # Check messages
        messages = response_data['data']['messages']
        self.assertEqual(len(messages), 2)

        # Check message order (oldest first)
        self.assertEqual(messages[0]['content'], 'First message')
        self.assertEqual(messages[1]['content'], 'Reply message')

    def test_get_messages_authentication_required(self):
        """
        Test get messages requires authentication
        """
        url = reverse('whatsapp:get_messages', kwargs={'lead_id': self.lead.id})
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_agent_can_get_assigned_lead_messages(self):
        """
        Test agent can get messages for assigned lead
        """
        self.client.login(email='agent@test.com', password='testpass123')

        url = reverse('whatsapp:get_messages', kwargs={'lead_id': self.lead.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_agent_cannot_get_unassigned_lead_messages(self):
        """
        Test agent cannot get messages for unassigned lead
        """
        # Create unassigned lead
        other_lead = Lead.objects.create(
            company=self.company,
            name='Other',
            phone='+201111111111',
            source=self.source,
            stage=self.stage
        )

        self.client.login(email='agent@test.com', password='testpass123')

        url = reverse('whatsapp:get_messages', kwargs={'lead_id': other_lead.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_get_messages_invalid_lead(self):
        """
        Test get messages with invalid lead ID
        """
        self.client.login(email='admin@test.com', password='testpass123')

        url = reverse('whatsapp:get_messages', kwargs={'lead_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_messages_marks_as_read(self):
        """
        Test get messages marks channel as read
        """
        # Verify initial unread count
        self.assertEqual(self.channel.unread_count, 5)

        self.client.login(email='admin@test.com', password='testpass123')

        url = reverse('whatsapp:get_messages', kwargs={'lead_id': self.lead.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Verify unread count reset
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.unread_count, 0)