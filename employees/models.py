from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta


class Employee(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('common_law', 'Common Law'),
    ]
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('intern', 'Intern'),
    ]
    
    WORK_DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    SALARY_FREQUENCY_CHOICES = [
        ('hourly', 'Hourly'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('annually', 'Annually'),
    ]
    
    ALLOWANCE_TYPE_CHOICES = [
        ('transport', 'Transport'),
        ('meal', 'Meal'),
        ('housing', 'Housing'),
        ('communication', 'Communication'),
        ('other', 'Other'),
    ]
    
    BENEFIT_TYPE_CHOICES = [
        ('health_insurance', 'Health Insurance'),
        ('dental', 'Dental'),
        ('vision', 'Vision'),
        ('life_insurance', 'Life Insurance'),
        ('pension', 'Pension'),
        ('vacation', 'Vacation'),
        ('sick_leave', 'Sick Leave'),
        ('other', 'Other'),
    ]
    
    TAX_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married_joint', 'Married Filing Jointly'),
        ('married_separate', 'Married Filing Separately'),
        ('head_of_household', 'Head of Household'),
    ]
    
    DOCUMENT_TYPE_CHOICES = [
        ('contract', 'Contract'),
        ('tax_form', 'Tax Form'),
        ('bank_form', 'Bank Form'),
        ('id_copy', 'ID Copy'),
        ('resume', 'Resume'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]
    
    LEAVE_TYPE_CHOICES = [
        ('vacation', 'Vacation'),
        ('sick', 'Sick'),
        ('personal', 'Personal'),
        ('maternity', 'Maternity'),
        ('paternity', 'Paternity'),
        ('bereavement', 'Bereavement'),
        ('other', 'Other'),
    ]
    
    LEAVE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    
    TERMINATION_TYPE_CHOICES = [
        ('voluntary', 'Voluntary'),
        ('involuntary', 'Involuntary'),
        ('retirement', 'Retirement'),
        ('end_of_contract', 'End of Contract'),
    ]
    
    DISCIPLINARY_TYPE_CHOICES = [
        ('verbal_warning', 'Verbal Warning'),
        ('written_warning', 'Written Warning'),
        ('suspension', 'Suspension'),
        ('termination', 'Termination'),
    ]
    
    ACCOUNT_TYPE_CHOICES = [
        ('savings', 'Savings'),
        ('checking', 'Checking'),
    ]
    
    # Basic Information
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profiles')
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='employees')
    employee_id = models.CharField(max_length=50, unique=True, blank=True)
    
    # Personal Information
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True)
    nationality = models.CharField(max_length=50, default='Jamaican')
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_address = models.TextField(blank=True)
    
    # Employment Information
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    
    # Work Schedule
    hours_per_week = models.PositiveIntegerField(default=40)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Probation
    probation_months = models.PositiveIntegerField(default=3)
    probation_end_date = models.DateField(null=True, blank=True)
    
    # Supervisor
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_employees')
    
    # Compensation
    base_salary_amount = models.DecimalField(max_digits=12, decimal_places=2)
    salary_currency = models.CharField(max_length=3, default='JMD')
    salary_frequency = models.CharField(max_length=20, choices=SALARY_FREQUENCY_CHOICES, default='monthly')
    overtime_eligible = models.BooleanField(default=True)
    overtime_rate = models.DecimalField(max_digits=4, decimal_places=2, default=1.5)
    
    # Tax Information
    trn = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="TRN must be exactly 9 digits")]
    )
    nis = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="NIS must be exactly 9 digits")]
    )
    tax_status = models.CharField(max_length=20, choices=TAX_STATUS_CHOICES, default='single')
    dependents = models.PositiveIntegerField(default=0)
    education_credit = models.BooleanField(default=False)
    pension_contribution_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.05)  # 5%
    
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    routing_number = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, blank=True)
    
    # Leave Entitlements
    vacation_days_entitlement = models.PositiveIntegerField(default=14)
    vacation_days_used = models.PositiveIntegerField(default=0)
    sick_days_entitlement = models.PositiveIntegerField(default=10)
    sick_days_used = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Termination Information
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)
    termination_type = models.CharField(max_length=20, choices=TERMINATION_TYPE_CHOICES, blank=True)
    notice_period = models.PositiveIntegerField(null=True, blank=True)
    final_pay_date = models.DateField(null=True, blank=True)
    exit_interview_completed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['business']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['trn']),
            models.Index(fields=['nis']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['business', 'employee_id']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def employment_status(self):
        if not self.is_active:
            return 'terminated'
        if self.probation_end_date and datetime.now().date() < self.probation_end_date:
            return 'probation' 
        return 'active'
    
    @property
    def vacation_days_remaining(self):
        return max(0, self.vacation_days_entitlement - self.vacation_days_used)
    
    @property
    def sick_days_remaining(self):
        return max(0, self.sick_days_entitlement - self.sick_days_used)
    
    def calculate_annual_gross_salary(self):
        """Calculate annual gross salary based on frequency"""
        amount = float(self.base_salary_amount)
        
        if self.salary_frequency == 'hourly':
            return amount * self.hours_per_week * 52
        elif self.salary_frequency == 'weekly':
            return amount * 52
        elif self.salary_frequency == 'bi-weekly':
            return amount * 26
        elif self.salary_frequency == 'monthly':
            return amount * 12
        elif self.salary_frequency == 'annually':
            return amount
        else:
            return amount * 12
    
    def terminate(self, termination_data):
        """Terminate employee"""
        self.is_active = False
        self.end_date = termination_data.get('date', datetime.now().date())
        self.termination_date = termination_data.get('date', datetime.now().date())
        self.termination_reason = termination_data.get('reason', '')
        self.termination_type = termination_data.get('type', 'voluntary')
        self.notice_period = termination_data.get('notice_period')
        self.final_pay_date = termination_data.get('final_pay_date')
        self.save()
    
    def save(self, *args, **kwargs):
        # Generate employee ID if not provided
        if not self.employee_id:
            year = datetime.now().year
            count = Employee.objects.filter(business=self.business).count()
            self.employee_id = f"EMP-{year}-{str(count + 1).zfill(4)}"
        
        # Set probation end date
        if not self.probation_end_date and self.start_date:
            self.probation_end_date = self.start_date + timedelta(days=self.probation_months * 30)
        
        super().save(*args, **kwargs)


class EmployeeAllowance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='allowances')
    allowance_type = models.CharField(max_length=20, choices=Employee.ALLOWANCE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    taxable = models.BooleanField(default=True)
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_allowance_type_display()}: {self.amount}"


class EmployeeBenefit(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='benefits')
    benefit_type = models.CharField(max_length=20, choices=Employee.BENEFIT_TYPE_CHOICES)
    provider = models.CharField(max_length=100, blank=True)
    coverage = models.CharField(max_length=200, blank=True)
    employer_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    employee_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_benefit_type_display()}"


class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=Employee.DOCUMENT_TYPE_CHOICES)
    filename = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    upload_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_document_type_display()}"


class EmployeeLeaveRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=Employee.LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveIntegerField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Employee.LEAVE_STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"


class EmployeePerformanceReview(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_reviews')
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='conducted_reviews')
    review_date = models.DateField()
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True)
    goals = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - Review {self.review_date} (Rating: {self.rating})"


class EmployeeDisciplinaryAction(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='disciplinary_actions')
    action_type = models.CharField(max_length=20, choices=Employee.DISCIPLINARY_TYPE_CHOICES)
    reason = models.TextField()
    issued_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='issued_disciplinary_actions')
    action_date = models.DateField()
    resolved = models.BooleanField(default=False)
    resolution_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_action_type_display()} ({self.action_date})"


class WorkDay(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='work_days')
    day = models.CharField(max_length=10, choices=Employee.WORK_DAY_CHOICES)
    
    class Meta:
        unique_together = ['employee', 'day']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_day_display()}"