from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta, date
import uuid
import traceback

from .models import User
from .serializers import UserRegistrationSerializer, UserSerializer

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
            return Response({
                'success': False,
                'message': 'User registration failed',
                'errors': user_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = user_serializer.save()
        tokens = get_tokens_for_user(user)
        
        # Initialize response data
        response_data = {
            'user': UserSerializer(user).data,
            'tokens': tokens
        }
        
        # Handle business creation
        payment_id = request.data.get('payment_id')
        business_name = request.data.get('business_name')
        
        # Create default business name if not provided
        if not business_name:
            business_name = f"{user.first_name or 'User'} {user.last_name or ''}'s Business".strip()
        
        # Always attempt to create business for registration
        print(f"Creating business for user {user.email} with plan {plan_name}")
        
        try:
            from businesses.models import Business
            from subscriptions.models import PayPalPayment
            print("Imported Business and PayPalPayment models successfully")
            
            # Initialize payment as None
            payment = None
            
            # Verify the payment exists and belongs to this user (if provided)
            if payment_id and payment_id != 'skip_payment' and not payment_id.startswith('skip_payment'):
                try:
                    payment = PayPalPayment.objects.get(id=payment_id, user=user)
                    print(f"Found payment: {payment.id}")
                except (PayPalPayment.DoesNotExist, ValueError) as e:
                    # Payment not found, but continue with registration
                    print(f"Warning: Payment {payment_id} not found for user {user.email}: {str(e)}")
            
            # Generate unique business identifiers
            unique_suffix = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for uniqueness
            registration_number = f"REG-{user.id}-{datetime.now().strftime('%Y%m%d')}-{unique_suffix}"
            trn_number = request.data.get('trn')
            
            # If no TRN provided, generate a unique one
            if not trn_number or len(str(trn_number)) != 9:
                # Generate a unique 9-digit TRN using timestamp and user ID
                timestamp_suffix = str(int(datetime.now().timestamp()))[-4:]  # Last 4 digits of timestamp
                user_id_padded = f"{user.id:05d}"  # Pad user ID to 5 digits
                trn_number = f"{user_id_padded}{timestamp_suffix}"  # 5 digits user ID + 4 digits timestamp = 9 digits
                
            # Ensure TRN is always a string and not empty
            trn_number = str(trn_number) if trn_number else f"{user.id:09d}"
            
            # Debug logging
            print(f"Generated registration_number: {registration_number}")
            print(f"Generated trn_number: {trn_number}")
            
            # Create business with all required fields
            business = Business.objects.create(
                owner=user,
                name=business_name,
                registration_number=registration_number,
                trn=trn_number,
                business_type=request.data.get('business_type', 'Other'),
                industry=request.data.get('industry', 'Other'),
                street=request.data.get('address', 'Not specified'),
                city=request.data.get('city', 'Kingston'),
                parish=request.data.get('parish', 'Kingston'),
                phone=request.data.get('phone', getattr(user, 'phone', None) or '8765551234'),
                email=request.data.get('business_email', user.email),
                subscription_status='active' if payment else 'trial',
                fiscal_year_end=date(datetime.now().year, 12, 31)  # Set fiscal year end to December 31
            )
            
            print(f"Business created successfully: {business.name} (ID: {business.id})")
            
            # Skip subscription creation for now due to model/table mismatch
            # TODO: Fix subscription model table name mismatch (expects subscriptions_subscription, but table is 'subscription')
            subscription = None
            print("Subscription creation skipped due to model/table mismatch")
            
            # Add business info to response
            response_data.update({
                'business': {
                    'id': business.id,
                    'name': business.name,
                    'registration_number': business.registration_number,
                    'trn': business.trn,
                    'subscription_status': business.subscription_status
                },
                'subscription': {
                    'plan_name': plan_name,
                    'status': 'active' if payment else 'trial',
                    'payment_id': payment.id if payment else None
                }
            })
            
        except Exception as business_error:
            error_details = traceback.format_exc()
            print(f"Warning: Business creation failed for user {user.email}: {str(business_error)}")
            print(f"Full error trace: {error_details}")
            # Don't fail the entire registration if business creation fails
            response_data['business_creation_warning'] = f'Business setup failed: {str(business_error)}'
        
        return Response({
            'success': True,
            'message': 'User registered successfully' + (' with business' if 'business' in response_data else ''),
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Registration error: {str(e)}")
        print(f"Full error trace: {error_details}")
        return Response({
            'success': False,
            'message': 'Registration failed due to server error',
            'error': str(e) if hasattr(request, 'user') and getattr(request.user, 'is_staff', False) else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)