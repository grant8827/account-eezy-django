from django.urls import path
from . import views

urlpatterns = [
    path('all/', views.all_transactions, name='all-transactions'),
    path('<int:business_id>/', views.transaction_list_create, name='transaction-list-create'),
    path('<int:business_id>/<int:pk>/', views.transaction_detail, name='transaction-detail'),
    path('<int:business_id>/<int:pk>/reconcile/', views.mark_transaction_reconciled, name='mark-transaction-reconciled'),
    path('<int:business_id>/summary/', views.transaction_summary, name='transaction-summary'),
    path('<int:business_id>/categories/', views.transaction_categories, name='transaction-categories'),
]