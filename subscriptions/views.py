from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from decimal import Decimal

from .models import Subscription, SubscriptionHistory, PaymentHistory
from .serializers import (
    SubscriptionListSerializer, SubscriptionDetailSerializer, 
    SubscriptionCreateSerializer, SubscriptionUsageSerializer,
    SubscriptionPlanComparisonSerializer, SubscriptionHistorySerializer,
    PaymentHistorySerializer
)
from businesses.models import Business


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_subscriptions(request):
    """Get all subscriptions for admin users"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    subscriptions = Subscription.objects.all().order_by('-created_at')
    serializer = SubscriptionListSerializer(subscriptions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_detail(request, business_id):
    """Get subscription details for a business"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    try:
        subscription = business.subscription
        serializer = SubscriptionDetailSerializer(subscription)
        return Response(serializer.data)
    except Subscription.DoesNotExist:
        return Response({'error': 'No subscription found for this business'}, 
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request, business_id):
    """Create a new subscription for a business"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    # Check if business already has a subscription
    if hasattr(business, 'subscription'):
        return Response({'error': 'Business already has a subscription'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    serializer = SubscriptionCreateSerializer(data=request.data)
    if serializer.is_valid():
        subscription = serializer.save(business=business)
        
        # Create history record
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action='created',
            details=f'Subscription created with {subscription.plan_type} plan',
            amount=subscription.amount,
            created_by=request.user
        )
        
        response_serializer = SubscriptionDetailSerializer(subscription)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_subscription(request, business_id):
    """Update subscription (upgrade/downgrade)"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    old_plan = subscription.plan_type
    old_amount = subscription.amount
    
    serializer = SubscriptionCreateSerializer(subscription, data=request.data, partial=True)
    if serializer.is_valid():
        subscription = serializer.save()
        
        # Determine if upgrade or downgrade
        plan_order = {'basic': 1, 'standard': 2, 'premium': 3, 'enterprise': 4}
        action = 'upgraded' if plan_order.get(subscription.plan_type, 0) > plan_order.get(old_plan, 0) else 'downgraded'
        
        # Create history record
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action=action,
            details=f'Plan changed from {old_plan} to {subscription.plan_type}',
            amount=subscription.amount,
            created_by=request.user
        )
        
        response_serializer = SubscriptionDetailSerializer(subscription)
        return Response(response_serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request, business_id):
    """Cancel a subscription"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    reason = request.data.get('reason', '')
    subscription.cancel(reason)
    
    serializer = SubscriptionDetailSerializer(subscription)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suspend_subscription(request, business_id):
    """Suspend a subscription"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    if subscription.status == 'suspended':
        return Response({'error': 'Subscription is already suspended'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    reason = request.data.get('reason', '')
    subscription.suspend(reason)
    
    serializer = SubscriptionDetailSerializer(subscription)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reactivate_subscription(request, business_id):
    """Reactivate a suspended subscription"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    if subscription.status != 'suspended':
        return Response({'error': 'Only suspended subscriptions can be reactivated'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    subscription.reactivate()
    
    serializer = SubscriptionDetailSerializer(subscription)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_usage(request, business_id):
    """Get subscription usage statistics"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    # Update usage before returning
    subscription.update_usage()
    
    # Calculate usage percentages
    employee_usage_percentage = (subscription.current_employees / subscription.max_employees * 100) if subscription.max_employees > 0 else 0
    transaction_usage_percentage = (subscription.transactions_this_month / subscription.max_transactions_per_month * 100) if subscription.max_transactions_per_month > 0 else 0
    payroll_usage_percentage = (subscription.payroll_runs_this_month / subscription.max_payroll_runs_per_month * 100) if subscription.max_payroll_runs_per_month > 0 else 0
    
    usage_data = {
        'plan_type': subscription.plan_type,
        'max_employees': subscription.max_employees,
        'current_employees': subscription.current_employees,
        'max_transactions_per_month': subscription.max_transactions_per_month,
        'transactions_this_month': subscription.transactions_this_month,
        'max_payroll_runs_per_month': subscription.max_payroll_runs_per_month,
        'payroll_runs_this_month': subscription.payroll_runs_this_month,
        'employee_usage_percentage': round(employee_usage_percentage, 2),
        'transaction_usage_percentage': round(transaction_usage_percentage, 2),
        'payroll_usage_percentage': round(payroll_usage_percentage, 2),
    }
    
    serializer = SubscriptionUsageSerializer(usage_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_history(request, business_id):
    """Get subscription history"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    history = subscription.history.all()
    serializer = SubscriptionHistorySerializer(history, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request, business_id):
    """Get payment history for subscription"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    subscription = get_object_or_404(Subscription, business=business)
    
    payments = subscription.payments.all()
    serializer = PaymentHistorySerializer(payments, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_comparison(request):
    """Get plan comparison data"""
    current_business_id = request.GET.get('business_id')
    current_plan = None
    
    if current_business_id:
        try:
            business = Business.objects.get(id=current_business_id, owner=request.user)
            current_plan = business.subscription.plan_type
        except (Business.DoesNotExist, Subscription.DoesNotExist):
            pass
    
    plans_data = [
        {
            'plan_type': 'basic',
            'display_name': 'Basic Plan',
            'monthly_price': Decimal('2999.00'),  # JMD 2,999
            'max_employees': 5,
            'max_transactions_per_month': 50,
            'max_payroll_runs_per_month': 2,
            'has_payroll': True,
            'has_financial_reporting': True,
            'has_tax_calculations': True,
            'has_multi_user_access': False,
            'has_api_access': False,
            'has_advanced_analytics': False,
            'has_priority_support': False,
            'is_current_plan': current_plan == 'basic'
        },
        {
            'plan_type': 'standard',
            'display_name': 'Standard Plan',
            'monthly_price': Decimal('5999.00'),  # JMD 5,999
            'max_employees': 25,
            'max_transactions_per_month': 250,
            'max_payroll_runs_per_month': 4,
            'has_payroll': True,
            'has_financial_reporting': True,
            'has_tax_calculations': True,
            'has_multi_user_access': True,
            'has_api_access': False,
            'has_advanced_analytics': True,
            'has_priority_support': False,
            'is_current_plan': current_plan == 'standard'
        },
        {
            'plan_type': 'premium',
            'display_name': 'Premium Plan',
            'monthly_price': Decimal('9999.00'),  # JMD 9,999
            'max_employees': 100,
            'max_transactions_per_month': 1000,
            'max_payroll_runs_per_month': 12,
            'has_payroll': True,
            'has_financial_reporting': True,
            'has_tax_calculations': True,
            'has_multi_user_access': True,
            'has_api_access': True,
            'has_advanced_analytics': True,
            'has_priority_support': True,
            'is_current_plan': current_plan == 'premium'
        },
        {
            'plan_type': 'enterprise',
            'display_name': 'Enterprise Plan',
            'monthly_price': Decimal('19999.00'),  # JMD 19,999
            'max_employees': 999999,
            'max_transactions_per_month': 999999,
            'max_payroll_runs_per_month': 999999,
            'has_payroll': True,
            'has_financial_reporting': True,
            'has_tax_calculations': True,
            'has_multi_user_access': True,
            'has_api_access': True,
            'has_advanced_analytics': True,
            'has_priority_support': True,
            'is_current_plan': current_plan == 'enterprise'
        }
    ]
    
    serializer = SubscriptionPlanComparisonSerializer(plans_data, many=True)
    return Response(serializer.data)