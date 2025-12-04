#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accounteezy.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create superuser
email = 'superadmin@accounteezy.com'
password = 'superadmin123'

# Check if user already exists
if User.objects.filter(email=email).exists():
    print(f"Superuser with email '{email}' already exists!")
    user = User.objects.get(email=email)
    print(f"User details:")
    print(f"  Email: {user.email}")
    print(f"  Is superuser: {user.is_superuser}")
    print(f"  Is staff: {user.is_staff}")
    print(f"  Is active: {user.is_active}")
else:
    # Create new superuser
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Super',
        last_name='Admin'
    )
    print(f"Superuser created successfully!")
    print(f"  Email: {user.email}")
    print(f"  Password: {password}")
    print(f"  Is superuser: {user.is_superuser}")
    print(f"  Is staff: {user.is_staff}")

print(f"\nYou can now login to Django Admin at: http://127.0.0.1:8000/admin/")
print(f"Email: {email}")
print(f"Password: {password}")