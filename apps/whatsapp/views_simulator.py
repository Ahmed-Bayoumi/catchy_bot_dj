"""
WhatsApp Webhook Simulator

This module provides a web interface to simulate WhatsApp webhooks
for testing purposes without needing a real Woztell account.

Features:
- Send test messages as if they came from WhatsApp
- Simulate different message types (text, media)
- Test lead creation flow
- Test message handling

Author: Catchy Bot CRM
Date: 2024
"""

import json
import logging
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from apps.accounts.decorators import company_required, admin_required
from .models import WoztellConfig, Message, Channel
from apps.leads.models import Lead

logger = logging.getLogger(__name__)


@login_required
@company_required
@admin_required
@require_http_methods(["GET"])
def webhook_simulator_page(request):
    """
    Webhook Simulator Page
    
    Displays a web interface for testing webhook functionality.
    
    URL: /api/webhook-simulator/
    
    Features:
    - Form to send test messages
    - List of recent messages
    - Configuration status
    - Quick test buttons
    """
    
    # Get company's Woztell config
    try:
        config = WoztellConfig.objects.get(
            company=request.user.company,
            is_active=True
        )
        has_config = True
    except WoztellConfig.DoesNotExist:
        config = None
        has_config = False
    
    # Get recent messages for this company
    recent_messages = Message.objects.filter(
        lead__company=request.user.company
    ).select_related('lead', 'user').order_by('-created_at')[:20]
    
    # Get all leads for this company (for dropdown)
    leads = Lead.objects.filter(
        company=request.user.company
    ).exclude(status='deleted').order_by('-created_at')[:50]
    
    context = {
        'config': config,
        'has_config': has_config,
        'recent_messages': recent_messages,
        'leads': leads,
        'page_title': 'WhatsApp Webhook Simulator'
    }
    
    return render(request, 'whatsapp/webhook_simulator.html', context)


@login_required
@company_required
@admin_required
@require_http_methods(["POST"])
def simulate_incoming_message(request):
    """
    Simulate Incoming Message
    
    Simulates a message coming from WhatsApp via Woztell webhook.
    Creates the lead if doesn't exist, saves message, updates channel.
    
    URL: /api/simulate-incoming-message/
    
    Request Payload:
    {
        "phone": "+201234567890",
        "name": "Ahmed Ali",
        "message": "Test message",
        "media_url": "",  # Optional
        "media_type": ""  # Optional
    }
    
    Returns:
        JsonResponse with result
    """
    
    try:
        # Parse JSON payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON payload'
            }, status=400)
        
        # Get Woztell config
        try:
            config = WoztellConfig.objects.get(
                company=request.user.company,
                is_active=True
            )
        except WoztellConfig.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Woztell configuration not found. Please create one first.'
            }, status=400)
        
        # Extract fields
        phone = payload.get('phone', '').strip()
        name = payload.get('name', '').strip()
        message_content = payload.get('message', '').strip()
        media_url = payload.get('media_url', '').strip()
        media_type = payload.get('media_type', '').strip()
        
        # Validate
        if not phone:
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number is required'
            }, status=400)
        
        if not message_content and not media_url:
            return JsonResponse({
                'status': 'error',
                'message': 'Message content or media URL is required'
            }, status=400)
        
        # Call the webhook receiver internally
        import requests
        
        webhook_url = f"{settings.SITE_URL}/api/webhook/woztell/{config.webhook_secret}/"
        
        webhook_payload = {
            'phone': phone,
            'name': name or f"User {phone[-4:]}",
            'message': message_content,
            'media_url': media_url if media_url else None,
            'media_type': media_type if media_type else None,
            'message_id': f'simulator_{phone}_{int(request.user.id)}'
        }
        
        # Remove None values
        webhook_payload = {k: v for k, v in webhook_payload.items() if v is not None}
        
        logger.info(f"Simulating webhook with payload: {webhook_payload}")
        
        # Send to webhook
        try:
            response = requests.post(
                webhook_url,
                json=webhook_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Message simulated successfully!',
                    'data': response_data.get('data', {})
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Webhook returned error: {response.text}'
                }, status=500)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling webhook: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error calling webhook: {str(e)}'
            }, status=500)
        except Exception as e:
            logger.error(f"Error simulating message: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': f'Simulation error: {str(e)}'
            }, status=500)

    except Exception as e:
        logger.error(f"Top-level error in simulator: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'System error: {str(e)}'
        }, status=500)


@login_required
@company_required
@admin_required
@require_http_methods(["POST"])
def quick_test_webhook(request):
    """
    Quick Test Webhook
    
    Sends a predefined test message to verify webhook is working.
    
    URL: /api/quick-test-webhook/
    
    Returns:
        JsonResponse with test result
    """
    
    try:
        # Get config
        config = WoztellConfig.objects.get(
            company=request.user.company,
            is_active=True
        )
    except WoztellConfig.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Please create Woztell configuration first'
        }, status=400)
    
    # Prepare test message
    test_payload = {
        'phone': '+201234567890',
        'name': 'Test User',
        'message': '🧪 This is a test message from the webhook simulator!'
    }
    
    # Call simulate_incoming_message internally
    import requests
    
    webhook_url = f"{settings.SITE_URL}/api/webhook/woztell/{config.webhook_secret}/"
    
    try:
        response = requests.post(
            webhook_url,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'status': 'success',
                'message': '✅ Test successful! Check the messages list below.',
                'data': response.json().get('data', {})
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'❌ Test failed: {response.text}'
            }, status=500)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'❌ Test failed: {str(e)}'
        }, status=500)


@login_required
@company_required
@require_http_methods(["GET"])
def get_lead_messages(request, lead_id):
    """
    Get Lead Messages (for simulator preview)
    
    Returns all messages for a specific lead.
    
    URL: /api/simulator/lead/<lead_id>/messages/
    
    Returns:
        JsonResponse with messages
    """
    
    try:
        # Get lead
        lead = Lead.objects.get(
            id=lead_id,
            company=request.user.company
        )
    except Lead.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Lead not found'
        }, status=404)
    
    # Get messages
    messages = Message.objects.filter(
        lead=lead
    ).select_related('user').order_by('created_at')
    
    # Build response
    messages_data = []
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'direction': msg.direction,
            'content': msg.content,
            'media_url': msg.media_url,
            'media_type': msg.media_type,
            'status': msg.status,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'user': msg.user.get_full_name() if msg.user else 'Customer'
        })
    
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
    })