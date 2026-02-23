from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import datetime, timedelta


class Payroll(models.Model):
    PAY_PERIOD_TYPE_CHOICES = [
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('mobile_payment', 'Mobile Payment'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='payrolls')
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='payrolls')
    payroll_number = models.CharField(max_length=50, unique=True, blank=True)
    
    # Pay Period
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    pay_period_type = models.CharField(max_length=20, choices=PAY_PERIOD_TYPE_CHOICES)
    
    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    back_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Work Record
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    holiday_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sick_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    vacation_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    unpaid_leave_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Jamaica Tax Deductions
    paye_taxable_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paye_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    paye_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    nis_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    nis_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.03)  # 3%
    
    education_tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.025)  # 2.5%
    education_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    heart_trust_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.03)  # 3%
    heart_trust_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Pension
    pension_employee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.05)  # 5%
    pension_employer_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.05)  # 5%
    pension_employee_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pension_employer_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Total Deductions
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Net Pay
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Payment Information
    pay_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    routing_number = models.CharField(max_length=20, blank=True)
    check_number = models.CharField(max_length=20, blank=True)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateTimeField(null=True, blank=True)
    
    # Jamaica Tax Calculation Settings
    personal_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=1500000)  # JMD 1.5M
    paye_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=1000000)  # JMD 1M
    education_tax_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=500000)  # JMD 500k
    
    # Status and Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    
    # User Tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_payrolls')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_payrolls')
    processed_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payroll'
        ordering = ['-pay_period_start', '-created_at']
        indexes = [
            models.Index(fields=['business', 'pay_period_start']),
            models.Index(fields=['employee', 'pay_period_start']),
            models.Index(fields=['payroll_number']),
            models.Index(fields=['status']),
            models.Index(fields=['pay_date']),
        ]
    
    def __str__(self):
        return f"{self.payroll_number} - {self.employee.full_name}"
    
    def calculate_jamaica_taxes(self):
        """Calculate Jamaica tax deductions (PAYE, NIS, Education Tax, HEART Trust)"""
        annual_gross = self.gross_earnings * 12  # Assuming monthly payroll
        
        # PAYE Calculation (Jamaica Income Tax)
        taxable_income = max(0, annual_gross - self.personal_allowance)
        
        paye_amount = Decimal('0')
        if taxable_income > 0:
            # Jamaica tax brackets for 2024
            if taxable_income <= Decimal('1500000'):
                paye_amount = Decimal('0')
            elif taxable_income <= Decimal('6000000'):
                paye_amount = (taxable_income - Decimal('1500000')) * Decimal('0.25')
            else:
                paye_amount = (Decimal('4500000') * Decimal('0.25')) + ((taxable_income - Decimal('6000000')) * Decimal('0.30'))
        
        self.paye_taxable_income = taxable_income
        self.paye_amount = paye_amount / 12  # Monthly amount
        
        # NIS Contribution (3% on income up to JMD 1M annually)
        nisable_income = min(annual_gross, Decimal('1000000'))
        self.nis_contribution = (nisable_income * Decimal(str(self.nis_rate))) / 12
        
        # Education Tax (2.5% on income above JMD 500k annually)
        education_taxable_income = max(Decimal('0'), annual_gross - self.education_tax_threshold)
        self.education_tax_amount = (education_taxable_income * Decimal(str(self.education_tax_rate))) / 12
        
        # HEART Trust/NTA (3% on income)
        self.heart_trust_amount = (annual_gross * Decimal(str(self.heart_trust_rate))) / 12
        
        # Pension contribution (if applicable)
        if self.pension_employee_rate > 0:
            self.pension_employee_contribution = self.gross_earnings * Decimal(str(self.pension_employee_rate))
            self.pension_employer_contribution = self.gross_earnings * Decimal(str(self.pension_employer_rate))
    
    def calculate_totals(self):
        """Calculate gross earnings, total deductions, and net pay"""
        # Calculate gross earnings
        self.gross_earnings = (
            self.basic_salary + 
            self.overtime_amount + 
            self.bonus + 
            self.commission + 
            self.back_pay
        )
        
        # Calculate Jamaica taxes
        self.calculate_jamaica_taxes()
        
        # Calculate total deductions
        self.total_deductions = (
            self.paye_amount +
            self.nis_contribution +
            self.education_tax_amount +
            self.heart_trust_amount +
            self.pension_employee_contribution
        )
        
        # Calculate net pay
        self.net_pay = self.gross_earnings - self.total_deductions
    
    def approve(self, approver, comments=''):
        """Approve payroll"""
        self.status = 'approved'
        PayrollApproval.objects.create(
            payroll=self,
            approver=approver,
            comments=comments
        )
        self.save()
    
    def mark_as_paid(self, user):
        """Mark payroll as paid"""
        self.is_paid = True
        self.paid_date = datetime.now()
        self.status = 'paid'
        self.processed_by = user
        self.processed_date = datetime.now()
        self.save()
    
    def save(self, *args, **kwargs):
        # Generate payroll number if not provided
        if not self.payroll_number:
            year = datetime.now().year
            month = str(datetime.now().month).zfill(2)
            count = Payroll.objects.filter(business=self.business).count()
            self.payroll_number = f"PAY-{year}{month}-{str(count + 1).zfill(5)}"
        
        # Calculate overtime amount
        self.overtime_amount = self.overtime_hours * self.overtime_rate
        
        # Calculate all totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)


class PayrollAllowance(models.Model):
    ALLOWANCE_TYPE_CHOICES = [
        ('transport', 'Transport'),
        ('meal', 'Meal'),
        ('housing', 'Housing'),
        ('communication', 'Communication'),
        ('other', 'Other'),
    ]
    
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='allowances')
    allowance_type = models.CharField(max_length=20, choices=ALLOWANCE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    taxable = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.payroll.employee.full_name} - {self.get_allowance_type_display()}: {self.amount}"


class PayrollDeduction(models.Model):
    DEDUCTION_TYPE_CHOICES = [
        ('loan_repayment', 'Loan Repayment'),
        ('union_dues', 'Union Dues'),
        ('insurance', 'Insurance'),
        ('garnishment', 'Garnishment'),
        ('advance', 'Advance'),
        ('other', 'Other'),
    ]
    
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='other_deductions')
    deduction_type = models.CharField(max_length=20, choices=DEDUCTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)
    recurring = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.payroll.employee.full_name} - {self.get_deduction_type_display()}: {self.amount}"


class PayrollApproval(models.Model):
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    approved_date = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.payroll.payroll_number} - Approved by {self.approver.get_full_name()}"