from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json


class PayPalPayment(models.Model):
    """Model to track PayPal payments for subscriptions"""
    
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('approved', 'Approved'),
        ('captured', 'Captured'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    INTENT_CHOICES = [
        ('capture', 'Capture'),
        ('authorize', 'Authorize'),
    ]
    
    # Payment Identification
    paypal_order_id = models.CharField(max_length=100, unique=True)
    paypal_payment_id = models.CharField(max_length=100, blank=True)
    paypal_payer_id = models.CharField(max_length=100, blank=True)
    
    # User and Subscription Info
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='paypal_payments')
    subscription = models.ForeignKey('subscriptions.Subscription', on_delete=models.CASCADE, null=True, blank=True, related_name='paypal_payments')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    intent = models.CharField(max_length=20, choices=INTENT_CHOICES, default='capture')
    
    # Plan Information
    plan_name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=20)
    billing_cycle = models.CharField(max_length=20)
    
    # PayPal Response Data
    paypal_create_response = models.JSONField(default=dict, blank=True)
    paypal_capture_response = models.JSONField(default=dict, blank=True)
    paypal_webhook_data = models.JSONField(default=dict, blank=True)
    
    # Payer Information
    payer_email = models.EmailField(blank=True)
    payer_name = models.CharField(max_length=100, blank=True)
    payer_country = models.CharField(max_length=2, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Failure tracking
    failure_reason = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['paypal_order_id']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"PayPal Payment {self.paypal_order_id} - {self.amount} {self.currency} - {self.get_status_display()}"
    
    def is_successful(self):
        """Check if payment was successful"""
        return self.status in ['captured', 'completed']
    
    def is_pending(self):
        """Check if payment is pending"""
        return self.status in ['created', 'approved']
    
    def is_failed(self):
        """Check if payment failed"""
        return self.status in ['cancelled', 'failed']
    
    def update_from_paypal_response(self, paypal_response):
        """Update payment details from PayPal API response"""
        try:
            if 'id' in paypal_response:
                self.paypal_order_id = paypal_response['id']
            
            if 'status' in paypal_response:
                paypal_status = paypal_response['status'].lower()
                if paypal_status == 'created':
                    self.status = 'created'
                elif paypal_status == 'approved':
                    self.status = 'approved'
                elif paypal_status == 'completed':
                    self.status = 'captured'
                else:
                    self.status = paypal_status
            
            # Extract payer information
            if 'payer' in paypal_response:
                payer = paypal_response['payer']
                if 'email_address' in payer:
                    self.payer_email = payer['email_address']
                if 'payer_id' in payer:
                    self.paypal_payer_id = payer['payer_id']
                if 'name' in payer:
                    name_info = payer['name']
                    if 'given_name' in name_info and 'surname' in name_info:
                        self.payer_name = f"{name_info['given_name']} {name_info['surname']}"
                if 'address' in payer and 'country_code' in payer['address']:
                    self.payer_country = payer['address']['country_code']
            
            # Store the full response
            if self.status == 'created':
                self.paypal_create_response = paypal_response
            elif self.status in ['captured', 'completed']:
                self.paypal_capture_response = paypal_response
            
            self.save()
            
        except Exception as e:
            self.failure_reason = f"Error updating from PayPal response: {str(e)}"
            self.status = 'failed'
            self.save()
    
    def create_subscription_from_payment(self):
        """Create or update subscription after successful payment"""
        if not self.is_successful():
            return None
        
        from subscriptions.models import Subscription
        from businesses.models import Business
        from datetime import datetime, timedelta
        
        try:
            # Get or create business for the user
            business, created = Business.objects.get_or_create(
                owner=self.user,
                defaults={
                    'business_name': f"{self.user.first_name} {self.user.last_name}'s Business",
                    'business_type': 'individual',
                    'currency': 'JMD',
                    'status': 'active',
                }
            )
            
            # Map plan names to plan types
            plan_type_mapping = {
                'starter': 'basic',
                'professional': 'standard', 
                'business': 'premium',
                'enterprise': 'enterprise'
            }
            
            plan_type = plan_type_mapping.get(self.plan_type.lower(), 'basic')
            
            # Create or update subscription
            subscription, created = Subscription.objects.get_or_create(
                business=business,
                defaults={
                    'plan_type': plan_type,
                    'billing_cycle': self.billing_cycle,
                    'amount': self.amount * 160,  # Convert USD to JMD
                    'currency': 'JMD',
                    'start_date': datetime.now().date(),
                    'payment_method': 'paypal',
                    'payment_processor_id': self.paypal_order_id,
                    'status': 'active',
                }
            )
            
            if not created:
                # Update existing subscription
                subscription.plan_type = plan_type
                subscription.billing_cycle = self.billing_cycle
                subscription.amount = self.amount * 160
                subscription.payment_processor_id = self.paypal_order_id
                subscription.status = 'active'
                subscription.save()
            
            # Link payment to subscription
            self.subscription = subscription
            self.save()
            
            return subscription
            
        except Exception as e:
            self.failure_reason = f"Error creating subscription: {str(e)}"
            self.save()
            return None


class PayPalWebhook(models.Model):
    """Model to track PayPal webhook events"""
    
    EVENT_TYPES = [
        ('PAYMENT.CAPTURE.COMPLETED', 'Payment Capture Completed'),
        ('PAYMENT.CAPTURE.DENIED', 'Payment Capture Denied'),
        ('PAYMENT.CAPTURE.PENDING', 'Payment Capture Pending'),
        ('PAYMENT.CAPTURE.REFUNDED', 'Payment Capture Refunded'),
        ('CHECKOUT.ORDER.APPROVED', 'Checkout Order Approved'),
        ('CHECKOUT.ORDER.COMPLETED', 'Checkout Order Completed'),
        ('BILLING.SUBSCRIPTION.CREATED', 'Billing Subscription Created'),
        ('BILLING.SUBSCRIPTION.CANCELLED', 'Billing Subscription Cancelled'),
    ]
    
    webhook_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    resource_id = models.CharField(max_length=100)  # PayPal order/payment ID
    webhook_data = models.JSONField()
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    related_payment = models.ForeignKey(PayPalPayment, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['webhook_id']),
            models.Index(fields=['event_type', 'processed']),
            models.Index(fields=['resource_id']),
        ]
    
    def __str__(self):
        return f"PayPal Webhook {self.webhook_id} - {self.event_type}"
    
    def process_webhook(self):
        """Process the webhook event"""
        try:
            if self.event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.COMPLETED']:
                # Find related payment and mark as completed
                payment = PayPalPayment.objects.filter(
                    paypal_order_id=self.resource_id
                ).first()
                
                if payment:
                    payment.status = 'completed'
                    payment.captured_at = timezone.now()
                    payment.paypal_webhook_data = self.webhook_data
                    payment.save()
                    
                    # Create subscription if not already created
                    if not payment.subscription:
                        payment.create_subscription_from_payment()
                    
                    self.related_payment = payment
            
            elif self.event_type == 'PAYMENT.CAPTURE.DENIED':
                payment = PayPalPayment.objects.filter(
                    paypal_order_id=self.resource_id
                ).first()
                
                if payment:
                    payment.status = 'failed'
                    payment.failure_reason = 'Payment denied by PayPal'
                    payment.save()
                    self.related_payment = payment
            
            self.processed = True
            self.processed_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            self.processing_error = str(e)
            self.save()
            return False