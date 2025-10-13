"""
URL configuration for accounteezy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def root_view(request):
    """Root endpoint showing server status and available API routes"""
    return JsonResponse({
        'message': 'AccountEezy Django Backend is running',
        'status': 'OK',
        'version': '1.0',
        'api_endpoints': {
            'root': '/api/',
            'authentication': '/api/auth/',
            'businesses': '/api/businesses/',
            'employees': '/api/employees/',
            'transactions': '/api/transactions/',
            'payroll': '/api/payroll/',
            'subscriptions': '/api/subscriptions/',
            'admin': '/admin/'
        }
    })

def api_root(request):
    """API root endpoint showing available API routes"""
    return JsonResponse({
        'message': 'Welcome to AccountEezy API',
        'version': '1.0',
        'endpoints': {
            'authentication': '/api/auth/',
            'businesses': '/api/businesses/',
            'employees': '/api/employees/',
            'transactions': '/api/transactions/',
            'payroll': '/api/payroll/',
            'subscriptions': '/api/subscriptions/',
            'admin': '/admin/'
        }
    })

urlpatterns = [
    path('', root_view, name='root'),  # Root endpoint
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),
    path('api/auth/', include('authentication.urls')),
    path('api/businesses/', include('businesses.urls')),
    path('api/employees/', include('employees.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/payroll/', include('payroll.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)