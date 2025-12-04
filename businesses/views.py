from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Q
from decimal import Decimal

from .models import Business
from .serializers import BusinessListSerializer, BusinessDetailSerializer, BusinessCreateSerializer
from employees.models import Employee
from transactions.models import Transaction
from payroll.models import Payroll


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def business_list_create(request):
    """List businesses for authenticated user or create a new business"""
    if request.method == 'GET':
        businesses = Business.objects.filter(owner=request.user)
        serializer = BusinessListSerializer(businesses, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Enforce one business per account rule
        existing_business = Business.objects.filter(owner=request.user).first()
        if existing_business:
            return Response({
                'error': 'Account already has a business. Each account can only have one business.',
                'existing_business_id': existing_business.id,
                'existing_business_name': existing_business.business_name
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = BusinessCreateSerializer(data=request.data)
        if serializer.is_valid():
            business = serializer.save(owner=request.user)
            response_serializer = BusinessDetailSerializer(business)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def business_detail(request, pk):
    """Get, update, or delete a specific business"""
    business = get_object_or_404(Business, id=pk, owner=request.user)
    
    if request.method == 'GET':
        serializer = BusinessDetailSerializer(business)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BusinessCreateSerializer(business, data=request.data, partial=True)
        if serializer.is_valid():
            business = serializer.save()
            response_serializer = BusinessDetailSerializer(business)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        business.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def business_employees(request, pk):
    """Get employees for a specific business"""
    business = get_object_or_404(Business, id=pk, owner=request.user)
    employees = Employee.objects.filter(business=business)
    
    # Basic employee data (you might want to create a separate serializer)
    employee_data = []
    for employee in employees:
        employee_data.append({
            'id': employee.id,
            'full_name': employee.full_name,
            'email': employee.email,
            'position': employee.position,
            'department': employee.department,
            'status': employee.status,
            'hire_date': employee.hire_date,
        })
    
    return Response(employee_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def business_transactions(request, pk):
    """Get transactions for a specific business"""
    business = get_object_or_404(Business, id=pk, owner=request.user)
    transactions = Transaction.objects.filter(business=business).order_by('-transaction_date')[:50]
    
    # Basic transaction data
    transaction_data = []
    for transaction in transactions:
        transaction_data.append({
            'id': transaction.id,
            'description': transaction.description,
            'amount': str(transaction.amount),
            'transaction_type': transaction.transaction_type,
            'transaction_date': transaction.transaction_date,
            'category': transaction.category,
        })
    
    return Response(transaction_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def business_payroll(request, pk):
    """Get payroll information for a specific business"""
    business = get_object_or_404(Business, id=pk, owner=request.user)
    payrolls = Payroll.objects.filter(business=business).order_by('-pay_period_start')[:20]
    
    # Basic payroll data
    payroll_data = []
    for payroll in payrolls:
        payroll_data.append({
            'id': payroll.id,
            'payroll_number': payroll.payroll_number,
            'employee_name': payroll.employee.full_name,
            'pay_period_start': payroll.pay_period_start,
            'pay_period_end': payroll.pay_period_end,
            'gross_earnings': str(payroll.gross_earnings),
            'net_pay': str(payroll.net_pay),
            'status': payroll.status,
        })
    
    return Response(payroll_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def business_dashboard(request, pk):
    """Get dashboard data for a specific business"""
    business = get_object_or_404(Business, id=pk, owner=request.user)
    
    # Calculate dashboard metrics
    total_employees = Employee.objects.filter(business=business, status='active').count()
    total_transactions = Transaction.objects.filter(business=business).count()
    
    # Financial summary (current month)
    from datetime import datetime, date
    current_month = date.today().replace(day=1)
    
    monthly_income = Transaction.objects.filter(
        business=business,
        transaction_type='income',
        transaction_date__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    monthly_expenses = Transaction.objects.filter(
        business=business,
        transaction_type='expense',
        transaction_date__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    pending_payrolls = Payroll.objects.filter(
        business=business,
        status__in=['draft', 'calculated']
    ).count()
    
    dashboard_data = {
        'business_name': business.business_name,
        'total_employees': total_employees,
        'total_transactions': total_transactions,
        'monthly_income': str(monthly_income),
        'monthly_expenses': str(monthly_expenses),
        'monthly_profit': str(monthly_income - monthly_expenses),
        'pending_payrolls': pending_payrolls,
        'business_type': business.business_type,
        'parish': business.parish,
    }
    
    return Response(dashboard_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard_summary(request):
    """Get dashboard summary data for all user's businesses"""
    user_businesses = Business.objects.filter(owner=request.user)
    
    # Aggregate metrics across all businesses
    total_businesses = user_businesses.count()
    total_employees = Employee.objects.filter(
        business__in=user_businesses, 
        is_active=True
    ).count()
    
    # Financial summary (current month)
    from datetime import datetime, date
    current_month = date.today().replace(day=1)
    
    monthly_payroll_total = Payroll.objects.filter(
        business__in=user_businesses,
        pay_period_start__gte=current_month,
        status='paid'
    ).aggregate(total=Sum('net_pay'))['total'] or Decimal('0')
    
    pending_transactions = Transaction.objects.filter(
        business__in=user_businesses,
        status='pending'
    ).count()
    
    # Recent transactions for display
    recent_transactions = Transaction.objects.filter(
        business__in=user_businesses
    ).order_by('-transaction_date')[:10]
    
    transaction_data = []
    for transaction in recent_transactions:
        transaction_data.append({
            'id': transaction.id,
            'business_name': transaction.business.business_name,
            'description': transaction.description,
            'amount': str(transaction.amount),
            'transaction_type': transaction.transaction_type,
            'transaction_date': transaction.transaction_date,
            'status': transaction.status,
        })
    
    # Business list with basic info
    business_data = []
    for business in user_businesses:
        business_data.append({
            'id': business.id,
            'business_name': business.business_name,
            'business_type': business.business_type,
            'registration_number': business.registration_number,
            'created_at': business.created_at,
        })
    
    summary_data = {
        'summary': {
            'totalBusinesses': total_businesses,
            'totalEmployees': total_employees,
            'monthlyPayroll': str(monthly_payroll_total),
            'pendingTransactions': pending_transactions,
        },
        'businesses': business_data,
        'recentTransactions': transaction_data,
    }
    
    return Response({
        'success': True,
        'data': summary_data
    })