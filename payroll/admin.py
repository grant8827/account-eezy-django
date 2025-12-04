from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Payroll, PayrollAllowance, PayrollDeduction, PayrollApproval


class PayrollAllowanceInline(admin.TabularInline):
    model = PayrollAllowance
    extra = 0
    fields = ('allowance_type', 'amount', 'taxable', 'description')


class PayrollDeductionInline(admin.TabularInline):
    model = PayrollDeduction
    extra = 0
    fields = ('deduction_type', 'amount', 'description', 'recurring')


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = [
        'payroll_number',
        'employee_link',
        'business_link',
        'pay_period_display',
        'gross_earnings_display',
        'net_pay_display',
        'status_display',
        'pay_date_display',
        'payroll_actions'
    ]
    
    list_filter = [
        'status',
        'pay_period_type',
        'is_paid',
        'payment_method',
        'business',
        'pay_date',
        'created_at'
    ]
    
    search_fields = [
        'payroll_number',
        'employee__user__first_name',
        'employee__user__last_name',
        'employee__employee_id',
        'business__business_name'
    ]
    
    date_hierarchy = 'pay_date'
    
    ordering = ['-pay_date', '-created_at']
    
    actions = [
        'approve_payrolls',
        'mark_as_paid',
        'recalculate_payrolls',
        'export_payroll_summary'
    ]
    
    inlines = [PayrollAllowanceInline, PayrollDeductionInline]
    
    fieldsets = (
        ('Payroll Information', {
            'fields': (
                ('payroll_number', 'business'),
                ('employee', 'pay_period_type'),
                ('pay_period_start', 'pay_period_end'),
                'pay_date'
            ),
            'classes': ('wide',)
        }),
        
        ('Earnings', {
            'fields': (
                ('basic_salary', 'gross_earnings'),
                ('overtime_hours', 'overtime_rate', 'overtime_amount'),
                ('bonus', 'commission', 'back_pay')
            ),
            'classes': ('wide',)
        }),
        
        ('Work Hours', {
            'fields': (
                'regular_hours',
                ('holiday_hours', 'sick_hours'),
                ('vacation_hours', 'unpaid_leave_hours')
            ),
            'classes': ('collapse',)
        }),
        
        ('Jamaica Tax Deductions', {
            'fields': (
                ('paye_taxable_income', 'paye_rate', 'paye_amount'),
                ('nis_rate', 'nis_contribution'),
                ('education_tax_rate', 'education_tax_amount'),
                ('heart_trust_rate', 'heart_trust_amount')
            ),
            'classes': ('wide',)
        }),
        
        ('Pension Contributions', {
            'fields': (
                ('pension_employee_rate', 'pension_employee_contribution'),
                ('pension_employer_rate', 'pension_employer_contribution')
            ),
            'classes': ('collapse',)
        }),
        
        ('Tax Thresholds', {
            'fields': (
                ('personal_allowance', 'paye_threshold'),
                'education_tax_threshold'
            ),
            'classes': ('collapse',)
        }),
        
        ('Totals', {
            'fields': (
                ('total_deductions', 'net_pay')
            ),
            'classes': ('wide',)
        }),
        
        ('Payment Details', {
            'fields': (
                ('payment_method', 'is_paid'),
                ('bank_name', 'account_number'),
                ('routing_number', 'check_number'),
                'paid_date'
            ),
            'classes': ('collapse',)
        }),
        
        ('Status & Processing', {
            'fields': (
                ('status', 'created_by'),
                ('processed_by', 'processed_date'),
                'notes'
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
    
    readonly_fields = [
        'created_at', 'updated_at', 'gross_earnings', 'total_deductions', 
        'net_pay', 'overtime_amount', 'paye_amount', 'nis_contribution',
        'education_tax_amount', 'heart_trust_amount', 'pension_employee_contribution',
        'pension_employer_contribution'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'business', 'employee__user', 'created_by', 'processed_by'
        ).prefetch_related('allowances', 'other_deductions')
    
    def employee_link(self, obj):
        """Display employee with link to employee admin."""
        if obj.employee:
            employee_url = reverse('admin:employees_employee_change', args=[obj.employee.id])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: none; font-weight: bold;">{}</a><br>'
                '<small style="color: #666;">{}</small>',
                employee_url,
                obj.employee.user.get_full_name() or obj.employee.user.email,
                obj.employee.employee_id
            )
        return '-'
    employee_link.short_description = 'Employee'
    employee_link.admin_order_field = 'employee__user__first_name'
    
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
    
    def pay_period_display(self, obj):
        """Display pay period information."""
        return format_html(
            '<span style="font-weight: bold;">{}</span><br>'
            '<small style="color: #666;">{} to {}</small>',
            obj.get_pay_period_type_display(),
            obj.pay_period_start.strftime('%b %d'),
            obj.pay_period_end.strftime('%b %d, %Y')
        )
    pay_period_display.short_description = 'Pay Period'
    pay_period_display.admin_order_field = 'pay_period_start'
    
    def gross_earnings_display(self, obj):
        """Display gross earnings breakdown."""
        breakdown = []
        if obj.basic_salary > 0:
            breakdown.append(f"Base: JMD {obj.basic_salary:,.2f}")
        if obj.overtime_amount > 0:
            breakdown.append(f"OT: JMD {obj.overtime_amount:,.2f}")
        if obj.bonus > 0:
            breakdown.append(f"Bonus: JMD {obj.bonus:,.2f}")
        
        return format_html(
            '<span style="font-weight: bold; font-size: 14px; color: #4caf50;">JMD {:,.2f}</span><br>'
            '<small style="color: #666;">{}</small>',
            obj.gross_earnings,
            ' | '.join(breakdown[:2]) if breakdown else 'Base salary only'
        )
    gross_earnings_display.short_description = 'Gross Earnings'
    gross_earnings_display.admin_order_field = 'gross_earnings'
    
    def net_pay_display(self, obj):
        """Display net pay with deduction summary."""
        deduction_percentage = (obj.total_deductions / obj.gross_earnings * 100) if obj.gross_earnings > 0 else 0
        
        return format_html(
            '<span style="font-weight: bold; font-size: 14px; color: #2196f3;">JMD {:,.2f}</span><br>'
            '<small style="color: #666;">Deductions: {:,.2f} ({:.1f}%)</small>',
            obj.net_pay,
            obj.total_deductions,
            deduction_percentage
        )
    net_pay_display.short_description = 'Net Pay'
    net_pay_display.admin_order_field = 'net_pay'
    
    def status_display(self, obj):
        """Display status with colored badges."""
        colors = {
            'draft': '#9e9e9e',       # Grey
            'calculated': '#ff9800',  # Orange
            'approved': '#2196f3',    # Blue
            'paid': '#4caf50',        # Green
            'cancelled': '#f44336'    # Red
        }
        color = colors.get(obj.status, '#9e9e9e')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def pay_date_display(self, obj):
        """Display pay date with days until/since payment."""
        if obj.pay_date:
            days_diff = (obj.pay_date - timezone.now().date()).days
            
            if days_diff > 0:
                timing_text = f"In {days_diff}d"
                timing_color = "#ff9800"
            elif days_diff == 0:
                timing_text = "Today"
                timing_color = "#4caf50"
            else:
                timing_text = f"{abs(days_diff)}d ago"
                timing_color = "#666"
            
            return format_html(
                '<span>{}</span><br>'
                '<small style="color: {};">{}</small>',
                obj.pay_date.strftime('%b %d, %Y'),
                timing_color,
                timing_text
            )
        return '-'
    pay_date_display.short_description = 'Pay Date'
    pay_date_display.admin_order_field = 'pay_date'
    
    def payroll_actions(self, obj):
        """Display quick action buttons."""
        actions = []
        
        # Status-based actions
        if obj.status == 'draft':
            actions.append(
                '<a href="#" onclick="calculatePayroll({})" '
                'style="background: #ff9800; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Calculate</a>'.format(obj.id)
            )
        elif obj.status == 'calculated':
            actions.append(
                '<a href="#" onclick="approvePayroll({})" '
                'style="background: #2196f3; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Approve</a>'.format(obj.id)
            )
        elif obj.status == 'approved' and not obj.is_paid:
            actions.append(
                '<a href="#" onclick="markAsPaid({})" '
                'style="background: #4caf50; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Pay</a>'.format(obj.id)
            )
        
        # Print payslip action
        if obj.status in ['approved', 'paid']:
            actions.append(
                '<a href="#" onclick="printPayslip({})" '
                'style="background: #9c27b0; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Print</a>'.format(obj.id)
            )
        
        return format_html(' '.join(actions))
    payroll_actions.short_description = 'Actions'
    
    # Admin Actions
    def approve_payrolls(self, request, queryset):
        """Approve selected payrolls."""
        count = 0
        for payroll in queryset.filter(status='calculated'):
            payroll.approve(request.user, 'Bulk approval via admin')
            count += 1
        self.message_user(request, f'{count} payrolls approved successfully.')
    approve_payrolls.short_description = 'Approve selected payrolls'
    
    def mark_as_paid(self, request, queryset):
        """Mark selected payrolls as paid."""
        count = 0
        for payroll in queryset.filter(status='approved', is_paid=False):
            payroll.mark_as_paid(request.user)
            count += 1
        self.message_user(request, f'{count} payrolls marked as paid.')
    mark_as_paid.short_description = 'Mark as paid'
    
    def recalculate_payrolls(self, request, queryset):
        """Recalculate selected payrolls."""
        count = 0
        for payroll in queryset.filter(status__in=['draft', 'calculated']):
            payroll.calculate_totals()
            payroll.save()
            count += 1
        self.message_user(request, f'{count} payrolls recalculated successfully.')
    recalculate_payrolls.short_description = 'Recalculate selected payrolls'


@admin.register(PayrollApproval)
class PayrollApprovalAdmin(admin.ModelAdmin):
    list_display = [
        'payroll_link',
        'approver_link',
        'approved_date_display',
        'comments_preview'
    ]
    
    list_filter = [
        'approved_date',
        'payroll__business'
    ]
    
    search_fields = [
        'payroll__payroll_number',
        'approver__first_name',
        'approver__last_name',
        'comments'
    ]
    
    def payroll_link(self, obj):
        """Display payroll with link."""
        payroll_url = reverse('admin:payroll_payroll_change', args=[obj.payroll.id])
        return format_html(
            '<a href="{}" style="color: #0066cc;">{}</a>',
            payroll_url,
            obj.payroll.payroll_number
        )
    payroll_link.short_description = 'Payroll'
    
    def approver_link(self, obj):
        """Display approver with link."""
        approver_url = reverse('admin:authentication_user_change', args=[obj.approver.id])
        return format_html(
            '<a href="{}" style="color: #0066cc;">{}</a>',
            approver_url,
            obj.approver.get_full_name() or obj.approver.email
        )
    approver_link.short_description = 'Approver'
    
    def approved_date_display(self, obj):
        """Display approval date."""
        return obj.approved_date.strftime('%b %d, %Y at %I:%M %p')
    approved_date_display.short_description = 'Approved'
    approved_date_display.admin_order_field = 'approved_date'
    
    def comments_preview(self, obj):
        """Display preview of comments."""
        if obj.comments:
            return obj.comments[:50] + '...' if len(obj.comments) > 50 else obj.comments
        return '-'
    comments_preview.short_description = 'Comments'


# Register inline models
admin.site.register(PayrollAllowance)
admin.site.register(PayrollDeduction)