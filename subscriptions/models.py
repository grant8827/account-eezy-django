from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json


class Subscription(models.Model):
    PLAN_TYPE_CHOICES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]
    
    # Basic Information
    business = models.OneToOneField('businesses.Business', on_delete=models.CASCADE, related_name='subscription')
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default='basic')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Billing Information
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, default='JMD')
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField()
    trial_end_date = models.DateField(null=True, blank=True)
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    auto_renew = models.BooleanField(default=True)
    payment_processor_id = models.CharField(max_length=100, blank=True)  # Stripe customer ID, etc.
    
    # Plan Limits
    max_employees = models.IntegerField(default=10)
    max_businesses = models.IntegerField(default=1)
    max_transactions_per_month = models.IntegerField(default=100)
    max_payroll_runs_per_month = models.IntegerField(default=4)
    
    # Features
    has_payroll = models.BooleanField(default=True)
    has_financial_reporting = models.BooleanField(default=True)
    has_tax_calculations = models.BooleanField(default=True)
    has_multi_user_access = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_advanced_analytics = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    
    # Usage Tracking
    current_employees = models.IntegerField(default=0)
    current_businesses = models.IntegerField(default=1)
    transactions_this_month = models.IntegerField(default=0)
    payroll_runs_this_month = models.IntegerField(default=0)
    last_usage_reset = models.DateField(auto_now_add=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business']),
            models.Index(fields=['status']),
            models.Index(fields=['next_billing_date']),
            models.Index(fields=['plan_type']),
        ]
    
    def __str__(self):
        return f"{self.business.business_name} - {self.get_plan_type_display()}"
    
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status == 'active' and (not self.end_date or self.end_date >= datetime.now().date())
    
    def is_trial(self):
        """Check if subscription is in trial period"""
        return self.trial_end_date and self.trial_end_date >= datetime.now().date()
    
    def days_until_renewal(self):
        """Calculate days until next billing"""
        if self.next_billing_date:
            delta = self.next_billing_date - datetime.now().date()
            return delta.days
        return 0
    
    def can_add_employee(self):
        """Check if can add more employees"""
        return self.current_employees < self.max_employees
    
    def can_add_transaction(self):
        """Check if can add more transactions this month"""
        return self.transactions_this_month < self.max_transactions_per_month
    
    def can_run_payroll(self):
        """Check if can run more payroll this month"""
        return self.payroll_runs_this_month < self.max_payroll_runs_per_month
    
    def update_usage(self):
        """Update current usage counts"""
        from employees.models import Employee
        from transactions.models import Transaction
        from payroll.models import Payroll
        
        # Update employee count
        self.current_employees = Employee.objects.filter(business=self.business, status='active').count()
        
        # Reset monthly counters if needed
        today = datetime.now().date()
        if today.month != self.last_usage_reset.month or today.year != self.last_usage_reset.year:
            self.transactions_this_month = 0
            self.payroll_runs_this_month = 0
            self.last_usage_reset = today
        
        # Update monthly transaction count
        first_day_of_month = today.replace(day=1)
        self.transactions_this_month = Transaction.objects.filter(
            business=self.business,
            transaction_date__gte=first_day_of_month
        ).count()
        
        # Update monthly payroll runs
        self.payroll_runs_this_month = Payroll.objects.filter(
            business=self.business,
            pay_period_start__gte=first_day_of_month
        ).count()
        
        self.save()
    
    def calculate_next_billing_date(self):
        """Calculate next billing date based on cycle"""
        if self.billing_cycle == 'monthly':
            self.next_billing_date = self.start_date + timedelta(days=30)
        elif self.billing_cycle == 'quarterly':
            self.next_billing_date = self.start_date + timedelta(days=90)
        elif self.billing_cycle == 'annually':
            self.next_billing_date = self.start_date + timedelta(days=365)
    
    def cancel(self, reason=''):
        """Cancel subscription"""
        self.status = 'cancelled'
        self.auto_renew = False
        SubscriptionHistory.objects.create(
            subscription=self,
            action='cancelled',
            details=reason
        )
        self.save()
    
    def suspend(self, reason=''):
        """Suspend subscription"""
        self.status = 'suspended'
        SubscriptionHistory.objects.create(
            subscription=self,
            action='suspended',
            details=reason
        )
        self.save()
    
    def reactivate(self):
        """Reactivate subscription"""
        self.status = 'active'
        SubscriptionHistory.objects.create(
            subscription=self,
            action='reactivated'
        )
        self.save()
    
    def save(self, *args, **kwargs):
        # Set plan limits based on plan type
        if self.plan_type == 'basic':
            self.max_employees = 5
            self.max_transactions_per_month = 50
            self.max_payroll_runs_per_month = 2
            self.has_multi_user_access = False
            self.has_api_access = False
            self.has_advanced_analytics = False
            self.has_priority_support = False
        elif self.plan_type == 'standard':
            self.max_employees = 25
            self.max_transactions_per_month = 250
            self.max_payroll_runs_per_month = 4
            self.has_multi_user_access = True
            self.has_api_access = False
            self.has_advanced_analytics = True
            self.has_priority_support = False
        elif self.plan_type == 'premium':
            self.max_employees = 100
            self.max_transactions_per_month = 1000
            self.max_payroll_runs_per_month = 12
            self.has_multi_user_access = True
            self.has_api_access = True
            self.has_advanced_analytics = True
            self.has_priority_support = True
        elif self.plan_type == 'enterprise':
            self.max_employees = 999999  # Unlimited
            self.max_transactions_per_month = 999999  # Unlimited
            self.max_payroll_runs_per_month = 999999  # Unlimited
            self.has_multi_user_access = True
            self.has_api_access = True
            self.has_advanced_analytics = True
            self.has_priority_support = True
        
        # Calculate next billing date if not set
        if not self.next_billing_date:
            self.calculate_next_billing_date()
        
        super().save(*args, **kwargs)


class SubscriptionHistory(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('upgraded', 'Upgraded'),
        ('downgraded', 'Downgraded'),
        ('renewed', 'Renewed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
        ('reactivated', 'Reactivated'),
        ('payment_failed', 'Payment Failed'),
        ('payment_succeeded', 'Payment Succeeded'),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Subscription histories'
    
    def __str__(self):
        return f"{self.subscription.business.business_name} - {self.get_action_display()}"


class PaymentHistory(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='JMD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_processor_response = models.JSONField(default=dict, blank=True)
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    payment_date = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscription', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['payment_date']),
        ]
    
    def __str__(self):
        return f"{self.subscription.business.business_name} - {self.amount} {self.currency} - {self.get_status_display()}"


# PayPal Integration Models

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
    # subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='paypal_payments')
    
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