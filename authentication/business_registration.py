from django.db import transaction, IntegrityError
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
@transaction.atomic
def register_with_business(request):
    """Enhanced registration endpoint that creates user and business in one flow"""
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
    
    # Handle comprehensive business creation
    payment_id = request.data.get('payment_id')
    
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
        
        # Use provided registration number or generate one
        registration_number = request.data.get('registration_number')
        if not registration_number:
            registration_number = f"REG-{user.id}-{datetime.now().strftime('%Y%m%d')}-{unique_suffix}"
        
        # Handle TRN - use provided or generate
        trn_number = request.data.get('trn')
        if not trn_number or len(str(trn_number)) != 9:
            # Generate a unique 9-digit TRN using timestamp and user ID
            timestamp_suffix = str(int(datetime.now().timestamp()))[-4:]  # Last 4 digits of timestamp
            user_id_padded = f"{user.id:05d}"  # Pad user ID to 5 digits
            trn_number = f"{user_id_padded}{timestamp_suffix}"  # 5 digits user ID + 4 digits timestamp = 9 digits
            
        # Ensure TRN is always a string and exactly 9 digits
        trn_number = str(trn_number)[:9] if trn_number else f"{user.id:09d}"
        
        # Handle NIS (optional)
        nis_number = request.data.get('nis', '')
        if nis_number and len(str(nis_number)) != 9:
            nis_number = ''  # Clear invalid NIS
        
        # Debug logging
        print(f"Generated registration_number: {registration_number}")
        print(f"Generated trn_number: {trn_number}")
        print(f"NIS number: {nis_number}")
        
        # Create business with comprehensive fields
        business = Business.objects.create(
            owner=user,
            business_name=business_name,
            registration_number=registration_number,
            trn=trn_number,
            nis=nis_number,
            business_type=request.data.get('business_type', 'Other'),
            industry=request.data.get('industry', 'Other'),
            
            # Address information
            street=request.data.get('street', 'Not specified'),
            city=request.data.get('city', 'Kingston'),
            parish=request.data.get('parish', 'Kingston'),
            postal_code=request.data.get('postal_code', ''),
            country=request.data.get('country', 'Jamaica'),
            
            # Contact information
            phone=request.data.get('business_phone', request.data.get('phone', getattr(user, 'phone', None) or '8765551234')),
            email=request.data.get('business_email', user.email),
            website=request.data.get('website', ''),
            
            # Business settings
            subscription_status='active' if payment else 'trial',
            subscription_plan=plan_name.lower() if plan_name else 'basic',
            pay_period='monthly',
            pay_day=28,
            overtime_rate=1.5,
            public_holiday_rate=2.0,
            paye_registered=False,
            nis_registered=bool(nis_number),
            education_tax_registered=False,
            heart_trust_registered=False,
            gct_registered=False,
            tax_year=datetime.now().year,
            fiscal_year_end=date(datetime.now().year, 12, 31),
            currency='JMD',
            timezone='America/Jamaica',
            date_format='DD/MM/YYYY',
            email_notifications=True,
            sms_notifications=False
        )
        
        print(f"Business created successfully: {business.business_name} (ID: {business.id})")
        
        # Add comprehensive business info to response
        response_data.update({
            'business': {
                'id': business.id,
                'business_name': business.business_name,
                'registration_number': business.registration_number,
                'trn': business.trn,
                'nis': business.nis,
                'business_type': business.business_type,
                'industry': business.industry,
                'street': business.street,
                'city': business.city,
                'parish': business.parish,
                'postal_code': business.postal_code,
                'country': business.country,
                'phone': business.phone,
                'email': business.email,
                'website': business.website,
                'subscription_status': business.subscription_status,
                'subscription_plan': business.subscription_plan,
                'is_active': True,
                'created_at': business.created_at.isoformat() if hasattr(business, 'created_at') else None
            },
            'subscription': {
                'plan_name': plan_name,
                'status': 'active' if payment else 'trial',
                'payment_id': payment.id if payment else None
            }
        })
        
    except IntegrityError:
        transaction.set_rollback(True)
        return Response({
            'success': False,
            'message': 'Business registration failed',
            'errors': {'business': ['A business is already associated with this user account.']}
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as business_error:
        transaction.set_rollback(True)
        error_details = traceback.format_exc()
        print(f"Warning: Business creation failed for user {user.email}: {str(business_error)}")
        print(f"Full error trace: {error_details}")
        return Response({
            'success': False,
            'message': 'Business registration failed due to a server error.',
            'errors': {'server': [str(business_error)]}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': True,
        'message': 'User registered successfully with business',
        'data': response_data
    }, status=status.HTTP_201_CREATED)