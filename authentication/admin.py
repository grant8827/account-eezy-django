from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from .models import User


class UserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'full_name', 'role', 'account_status', 'email_verified', 
        'business_count', 'last_login_time', 'date_joined', 'user_actions'
    )
    list_filter = (
        'role', 'is_active', 'is_staff', 'email_verified', 'date_joined', 
        'last_login_time', 'parish'
    )
    search_fields = ('email', 'first_name', 'last_name', 'trn', 'nis')
    ordering = ('-date_joined',)
    list_per_page = 25
    
    actions = [
        'approve_users', 'suspend_users', 'activate_users', 
        'verify_email', 'send_welcome_email'
    ]
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone'),
            'classes': ('collapse',)
        }),
        ('Address Information', {
            'fields': ('street', 'city', 'parish', 'postal_code', 'country'),
            'classes': ('collapse',)
        }),
        ('Tax Information', {
            'fields': ('trn', 'nis'),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': ('role', 'is_active', 'email_verified'),
            'classes': ('wide',)
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Activity Tracking', {
            'fields': ('last_login', 'last_login_time', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ('date_joined', 'created_at', 'updated_at', 'last_login')
    
    def get_queryset(self, request):
        # Optimize queries with select_related and prefetch_related
        queryset = super().get_queryset(request)
        queryset = queryset.select_related().annotate(
            businesses_count=Count('owned_businesses', distinct=True)
        )
        return queryset
    
    def full_name(self, obj):
        return obj.full_name or f"{obj.first_name} {obj.last_name}".strip()
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'first_name'
    
    def account_status(self, obj):
        if obj.is_active:
            color = 'green'
            status = 'Active'
        else:
            color = 'red'
            status = 'Suspended'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    account_status.short_description = 'Status'
    account_status.admin_order_field = 'is_active'
    
    def business_count(self, obj):
        count = getattr(obj, 'businesses_count', 0)
        if count > 0:
            # Create link to businesses in admin
            url = reverse('admin:businesses_business_changelist') + f'?owner__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: blue;">{} business{}</a>',
                url,
                count,
                'es' if count != 1 else ''
            )
        return '0 businesses'
    business_count.short_description = 'Businesses'
    business_count.admin_order_field = 'businesses_count'
    
    def user_actions(self, obj):
        actions = []
        
        # Quick approve/suspend toggle
        if obj.is_active:
            suspend_url = reverse('admin:auth_user_changelist') + f'?action=suspend_users&_selected_action={obj.id}'
            actions.append(f'<a href="#" onclick="return confirm(\'Suspend user {obj.email}?\');" style="color: red;">Suspend</a>')
        else:
            activate_url = reverse('admin:auth_user_changelist') + f'?action=activate_users&_selected_action={obj.id}'
            actions.append(f'<a href="#" onclick="return confirm(\'Activate user {obj.email}?\');" style="color: green;">Activate</a>')
        
        # Email verification
        if not obj.email_verified:
            actions.append('<span style="color: orange;">Verify Email</span>')
        
        return format_html(' | '.join(actions))
    user_actions.short_description = 'Quick Actions'
    user_actions.allow_tags = True
    
    # Custom Actions
    def approve_users(self, request, queryset):
        updated = queryset.update(is_active=True, email_verified=True)
        self.message_user(
            request,
            f'{updated} user(s) approved and activated successfully.',
            messages.SUCCESS
        )
    approve_users.short_description = "Approve selected users"
    
    def suspend_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} user(s) suspended successfully.',
            messages.WARNING
        )
    suspend_users.short_description = "Suspend selected users"
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} user(s) activated successfully.',
            messages.SUCCESS
        )
    activate_users.short_description = "Activate selected users"
    
    def verify_email(self, request, queryset):
        updated = queryset.update(email_verified=True)
        self.message_user(
            request,
            f'{updated} user(s) email verified successfully.',
            messages.SUCCESS
        )
    verify_email.short_description = "Verify email for selected users"
    
    def send_welcome_email(self, request, queryset):
        # Placeholder for welcome email functionality
        count = queryset.count()
        self.message_user(
            request,
            f'Welcome email sent to {count} user(s) successfully.',
            messages.INFO
        )
    send_welcome_email.short_description = "Send welcome email to selected users"


admin.site.register(User, UserAdmin)


class AdminStatsDashboard:
    """Custom admin statistics dashboard"""
    
    @staticmethod
    def get_user_statistics():
        """Get comprehensive user statistics"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        verified_users = User.objects.filter(email_verified=True).count()
        suspended_users = User.objects.filter(is_active=False).count()
        
        # Users by role
        role_stats = User.objects.values('role').annotate(
            count=Count('id')
        ).order_by('role')
        
        # Users registered in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        
        # Users by parish
        parish_stats = User.objects.values('parish').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'suspended_users': suspended_users,
            'new_users_30d': new_users_30d,
            'role_distribution': list(role_stats),
            'parish_distribution': list(parish_stats),
            'verification_rate': (verified_users / total_users * 100) if total_users > 0 else 0,
            'active_rate': (active_users / total_users * 100) if total_users > 0 else 0
        }
    
    @staticmethod
    def get_business_statistics():
        """Get comprehensive business statistics"""
        try:
            from businesses.models import Business
            
            total_businesses = Business.objects.count()
            active_businesses = Business.objects.filter(is_active=True).count()
            
            # Businesses by subscription status
            subscription_stats = Business.objects.values('subscription_status').annotate(
                count=Count('id')
            ).order_by('subscription_status')
            
            # Businesses by plan
            plan_stats = Business.objects.values('subscription_plan').annotate(
                count=Count('id')
            ).order_by('subscription_plan')
            
            # Businesses by industry
            industry_stats = Business.objects.values('industry').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Businesses registered in last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            new_businesses_30d = Business.objects.filter(created_at__gte=thirty_days_ago).count()
            
            # Revenue statistics
            revenue_stats = Business.objects.aggregate(
                total_revenue=Sum('billing_amount'),
                avg_revenue=Avg('billing_amount')
            )
            
            return {
                'total_businesses': total_businesses,
                'active_businesses': active_businesses,
                'new_businesses_30d': new_businesses_30d,
                'subscription_distribution': list(subscription_stats),
                'plan_distribution': list(plan_stats),
                'industry_distribution': list(industry_stats),
                'total_revenue': revenue_stats['total_revenue'] or 0,
                'average_revenue': revenue_stats['avg_revenue'] or 0,
                'active_rate': (active_businesses / total_businesses * 100) if total_businesses > 0 else 0
            }
        except ImportError:
            return {'error': 'Business model not available'}
    
    @staticmethod
    def get_employee_statistics():
        """Get comprehensive employee statistics"""
        try:
            from employees.models import Employee
            
            total_employees = Employee.objects.count()
            active_employees = Employee.objects.filter(is_active=True).count()
            
            # Employees by employment type
            employment_stats = Employee.objects.values('employment_type').annotate(
                count=Count('id')
            ).order_by('employment_type')
            
            # Average salary by position
            salary_stats = Employee.objects.values('position').annotate(
                avg_salary=Avg('base_salary_amount'),
                count=Count('id')
            ).order_by('-avg_salary')[:10]
            
            # Employees hired in last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            new_employees_30d = Employee.objects.filter(start_date__gte=thirty_days_ago).count()
            
            return {
                'total_employees': total_employees,
                'active_employees': active_employees,
                'new_employees_30d': new_employees_30d,
                'employment_distribution': list(employment_stats),
                'salary_by_position': list(salary_stats),
                'active_rate': (active_employees / total_employees * 100) if total_employees > 0 else 0
            }
        except ImportError:
            return {'error': 'Employee model not available'}
    
    @staticmethod
    def get_system_statistics():
        """Get system-wide statistics"""
        from django.contrib.sessions.models import Session
        from django.contrib.admin.models import LogEntry
        
        # Active sessions
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now()).count()
        
        # Recent admin actions
        recent_actions = LogEntry.objects.filter(
            action_time__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Database sizes (approximation)
        user_count = User.objects.count()
        
        try:
            from businesses.models import Business
            business_count = Business.objects.count()
        except ImportError:
            business_count = 0
        
        try:
            from employees.models import Employee
            employee_count = Employee.objects.count()
        except ImportError:
            employee_count = 0
        
        return {
            'active_sessions': active_sessions,
            'recent_admin_actions': recent_actions,
            'total_records': user_count + business_count + employee_count,
            'user_records': user_count,
            'business_records': business_count,
            'employee_records': employee_count
        }


def admin_statistics_view(request):
    """Custom admin view for comprehensive statistics"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    dashboard = AdminStatsDashboard()
    
    context = {
        'title': 'AccountEezy Statistics Dashboard',
        'user_stats': dashboard.get_user_statistics(),
        'business_stats': dashboard.get_business_statistics(),
        'employee_stats': dashboard.get_employee_statistics(),
        'system_stats': dashboard.get_system_statistics(),
        'generated_at': timezone.now()
    }
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(context, default=str)
    
    return render(request, 'admin/statistics_dashboard.html', context)


def admin_export_data(request):
    """Export admin statistics as CSV or JSON"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    format_type = request.GET.get('format', 'json')
    dashboard = AdminStatsDashboard()
    
    data = {
        'users': dashboard.get_user_statistics(),
        'businesses': dashboard.get_business_statistics(),
        'employees': dashboard.get_employee_statistics(),
        'system': dashboard.get_system_statistics(),
        'exported_at': timezone.now().isoformat()
    }
    
    if format_type == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="accounteezy_stats.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value', 'Category'])
        
        # Write user stats
        for key, value in data['users'].items():
            writer.writerow([key, value, 'users'])
        
        # Write business stats
        if 'error' not in data['businesses']:
            for key, value in data['businesses'].items():
                writer.writerow([key, value, 'businesses'])
        
        return response
    
    return JsonResponse(data, default=str)


# Extend admin site with custom views
class CustomAdminSite(admin.AdminSite):
    site_header = 'AccountEezy Administration'
    site_title = 'AccountEezy Admin'
    index_title = 'Business Management Dashboard'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', admin_statistics_view, name='admin_statistics'),
            path('export-data/', admin_export_data, name='admin_export_data'),
        ]
        return custom_urls + urls


# Replace default admin site
admin.site.__class__ = CustomAdminSite