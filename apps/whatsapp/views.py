import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from apps.core.models import Company, LeadSource
from apps.leads.models import Lead
from apps.accounts.decorators import company_required
from .models import WoztellConfig, Message, Channel
from .woztell_api import send_whatsapp_message

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_receiver(request, webhook_secret):

    logger.info(f"Webhook received with secret: {webhook_secret}")

    try:
        # Step 1: Validate webhook secret and get config
        try:
            config = WoztellConfig.objects.get(
                webhook_secret=webhook_secret,
                is_active=True
            )
        except WoztellConfig.DoesNotExist:
            logger.error(f"Invalid webhook secret: {webhook_secret}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid webhook secret'
            }, status=401)

        # Step 2: Parse JSON payload
        try:
            payload = json.loads(request.body)
            logger.info(f"Payload received: {payload}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON payload'
            }, status=400)

        # Step 3: Extract required fields
        phone = payload.get('phone')
        name = payload.get('name', '')
        message_content = payload.get('message', '')
        message_id = payload.get('message_id', '')
        media_url = payload.get('media_url')
        media_type = payload.get('media_type')

        # Validate required fields
        if not phone:
            logger.error("Missing phone number in payload")
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number is required'
            }, status=400)

        if not message_content and not media_url:
            logger.error("Missing message content and media")
            return JsonResponse({
                'status': 'error',
                'message': 'Message content or media is required'
            }, status=400)

        # Step 4: Use transaction to ensure data consistency
        with transaction.atomic():

            # Step 5: Get WhatsApp source
            whatsapp_source, _ = LeadSource.objects.get_or_create(
                name='WhatsApp',
                defaults={
                    'icon': 'fab fa-whatsapp',
                    'color': '#25D366',
                    'order': 1,
                    'is_active': True
                }
            )

            # Step 6: Find or create lead
            lead, lead_created = Lead.objects.get_or_create(
                company=config.company,
                phone=phone,
                defaults={
                    'name': name or f"WhatsApp User {phone[-4:]}",
                    'source': whatsapp_source,
                    'status': 'new',
                    'priority': 'medium'
                }
            )

            # Update lead name if provided and different
            if name and lead.name != name:
                lead.name = name
                lead.save(update_fields=['name'])

            # Log lead status
            if lead_created:
                logger.info(f"New lead created: {lead.id} - {lead.name}")
            else:
                logger.info(f"Existing lead found: {lead.id} - {lead.name}")

            # Step 7: Save incoming message
            message = Message.objects.create(
                lead=lead,
                direction=Message.DIRECTION_INCOMING,
                content=message_content if message_content else '[Media]',
                media_url=media_url,
                media_type=media_type,
                status=Message.STATUS_DELIVERED,  # Already delivered via WhatsApp
                woztell_message_id=message_id
            )

            logger.info(f"Message saved: {message.id}")

            # Step 8: Get or create channel
            channel, channel_created = Channel.objects.get_or_create(
                company=config.company,
                lead=lead,
                channel_type=Channel.TYPE_WHATSAPP,
                defaults={
                    'channel_id': config.channel_id,
                    'is_active': True
                }
            )

            # Step 9: Update channel metadata
            channel.increment_unread()  # Increment unread count
            channel.update_last_message()  # Update last message timestamp

            logger.info(f"Channel updated: {channel.id}")

            # Step 10: TODO - Send WebSocket notification to online users
            # This will be implemented in Phase 6 (Chat App)
            # For now, we just log it
            logger.info(f"TODO: Send WebSocket notification for lead {lead.id}")

        # Step 11: Return success response
        return JsonResponse({
            'status': 'success',
            'message': 'Message received and processed',
            'data': {
                'lead_id': lead.id,
                'lead_name': lead.name,
                'message_id': message.id,
                'channel_id': channel.id,
                'lead_created': lead_created,
                'channel_created': channel_created
            }
        }, status=200)

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in webhook: {str(e)}", exc_info=True)

        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def webhook_test(request, webhook_secret):

    try:
        config = WoztellConfig.objects.get(
            webhook_secret=webhook_secret,
            is_active=True
        )

        logger.info(f"Webhook test successful for company: {config.company.name}")

        return HttpResponse(
            f"Webhook is active for {config.company.name}",
            status=200
        )

    except WoztellConfig.DoesNotExist:
        logger.error(f"Webhook test failed: Invalid secret {webhook_secret}")

        return HttpResponse(
            "Invalid webhook secret",
            status=401
        )


@login_required
@company_required
@require_http_methods(["POST"])
def send_message_api(request):

    logger.info(f"Send message request from user: {request.user.email}")

    try:
        # Step 1: Parse JSON payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON payload'
            }, status=400)

        # Step 2: Extract fields
        lead_id = payload.get('lead_id')
        message_content = payload.get('message', '')
        media_url = payload.get('media_url')
        media_type = payload.get('media_type')

        # Step 3: Validate required fields
        if not lead_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Lead ID is required'
            }, status=400)

        if not message_content and not media_url:
            return JsonResponse({
                'status': 'error',
                'message': 'Message content or media is required'
            }, status=400)

        # Step 4: Get lead and validate access
        try:
            lead = Lead.objects.get(
                id=lead_id,
                company=request.user.company
            )
        except Lead.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Lead not found or access denied'
            }, status=404)

        # Step 5: Check permissions
        # Agent can only send to assigned leads
        if request.user.is_agent():
            if lead.assigned_to != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'You can only send messages to your assigned leads'
                }, status=403)

        # Step 6: Use transaction
        with transaction.atomic():

            # Step 7: Create outgoing message
            message = Message.objects.create(
                lead=lead,
                user=request.user,
                direction=Message.DIRECTION_OUTGOING,
                content=message_content if message_content else '[Media]',
                media_url=media_url,
                media_type=media_type,
                status=Message.STATUS_PENDING
            )

            logger.info(f"Outgoing message created: {message.id}")

            # Step 8: Send via Woztell API
            success, error = send_whatsapp_message(message)

            if not success:
                # Message failed, already marked as failed in send_whatsapp_message()
                logger.error(f"Failed to send message {message.id}: {error}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Failed to send message: {error}'
                }, status=500)

            logger.info(f"Message {message.id} sent successfully")

            # Step 9: Update channel
            channel, _ = Channel.objects.get_or_create(
                company=request.user.company,
                lead=lead,
                channel_type=Channel.TYPE_WHATSAPP,
                defaults={
                    'is_active': True
                }
            )

            # Update last message timestamp (no need to increment unread for outgoing)
            channel.update_last_message()

            # Step 10: Refresh message from DB to get updated fields
            message.refresh_from_db()

        # Step 11: Return success response
        return JsonResponse({
            'status': 'success',
            'message': 'Message sent successfully',
            'data': {
                'message_id': message.id,
                'woztell_message_id': message.woztell_message_id,
                'status': message.status,
                'created_at': message.created_at.isoformat()
            }
        }, status=200)

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in send_message_api: {str(e)}", exc_info=True)

        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)


@login_required
@company_required
@require_http_methods(["GET"])
def get_messages_api(request, lead_id):

    try:
        # Step 1: Get lead and validate access
        try:
            lead = Lead.objects.get(
                id=lead_id,
                company=request.user.company
            )
        except Lead.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Lead not found or access denied'
            }, status=404)

        # Step 2: Check permissions for agents
        if request.user.is_agent():
            if lead.assigned_to != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Access denied'
                }, status=403)

        # Step 3: Get all messages for this lead
        messages = Message.objects.filter(
            lead=lead
        ).select_related('user').order_by('created_at')

        # Step 4: Build response data
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'direction': msg.direction,
                'content': msg.content,
                'media_url': msg.media_url,
                'media_type': msg.media_type,
                'status': msg.status,
                'created_at': msg.created_at.isoformat(),
                'user': {
                    'id': msg.user.id,
                    'name': msg.user.get_full_name()
                } if msg.user else None
            })

        # Step 5: Mark channel as read
        try:
            channel = Channel.objects.get(
                lead=lead,
                channel_type=Channel.TYPE_WHATSAPP
            )
            channel.mark_as_read()
        except Channel.DoesNotExist:
            pass  # Channel doesn't exist yet, that's ok

        # Step 6: Return response
        return JsonResponse({
            'status': 'success',
            'data': {
                'lead': {
                    'id': lead.id,
                    'name': lead.name,
                    'phone': lead.phone
                },
                'messages': messages_data
            }
        }, status=200)

    except Exception as e:
        logger.error(f"Error in get_messages_api: {str(e)}", exc_info=True)

        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)