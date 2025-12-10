from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from datetime import datetime
from decimal import Decimal


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('asset_purchase', 'Asset Purchase'),
        ('asset_sale', 'Asset Sale'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
    ]
    
    CURRENCY_CHOICES = [
        ('JMD', 'Jamaican Dollar'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('CAD', 'Canadian Dollar'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('mobile_money', 'Mobile Money'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    # Basic Information
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='transactions')
    transaction_number = models.CharField(max_length=50, unique=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    category = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    
    # Financial Information
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='JMD')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    
    # Transaction Details
    transaction_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    
    # Vendor Information
    vendor_name = models.CharField(max_length=200, blank=True)
    vendor_trn = models.CharField(max_length=9, blank=True)
    vendor_address = models.TextField(blank=True)
    vendor_phone = models.CharField(max_length=20, blank=True)
    vendor_email = models.EmailField(blank=True)
    
    # Customer Information
    customer_name = models.CharField(max_length=200, blank=True)
    customer_trn = models.CharField(max_length=9, blank=True)
    customer_address = models.TextField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    
    # Tax Information
    is_taxable = models.BooleanField(default=True)
    gct_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.15)  # 15% GCT
    gct_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    withholding_tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    withholding_tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status and Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    reconciled = models.BooleanField(default=False)
    reconciled_date = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reconciled_transactions')
    
    # User Tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_transactions')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transactions')
    approved_date = models.DateTimeField(null=True, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['business', 'transaction_date']),
            models.Index(fields=['transaction_number']),
            models.Index(fields=['transaction_type', 'category']),
            models.Index(fields=['created_by']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['status']),
            models.Index(fields=['reconciled']),
        ]
    
    def __str__(self):
        return f"{self.transaction_number} - {self.description}"
    
    @property
    def total_amount(self):
        """Calculate total amount including tax"""
        return self.amount + self.gct_amount + self.withholding_tax_amount
    
    def mark_reconciled(self, user):
        """Mark transaction as reconciled"""
        self.reconciled = True
        self.reconciled_date = datetime.now()
        self.reconciled_by = user
        self.save()
    
    def save(self, *args, **kwargs):
        # Generate transaction number if not provided
        if not self.transaction_number:
            year = datetime.now().year
            business_id = self.business.id
            # Find the highest existing transaction number for this business and year
            existing_transactions = Transaction.objects.filter(
                business=self.business,
                transaction_number__startswith=f"TXN-{business_id}-{year}-"
            ).order_by('-transaction_number')
            
            if existing_transactions.exists():
                # Extract number from the highest transaction number
                last_number = existing_transactions.first().transaction_number
                try:
                    last_seq = int(last_number.split('-')[-1])
                    next_seq = last_seq + 1
                except (ValueError, IndexError):
                    next_seq = 1
            else:
                next_seq = 1
                
            self.transaction_number = f"TXN-{business_id}-{year}-{str(next_seq).zfill(6)}"
        
        # Calculate GCT amount if taxable
        if self.is_taxable and self.gct_rate > 0:
            self.gct_amount = self.amount * Decimal(str(self.gct_rate))
        
        # Calculate withholding tax amount
        if self.withholding_tax_rate > 0:
            self.withholding_tax_amount = self.amount * Decimal(str(self.withholding_tax_rate))
        
        super().save(*args, **kwargs)


class TransactionAttachment(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction.transaction_number} - {self.original_name}"