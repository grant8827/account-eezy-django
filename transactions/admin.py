from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Transaction, TransactionAttachment


class TransactionAttachmentInline(admin.TabularInline):
    model = TransactionAttachment
    extra = 0
    fields = ('original_name', 'file_size', 'mime_type', 'upload_date')
    readonly_fields = ('upload_date',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_number',
        'business_link',
        'transaction_type_display',
        'amount_display',
        'transaction_date_display',
        'status_display',
        'reconciled_display',
        'created_by_link',
        'transaction_actions'
    ]
    
    list_filter = [
        'transaction_type',
        'status',
        'reconciled',
        'is_taxable',
        'currency',
        'payment_method',
        'transaction_date',
        'created_at',
        'business'
    ]
    
    search_fields = [
        'transaction_number',
        'description',
        'category',
        'vendor_name',
        'customer_name',
        'reference',
        'business__business_name'
    ]
    
    date_hierarchy = 'transaction_date'
    
    ordering = ['-transaction_date', '-created_at']
    
    actions = [
        'mark_as_reconciled',
        'mark_as_completed',
        'approve_transactions',
        'export_transactions'
    ]
    
    inlines = [TransactionAttachmentInline]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                ('transaction_number', 'business'),
                ('transaction_type', 'category'),
                'description',
                'transaction_date'
            ),
            'classes': ('wide',)
        }),
        
        ('Financial Information', {
            'fields': (
                ('amount', 'currency'),
                ('exchange_rate', 'payment_method'),
                'reference'
            ),
            'classes': ('wide',)
        }),
        
        ('Tax Information', {
            'fields': (
                'is_taxable',
                ('gct_rate', 'gct_amount'),
                ('withholding_tax_rate', 'withholding_tax_amount')
            ),
            'classes': ('collapse',)
        }),
        
        ('Vendor Information', {
            'fields': (
                ('vendor_name', 'vendor_trn'),
                ('vendor_phone', 'vendor_email'),
                'vendor_address'
            ),
            'classes': ('collapse',)
        }),
        
        ('Customer Information', {
            'fields': (
                ('customer_name', 'customer_trn'),
                ('customer_phone', 'customer_email'),
                'customer_address'
            ),
            'classes': ('collapse',)
        }),
        
        ('Status & Approval', {
            'fields': (
                ('status', 'reconciled'),
                ('created_by', 'approved_by'),
                ('approved_date', 'reconciled_date', 'reconciled_by')
            ),
            'classes': ('wide',)
        }),
        
        ('Additional Information', {
            'fields': (
                'notes',
                'tags'
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
    
    readonly_fields = ['created_at', 'updated_at', 'gct_amount', 'withholding_tax_amount']
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'business', 'created_by', 'approved_by', 'reconciled_by'
        ).prefetch_related('attachments')
    
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
    
    def transaction_type_display(self, obj):
        """Display transaction type with colored badges."""
        colors = {
            'income': '#4caf50',         # Green
            'expense': '#f44336',        # Red
            'asset_purchase': '#2196f3', # Blue
            'asset_sale': '#ff9800',     # Orange
            'liability': '#9c27b0',      # Purple
            'equity': '#607d8b',         # Blue Grey
            'transfer': '#795548',       # Brown
            'adjustment': '#9e9e9e'      # Grey
        }
        color = colors.get(obj.transaction_type, '#9e9e9e')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_transaction_type_display()
        )
    transaction_type_display.short_description = 'Type'
    transaction_type_display.admin_order_field = 'transaction_type'
    
    def amount_display(self, obj):
        """Display amount with currency and tax information."""
        total = obj.total_amount
        tax_info = []
        
        if obj.gct_amount > 0:
            tax_info.append(f"GCT: {obj.currency} {obj.gct_amount:,.2f}")
        if obj.withholding_tax_amount > 0:
            tax_info.append(f"WHT: {obj.currency} {obj.withholding_tax_amount:,.2f}")
        
        return format_html(
            '<span style="font-weight: bold; font-size: 14px;">{} {:,.2f}</span><br>'
            '<small style="color: #666;">{}</small>',
            obj.currency,
            total,
            ' | '.join(tax_info) if tax_info else f"Base: {obj.currency} {obj.amount:,.2f}"
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def transaction_date_display(self, obj):
        """Display transaction date with days ago."""
        if obj.transaction_date:
            days_ago = (timezone.now().date() - obj.transaction_date).days
            return format_html(
                '<span>{}</span><br>'
                '<small style="color: #666;">{}</small>',
                obj.transaction_date.strftime('%b %d, %Y'),
                f"{days_ago}d ago" if days_ago > 0 else "Today"
            )
        return '-'
    transaction_date_display.short_description = 'Date'
    transaction_date_display.admin_order_field = 'transaction_date'
    
    def status_display(self, obj):
        """Display status with colored indicators."""
        colors = {
            'pending': '#ff9800',    # Orange
            'completed': '#4caf50',  # Green
            'cancelled': '#f44336',  # Red
            'on_hold': '#9e9e9e'     # Grey
        }
        color = colors.get(obj.status, '#9e9e9e')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def reconciled_display(self, obj):
        """Display reconciliation status."""
        if obj.reconciled:
            return format_html(
                '<span style="color: #4caf50; font-size: 16px;">✓</span><br>'
                '<small>{}</small>',
                obj.reconciled_date.strftime('%b %d') if obj.reconciled_date else ''
            )
        return format_html(
            '<span style="color: #ff9800; font-size: 16px;">⏳</span>'
        )
    reconciled_display.short_description = 'Reconciled'
    reconciled_display.admin_order_field = 'reconciled'
    
    def created_by_link(self, obj):
        """Display creator with link to user admin."""
        if obj.created_by:
            user_url = reverse('admin:authentication_user_change', args=[obj.created_by.id])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: none;">{}</a>',
                user_url,
                obj.created_by.get_full_name() or obj.created_by.email
            )
        return '-'
    created_by_link.short_description = 'Created By'
    created_by_link.admin_order_field = 'created_by__first_name'
    
    def transaction_actions(self, obj):
        """Display quick action buttons."""
        actions = []
        
        # Reconciliation actions
        if not obj.reconciled:
            actions.append(
                '<a href="#" onclick="reconcileTransaction({})" '
                'style="background: #4caf50; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Reconcile</a>'.format(obj.id)
            )
        
        # Status actions
        if obj.status == 'pending':
            actions.append(
                '<a href="#" onclick="approveTransaction({})" '
                'style="background: #2196f3; color: white; padding: 2px 6px; '
                'border-radius: 4px; text-decoration: none; font-size: 10px;">Approve</a>'.format(obj.id)
            )
        
        # View details
        actions.append(
            '<a href="{}" '
            'style="background: #9e9e9e; color: white; padding: 2px 6px; '
            'border-radius: 4px; text-decoration: none; font-size: 10px;">Edit</a>'.format(
                reverse('admin:transactions_transaction_change', args=[obj.id])
            )
        )
        
        return format_html(' '.join(actions))
    transaction_actions.short_description = 'Actions'
    
    # Admin Actions
    def mark_as_reconciled(self, request, queryset):
        """Mark selected transactions as reconciled."""
        count = 0
        for transaction in queryset.filter(reconciled=False):
            transaction.mark_reconciled(request.user)
            count += 1
        self.message_user(request, f'{count} transactions marked as reconciled.')
    mark_as_reconciled.short_description = 'Mark as reconciled'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected transactions as completed."""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} transactions marked as completed.')
    mark_as_completed.short_description = 'Mark as completed'
    
    def approve_transactions(self, request, queryset):
        """Approve selected transactions."""
        updated = queryset.update(
            status='completed',
            approved_by=request.user,
            approved_date=timezone.now()
        )
        self.message_user(request, f'{updated} transactions approved successfully.')
    approve_transactions.short_description = 'Approve selected transactions'


@admin.register(TransactionAttachment)
class TransactionAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_link',
        'original_name',
        'file_size_display',
        'mime_type',
        'upload_date_display'
    ]
    
    list_filter = [
        'mime_type',
        'upload_date',
        'transaction__business'
    ]
    
    search_fields = [
        'original_name',
        'transaction__transaction_number',
        'transaction__description'
    ]
    
    def transaction_link(self, obj):
        """Display transaction with link."""
        transaction_url = reverse('admin:transactions_transaction_change', args=[obj.transaction.id])
        return format_html(
            '<a href="{}" style="color: #0066cc;">{}</a>',
            transaction_url,
            obj.transaction.transaction_number
        )
    transaction_link.short_description = 'Transaction'
    
    def file_size_display(self, obj):
        """Display file size in human readable format."""
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'File Size'
    
    def upload_date_display(self, obj):
        """Display upload date."""
        return obj.upload_date.strftime('%b %d, %Y at %I:%M %p')
    upload_date_display.short_description = 'Uploaded'
    upload_date_display.admin_order_field = 'upload_date'


# Enhanced admin site customization for transactions
admin.site.site_header = "AccountEezy Admin Portal"
admin.site.site_title = "AccountEezy Administration"
admin.site.index_title = "Business & Financial Management"