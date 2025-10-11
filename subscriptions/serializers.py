from rest_framework import serializers
from .models import Subscription, SubscriptionHistory, PaymentHistory


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = SubscriptionHistory
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class SubscriptionListSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.business_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_trial = serializers.BooleanField(read_only=True)
    days_until_renewal = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'business_name', 'plan_type', 'status', 'amount', 'currency',
            'billing_cycle', 'next_billing_date', 'is_active', 'is_trial',
            'days_until_renewal', 'auto_renew'
        ]


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.business_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_trial = serializers.BooleanField(read_only=True)
    days_until_renewal = serializers.IntegerField(read_only=True)
    can_add_employee = serializers.BooleanField(read_only=True)
    can_add_transaction = serializers.BooleanField(read_only=True)
    can_run_payroll = serializers.BooleanField(read_only=True)
    history = SubscriptionHistorySerializer(many=True, read_only=True)
    payments = PaymentHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'current_employees',
            'current_businesses', 'transactions_this_month',
            'payroll_runs_this_month', 'last_usage_reset'
        )


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        exclude = [
            'id', 'created_at', 'updated_at', 'current_employees',
            'current_businesses', 'transactions_this_month',
            'payroll_runs_this_month', 'last_usage_reset',
            'next_billing_date'
        ]


class SubscriptionUsageSerializer(serializers.Serializer):
    plan_type = serializers.CharField()
    max_employees = serializers.IntegerField()
    current_employees = serializers.IntegerField()
    max_transactions_per_month = serializers.IntegerField()
    transactions_this_month = serializers.IntegerField()
    max_payroll_runs_per_month = serializers.IntegerField()
    payroll_runs_this_month = serializers.IntegerField()
    employee_usage_percentage = serializers.FloatField()
    transaction_usage_percentage = serializers.FloatField()
    payroll_usage_percentage = serializers.FloatField()


class SubscriptionPlanComparisonSerializer(serializers.Serializer):
    plan_type = serializers.CharField()
    display_name = serializers.CharField()
    monthly_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_employees = serializers.IntegerField()
    max_transactions_per_month = serializers.IntegerField()
    max_payroll_runs_per_month = serializers.IntegerField()
    has_payroll = serializers.BooleanField()
    has_financial_reporting = serializers.BooleanField()
    has_tax_calculations = serializers.BooleanField()
    has_multi_user_access = serializers.BooleanField()
    has_api_access = serializers.BooleanField()
    has_advanced_analytics = serializers.BooleanField()
    has_priority_support = serializers.BooleanField()
    is_current_plan = serializers.BooleanField()


# Alias for main subscription serializer
SubscriptionSerializer = SubscriptionDetailSerializer