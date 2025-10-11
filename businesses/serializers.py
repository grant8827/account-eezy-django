from rest_framework import serializers
from .models import Business


class BusinessListSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Business
        fields = [
            'id', 'business_name', 'business_type', 'industry', 'parish',
            'owner_name', 'employee_count', 'status', 'created_at'
        ]
    
    def get_employee_count(self, obj):
        return obj.employees.filter(status='active').count()


class BusinessDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    active_employees = serializers.SerializerMethodField()
    
    class Meta:
        model = Business
        fields = '__all__'
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at')
    
    def get_employee_count(self, obj):
        return obj.employees.filter(status='active').count()
    
    def get_active_employees(self, obj):
        return obj.employees.filter(status='active').count()


class BusinessCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        exclude = ['id', 'owner', 'created_at', 'updated_at']
    
    def validate_trn(self, value):
        """Validate Tax Registration Number format"""
        if value and len(value) != 9:
            raise serializers.ValidationError("TRN must be 9 digits")
        return value
    
    def validate_nis_employer_number(self, value):
        """Validate NIS Employer Number format"""
        if value and len(value) < 6:
            raise serializers.ValidationError("NIS Employer Number must be at least 6 characters")
        return value


class BusinessSummarySerializer(serializers.Serializer):
    """Serializer for business summary/dashboard data"""
    business_name = serializers.CharField()
    total_employees = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    monthly_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_payrolls = serializers.IntegerField()
    recent_transactions = serializers.ListField(child=serializers.DictField(), required=False)
    upcoming_payrolls = serializers.ListField(child=serializers.DictField(), required=False)