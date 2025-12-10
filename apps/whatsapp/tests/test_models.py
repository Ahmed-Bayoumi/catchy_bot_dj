"""
Testing approach:
- Test model creation
- Test field validation
- Test relationships (ForeignKey, OneToOne)
- Test custom methods
- Test model constraints
- Test string representation
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError
from apps.core.models import Company, LeadSource, LeadStage
from apps.leads.models import Lead
from apps.whatsapp.models import WoztellConfig, Message, Channel

User = get_user_model()


class WoztellConfigModelTest(TestCase):
    """
    Tests:
    - Model creation
    - Field validation
    - OneToOne relationship with Company
    - Custom methods (get_webhook_url)
    - String representation
    - Constraints
    """

    def setUp(self):
        """
        Creates:
        - Test company
        - Test user (admin)
        """
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            email='test@clinic.com',
            phone='+201234567890',
            is_active=True)

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            company=self.company,
            role='admin'
        )

    def test_woztell_config_creation(self):
        """
        Validates:
        - All fields are saved correctly
        - Timestamps are auto-generated
        - Default values work
        """
        config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_api_key_12345',
            api_secret='test_api_secret_67890',
            channel_id='CH123456',
            webhook_secret='webhook_secret_abc',
            webhook_url='https://example.com/webhook/',
            is_active=True
        )

        self.assertEqual(config.company, self.company)
        self.assertEqual(config.api_key, 'test_api_key_12345')
        self.assertEqual(config.api_secret, 'test_api_secret_67890')
        self.assertEqual(config.channel_id, 'CH123456')
        self.assertEqual(config.webhook_secret, 'webhook_secret_abc')
        self.assertTrue(config.is_active)

        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)

    def test_woztell_config_string_representation(self):
        """
        Test __str__ method
        """
        config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_key',
            api_secret='test_secret',
            channel_id='CH123',
            webhook_secret='secret'
        )

        expected = f"Woztell Config - {self.company.name}"
        self.assertEqual(str(config), expected)

    def test_woztell_config_one_to_one_relationship(self):
        """
        Validates:
        - One company can have only one config
        - Attempting to create duplicate raises error
        - Can access config from company using related_name
        """
        config1 = WoztellConfig.objects.create(
            company=self.company,
            api_key='key1',
            api_secret='secret1',
            channel_id='CH1',
            webhook_secret='webhook1'
        )

        self.assertEqual(self.company.woztell_config, config1)

        # Attempt to create second config for same company (should fail)
        with self.assertRaises(IntegrityError):
            WoztellConfig.objects.create(
                company=self.company,
                api_key='key2',
                api_secret='secret2',
                channel_id='CH2',
                webhook_secret='webhook2'
            )

    def test_get_webhook_url_method(self):
        """
        Test get_webhook_url() method
        """
        from django.conf import settings

        config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_key',
            api_secret='test_secret',
            channel_id='CH123',
            webhook_secret='my_secret_key_123'
        )

        if not hasattr(settings, 'SITE_URL'):
            settings.SITE_URL = 'https://example.com'

        webhook_url = config.get_webhook_url()

        self.assertIn('/api/webhook/woztell/', webhook_url)
        self.assertIn('my_secret_key_123', webhook_url)
        self.assertTrue(webhook_url.endswith('/'))

    def test_woztell_config_is_active_default(self):
        """
        Test is_active field default value

        """
        config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_key',
            api_secret='test_secret',
            channel_id='CH123',
            webhook_secret='secret'
            # is_active not specified
        )

        self.assertTrue(config.is_active)

    def test_woztell_config_cascade_delete(self):
        """
        Test CASCADE deletion

        When company is deleted, config should also be deleted
        """
        config = WoztellConfig.objects.create(
            company=self.company,
            api_key='test_key',
            api_secret='test_secret',
            channel_id='CH123',
            webhook_secret='secret'
        )

        config_id = config.id

        self.company.delete()

        self.assertFalse(
            WoztellConfig.objects.filter(id=config_id).exists()
        )


class MessageModelTest(TestCase):
    """
    Tests:
    - Message creation (incoming and outgoing)
    - Field validation
    - Relationships (Lead, User)
    - Status changes
    - Media handling
    - Custom methods
    - Ordering
    """

    def setUp(self):
        """
        Creates:
        - Company
        - Admin user and agent user
        - Lead source and stage
        - Test lead
        """
        self.company = Company.objects.create(
            name='Test Clinic',
            slug='test-clinic',
            email='test@clinic.com',
            is_active=True
        )

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

        self.whatsapp_source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366',
            order=1,
            is_active=True
        )

        self.lead_stage = LeadStage.objects.create(
            name='Lead',
            stage_type='lead',
            icon='fas fa-user',
            color='#17a2b8',
            order=1,
            is_active=True
        )

        self.lead = Lead.objects.create(
            company=self.company,
            name='Ahmed Ali',
            phone='+201234567890',
            source=self.whatsapp_source,
            stage=self.lead_stage,
            status='new',
            priority='medium'
        )

    def test_message_creation_incoming(self):
        """
        Validates:
        - All fields are saved correctly
        - Direction is incoming
        - User is None (message from customer)
        - Default status is pending
        """
        message = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='السلام عليكم، عايز أحجز كشف',
            status=Message.STATUS_DELIVERED
        )

        # Test field values
        self.assertEqual(message.lead, self.lead)
        self.assertEqual(message.direction, Message.DIRECTION_INCOMING)
        self.assertEqual(message.content, 'السلام عليكم، عايز أحجز كشف')
        self.assertEqual(message.status, Message.STATUS_DELIVERED)
        self.assertIsNone(message.user)  # Incoming messages have no user

        # Test timestamps
        self.assertIsNotNone(message.created_at)
        self.assertIsNotNone(message.updated_at)

    def test_message_creation_outgoing(self):
        """
        Validates:
        - Direction is outgoing
        - User is set (who sent the message)
        - Status defaults to pending
        """
        message = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='أهلاً بحضرتك، تحب تحجز إمتى؟'
        )

        # Test field values
        self.assertEqual(message.direction, Message.DIRECTION_OUTGOING)
        self.assertEqual(message.user, self.agent_user)
        self.assertEqual(message.status, Message.STATUS_PENDING)  # Default

    def test_message_string_representation(self):
        """
        Test __str__ method
        """
        incoming = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Test message'
        )

        self.assertIn('←', str(incoming))  # Incoming arrow
        self.assertIn(self.lead.name, str(incoming))
        self.assertIn('Test message', str(incoming))

        outgoing = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Reply message'
        )

        self.assertIn('→', str(outgoing))  # Outgoing arrow

    def test_message_is_incoming_method(self):
        """
        Test is_incoming() method
        """
        incoming = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Test'
        )

        outgoing = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test'
        )

        self.assertTrue(incoming.is_incoming())
        self.assertFalse(outgoing.is_incoming())

    def test_message_is_outgoing_method(self):
        """
        Test is_outgoing() method
        """
        incoming = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Test'
        )

        outgoing = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test'
        )

        self.assertFalse(incoming.is_outgoing())
        self.assertTrue(outgoing.is_outgoing())

    def test_message_has_media_method(self):
        """
        Test has_media() method
        """
        text_message = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Just text'
        )

        self.assertFalse(text_message.has_media())

        image_message = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Check this image',
            media_url='https://example.com/image.jpg',
            media_type=Message.MEDIA_IMAGE
        )

        self.assertTrue(image_message.has_media())

    def test_message_mark_as_sent(self):
        """
        Should:
        - Change status to sent
        - Save woztell_message_id if provided
        """
        message = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test message',
            status=Message.STATUS_PENDING
        )

        message.mark_as_sent(woztell_message_id='woztell_msg_123')

        message.refresh_from_db()

        self.assertEqual(message.status, Message.STATUS_SENT)
        self.assertEqual(message.woztell_message_id, 'woztell_msg_123')

    def test_message_mark_as_delivered(self):
        """
        Test mark_as_delivered() method
        """
        message = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test',
            status=Message.STATUS_SENT
        )

        message.mark_as_delivered()
        message.refresh_from_db()

        self.assertEqual(message.status, Message.STATUS_DELIVERED)

    def test_message_mark_as_read(self):
        """
        Test mark_as_read() method
        """
        message = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test',
            status=Message.STATUS_DELIVERED
        )

        message.mark_as_read()
        message.refresh_from_db()

        self.assertEqual(message.status, Message.STATUS_READ)

    def test_message_mark_as_failed(self):
        """
        Test mark_as_failed() method

        Should:
        - Change status to failed
        - Save error message
        """
        message = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test',
            status=Message.STATUS_PENDING
        )

        error = 'Network timeout error'
        message.mark_as_failed(error)
        message.refresh_from_db()

        self.assertEqual(message.status, Message.STATUS_FAILED)
        self.assertEqual(message.error_message, error)

    def test_message_ordering(self):
        """
        Test messages are ordered by created_at descending

        Newest message should come first
        """
        msg1 = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='First message'
        )

        msg2 = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Second message'
        )

        msg3 = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Third message'
        )

        messages = Message.objects.all()

        self.assertEqual(messages[0], msg3)
        self.assertEqual(messages[1], msg2)
        self.assertEqual(messages[2], msg1)

    def test_message_cascade_delete_from_lead(self):
        """
        Test CASCADE deletion

        When lead is deleted, all its messages should be deleted
        """
        msg1 = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Message 1'
        )

        msg2 = Message.objects.create(
            lead=self.lead,
            direction=Message.DIRECTION_INCOMING,
            content='Message 2'
        )

        msg1_id = msg1.id
        msg2_id = msg2.id

        self.lead.delete()

        # Messages should not exist
        self.assertFalse(Message.objects.filter(id=msg1_id).exists())
        self.assertFalse(Message.objects.filter(id=msg2_id).exists())

    def test_message_set_null_when_user_deleted(self):
        """
        Test SET_NULL on user deletion

        When user is deleted, message.user becomes None
        """
        message = Message.objects.create(
            lead=self.lead,
            user=self.agent_user,
            direction=Message.DIRECTION_OUTGOING,
            content='Test'
        )

        message_id = message.id

        self.agent_user.delete()

        # Message should still exist
        message = Message.objects.get(id=message_id)

        # But user should be None
        self.assertIsNone(message.user)


class ChannelModelTest(TestCase):
    """
    Tests:
    - Channel creation
    - Unique constraint (one channel per type per lead)
    - Custom methods
    - Relationships
    - Ordering
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

        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            company=self.company,
            role='agent'
        )

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

        self.lead = Lead.objects.create(
            company=self.company,
            name='Test Lead',
            phone='+201234567890',
            source=self.source,
            stage=self.stage
        )

    def test_channel_creation(self):
        """
        Test creating a channel
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP,
            channel_id='ch_12345',
            is_active=True
        )


        self.assertEqual(channel.company, self.company)
        self.assertEqual(channel.lead, self.lead)
        self.assertEqual(channel.channel_type, Channel.TYPE_WHATSAPP)
        self.assertEqual(channel.unread_count, 0)  # Default
        self.assertTrue(channel.is_active)


        self.assertIsNotNone(channel.created_at)
        self.assertIsNotNone(channel.updated_at)

    def test_channel_string_representation(self):
        """
        Test __str__ method
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        expected = f"WhatsApp - {self.lead.name}"
        self.assertEqual(str(channel), expected)

    def test_channel_unique_together_constraint(self):
        """
        One lead can have only one channel per channel_type
        """
        # Create first WhatsApp channel
        channel1 = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        # Attempt to create second WhatsApp channel (should fail)
        with self.assertRaises(IntegrityError):
            Channel.objects.create(
                company=self.company,
                lead=self.lead,
                channel_type=Channel.TYPE_WHATSAPP
            )

        # But can create SMS channel (different type)
        channel2 = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_SMS
        )

        self.assertIsNotNone(channel2)

    def test_channel_increment_unread(self):
        """
        Test increment_unread() method
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        # Initial count is 0
        self.assertEqual(channel.unread_count, 0)

        # Increment
        channel.increment_unread()
        self.assertEqual(channel.unread_count, 1)

        # Increment again
        channel.increment_unread()
        self.assertEqual(channel.unread_count, 2)

    def test_channel_mark_as_read(self):
        """
        Test mark_as_read() method
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP,
            unread_count=5
        )

        # Mark as read
        channel.mark_as_read()

        # Refresh from database
        channel.refresh_from_db()

        self.assertEqual(channel.unread_count, 0)

    def test_channel_update_last_message(self):
        """
        Test update_last_message() method
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        # Initially None
        self.assertIsNone(channel.last_message_at)

        # Update
        channel.update_last_message()

        # Refresh
        channel.refresh_from_db()

        # Should have timestamp now
        self.assertIsNotNone(channel.last_message_at)

        # Should be recent (within last minute)
        time_diff = timezone.now() - channel.last_message_at
        self.assertLess(time_diff.total_seconds(), 60)

    def test_channel_ordering(self):
        """
        Test channels are ordered by last_message_at descending

        Most recent activity first
        """
        # Create channels
        channel1 = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        # Create another lead for second channel
        lead2 = Lead.objects.create(
            company=self.company,
            name='Second Lead',
            phone='+201111111111',
            source=self.source,
            stage=self.stage
        )

        channel2 = Channel.objects.create(
            company=self.company,
            lead=lead2,
            channel_type=Channel.TYPE_WHATSAPP
        )

        # Update channel2's last message (make it more recent)
        channel2.update_last_message()

        # Get all channels
        channels = Channel.objects.all()

        # channel2 should come first (most recent)
        self.assertEqual(channels[0], channel2)

    def test_channel_cascade_delete_from_lead(self):
        """
        Test CASCADE deletion

        When lead is deleted, its channels are deleted
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        channel_id = channel.id

        # Delete lead
        self.lead.delete()

        # Channel should not exist
        self.assertFalse(Channel.objects.filter(id=channel_id).exists())

    def test_channel_cascade_delete_from_company(self):
        """
        Test CASCADE deletion

        When company is deleted, its channels are deleted
        """
        channel = Channel.objects.create(
            company=self.company,
            lead=self.lead,
            channel_type=Channel.TYPE_WHATSAPP
        )

        channel_id = channel.id

        # Delete company
        self.company.delete()

        # Channel should not exist
        self.assertFalse(Channel.objects.filter(id=channel_id).exists())