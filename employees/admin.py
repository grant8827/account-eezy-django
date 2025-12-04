from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from datetime import datetime, date
from .models import (
    Employee, 
    EmployeeAllowance, 
    EmployeeBenefit, 
    EmployeeDocument,
    EmployeeLeaveRequest,
    EmployeePerformanceReview,
    EmployeeDisciplinaryAction,
    WorkDay
)


class EmployeeAllowanceInline(admin.TabularInline):
    model = EmployeeAllowance
    extra = 0
    fields = ('allowance_type', 'amount', 'taxable', 'description', 'is_active')


class EmployeeBenefitInline(admin.TabularInline):
    model = EmployeeBenefit
    extra = 0
    fields = ('benefit_type', 'provider', 'employer_contribution', 'employee_contribution', 'start_date', 'is_active')


class WorkDayInline(admin.TabularInline):
    model = WorkDay
    extra = 0
    fields = ('day',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_name_display',
        'employee_id',
        'business_link',
        'position',
        'employment_status_display',
        'salary_display',
        'start_date_display',
        'leave_balance_display',
        'employee_actions'
    ]
    
    list_filter = [
        'business',
        'employment_type',
        'department',
        'is_active',
        'start_date',
        'gender',
        'marital_status',
        'overtime_eligible',
        'salary_frequency'
    ]
    
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'employee_id',
        'trn',
        'nis',
        'position',
        'department'
    ]
    
    date_hierarchy = 'start_date'
    
    ordering = ['-start_date']
    
    actions = [
        'activate_employees',
        'deactivate_employees',
        'grant_vacation_days',
        'export_employee_data'
    ]
    
    inlines = [EmployeeAllowanceInline, EmployeeBenefitInline, WorkDayInline]
    
    fieldsets = (
        ('Employee Identity', {
            'fields': (
                ('user', 'business'),
                ('employee_id', 'position', 'department'),
                'start_date',
                'employment_type'
            ),
            'classes': ('wide',)
        }),
        
        ('Personal Information', {
            'fields': (
                'date_of_birth',
                ('gender', 'marital_status'),
                'nationality'
            ),
            'classes': ('wide',)
        }),
        
        ('Emergency Contact', {
            'fields': (
                ('emergency_contact_name', 'emergency_contact_relationship'),
                ('emergency_contact_phone',),
                'emergency_contact_address'
            ),
            'classes': ('collapse',)
        }),
        
        ('Work Schedule', {
            'fields': (
                'hours_per_week',
                ('start_time', 'end_time'),
                ('probation_months', 'probation_end_date'),
                'supervisor'
            ),
            'classes': ('wide',)
        }),
        
        ('Compensation', {
            'fields': (
                ('base_salary_amount', 'salary_currency'),
                'salary_frequency',
                ('overtime_eligible', 'overtime_rate')
            ),
            'classes': ('wide',)
        }),
        
        ('Tax Information', {
            'fields': (
                ('trn', 'nis'),
                ('tax_status', 'dependents'),
                ('education_credit', 'pension_contribution_rate')
            ),
            'classes': ('wide',)
        }),
        
        ('Banking Details', {
            'fields': (
                ('bank_name', 'account_type'),
                ('account_number', 'routing_number')
            ),
            'classes': ('collapse',)
        }),
        
        ('Leave Entitlements', {
            'fields': (
                ('vacation_days_entitlement', 'vacation_days_used'),
                ('sick_days_entitlement', 'sick_days_used')
            ),
            'classes': ('wide',)
        }),
        
        ('Employment Status', {
            'fields': (
                'is_active',
                ('end_date', 'termination_date'),
                ('termination_type', 'termination_reason'),
                ('notice_period', 'final_pay_date'),
                'exit_interview_completed'
            ),
            'classes': ('wide',)
        }),
        
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at', 'probation_end_date']
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'user', 'business', 'supervisor'
        ).prefetch_related('allowances', 'benefits')
    
    def employee_name_display(self, obj):
        """Display employee name with link to user admin."""
        if obj.user:
            user_url = reverse('admin:authentication_user_change', args=[obj.user.id])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: none; font-weight: bold;">{}</a>',
                user_url,
                obj.user.get_full_name() or obj.user.email
            )
        return '-'
    employee_name_display.short_description = 'Employee Name'
    employee_name_display.admin_order_field = 'user__first_name'
    
    def business_link(self, obj):
        """Display business with link to business admin."""
        if obj.business:
            business_url = reverse('admin:businesses_business_change', args=[obj.business.id])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: none;">{}</a>',
                business_url,
                obj.business.business_name
            )
        return '-'
    business_link.short_description = 'Business'
    business_link.admin_order_field = 'business__business_name'
    
    def employment_status_display(self, obj):
        """Display employment status with colored indicators."""
        status = obj.employment_status
        colors = {
            'active': '#4caf50',      # Green
            'probation': '#ff9800',   # Orange
            'terminated': '#f44336'   # Red
        }
        color = colors.get(status, '#9e9e9e')
        
        status_text = {
            'active': 'Active',
            'probation': 'Probation',
            'terminated': 'Terminated'
        }.get(status, 'Unknown')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            status_text
        )
    employment_status_display.short_description = 'Status'
    employment_status_display.admin_order_field = 'is_active'
    
    def salary_display(self, obj):
        """Display salary information."""
        if obj.base_salary_amount:
            return format_html(
                '<span style="font-weight: bold;">{} {}</span><br>'
                '<small style="color: #666;">{}</small>',
                obj.salary_currency,
                f"{obj.base_salary_amount:,.2f}",
                obj.get_salary_frequency_display()
            )
        return '-'
    salary_display.short_description = 'Salary'
    salary_display.admin_order_field = 'base_salary_amount'
    
    def start_date_display(self, obj):
        """Display start date with tenure calculation."""
        if obj.start_date:
            tenure_days = (date.today() - obj.start_date).days
            tenure_years = tenure_days // 365
            tenure_months = (tenure_days % 365) // 30
            
            tenure_text = []
            if tenure_years > 0:
                tenure_text.append(f"{tenure_years}y")
            if tenure_months > 0:
                tenure_text.append(f"{tenure_months}m")
            
            return format_html(
                '<span>{}</span><br>'
                '<small style="color: #666;">{}</small>',
                obj.start_date.strftime('%b %d, %Y'),
                ' '.join(tenure_text) if tenure_text else f"{tenure_days}d"
            )
        return '-'
    start_date_display.short_description = 'Start Date'
    start_date_display.admin_order_field = 'start_date'
    
    def leave_balance_display(self, obj):
        """Display leave balances."""
        return format_html(
            '<span style="color: #2196f3;">🏖️ {}/{}</span><br>'
            '<span style="color: #ff5722;">🤒 {}/{}</span>',
            obj.vacation_days_remaining,
            obj.vacation_days_entitlement,
            obj.sick_days_remaining,
            obj.sick_days_entitlement
        )
    leave_balance_display.short_description = 'Leave Balance'
    
    def employee_actions(self, obj):
        """Display quick action buttons."""
        actions = []
        
        # Status actions
        if obj.is_active:
            actions.append(
                '<a href="#" onclick="deactivateEmployee({})" '
                'style="background: #f44336; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Deactivate</a>'.format(obj.id)
            )
        else:
            actions.append(
                '<a href="#" onclick="activateEmployee({})" '
                'style="background: #4caf50; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Activate</a>'.format(obj.id)
            )
        
        # Leave actions
        if obj.vacation_days_remaining < 5:
            actions.append(
                '<a href="#" onclick="grantLeave({})" '
                'style="background: #2196f3; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Grant Leave</a>'.format(obj.id)
            )
        
        return format_html(' '.join(actions))
    employee_actions.short_description = 'Actions'
    
    # Admin Actions
    def activate_employees(self, request, queryset):
        """Activate selected employees."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} employees activated successfully.')
    activate_employees.short_description = 'Activate selected employees'
    
    def deactivate_employees(self, request, queryset):
        """Deactivate selected employees."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} employees deactivated successfully.')
    deactivate_employees.short_description = 'Deactivate selected employees'
    
    def grant_vacation_days(self, request, queryset):
        """Grant 5 additional vacation days."""
        count = 0
        for employee in queryset:
            employee.vacation_days_entitlement += 5
            employee.save()
            count += 1
        self.message_user(request, f'Granted 5 vacation days to {count} employees.')
    grant_vacation_days.short_description = 'Grant 5 vacation days'


@admin.register(EmployeeLeaveRequest)
class EmployeeLeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        'employee_name',
        'leave_type_display',
        'date_range',
        'days',
        'status_display',
        'request_date_display'
    ]
    
    list_filter = [
        'leave_type',
        'status',
        'start_date',
        'employee__business'
    ]
    
    search_fields = [
        'employee__user__first_name',
        'employee__user__last_name',
        'employee__employee_id'
    ]
    
    actions = ['approve_leave', 'deny_leave']
    
    def employee_name(self, obj):
        return obj.employee.user.get_full_name()
    employee_name.short_description = 'Employee'
    employee_name.admin_order_field = 'employee__user__first_name'
    
    def leave_type_display(self, obj):
        colors = {
            'vacation': '#4caf50',
            'sick': '#ff5722',
            'personal': '#2196f3',
            'maternity': '#e91e63',
            'paternity': '#9c27b0'
        }
        color = colors.get(obj.leave_type, '#9e9e9e')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 8px; font-size: 10px;">{}</span>',
            color,
            obj.get_leave_type_display()
        )
    leave_type_display.short_description = 'Type'
    
    def date_range(self, obj):
        return f"{obj.start_date} to {obj.end_date}"
    date_range.short_description = 'Date Range'
    
    def status_display(self, obj):
        colors = {
            'pending': '#ff9800',
            'approved': '#4caf50',
            'denied': '#f44336'
        }
        color = colors.get(obj.status, '#9e9e9e')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def request_date_display(self, obj):
        return obj.request_date.strftime('%b %d, %Y')
    request_date_display.short_description = 'Requested'
    request_date_display.admin_order_field = 'request_date'
    
    def approve_leave(self, request, queryset):
        updated = queryset.update(status='approved', approved_date=datetime.now())
        self.message_user(request, f'{updated} leave requests approved.')
    approve_leave.short_description = 'Approve selected leave requests'
    
    def deny_leave(self, request, queryset):
        updated = queryset.update(status='denied')
        self.message_user(request, f'{updated} leave requests denied.')
    deny_leave.short_description = 'Deny selected leave requests'


@admin.register(EmployeePerformanceReview)
class EmployeePerformanceReviewAdmin(admin.ModelAdmin):
    list_display = [
        'employee_name',
        'reviewer_name', 
        'review_date',
        'rating_display',
        'review_actions'
    ]
    
    list_filter = [
        'rating',
        'review_date',
        'employee__business'
    ]
    
    search_fields = [
        'employee__user__first_name',
        'employee__user__last_name',
        'reviewer__user__first_name',
        'reviewer__user__last_name'
    ]
    
    def employee_name(self, obj):
        return obj.employee.user.get_full_name()
    employee_name.short_description = 'Employee'
    
    def reviewer_name(self, obj):
        return obj.reviewer.user.get_full_name()
    reviewer_name.short_description = 'Reviewer'
    
    def rating_display(self, obj):
        stars = '⭐' * obj.rating + '☆' * (5 - obj.rating)
        color = '#4caf50' if obj.rating >= 4 else '#ff9800' if obj.rating >= 3 else '#f44336'
        
        return format_html(
            '<span style="color: {};">{}</span> ({}/5)',
            color,
            stars,
            obj.rating
        )
    rating_display.short_description = 'Rating'
    
    def review_actions(self, obj):
        return format_html(
            '<a href="#" style="color: #0066cc; text-decoration: none; font-size: 11px;">View Details</a>'
        )
    review_actions.short_description = 'Actions'


# Register other models with basic admin
admin.site.register(EmployeeAllowance)
admin.site.register(EmployeeBenefit)
admin.site.register(EmployeeDocument)
admin.site.register(EmployeeDisciplinaryAction)