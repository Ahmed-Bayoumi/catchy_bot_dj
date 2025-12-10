"""
This module handles communication with Woztell API for sending WhatsApp messages.

Features:
- Send text messages
- Send media messages (images, videos, documents)
- Handle API errors
- Update message status
"""

import requests
import logging
from typing import Dict, Optional, Tuple
from .models import Message, WoztellConfig

logger = logging.getLogger(__name__)


class WoztellAPIError(Exception):
    """
    Custom exception for Woztell API errors

    Used to distinguish Woztell API errors from other exceptions.
    """
    pass


class WoztellAPIClient:

    BASE_URL = 'https://api.woztell.com/v1'

    def __init__(self, config: WoztellConfig):

        self.config = config
        self.api_key = config.api_key
        self.api_secret = config.api_secret
        self.channel_id = config.channel_id

    def _get_headers(self) -> Dict[str, str]:

        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'X-API-Secret': self.api_secret
        }

    def _make_request(self,endpoint: str,method: str = 'POST',data: Optional[Dict] = None) -> Tuple[bool, Optional[Dict], Optional[str]]:

        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        try:
            logger.info(f"Making {method} request to {url}")

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
            elif method == 'PUT':
                response = requests.put(
                    url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.info(f"Response status: {response.status_code}")

            if response.status_code in [200, 201]:
                response_data = response.json()
                logger.info(f"API request successful: {response_data}")
                return True, response_data, None
            else:
                # API returned error
                error_message = f"API returned {response.status_code}"
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_message)
                except:
                    error_message = response.text or error_message

                logger.error(f"API error: {error_message}")
                return False, None, error_message

        except requests.exceptions.Timeout:
            error_message = "Request timeout - Woztell API did not respond"
            logger.error(error_message)
            return False, None, error_message

        except requests.exceptions.ConnectionError:
            error_message = "Connection error - Could not reach Woztell API"
            logger.error(error_message)
            return False, None, error_message

        except requests.exceptions.RequestException as e:
            error_message = f"Request error: {str(e)}"
            logger.error(error_message)
            return False, None, error_message

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(error_message, exc_info=True)
            return False, None, error_message

    def send_text_message(self,phone: str,message: str) -> Tuple[bool, Optional[str], Optional[str]]:

        logger.info(f"Sending text message to {phone}")

        # Prepare payload
        payload = {
            'channel_id': self.channel_id,
            'phone': phone,
            'type': 'text',
            'content': message
        }

        # Make API request
        success, response_data, error = self._make_request(
            endpoint='/messages/send',
            method='POST',
            data=payload
        )

        if success and response_data:
            woztell_message_id = response_data.get('message_id')
            logger.info(f"Message sent successfully. ID: {woztell_message_id}")
            return True, woztell_message_id, None
        else:
            return False, None, error

    def send_media_message(self,phone: str,media_url: str,media_type: str,caption: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:

        logger.info(f"Sending {media_type} message to {phone}")

        payload = {
            'channel_id': self.channel_id,
            'phone': phone,
            'type': media_type,
            'media_url': media_url
        }

        if caption:
            payload['caption'] = caption

        success, response_data, error = self._make_request(
            endpoint='/messages/send',
            method='POST',
            data=payload
        )

        if success and response_data:
            woztell_message_id = response_data.get('message_id')
            logger.info(f"Media message sent successfully. ID: {woztell_message_id}")
            return True, woztell_message_id, None
        else:
            return False, None, error

    def get_message_status(self,woztell_message_id: str) -> Tuple[bool, Optional[str], Optional[str]]:

        logger.info(f"Getting status for message {woztell_message_id}")

        success, response_data, error = self._make_request(
            endpoint=f'/messages/{woztell_message_id}/status',
            method='GET'
        )

        if success and response_data:
            status = response_data.get('status', 'unknown')
            logger.info(f"Message status: {status}")
            return True, status, None
        else:
            return False, None, error


def send_whatsapp_message(message_obj: Message) -> Tuple[bool, Optional[str]]:

    try:
        # Validate message is outgoing
        if not message_obj.is_outgoing():
            error = "Can only send outgoing messages"
            logger.error(error)
            return False, error

        # Get WoztellConfig
        try:
            config = WoztellConfig.objects.get(
                company=message_obj.lead.company,
                is_active=True
            )
        except WoztellConfig.DoesNotExist:
            error = "Woztell configuration not found or inactive"
            logger.error(error)
            message_obj.mark_as_failed(error)
            return False, error

        # Create API client
        client = WoztellAPIClient(config)

        # Send message
        if message_obj.has_media():
            # Send media message
            success, woztell_id, error = client.send_media_message(
                phone=message_obj.lead.phone,
                media_url=message_obj.media_url,
                media_type=message_obj.media_type,
                caption=message_obj.content if message_obj.content else None
            )
        else:
            # Send text message
            success, woztell_id, error = client.send_text_message(
                phone=message_obj.lead.phone,
                message=message_obj.content
            )

        # Update message status
        if success:
            message_obj.mark_as_sent(woztell_message_id=woztell_id)
            logger.info(f"Message {message_obj.id} sent successfully")
            return True, None
        else:
            message_obj.mark_as_failed(error)
            logger.error(f"Message {message_obj.id} failed: {error}")
            return False, error

    except Exception as e:
        error = f"Unexpected error: {str(e)}"
        logger.error(error, exc_info=True)
        message_obj.mark_as_failed(error)
        return False, error

