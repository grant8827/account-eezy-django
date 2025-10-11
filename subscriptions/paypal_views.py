from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import json
import logging

from .paypal_service import PayPalService
from .paypal_models import PayPalPayment, PayPalWebhook
from .models import Subscription
from .serializers import SubscriptionSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_paypal_order(request):
    """Create a PayPal order for subscription payment"""
    try:
        data = request.data
        required_fields = ['plan_name', 'plan_type', 'billing_cycle', 'amount']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return Response({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare payment data
        payment_data = {
            'user_id': request.user.id,
            'plan_name': data['plan_name'],
            'plan_type': data['plan_type'],
            'billing_cycle': data['billing_cycle'],
            'amount': float(data['amount'])
        }
        
        # Create PayPal order
        paypal_service = PayPalService()
        result = paypal_service.create_order(payment_data)
        
        if result and result.get('success'):
            return Response({
                'success': True,
                'order_id': result['order_id'],
                'payment_id': result['payment_id'],
                'approval_url': result['approval_url']
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to create PayPal order'),
                'details': result.get('details', '')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error creating PayPal order: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def capture_paypal_order(request):
    """Capture a PayPal order after user approval"""
    try:
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({
                'success': False,
                'error': 'order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the payment belongs to the current user
        try:
            payment = PayPalPayment.objects.get(
                paypal_order_id=order_id,
                user=request.user
            )
        except PayPalPayment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found or unauthorized'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Capture the order
        paypal_service = PayPalService()
        result = paypal_service.capture_order(order_id)
        
        if result and result.get('success'):
            # Get updated payment and subscription info
            payment.refresh_from_db()
            subscription_data = None
            
            if payment.subscription:
                subscription_data = SubscriptionSerializer(payment.subscription).data
            
            return Response({
                'success': True,
                'payment_id': result['payment_id'],
                'subscription_id': result.get('subscription_id'),
                'subscription': subscription_data,
                'status': payment.status
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to capture payment'),
                'details': result.get('details', '')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error capturing PayPal order: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, payment_id):
    """Get payment status"""
    try:
        payment = PayPalPayment.objects.get(
            id=payment_id,
            user=request.user
        )
        
        subscription_data = None
        if payment.subscription:
            subscription_data = SubscriptionSerializer(payment.subscription).data
        
        return Response({
            'success': True,
            'payment': {
                'id': payment.id,
                'paypal_order_id': payment.paypal_order_id,
                'status': payment.status,
                'amount': payment.amount,
                'currency': payment.currency,
                'plan_name': payment.plan_name,
                'plan_type': payment.plan_type,
                'billing_cycle': payment.billing_cycle,
                'created_at': payment.created_at,
                'captured_at': payment.captured_at,
            },
            'subscription': subscription_data
        }, status=status.HTTP_200_OK)
        
    except PayPalPayment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting payment status: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_payments(request):
    """Get all payments for the current user"""
    try:
        payments = PayPalPayment.objects.filter(user=request.user).order_by('-created_at')
        
        payments_data = []
        for payment in payments:
            subscription_data = None
            if payment.subscription:
                subscription_data = SubscriptionSerializer(payment.subscription).data
            
            payments_data.append({
                'id': payment.id,
                'paypal_order_id': payment.paypal_order_id,
                'status': payment.status,
                'amount': payment.amount,
                'currency': payment.currency,
                'plan_name': payment.plan_name,
                'plan_type': payment.plan_type,
                'billing_cycle': payment.billing_cycle,
                'created_at': payment.created_at,
                'captured_at': payment.captured_at,
                'subscription': subscription_data
            })
        
        return Response({
            'success': True,
            'payments': payments_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user payments: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
def paypal_webhook(request):
    """Handle PayPal webhook notifications"""
    try:
        headers = {
            'PAYPAL-AUTH-ALGO': request.META.get('HTTP_PAYPAL_AUTH_ALGO'),
            'PAYPAL-CERT-ID': request.META.get('HTTP_PAYPAL_CERT_ID'),
            'PAYPAL-TRANSMISSION-ID': request.META.get('HTTP_PAYPAL_TRANSMISSION_ID'),
            'PAYPAL-TRANSMISSION-SIG': request.META.get('HTTP_PAYPAL_TRANSMISSION_SIG'),
            'PAYPAL-TRANSMISSION-TIME': request.META.get('HTTP_PAYPAL_TRANSMISSION_TIME'),
        }
        
        body = request.body.decode('utf-8')
        
        # Process webhook
        paypal_service = PayPalService()
        result = paypal_service.process_webhook(headers, body)
        
        if result.get('success'):
            logger.info(f"PayPal webhook processed successfully: {result.get('webhook_id')}")
            return HttpResponse(status=200)
        else:
            logger.error(f"Failed to process PayPal webhook: {result.get('error')}")
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        return HttpResponse(status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_subscription(request):
    """Get current user's subscription"""
    try:
        # Get user's business and subscription
        from businesses.models import Business
        
        business = Business.objects.filter(owner=request.user).first()
        if not business:
            return Response({
                'success': False,
                'error': 'No business found for user'
            }, status=status.HTTP_404_NOT_FOUND)
        
        subscription = Subscription.objects.filter(business=business).first()
        if not subscription:
            return Response({
                'success': False,
                'error': 'No subscription found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        subscription_data = SubscriptionSerializer(subscription).data
        
        return Response({
            'success': True,
            'subscription': subscription_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user subscription: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_payment_success(request):
    """Simulate a successful payment for testing purposes (development only)"""
    try:
        from django.conf import settings
        
        # Only allow in debug mode
        if not settings.DEBUG:
            return Response({
                'success': False,
                'error': 'Not available in production'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        required_fields = ['plan_name', 'plan_type', 'billing_cycle', 'amount']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return Response({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a simulated successful payment
        payment = PayPalPayment.objects.create(
            paypal_order_id=f"SIMULATED-{request.user.id}-{timezone.now().timestamp()}",
            user=request.user,
            amount=float(data['amount']) / 160,  # Convert JMD to USD
            currency='USD',
            plan_name=data['plan_name'],
            plan_type=data['plan_type'],
            billing_cycle=data['billing_cycle'],
            status='completed',
            payer_email=request.user.email,
            payer_name=f"{request.user.first_name} {request.user.last_name}",
            captured_at=timezone.now()
        )
        
        # Create subscription
        subscription = payment.create_subscription_from_payment()
        
        subscription_data = None
        if subscription:
            subscription_data = SubscriptionSerializer(subscription).data
        
        return Response({
            'success': True,
            'payment_id': payment.id,
            'subscription_id': subscription.id if subscription else None,
            'subscription': subscription_data,
            'simulated': True
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error simulating payment: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)