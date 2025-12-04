from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 
        'owner_link', 
        'subscription_status_display', 
        'subscription_plan',
        'employee_count_display',
        'payment_status_display',
        'is_active_display',
        'created_at_display',
        'business_actions'
    ]
    
    list_filter = [
        'subscription_status',
        'subscription_plan', 
        'payment_status',
        'business_type',
        'industry',
        'parish',
        'is_active',
        'created_at',
        'paye_registered',
        'gct_registered'
    ]
    
    search_fields = [
        'business_name',
        'owner__first_name',
        'owner__last_name', 
        'owner__email',
        'registration_number',
        'trn',
        'email',
        'phone'
    ]
    
    date_hierarchy = 'created_at'
    
    ordering = ['-created_at']
    
    actions = [
        'approve_businesses',
        'suspend_businesses', 
        'activate_businesses',
        'mark_payment_paid',
        'extend_trial',
        'upgrade_to_premium'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'business_name',
                'owner',
                'registration_number', 
                'trn',
                'nis',
                'business_type',
                'industry'
            ),
            'classes': ('wide',)
        }),
        
        ('Contact & Location', {
            'fields': (
                ('street', 'city'),
                ('parish', 'postal_code'),
                'country',
                ('phone', 'email'),
                'website'
            ),
            'classes': ('wide',)
        }),
        
        ('Subscription Management', {
            'fields': (
                ('subscription_status', 'subscription_plan'),
                ('subscription_start_date', 'subscription_end_date'),
                ('billing_amount', 'payment_method'),
                ('payment_status', 'last_billing_date', 'next_billing_date')
            ),
            'classes': ('wide',)
        }),
        
        ('Payroll Settings', {
            'fields': (
                ('pay_period', 'pay_day'),
                ('overtime_rate', 'public_holiday_rate')
            ),
            'classes': ('collapse',)
        }),
        
        ('Tax Registration', {
            'fields': (
                ('paye_registered', 'nis_registered'),
                ('education_tax_registered', 'heart_trust_registered'),
                ('gct_registered', 'tax_year')
            ),
            'classes': ('collapse',)
        }),
        
        ('Business Settings', {
            'fields': (
                ('fiscal_year_end', 'currency'),
                ('timezone', 'date_format'),
                ('email_notifications', 'sms_notifications')
            ),
            'classes': ('collapse',)
        }),
        
        ('Status & Activity', {
            'fields': (
                'is_active',
                'created_at',
                'updated_at'
            ),
            'classes': ('wide',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queryset with related data and annotations."""
        return super().get_queryset(request).select_related('owner').annotate(
            employee_count=Count('employees', filter=Q(employees__is_active=True))
        )
    
    def owner_link(self, obj):
        """Display owner with link to user admin."""
        if obj.owner:
            url = reverse('admin:authentication_user_change', args=[obj.owner.id])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: none;">{} {}</a>',
                url,
                obj.owner.first_name or '',
                obj.owner.last_name or obj.owner.email
            )
        return '-'
    owner_link.short_description = 'Owner'
    owner_link.admin_order_field = 'owner__email'
    
    def subscription_status_display(self, obj):
        """Display subscription status with colored badges."""
        colors = {
            'trial': '#ff9800',      # Orange
            'active': '#4caf50',     # Green
            'suspended': '#f44336',  # Red
            'cancelled': '#9e9e9e'   # Grey
        }
        color = colors.get(obj.subscription_status, '#9e9e9e')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_subscription_status_display()
        )
    subscription_status_display.short_description = 'Subscription'
    subscription_status_display.admin_order_field = 'subscription_status'
    
    def employee_count_display(self, obj):
        """Display employee count with link to employees."""
        count = getattr(obj, 'employee_count', 0)
        if count > 0:
            # Note: Assuming employees admin exists
            return format_html(
                '<span style="background-color: #e3f2fd; color: #1976d2; '
                'padding: 2px 6px; border-radius: 8px; font-size: 11px;">{} employees</span>',
                count
            )
        return format_html(
            '<span style="color: #9e9e9e; font-style: italic;">No employees</span>'
        )
    employee_count_display.short_description = 'Employees'
    employee_count_display.admin_order_field = 'employee_count'
    
    def payment_status_display(self, obj):
        """Display payment status with colored indicators."""
        colors = {
            'paid': '#4caf50',     # Green
            'pending': '#ff9800',  # Orange
            'failed': '#f44336'    # Red
        }
        color = colors.get(obj.payment_status, '#9e9e9e')
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.get_payment_status_display()
        )
    payment_status_display.short_description = 'Payment'
    payment_status_display.admin_order_field = 'payment_status'
    
    def is_active_display(self, obj):
        """Display active status with icons."""
        if obj.is_active:
            return format_html(
                '<span style="color: #4caf50; font-size: 16px;">✓</span>'
            )
        return format_html(
            '<span style="color: #f44336; font-size: 16px;">✗</span>'
        )
    is_active_display.short_description = 'Active'
    is_active_display.admin_order_field = 'is_active'
    
    def created_at_display(self, obj):
        """Display creation date in a readable format."""
        if obj.created_at:
            return obj.created_at.strftime('%b %d, %Y')
        return '-'
    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'
    
    def business_actions(self, obj):
        """Display quick action buttons."""
        actions = []
        
        # Subscription actions
        if obj.subscription_status == 'trial':
            actions.append(
                '<a href="#" onclick="extendTrial({})" '
                'style="background: #ff9800; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Extend Trial</a>'.format(obj.id)
            )
        
        if obj.subscription_plan != 'premium':
            actions.append(
                '<a href="#" onclick="upgradePremium({})" '
                'style="background: #9c27b0; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Upgrade</a>'.format(obj.id)
            )
        
        # Status actions
        if not obj.is_active:
            actions.append(
                '<a href="#" onclick="activateBusiness({})" '
                'style="background: #4caf50; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Activate</a>'.format(obj.id)
            )
        else:
            actions.append(
                '<a href="#" onclick="suspendBusiness({})" '
                'style="background: #f44336; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Suspend</a>'.format(obj.id)
            )
        
        return format_html(' '.join(actions))
    business_actions.short_description = 'Actions'
    
    # Admin Actions
    def approve_businesses(self, request, queryset):
        """Approve selected businesses."""
        updated = queryset.update(is_active=True, subscription_status='active')
        self.message_user(request, f'{updated} businesses approved successfully.')
    approve_businesses.short_description = 'Approve selected businesses'
    
    def suspend_businesses(self, request, queryset):
        """Suspend selected businesses."""
        updated = queryset.update(is_active=False, subscription_status='suspended')
        self.message_user(request, f'{updated} businesses suspended successfully.')
    suspend_businesses.short_description = 'Suspend selected businesses'
    
    def activate_businesses(self, request, queryset):
        """Activate selected businesses."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} businesses activated successfully.')
    activate_businesses.short_description = 'Activate selected businesses'
    
    def mark_payment_paid(self, request, queryset):
        """Mark payment as paid for selected businesses."""
        updated = queryset.update(
            payment_status='paid',
            last_billing_date=timezone.now()
        )
        self.message_user(request, f'Payment marked as paid for {updated} businesses.')
    mark_payment_paid.short_description = 'Mark payment as paid'
    
    def extend_trial(self, request, queryset):
        """Extend trial period by 30 days."""
        count = 0
        for business in queryset.filter(subscription_status='trial'):
            if business.subscription_end_date:
                business.subscription_end_date += timedelta(days=30)
            else:
                business.subscription_end_date = timezone.now() + timedelta(days=30)
            business.save()
            count += 1
        self.message_user(request, f'Trial extended for {count} businesses.')
    extend_trial.short_description = 'Extend trial by 30 days'
    
    def upgrade_to_premium(self, request, queryset):
        """Upgrade selected businesses to premium."""
        updated = queryset.update(
            subscription_plan='premium',
            subscription_status='active'
        )
        self.message_user(request, f'{updated} businesses upgraded to premium.')
    upgrade_to_premium.short_description = 'Upgrade to Premium plan'
    
    class Media:
        js = ('admin/js/business_actions.js',)
        css = {
            'all': ('admin/css/business_admin.css',)
        }


# Add custom CSS and JS for enhanced admin interface
admin.site.site_header = "AccountEezy Admin"
admin.site.site_title = "AccountEezy Admin Portal"
admin.site.index_title = "Business Management Dashboard"