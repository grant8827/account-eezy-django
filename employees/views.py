from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Employee, EmployeeLeaveRequest
from .serializers import (
    EmployeeSerializer, EmployeeCreateSerializer, 
    EmployeeLeaveRequestSerializer
)
from businesses.models import Business


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def employee_list_create(request, business_id):
    """List employees for a business or create new employee"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    if request.method == 'GET':
        employees = Employee.objects.filter(business=business).select_related(
            'user', 'supervisor'
        ).prefetch_related(
            'work_days', 'allowances', 'benefits', 'documents',
            'leave_requests', 'performance_reviews', 'disciplinary_actions'
        )
        
        # Filter by active status if requested
        active_only = request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            employees = employees.filter(is_active=True)
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            employees = employees.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(position__icontains=search) |
                Q(department__icontains=search)
            )
        
        serializer = EmployeeSerializer(employees, many=True)
        return Response({
            'success': True,
            'data': {'employees': serializer.data}
        })
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['business'] = business.id
        serializer = EmployeeCreateSerializer(data=data, context={'business': business})
        if serializer.is_valid():
            employee = serializer.save(business=business)
            response_serializer = EmployeeSerializer(employee)
            return Response({
                'success': True,
                'message': 'Employee created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'message': 'Employee creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def employee_detail(request, business_id, pk):
    """Get, update or delete employee"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    employee = get_object_or_404(Employee, pk=pk, business=business)
    
    if request.method == 'GET':
        serializer = EmployeeSerializer(employee)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = EmployeeSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Employee updated successfully',
                'data': serializer.data
            })
        return Response({
            'success': False,
            'message': 'Employee update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Soft delete - mark as inactive
        employee.is_active = False
        employee.save()
        return Response({
            'success': True,
            'message': 'Employee deactivated successfully'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def employee_terminate(request, business_id, pk):
    """Terminate an employee"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    employee = get_object_or_404(Employee, pk=pk, business=business)
    
    termination_data = {
        'date': request.data.get('date'),
        'reason': request.data.get('reason', ''),
        'type': request.data.get('type', 'voluntary'),
        'notice_period': request.data.get('notice_period'),
        'final_pay_date': request.data.get('final_pay_date')
    }
    
    employee.terminate(termination_data)
    
    serializer = EmployeeSerializer(employee)
    return Response({
        'success': True,
        'message': 'Employee terminated successfully',
        'data': serializer.data
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def employee_leave_requests(request, business_id, employee_id):
    """Get leave requests for employee or create new leave request"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    employee = get_object_or_404(Employee, pk=employee_id, business=business)
    
    if request.method == 'GET':
        leave_requests = EmployeeLeaveRequest.objects.filter(employee=employee)
        serializer = EmployeeLeaveRequestSerializer(leave_requests, many=True)
        return Response({
            'success': True,
            'data': {'leave_requests': serializer.data}
        })
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['employee'] = employee.id
        serializer = EmployeeLeaveRequestSerializer(data=data)
        if serializer.is_valid():
            serializer.save(employee=employee)
            return Response({
                'success': True,
                'message': 'Leave request created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'message': 'Leave request creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def process_leave_request(request, business_id, employee_id, request_id):
    """Approve or deny leave request"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    employee = get_object_or_404(Employee, pk=employee_id, business=business)
    leave_request = get_object_or_404(EmployeeLeaveRequest, pk=request_id, employee=employee)
    
    status_value = request.data.get('status')
    if status_value not in ['approved', 'denied']:
        return Response({
            'success': False,
            'message': 'Status must be either approved or denied'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    leave_request.status = status_value
    if status_value == 'approved':
        from datetime import datetime
        leave_request.approved_date = datetime.now()
        # Update used leave days
        if leave_request.leave_type == 'vacation':
            employee.vacation_days_used += leave_request.days
        elif leave_request.leave_type == 'sick':
            employee.sick_days_used += leave_request.days
        employee.save()
    
    leave_request.save()
    
    serializer = EmployeeLeaveRequestSerializer(leave_request)
    return Response({
        'success': True,
        'message': f'Leave request {status_value} successfully',
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_employees(request):
    """Get all employees across all user's businesses"""
    businesses = Business.objects.filter(owner=request.user)
    employees = Employee.objects.filter(business__in=businesses)
    
    # Filter by active status if requested
    active_only = request.query_params.get('active_only', 'false').lower() == 'true'
    if active_only:
        employees = employees.filter(is_active=True)
    
    serializer = EmployeeSerializer(employees, many=True)
    return Response({
        'success': True,
        'data': {'employees': serializer.data}
    })