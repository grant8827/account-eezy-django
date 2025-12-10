from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg, Count, Q
from decimal import Decimal
from datetime import datetime, date, timedelta

from .models import Payroll, PayrollAllowance, PayrollDeduction
from .serializers import (
    PayrollListSerializer, PayrollDetailSerializer, PayrollCreateSerializer,
    PayrollSummarySerializer, PayrollTaxReportSerializer
)
from businesses.models import Business
from employees.models import Employee


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_payrolls(request):
    """Get all payrolls for admin users"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    payrolls = Payroll.objects.all().order_by('-pay_period_start')
    serializer = PayrollListSerializer(payrolls, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payroll_list_create(request, business_id):
    """List payrolls for a business or create a new payroll"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    if request.method == 'GET':
        # Query parameters for filtering
        employee_id = request.GET.get('employee_id')
        status_filter = request.GET.get('status')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        payrolls = Payroll.objects.filter(business=business)
        
        if employee_id:
            payrolls = payrolls.filter(employee_id=employee_id)
        if status_filter:
            payrolls = payrolls.filter(status=status_filter)
        if start_date:
            payrolls = payrolls.filter(pay_period_start__gte=start_date)
        if end_date:
            payrolls = payrolls.filter(pay_period_end__lte=end_date)
        
        payrolls = payrolls.order_by('-pay_period_start')
        serializer = PayrollListSerializer(payrolls, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Validate employee belongs to business
        employee_id = request.data.get('employee')
        if employee_id:
            employee = get_object_or_404(Employee, id=employee_id, business=business)
        
        serializer = PayrollCreateSerializer(data=request.data)
        if serializer.is_valid():
            payroll = serializer.save(
                business=business,
                created_by=request.user
            )
            response_serializer = PayrollDetailSerializer(payroll)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def payroll_detail(request, business_id, pk):
    """Get, update, or delete a specific payroll"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    payroll = get_object_or_404(Payroll, id=pk, business=business)
    
    if request.method == 'GET':
        serializer = PayrollDetailSerializer(payroll)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only allow updates if payroll is in draft status
        if payroll.status != 'draft':
            return Response({
                'error': 'Only draft payrolls can be updated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PayrollCreateSerializer(payroll, data=request.data, partial=True)
        if serializer.is_valid():
            payroll = serializer.save()
            response_serializer = PayrollDetailSerializer(payroll)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only allow deletion if payroll is in draft status
        if payroll.status != 'draft':
            return Response({
                'error': 'Only draft payrolls can be deleted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payroll.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_payroll(request, business_id, pk):
    """Approve a payroll"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    payroll = get_object_or_404(Payroll, id=pk, business=business)
    
    if payroll.status not in ['draft', 'calculated']:
        return Response({
            'error': 'Only draft or calculated payrolls can be approved'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    comments = request.data.get('comments', '')
    payroll.approve(request.user, comments)
    
    serializer = PayrollDetailSerializer(payroll)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_payroll_paid(request, business_id, pk):
    """Mark a payroll as paid"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    payroll = get_object_or_404(Payroll, id=pk, business=business)
    
    if payroll.status != 'approved':
        return Response({
            'error': 'Only approved payrolls can be marked as paid'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    payroll.mark_as_paid(request.user)
    
    serializer = PayrollDetailSerializer(payroll)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_summary(request, business_id):
    """Get payroll summary for a business"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    # Date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    payrolls = Payroll.objects.filter(business=business)
    
    if start_date:
        payrolls = payrolls.filter(pay_period_start__gte=start_date)
    if end_date:
        payrolls = payrolls.filter(pay_period_end__lte=end_date)
    
    # Calculate summary statistics
    summary_data = payrolls.aggregate(
        total_payrolls=Count('id'),
        total_gross_pay=Sum('gross_earnings') or Decimal('0'),
        total_net_pay=Sum('net_pay') or Decimal('0'),
        total_deductions=Sum('total_deductions') or Decimal('0'),
        average_gross_pay=Avg('gross_earnings') or Decimal('0'),
        average_net_pay=Avg('net_pay') or Decimal('0'),
        total_paye=Sum('paye_amount') or Decimal('0'),
        total_nis=Sum('nis_contribution') or Decimal('0'),
        total_education_tax=Sum('education_tax_amount') or Decimal('0'),
        total_heart_trust=Sum('heart_trust_amount') or Decimal('0'),
        unpaid_payrolls=Count('id', filter=Q(is_paid=False)),
        draft_payrolls=Count('id', filter=Q(status='draft'))
    )
    
    serializer = PayrollSummarySerializer(summary_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_tax_report(request, business_id):
    """Generate tax report for Jamaica tax authorities"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    # Date range (required for tax reports)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        return Response({
            'error': 'start_date and end_date are required for tax reports'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return Response({
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    payrolls = Payroll.objects.filter(
        business=business,
        pay_period_start__gte=start_date,
        pay_period_end__lte=end_date,
        status__in=['approved', 'paid']
    ).order_by('pay_period_start')
    
    # Calculate tax totals
    tax_data = payrolls.aggregate(
        total_paye=Sum('paye_amount') or Decimal('0'),
        total_nis=Sum('nis_contribution') or Decimal('0'),
        total_education_tax=Sum('education_tax_amount') or Decimal('0'),
        total_heart_trust=Sum('heart_trust_amount') or Decimal('0'),
        total_gross_pay=Sum('gross_earnings') or Decimal('0'),
        employee_count=Count('employee', distinct=True)
    )
    
    report_data = {
        'period_start': start_date,
        'period_end': end_date,
        **tax_data,
        'payroll_entries': PayrollListSerializer(payrolls, many=True).data
    }
    
    serializer = PayrollTaxReportSerializer(report_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_employees(request, business_id):
    """Get all active employees for payroll processing"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    employees = Employee.objects.filter(
        business=business,
        is_active=True
    ).select_related('user').order_by('user__first_name', 'user__last_name')
    
    employee_data = []
    for employee in employees:
        employee_data.append({
            'id': employee.id,
            'employee_id': employee.employee_id,
            'first_name': employee.user.first_name,
            'last_name': employee.user.last_name,
            'full_name': employee.full_name,
            'position': employee.position,
            'department': employee.department,
            'base_salary_amount': str(employee.base_salary_amount),
            'salary_frequency': employee.salary_frequency,
            'employment_type': employee.employment_type,
            'start_date': employee.start_date,
            'trn': employee.trn,
            'nis': employee.nis
        })
    
    return Response({
        'success': True,
        'data': {
            'employees': employee_data,
            'count': len(employee_data)
        }
    })