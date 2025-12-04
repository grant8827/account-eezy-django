from django.urls import path
from . import views
from . import business_registration

urlpatterns = [
    path('register/', views.register, name='register'),
    path('register-with-business/', business_registration.register_with_business, name='register_with_business'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('user/', views.profile, name='user'),  # Alias for profile to match frontend
    path('refresh/', views.refresh_token, name='refresh_token'),  # Token refresh endpoint
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('health/', views.health, name='auth_health'),
]