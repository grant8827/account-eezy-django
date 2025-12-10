from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from datetime import datetime, timedelta
from .models import Transaction
from .serializers import (
    TransactionSerializer, TransactionCreateSerializer, TransactionSummarySerializer
)
from businesses.models import Business


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def transaction_list_create(request, business_id):
    """List transactions for a business or create new transaction"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    if request.method == 'GET':
        transactions = Transaction.objects.filter(business=business).select_related(
            'created_by', 'approved_by', 'reconciled_by'
        ).prefetch_related('attachments')
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            transactions = transactions.filter(transaction_date__gte=start_date)
        if end_date:
            transactions = transactions.filter(transaction_date__lte=end_date)
        
        # Filter by transaction type
        transaction_type = request.query_params.get('type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        # Filter by category
        category = request.query_params.get('category')
        if category:
            transactions = transactions.filter(category__icontains=category)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            transactions = transactions.filter(status=status_filter)
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            transactions = transactions.filter(
                Q(description__icontains=search) |
                Q(transaction_number__icontains=search) |
                Q(vendor_name__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(reference__icontains=search)
            )
        
        # Filter reconciled transactions
        reconciled = request.query_params.get('reconciled')
        if reconciled is not None:
            transactions = transactions.filter(reconciled=reconciled.lower() == 'true')
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            'success': True,
            'data': {'transactions': serializer.data}
        })
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['business'] = business.id
        serializer = TransactionCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()
            response_serializer = TransactionSerializer(transaction)
            return Response({
                'success': True,
                'message': 'Transaction created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'message': 'Transaction creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def transaction_detail(request, business_id, pk):
    """Get, update or delete transaction"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    transaction = get_object_or_404(Transaction, pk=pk, business=business)
    
    if request.method == 'GET':
        serializer = TransactionSerializer(transaction)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = TransactionSerializer(transaction, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Transaction updated successfully',
                'data': serializer.data
            })
        return Response({
            'success': False,
            'message': 'Transaction update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        transaction.delete()
        return Response({
            'success': True,
            'message': 'Transaction deleted successfully'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_transaction_reconciled(request, business_id, pk):
    """Mark transaction as reconciled"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    transaction = get_object_or_404(Transaction, pk=pk, business=business)
    
    transaction.mark_reconciled(request.user)
    
    serializer = TransactionSerializer(transaction)
    return Response({
        'success': True,
        'message': 'Transaction marked as reconciled',
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_summary(request, business_id):
    """Get financial summary for a business"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    # Get date range (default to current month)
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    if not start_date or not end_date:
        today = datetime.now().date()
        start_date = today.replace(day=1)  # First day of current month
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # Get summary by transaction type
    summary = Transaction.objects.filter(
        business=business,
        transaction_date__gte=start_date,
        transaction_date__lte=end_date,
        status='completed'
    ).values('transaction_type').annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('transaction_type')
    
    # Calculate totals
    total_income = sum(item['total_amount'] for item in summary if item['transaction_type'] == 'income') or 0
    total_expenses = sum(item['total_amount'] for item in summary if item['transaction_type'] == 'expense') or 0
    net_income = total_income - total_expenses
    
    serializer = TransactionSummarySerializer(summary, many=True)
    return Response({
        'success': True,
        'data': {
            'summary': serializer.data,
            'totals': {
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_income': net_income
            },
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_categories(request, business_id):
    """Get unique transaction categories for a business"""
    business = get_object_or_404(Business, id=business_id, owner=request.user)
    
    categories = Transaction.objects.filter(
        business=business
    ).values_list('category', flat=True).distinct().order_by('category')
    
    return Response({
        'success': True,
        'data': {'categories': list(categories)}
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_transactions(request):
    """Get all transactions across all user's businesses"""
    businesses = Business.objects.filter(owner=request.user)
    transactions = Transaction.objects.filter(business__in=businesses).select_related(
        'business', 'created_by', 'approved_by', 'reconciled_by'
    ).prefetch_related('attachments')
    
    # Apply same filters as business-specific endpoint
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    if start_date:
        transactions = transactions.filter(transaction_date__gte=start_date)
    if end_date:
        transactions = transactions.filter(transaction_date__lte=end_date)
    
    serializer = TransactionSerializer(transactions, many=True)
    return Response({
        'success': True,
        'data': {'transactions': serializer.data}
    })