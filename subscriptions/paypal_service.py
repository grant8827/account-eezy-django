import os
import requests
import base64
import json
from django.conf import settings
from django.utils import timezone
from .paypal_models import PayPalPayment, PayPalWebhook
import logging

logger = logging.getLogger(__name__)


class PayPalService:
    """Service class for PayPal API interactions"""
    
    def __init__(self):
        self.client_id = getattr(settings, 'PAYPAL_CLIENT_ID', os.getenv('PAYPAL_CLIENT_ID'))
        self.client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', os.getenv('PAYPAL_CLIENT_SECRET'))
        self.mode = getattr(settings, 'PAYPAL_MODE', os.getenv('PAYPAL_MODE', 'sandbox'))
        
        if self.mode == 'sandbox':
            self.base_url = 'https://api-m.sandbox.paypal.com'
        else:
            self.base_url = 'https://api-m.paypal.com'
        
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self):
        """Get or refresh PayPal access token"""
        if self.access_token and self.token_expires_at and timezone.now() < self.token_expires_at:
            return self.access_token
        
        try:
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Accept': 'application/json',
                'Accept-Language': 'en_US',
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = 'grant_type=client_credentials'
            
            response = requests.post(
                f'{self.base_url}/v1/oauth2/token',
                headers=headers,
                data=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in - 60)
                return self.access_token
            else:
                logger.error(f"Failed to get PayPal access token: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting PayPal access token: {str(e)}")
            return None
    
    def create_order(self, payment_data):
        """Create a PayPal order"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'PayPal-Request-Id': f"order-{payment_data['user_id']}-{timezone.now().timestamp()}"
            }
            
            # Convert JMD to USD (approximate rate: 160 JMD = 1 USD)
            usd_amount = round(payment_data['amount'] / 160, 2)
            
            order_data = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": str(usd_amount)
                    },
                    "description": f"AccountEezy {payment_data['plan_name']} Plan - {payment_data['billing_cycle']}",
                    "custom_id": f"user_{payment_data['user_id']}_plan_{payment_data['plan_type']}"
                }],
                "application_context": {
                    "brand_name": "AccountEezy",
                    "landing_page": "BILLING",
                    "user_action": "PAY_NOW",
                    "return_url": f"{settings.FRONTEND_URL}/payment/success",
                    "cancel_url": f"{settings.FRONTEND_URL}/payment/cancel"
                }
            }
            
            response = requests.post(
                f'{self.base_url}/v2/checkout/orders',
                headers=headers,
                json=order_data
            )
            
            if response.status_code == 201:
                order_response = response.json()
                
                # Create PayPalPayment record
                payment = PayPalPayment.objects.create(
                    paypal_order_id=order_response['id'],
                    user_id=payment_data['user_id'],
                    amount=usd_amount,
                    currency='USD',
                    plan_name=payment_data['plan_name'],
                    plan_type=payment_data['plan_type'],
                    billing_cycle=payment_data['billing_cycle'],
                    status='created',
                    paypal_create_response=order_response
                )
                
                return {
                    'success': True,
                    'order_id': order_response['id'],
                    'payment_id': payment.id,
                    'approval_url': next(
                        (link['href'] for link in order_response.get('links', []) 
                         if link.get('rel') == 'approve'), 
                        None
                    )
                }
            else:
                logger.error(f"Failed to create PayPal order: {response.text}")
                return {
                    'success': False,
                    'error': 'Failed to create PayPal order',
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Error creating PayPal order: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def capture_order(self, order_id):
        """Capture a PayPal order"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'PayPal-Request-Id': f"capture-{order_id}-{timezone.now().timestamp()}"
            }
            
            response = requests.post(
                f'{self.base_url}/v2/checkout/orders/{order_id}/capture',
                headers=headers
            )
            
            if response.status_code == 201:
                capture_response = response.json()
                
                # Update PayPalPayment record
                try:
                    payment = PayPalPayment.objects.get(paypal_order_id=order_id)
                    payment.update_from_paypal_response(capture_response)
                    payment.captured_at = timezone.now()
                    
                    # Create subscription if payment successful
                    if payment.is_successful():
                        subscription = payment.create_subscription_from_payment()
                        if subscription:
                            logger.info(f"Created subscription {subscription.id} for payment {payment.id}")
                    
                    return {
                        'success': True,
                        'payment_id': payment.id,
                        'subscription_id': payment.subscription.id if payment.subscription else None,
                        'capture_response': capture_response
                    }
                    
                except PayPalPayment.DoesNotExist:
                    logger.error(f"PayPal payment not found for order {order_id}")
                    return {
                        'success': False,
                        'error': 'Payment record not found'
                    }
            else:
                logger.error(f"Failed to capture PayPal order: {response.text}")
                return {
                    'success': False,
                    'error': 'Failed to capture payment',
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Error capturing PayPal order: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_order_details(self, order_id):
        """Get PayPal order details"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(
                f'{self.base_url}/v2/checkout/orders/{order_id}',
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get PayPal order details: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting PayPal order details: {str(e)}")
            return None
    
    def verify_webhook_signature(self, headers, body):
        """Verify PayPal webhook signature"""
        try:
            webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', os.getenv('PAYPAL_WEBHOOK_ID'))
            if not webhook_id:
                logger.warning("PayPal webhook ID not configured")
                return True  # Skip verification in development
            
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            verify_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            verify_data = {
                "auth_algo": headers.get('PAYPAL-AUTH-ALGO'),
                "cert_id": headers.get('PAYPAL-CERT-ID'),
                "transmission_id": headers.get('PAYPAL-TRANSMISSION-ID'),
                "transmission_sig": headers.get('PAYPAL-TRANSMISSION-SIG'),
                "transmission_time": headers.get('PAYPAL-TRANSMISSION-TIME'),
                "webhook_id": webhook_id,
                "webhook_event": json.loads(body) if isinstance(body, str) else body
            }
            
            response = requests.post(
                f'{self.base_url}/v1/notifications/verify-webhook-signature',
                headers=verify_headers,
                json=verify_data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('verification_status') == 'SUCCESS'
            else:
                logger.error(f"Failed to verify webhook signature: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def process_webhook(self, headers, body):
        """Process PayPal webhook"""
        try:
            # Verify webhook signature
            if not self.verify_webhook_signature(headers, body):
                logger.warning("PayPal webhook signature verification failed")
                # In production, you might want to reject unverified webhooks
                # return {'success': False, 'error': 'Invalid signature'}
            
            webhook_data = json.loads(body) if isinstance(body, str) else body
            
            # Create webhook record
            webhook = PayPalWebhook.objects.create(
                webhook_id=webhook_data.get('id'),
                event_type=webhook_data.get('event_type'),
                resource_id=webhook_data.get('resource', {}).get('id', ''),
                webhook_data=webhook_data
            )
            
            # Process the webhook
            success = webhook.process_webhook()
            
            return {
                'success': success,
                'webhook_id': webhook.id,
                'processed': webhook.processed
            }
            
        except Exception as e:
            logger.error(f"Error processing PayPal webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }