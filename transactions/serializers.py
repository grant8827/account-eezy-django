from rest_framework import serializers
from .models import Transaction, TransactionAttachment


class TransactionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionAttachment
        fields = [
            'id', 'filename', 'original_name', 'file_path',
            'file_size', 'mime_type', 'upload_date'
        ]
        read_only_fields = ['id', 'upload_date']


class TransactionSerializer(serializers.ModelSerializer):
    total_amount = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    reconciled_by_name = serializers.CharField(source='reconciled_by.get_full_name', read_only=True)
    attachments = TransactionAttachmentSerializer(many=True, read_only=True)
    business = serializers.SerializerMethodField()
    
    def get_business(self, obj):
        return {
            'id': obj.business.id,
            'business_name': obj.business.business_name
        }
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'business', 'transaction_number', 'transaction_type', 'category', 'description',
            # Financial Information
            'amount', 'currency', 'exchange_rate', 'total_amount',
            # Transaction Details
            'transaction_date', 'payment_method', 'reference',
            # Vendor Information
            'vendor_name', 'vendor_trn', 'vendor_address', 'vendor_phone', 'vendor_email',
            # Customer Information
            'customer_name', 'customer_trn', 'customer_address', 'customer_phone', 'customer_email',
            # Tax Information
            'is_taxable', 'gct_rate', 'gct_amount', 'withholding_tax_rate', 'withholding_tax_amount',
            # Status and Approval
            'status', 'reconciled', 'reconciled_date', 'reconciled_by', 'reconciled_by_name',
            # User Tracking
            'created_by', 'created_by_name', 'approved_by', 'approved_by_name', 'approved_date',
            # Additional Information
            'notes', 'tags', 'attachments',
            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'transaction_number', 'total_amount', 'gct_amount', 'withholding_tax_amount',
            'created_at', 'updated_at', 'reconciled_date', 'approved_date'
        ]


class TransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'business', 'transaction_type', 'category', 'description',
            'amount', 'currency', 'exchange_rate',
            'transaction_date', 'payment_method', 'reference',
            'vendor_name', 'vendor_trn', 'vendor_address', 'vendor_phone', 'vendor_email',
            'customer_name', 'customer_trn', 'customer_address', 'customer_phone', 'customer_email',
            'is_taxable', 'gct_rate', 'withholding_tax_rate',
            'status', 'notes', 'tags'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSummarySerializer(serializers.Serializer):
    """Serializer for financial summary data"""
    transaction_type = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    count = serializers.IntegerField()