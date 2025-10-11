from django.urls import path
from . import views

urlpatterns = [
    path('all/', views.all_payrolls, name='all-payrolls'),
    path('<int:business_id>/', views.payroll_list_create, name='payroll-list-create'),
    path('<int:business_id>/<int:pk>/', views.payroll_detail, name='payroll-detail'),
    path('<int:business_id>/<int:pk>/approve/', views.approve_payroll, name='approve-payroll'),
    path('<int:business_id>/<int:pk>/pay/', views.mark_payroll_paid, name='mark-payroll-paid'),
    path('<int:business_id>/summary/', views.payroll_summary, name='payroll-summary'),
    path('<int:business_id>/tax-report/', views.generate_tax_report, name='generate-tax-report'),
]