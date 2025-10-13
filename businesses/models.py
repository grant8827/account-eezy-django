from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator


class Business(models.Model):
    BUSINESS_TYPE_CHOICES = [
        ('Sole Proprietorship', 'Sole Proprietorship'),
        ('Partnership', 'Partnership'),
        ('Limited Liability Company', 'Limited Liability Company'),
        ('Corporation', 'Corporation'),
        ('Non-Profit Organization', 'Non-Profit Organization'),
        ('Cooperative', 'Cooperative'),
        ('Other', 'Other'),
    ]
    
    INDUSTRY_CHOICES = [
        ('Agriculture', 'Agriculture'),
        ('Mining', 'Mining'),
        ('Manufacturing', 'Manufacturing'),
        ('Construction', 'Construction'),
        ('Retail Trade', 'Retail Trade'),
        ('Wholesale Trade', 'Wholesale Trade'),
        ('Transportation', 'Transportation'),
        ('Information Technology', 'Information Technology'),
        ('Finance and Insurance', 'Finance and Insurance'),
        ('Real Estate', 'Real Estate'),
        ('Professional Services', 'Professional Services'),
        ('Education', 'Education'),
        ('Healthcare', 'Healthcare'),
        ('Hospitality', 'Hospitality'),
        ('Entertainment', 'Entertainment'),
        ('Government', 'Government'),
        ('Other', 'Other'),
    ]
    
    PARISH_CHOICES = [
        ('Kingston', 'Kingston'),
        ('St. Andrew', 'St. Andrew'),
        ('St. Thomas', 'St. Thomas'),
        ('Portland', 'Portland'),
        ('St. Mary', 'St. Mary'),
        ('St. Ann', 'St. Ann'),
        ('Trelawny', 'Trelawny'),
        ('St. James', 'St. James'),
        ('Hanover', 'Hanover'),
        ('Westmoreland', 'Westmoreland'),
        ('St. Elizabeth', 'St. Elizabeth'),
        ('Manchester', 'Manchester'),
        ('Clarendon', 'Clarendon'),
        ('St. Catherine', 'St. Catherine'),
    ]
    
    SUBSCRIPTION_STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    
    SUBSCRIPTION_PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    
    PAY_PERIOD_CHOICES = [
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    # Basic Information
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_businesses')
    name = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=50, unique=True)
    trn = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="TRN must be exactly 9 digits")],
        unique=True
    )
    nis = models.CharField(
        max_length=9,
        blank=True,
        validators=[RegexValidator(regex=r'^\d{9}$', message="NIS must be exactly 9 digits")]
    )
    business_type = models.CharField(max_length=30, choices=BUSINESS_TYPE_CHOICES)
    industry = models.CharField(max_length=30, choices=INDUSTRY_CHOICES)
    
    # Address
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    parish = models.CharField(max_length=20, choices=PARISH_CHOICES)
    postal_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=100, default='Jamaica')
    
    # Contact Information
    phone = models.CharField(max_length=20, validators=[RegexValidator(regex=r'^\+?[\d\s\-\(\)]{7,20}$', message="Please enter a valid phone number")])
    email = models.EmailField()
    website = models.URLField(blank=True)
    
    # Subscription Information
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='trial')
    subscription_plan = models.CharField(max_length=20, choices=SUBSCRIPTION_PLAN_CHOICES, default='basic')
    subscription_start_date = models.DateTimeField(auto_now_add=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # Billing Information
    last_billing_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    billing_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('pending', 'Pending'), ('failed', 'Failed')], default='pending')
    
    # Payroll Settings
    pay_period = models.CharField(max_length=20, choices=PAY_PERIOD_CHOICES, default='monthly')
    pay_day = models.PositiveIntegerField(default=28)
    overtime_rate = models.DecimalField(max_digits=4, decimal_places=2, default=1.5)
    public_holiday_rate = models.DecimalField(max_digits=4, decimal_places=2, default=2.0)
    
    # Tax Settings
    paye_registered = models.BooleanField(default=False)
    nis_registered = models.BooleanField(default=False)
    education_tax_registered = models.BooleanField(default=False)
    heart_trust_registered = models.BooleanField(default=False)
    gct_registered = models.BooleanField(default=False)
    tax_year = models.PositiveIntegerField(default=2024)
    
    # Settings
    fiscal_year_end = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='JMD')
    timezone = models.CharField(max_length=50, default='America/Jamaica')
    date_format = models.CharField(max_length=20, default='DD/MM/YYYY')
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'business'
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['trn']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['subscription_status']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def employee_count(self):
        return self.employees.filter(is_active=True).count()
    
    def save(self, *args, **kwargs):
        # Set subscription end date for trial (30 days)
        if self.subscription_status == 'trial' and not self.subscription_end_date:
            from datetime import datetime, timedelta
            self.subscription_end_date = datetime.now() + timedelta(days=30)
        super().save(*args, **kwargs)