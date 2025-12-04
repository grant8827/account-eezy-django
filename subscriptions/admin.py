from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Subscription, SubscriptionHistory, PaymentHistory, 
    PayPalPayment, PayPalWebhook
)


class SubscriptionHistoryInline(admin.TabularInline):
    model = SubscriptionHistory
    extra = 0
    fields = ('action', 'details', 'amount', 'created_at', 'created_by')
    readonly_fields = ('created_at',)


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    fields = ('amount', 'status', 'payment_method', 'payment_date', 'transaction_id')
    readonly_fields = ('payment_date',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'business_link',
        'plan_type_display',
        'status_display',
        'amount_display',
        'billing_cycle_display',
        'next_billing_display',
        'usage_display',
        'subscription_actions'
    ]
    
    list_filter = [
        'plan_type',
        'status',
        'billing_cycle',
        'payment_method',
        'auto_renew',
        'next_billing_date',
        'created_at'
    ]
    
    search_fields = [
        'business__business_name',
        'business__owner__email',
        'business__owner__first_name',
        'business__owner__last_name',
        'payment_processor_id'
    ]
    
    date_hierarchy = 'next_billing_date'
    
    ordering = ['-created_at']
    
    actions = [
        'activate_subscriptions',
        'suspend_subscriptions',
        'cancel_subscriptions',
        'update_usage_stats',
        'extend_trial'
    ]
    
    inlines = [SubscriptionHistoryInline, PaymentHistoryInline]
    
    fieldsets = (
        ('Subscription Details', {
            'fields': (
                'business',
                ('plan_type', 'status'),
                ('billing_cycle', 'amount', 'currency'),
                ('auto_renew', 'payment_method')
            ),
            'classes': ('wide',)
        }),
        
        ('Billing Dates', {
            'fields': (
                ('start_date', 'end_date'),
                ('next_billing_date', 'trial_end_date')
            ),
            'classes': ('wide',)
        }),
        
        ('Plan Limits', {
            'fields': (
                ('max_employees', 'max_businesses'),
                ('max_transactions_per_month', 'max_payroll_runs_per_month')
            ),
            'classes': ('wide',)
        }),
        
        ('Features', {
            'fields': (
                ('has_payroll', 'has_financial_reporting'),
                ('has_tax_calculations', 'has_multi_user_access'),
                ('has_api_access', 'has_advanced_analytics'),
                'has_priority_support'
            ),
            'classes': ('collapse',)
        }),
        
        ('Current Usage', {
            'fields': (
                ('current_employees', 'current_businesses'),
                ('transactions_this_month', 'payroll_runs_this_month'),
                'last_usage_reset'
            ),
            'classes': ('wide',)
        }),
        
        ('Payment Processing', {
            'fields': (
                'payment_processor_id',
            ),
            'classes': ('collapse',)
        }),
        
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_usage_reset']
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'business', 'business__owner'
        ).prefetch_related('history', 'payments')
    
    def business_link(self, obj):
        """Display business with link and owner info."""
        if obj.business:
            business_url = reverse('admin:businesses_business_change', args=[obj.business.id])
            owner_name = obj.business.owner.get_full_name() or obj.business.owner.email
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: none; font-weight: bold;">{}</a><br>'
                '<small style="color: #666;">Owner: {}</small>',
                business_url,
                obj.business.business_name,
                owner_name
            )
        return '-'
    business_link.short_description = 'Business'
    business_link.admin_order_field = 'business__business_name'
    
    def plan_type_display(self, obj):
        """Display plan type with colored badges."""
        colors = {
            'basic': '#9e9e9e',        # Grey
            'standard': '#2196f3',     # Blue
            'premium': '#ff9800',      # Orange
            'enterprise': '#9c27b0'    # Purple
        }
        color = colors.get(obj.plan_type, '#9e9e9e')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{}</span>',
            color,
            obj.get_plan_type_display()
        )
    plan_type_display.short_description = 'Plan'
    plan_type_display.admin_order_field = 'plan_type'
    
    def status_display(self, obj):
        """Display status with colored indicators."""
        colors = {
            'active': '#4caf50',      # Green
            'inactive': '#9e9e9e',    # Grey
            'cancelled': '#f44336',   # Red
            'suspended': '#ff9800',   # Orange
            'expired': '#795548'      # Brown
        }
        color = colors.get(obj.status, '#9e9e9e')
        
        icon = '✓' if obj.status == 'active' else '⚠' if obj.status in ['suspended', 'expired'] else '✗'
        
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span> {}',
            color,
            icon,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def amount_display(self, obj):
        """Display billing amount with cycle."""
        return format_html(
            '<span style="font-weight: bold; font-size: 14px;">{} {:,.2f}</span><br>'
            '<small style="color: #666;">per {}</small>',
            obj.currency,
            obj.amount,
            obj.billing_cycle
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def billing_cycle_display(self, obj):
        """Display billing cycle with auto-renew status."""
        auto_renew_text = "Auto-renew" if obj.auto_renew else "Manual"
        auto_renew_color = "#4caf50" if obj.auto_renew else "#ff9800"
        
        return format_html(
            '<span style="font-weight: bold;">{}</span><br>'
            '<small style="color: {};">{}</small>',
            obj.get_billing_cycle_display(),
            auto_renew_color,
            auto_renew_text
        )
    billing_cycle_display.short_description = 'Billing'
    billing_cycle_display.admin_order_field = 'billing_cycle'
    
    def next_billing_display(self, obj):
        """Display next billing date with countdown."""
        if obj.next_billing_date:
            days_until = obj.days_until_renewal()
            
            if days_until > 0:
                countdown_text = f"In {days_until}d"
                countdown_color = "#4caf50" if days_until > 7 else "#ff9800"
            elif days_until == 0:
                countdown_text = "Today"
                countdown_color = "#f44336"
            else:
                countdown_text = f"{abs(days_until)}d overdue"
                countdown_color = "#f44336"
            
            return format_html(
                '<span>{}</span><br>'
                '<small style="color: {}; font-weight: bold;">{}</small>',
                obj.next_billing_date.strftime('%b %d, %Y'),
                countdown_color,
                countdown_text
            )
        return '-'
    next_billing_display.short_description = 'Next Billing'
    next_billing_display.admin_order_field = 'next_billing_date'
    
    def usage_display(self, obj):
        """Display current usage vs limits."""
        employee_percentage = (obj.current_employees / obj.max_employees * 100) if obj.max_employees > 0 else 0
        transaction_percentage = (obj.transactions_this_month / obj.max_transactions_per_month * 100) if obj.max_transactions_per_month > 0 else 0
        
        employee_color = "#f44336" if employee_percentage > 80 else "#ff9800" if employee_percentage > 60 else "#4caf50"
        transaction_color = "#f44336" if transaction_percentage > 80 else "#ff9800" if transaction_percentage > 60 else "#4caf50"
        
        return format_html(
            '<div style="font-size: 11px;">'
            '<span style="color: {};">👥 {}/{} employees</span><br>'
            '<span style="color: {};">💼 {}/{} transactions</span>'
            '</div>',
            employee_color,
            obj.current_employees,
            obj.max_employees,
            transaction_color,
            obj.transactions_this_month,
            obj.max_transactions_per_month
        )
    usage_display.short_description = 'Usage'
    
    def subscription_actions(self, obj):
        """Display quick action buttons."""
        actions = []
        
        # Status-based actions
        if obj.status == 'inactive':
            actions.append(
                '<a href="#" onclick="activateSubscription({})" '
                'style="background: #4caf50; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Activate</a>'.format(obj.id)
            )
        elif obj.status == 'active':
            actions.append(
                '<a href="#" onclick="suspendSubscription({})" '
                'style="background: #ff9800; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Suspend</a>'.format(obj.id)
            )
        
        # Plan upgrade/downgrade
        if obj.plan_type != 'enterprise':
            actions.append(
                '<a href="#" onclick="upgradeSubscription({})" '
                'style="background: #9c27b0; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Upgrade</a>'.format(obj.id)
            )
        
        # Trial extension
        if obj.is_trial():
            actions.append(
                '<a href="#" onclick="extendTrial({})" '
                'style="background: #2196f3; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Extend Trial</a>'.format(obj.id)
            )
        
        return format_html(' '.join(actions))
    subscription_actions.short_description = 'Actions'
    
    # Admin Actions
    def activate_subscriptions(self, request, queryset):
        """Activate selected subscriptions."""
        count = 0
        for subscription in queryset.exclude(status='active'):
            subscription.reactivate()
            count += 1
        self.message_user(request, f'{count} subscriptions activated successfully.')
    activate_subscriptions.short_description = 'Activate selected subscriptions'
    
    def suspend_subscriptions(self, request, queryset):
        """Suspend selected subscriptions."""
        count = 0
        for subscription in queryset.filter(status='active'):
            subscription.suspend('Suspended via admin action')
            count += 1
        self.message_user(request, f'{count} subscriptions suspended successfully.')
    suspend_subscriptions.short_description = 'Suspend selected subscriptions'
    
    def cancel_subscriptions(self, request, queryset):
        """Cancel selected subscriptions."""
        count = 0
        for subscription in queryset.exclude(status='cancelled'):
            subscription.cancel('Cancelled via admin action')
            count += 1
        self.message_user(request, f'{count} subscriptions cancelled successfully.')
    cancel_subscriptions.short_description = 'Cancel selected subscriptions'
    
    def update_usage_stats(self, request, queryset):
        """Update usage statistics for selected subscriptions."""
        count = 0
        for subscription in queryset:
            subscription.update_usage()
            count += 1
        self.message_user(request, f'Usage statistics updated for {count} subscriptions.')
    update_usage_stats.short_description = 'Update usage statistics'
    
    def extend_trial(self, request, queryset):
        """Extend trial period by 30 days."""
        count = 0
        for subscription in queryset.filter(status='active'):
            if subscription.trial_end_date:
                subscription.trial_end_date += timedelta(days=30)
                subscription.save()
                count += 1
        self.message_user(request, f'Trial extended for {count} subscriptions.')
    extend_trial.short_description = 'Extend trial by 30 days'


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'subscription_link',
        'amount_display',
        'status_display',
        'payment_method',
        'billing_period_display',
        'payment_date_display'
    ]
    
    list_filter = [
        'status',
        'payment_method',
        'currency',
        'payment_date',
        'created_at'
    ]
    
    search_fields = [
        'subscription__business__business_name',
        'transaction_id',
        'failure_reason'
    ]
    
    date_hierarchy = 'payment_date'
    
    ordering = ['-created_at']
    
    def subscription_link(self, obj):
        """Display subscription with link."""
        if obj.subscription:
            subscription_url = reverse('admin:subscriptions_subscription_change', args=[obj.subscription.id])
            return format_html(
                '<a href="{}" style="color: #0066cc;">{}</a>',
                subscription_url,
                obj.subscription.business.business_name
            )
        return '-'
    subscription_link.short_description = 'Subscription'
    
    def amount_display(self, obj):
        """Display payment amount with currency."""
        return format_html(
            '<span style="font-weight: bold;">{} {:,.2f}</span>',
            obj.currency,
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def status_display(self, obj):
        """Display payment status with colored indicators."""
        colors = {
            'pending': '#ff9800',      # Orange
            'processing': '#2196f3',   # Blue
            'succeeded': '#4caf50',    # Green
            'failed': '#f44336',       # Red
            'cancelled': '#9e9e9e',    # Grey
            'refunded': '#795548'      # Brown
        }
        color = colors.get(obj.status, '#9e9e9e')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def billing_period_display(self, obj):
        """Display billing period."""
        return format_html(
            '{} to {}',
            obj.billing_period_start.strftime('%b %d'),
            obj.billing_period_end.strftime('%b %d, %Y')
        )
    billing_period_display.short_description = 'Billing Period'
    
    def payment_date_display(self, obj):
        """Display payment date."""
        if obj.payment_date:
            return obj.payment_date.strftime('%b %d, %Y at %I:%M %p')
        return '-'
    payment_date_display.short_description = 'Payment Date'
    payment_date_display.admin_order_field = 'payment_date'


@admin.register(PayPalPayment)
class PayPalPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'paypal_order_id',
        'user_link',
        'amount_display',
        'plan_display',
        'status_display',
        'created_at_display'
    ]
    
    list_filter = [
        'status',
        'plan_type',
        'billing_cycle',
        'currency',
        'created_at'
    ]
    
    search_fields = [
        'paypal_order_id',
        'paypal_payment_id',
        'user__email',
        'user__first_name',
        'user__last_name',
        'payer_email'
    ]
    
    date_hierarchy = 'created_at'
    
    ordering = ['-created_at']
    
    readonly_fields = [
        'paypal_order_id', 'paypal_payment_id', 'created_at', 
        'approved_at', 'captured_at', 'updated_at'
    ]
    
    def user_link(self, obj):
        """Display user with link."""
        if obj.user:
            user_url = reverse('admin:authentication_user_change', args=[obj.user.id])
            return format_html(
                '<a href="{}" style="color: #0066cc;">{}</a>',
                user_url,
                obj.user.get_full_name() or obj.user.email
            )
        return '-'
    user_link.short_description = 'User'
    
    def amount_display(self, obj):
        """Display payment amount."""
        return format_html(
            '<span style="font-weight: bold;">{} {:,.2f}</span>',
            obj.currency,
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def plan_display(self, obj):
        """Display plan information."""
        return format_html(
            '<span style="font-weight: bold;">{}</span><br>'
            '<small style="color: #666;">{} - {}</small>',
            obj.plan_name,
            obj.plan_type.title(),
            obj.billing_cycle
        )
    plan_display.short_description = 'Plan'
    
    def status_display(self, obj):
        """Display PayPal payment status."""
        colors = {
            'created': '#9e9e9e',      # Grey
            'approved': '#2196f3',     # Blue
            'captured': '#4caf50',     # Green
            'completed': '#4caf50',    # Green
            'cancelled': '#f44336',    # Red
            'failed': '#f44336',       # Red
            'refunded': '#795548'      # Brown
        }
        color = colors.get(obj.status, '#9e9e9e')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 8px; font-size: 10px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def created_at_display(self, obj):
        """Display creation date."""
        return obj.created_at.strftime('%b %d, %Y at %I:%M %p')
    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'


# Register remaining models
admin.site.register(SubscriptionHistory)
admin.site.register(PayPalWebhook)