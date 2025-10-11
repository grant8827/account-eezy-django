from django.urls import path
from . import views
from . import paypal_views

urlpatterns = [
    # Existing subscription endpoints
    path('all/', views.all_subscriptions, name='all-subscriptions'),
    path('<int:business_id>/', views.subscription_detail, name='subscription-detail'),
    path('<int:business_id>/create/', views.create_subscription, name='create-subscription'),
    path('<int:business_id>/update/', views.update_subscription, name='update-subscription'),
    path('<int:business_id>/cancel/', views.cancel_subscription, name='cancel-subscription'),
    path('<int:business_id>/suspend/', views.suspend_subscription, name='suspend-subscription'),
    path('<int:business_id>/reactivate/', views.reactivate_subscription, name='reactivate-subscription'),
    path('<int:business_id>/usage/', views.subscription_usage, name='subscription-usage'),
    path('<int:business_id>/history/', views.subscription_history, name='subscription-history'),
    path('<int:business_id>/payments/', views.payment_history, name='payment-history'),
    path('plans/', views.plan_comparison, name='plan-comparison'),
    
    # PayPal payment endpoints
    path('paypal/create-order/', paypal_views.create_paypal_order, name='create-paypal-order'),
    path('paypal/capture-order/', paypal_views.capture_paypal_order, name='capture-paypal-order'),
    path('paypal/payment/<int:payment_id>/', paypal_views.get_payment_status, name='get-payment-status'),
    path('paypal/payments/', paypal_views.get_user_payments, name='get-user-payments'),
    path('paypal/webhook/', paypal_views.paypal_webhook, name='paypal-webhook'),
    path('paypal/subscription/', paypal_views.get_user_subscription, name='get-user-subscription'),
    path('paypal/simulate-payment/', paypal_views.simulate_payment_success, name='simulate-payment-success'),
]