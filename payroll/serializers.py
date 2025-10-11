from rest_framework import serializers
from .models import Payroll, PayrollAllowance, PayrollDeduction, PayrollApproval


class PayrollAllowanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollAllowance
        fields = '__all__'
        read_only_fields = ('id',)


class PayrollDeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollDeduction
        fields = '__all__'
        read_only_fields = ('id',)


class PayrollApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.get_full_name', read_only=True)
    
    class Meta:
        model = PayrollApproval
        fields = '__all__'
        read_only_fields = ('id', 'approved_date')


class PayrollListSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_nis = serializers.CharField(source='employee.nis_number', read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'payroll_number', 'employee_name', 'employee_nis',
            'pay_period_start', 'pay_period_end', 'gross_earnings',
            'total_deductions', 'net_pay', 'status', 'pay_date', 'is_paid'
        ]


class PayrollDetailSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_nis = serializers.CharField(source='employee.nis_number', read_only=True)
    business_name = serializers.CharField(source='business.business_name', read_only=True)
    allowances = PayrollAllowanceSerializer(many=True, read_only=True)
    other_deductions = PayrollDeductionSerializer(many=True, read_only=True)
    approvals = PayrollApprovalSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payroll
        fields = '__all__'


class PayrollCreateSerializer(serializers.ModelSerializer):
    allowances = PayrollAllowanceSerializer(many=True, required=False)
    other_deductions = PayrollDeductionSerializer(many=True, required=False)
    
    class Meta:
        model = Payroll
        exclude = ['id', 'created_at', 'updated_at', 'payroll_number', 'gross_earnings', 
                  'total_deductions', 'net_pay', 'paye_amount', 'nis_contribution',
                  'education_tax_amount', 'heart_trust_amount', 'pension_employee_contribution',
                  'pension_employer_contribution']
    
    def create(self, validated_data):
        allowances_data = validated_data.pop('allowances', [])
        deductions_data = validated_data.pop('other_deductions', [])
        
        payroll = Payroll.objects.create(**validated_data)
        
        # Create allowances
        for allowance_data in allowances_data:
            PayrollAllowance.objects.create(payroll=payroll, **allowance_data)
        
        # Create deductions
        for deduction_data in deductions_data:
            PayrollDeduction.objects.create(payroll=payroll, **deduction_data)
        
        return payroll


class PayrollSummarySerializer(serializers.Serializer):
    total_payrolls = serializers.IntegerField()
    total_gross_pay = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_net_pay = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_deductions = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_gross_pay = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_net_pay = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paye = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_nis = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_education_tax = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_heart_trust = serializers.DecimalField(max_digits=15, decimal_places=2)
    unpaid_payrolls = serializers.IntegerField()
    draft_payrolls = serializers.IntegerField()


class PayrollTaxReportSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_paye = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_nis = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_education_tax = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_heart_trust = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_gross_pay = serializers.DecimalField(max_digits=15, decimal_places=2)
    employee_count = serializers.IntegerField()
    payroll_entries = PayrollListSerializer(many=True)