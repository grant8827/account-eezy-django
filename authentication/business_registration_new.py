from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta, date
import uuid

from .models import User
from .serializers import UserRegistrationSerializer, UserSerializer
from businesses.models import Business
from subscriptions.models import PayPalPayment

User = get_user_model()


def get_tokens_for_user(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    return {
        'refreshToken': str(refresh),
        'token': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register_with_business(request):
    """Enhanced registration endpoint that creates user and business in one flow"""
    try:
        # Extract data
        email = request.data.get('email')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        business_name = request.data.get('business_name')
        plan_name = request.data.get('plan_name', 'Starter')
        payment_id = request.data.get('payment_id')  # Optional PayPal payment ID
        
        print(f"🔥 Starting registration for {email} with business: {business_name}")
        
        # Validate required fields
        if not email or not password or not business_name:
            return Response({
                'success': False,
                'message': 'Missing required fields',
                'errors': {
                    'required_fields': ['email', 'password', 'business_name']
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password confirmation
        if not password_confirm or password != password_confirm:
            return Response({
                'success': False,
                'message': 'User registration failed',
                'errors': {
                    'password_confirm': ['This field is required.'] if not password_confirm else ['Passwords do not match.']
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user using existing serializer
        user_data = {
            'email': email,
            'password': password,
            'password_confirm': password_confirm
        }
        
        user_serializer = UserRegistrationSerializer(data=user_data)
        if not user_serializer.is_valid():
            print(f"❌ User serializer validation failed: {user_serializer.errors}")
            return Response({
                'success': False,
                'message': 'User registration failed',
                'errors': user_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save user
        user = user_serializer.save()
        print(f"✅ User created successfully: {user.email} (ID: {user.id})")
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        # Prepare response data
        response_data = {
            'user': UserSerializer(user).data,
            'tokens': tokens
        }
        
        # Look for existing PayPal payment
        payment = None
        if payment_id:
            try:
                payment = PayPalPayment.objects.get(paypal_order_id=payment_id)
                print(f"💰 Found PayPal payment: {payment.id}")
            except PayPalPayment.DoesNotExist:
                print(f"⚠️ PayPal payment not found: {payment_id}")
        
        # Try to create business
        if business_name:
            try:
                print(f"🏢 Attempting to create business for user {user.id}: {business_name}")
                
                # Create business for the user
                business = Business.objects.create(
                    owner=user,
                    name=business_name,
                    subscription_status='trial',
                    subscription_plan=plan_name or 'Starter',
                    is_active=True,
                    fiscal_year_end=date(datetime.now().year, 12, 31)  # Set fiscal year end to December 31
                )
                print(f"✅ Business created successfully: {business.name} (ID: {business.id})")
                
                # Skip subscription creation for now due to model/table mismatch
                # TODO: Fix subscription model table name mismatch (expects subscriptions_subscription, but table is 'subscription')
                subscription = None
                print("⚠️ Subscription creation skipped due to model/table mismatch")
                
                # Add business info to response
                response_data.update({
                    'business': {
                        'id': business.id,
                        'name': business.name,
                        'subscription_status': business.subscription_status
                    },
                    'subscription': {
                        'id': subscription.id if subscription else None,
                        'plan_name': subscription.plan_name if subscription else plan_name,
                        'status': subscription.status if subscription else 'trial',
                        'next_billing_date': subscription.next_billing_date.isoformat() if subscription else None
                    } if subscription else None
                })
                
            except Exception as business_error:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ Business creation failed for user {user.email}: {str(business_error)}")
                print(f"📋 Full error trace: {error_details}")
                # Don't fail the entire registration if business creation fails
                response_data['business_creation_warning'] = f'Business setup failed: {str(business_error)}'
        
        print(f"🎉 Registration completed successfully for {user.email}")
        return Response({
            'success': True,
            'message': 'User and business registered successfully',
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import traceback
        print(f"💥 Business registration error: {str(e)}")
        print(f"📋 Full error trace: {traceback.format_exc()}")
        return Response({
            'success': False,
            'message': 'Registration failed',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)