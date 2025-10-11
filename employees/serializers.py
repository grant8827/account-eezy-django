from rest_framework import serializers
from .models import (
    Employee, EmployeeAllowance, EmployeeBenefit, EmployeeDocument,
    EmployeeLeaveRequest, EmployeePerformanceReview, EmployeeDisciplinaryAction, WorkDay
)
from authentication.serializers import UserSerializer


class WorkDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkDay
        fields = ['day']


class EmployeeAllowanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAllowance
        fields = ['id', 'allowance_type', 'amount', 'taxable', 'description', 'is_active']
        read_only_fields = ['id']


class EmployeeBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBenefit
        fields = [
            'id', 'benefit_type', 'provider', 'coverage', 'employer_contribution',
            'employee_contribution', 'start_date', 'end_date', 'is_active'
        ]
        read_only_fields = ['id']


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = [
            'id', 'document_type', 'filename', 'original_name', 'file_path',
            'file_size', 'mime_type', 'upload_date', 'expiry_date'
        ]
        read_only_fields = ['id', 'upload_date']


class EmployeeLeaveRequestSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeeLeaveRequest
        fields = [
            'id', 'leave_type', 'start_date', 'end_date', 'days', 'reason',
            'status', 'approved_by', 'approved_by_name', 'request_date', 'approved_date'
        ]
        read_only_fields = ['id', 'request_date', 'approved_date']
    
    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None


class EmployeePerformanceReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
    
    class Meta:
        model = EmployeePerformanceReview
        fields = [
            'id', 'reviewer', 'reviewer_name', 'review_date', 'rating',
            'comments', 'goals', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeDisciplinaryActionSerializer(serializers.ModelSerializer):
    issued_by_name = serializers.CharField(source='issued_by.full_name', read_only=True)
    
    class Meta:
        model = EmployeeDisciplinaryAction
        fields = [
            'id', 'action_type', 'reason', 'issued_by', 'issued_by_name',
            'action_date', 'resolved', 'resolution_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    employment_status = serializers.ReadOnlyField()
    vacation_days_remaining = serializers.ReadOnlyField()
    sick_days_remaining = serializers.ReadOnlyField()
    annual_gross_salary = serializers.SerializerMethodField()
    supervisor_name = serializers.CharField(source='supervisor.full_name', read_only=True)
    work_days = WorkDaySerializer(many=True, read_only=True)
    allowances = EmployeeAllowanceSerializer(many=True, read_only=True)
    benefits = EmployeeBenefitSerializer(many=True, read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    leave_requests = EmployeeLeaveRequestSerializer(many=True, read_only=True)
    performance_reviews = EmployeePerformanceReviewSerializer(many=True, read_only=True)
    disciplinary_actions = EmployeeDisciplinaryActionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'business', 'employee_id', 'full_name', 'age', 'employment_status',
            # Personal Information
            'date_of_birth', 'gender', 'marital_status', 'nationality',
            # Emergency Contact
            'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_contact_phone', 'emergency_contact_address',
            # Employment Information
            'position', 'department', 'start_date', 'end_date', 'employment_type',
            # Work Schedule
            'hours_per_week', 'start_time', 'end_time', 'work_days',
            # Probation
            'probation_months', 'probation_end_date',
            # Supervisor
            'supervisor', 'supervisor_name',
            # Compensation
            'base_salary_amount', 'salary_currency', 'salary_frequency',
            'overtime_eligible', 'overtime_rate', 'annual_gross_salary',
            # Tax Information
            'trn', 'nis', 'tax_status', 'dependents', 'education_credit',
            'pension_contribution_rate',
            # Bank Details
            'bank_name', 'account_number', 'routing_number', 'account_type',
            # Leave
            'vacation_days_entitlement', 'vacation_days_used', 'vacation_days_remaining',
            'sick_days_entitlement', 'sick_days_used', 'sick_days_remaining',
            # Related Data
            'allowances', 'benefits', 'documents', 'leave_requests',
            'performance_reviews', 'disciplinary_actions',
            # Termination
            'termination_date', 'termination_reason', 'termination_type',
            'notice_period', 'final_pay_date', 'exit_interview_completed',
            # Status
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_id', 'created_at', 'updated_at']
    
    def get_annual_gross_salary(self, obj):
        return obj.calculate_annual_gross_salary()


class EmployeeCreateSerializer(serializers.ModelSerializer):
    work_days = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    
    class Meta:
        model = Employee
        fields = [
            'user', 'business', 'date_of_birth', 'gender', 'marital_status', 'nationality',
            'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_contact_phone', 'emergency_contact_address',
            'position', 'department', 'start_date', 'employment_type',
            'hours_per_week', 'start_time', 'end_time', 'work_days',
            'probation_months', 'supervisor',
            'base_salary_amount', 'salary_currency', 'salary_frequency',
            'overtime_eligible', 'overtime_rate',
            'trn', 'nis', 'tax_status', 'dependents', 'education_credit',
            'pension_contribution_rate',
            'bank_name', 'account_number', 'routing_number', 'account_type',
            'vacation_days_entitlement', 'sick_days_entitlement'
        ]
    
    def create(self, validated_data):
        work_days = validated_data.pop('work_days', [])
        employee = Employee.objects.create(**validated_data)
        
        # Create work days
        for day in work_days:
            WorkDay.objects.create(employee=employee, day=day)
        
        return employee