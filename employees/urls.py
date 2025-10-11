from django.urls import path
from . import views

urlpatterns = [
    path('all/', views.all_employees, name='all-employees'),
    path('<int:business_id>/', views.employee_list_create, name='employee-list-create'),
    path('<int:business_id>/<int:pk>/', views.employee_detail, name='employee-detail'),
    path('<int:business_id>/<int:pk>/terminate/', views.employee_terminate, name='employee-terminate'),
    path('<int:business_id>/<int:employee_id>/leave-requests/', views.employee_leave_requests, name='employee-leave-requests'),
    path('<int:business_id>/<int:employee_id>/leave-requests/<int:request_id>/process/', views.process_leave_request, name='process-leave-request'),
]