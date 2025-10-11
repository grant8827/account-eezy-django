from django.urls import path
from . import views

urlpatterns = [
    path('', views.business_list_create, name='business-list-create'),
    path('<int:pk>/', views.business_detail, name='business-detail'),
    path('<int:pk>/employees/', views.business_employees, name='business-employees'),
    path('<int:pk>/transactions/', views.business_transactions, name='business-transactions'),
    path('<int:pk>/payroll/', views.business_payroll, name='business-payroll'),
    path('<int:pk>/dashboard/', views.business_dashboard, name='business-dashboard'),
]