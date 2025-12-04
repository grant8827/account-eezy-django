#!/usr/bin/env python
"""
Manual superuser creation script for AccountEezy Django backend
"""
import os
import sys
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accounteezy.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

def create_superuser():
    """Create a superuser account"""
    print("🚀 Creating AccountEezy Superuser...")
    print("=" * 50)
    
    # Check if superuser already exists
    if User.objects.filter(is_superuser=True).exists():
        print("⚠️  A superuser already exists!")
        existing_superuser = User.objects.filter(is_superuser=True).first()
        print(f"   Email: {existing_superuser.email}")
        
        overwrite = input("\nDo you want to create another superuser? (y/N): ").lower().strip()
        if overwrite not in ['y', 'yes']:
            print("❌ Superuser creation cancelled.")
            return False
    
    # Get superuser details
    print("\n📝 Enter superuser details:")
    
    # Email (username)
    while True:
        email = input("Email address: ").strip()
        if not email:
            print("❌ Email is required!")
            continue
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            print(f"❌ User with email '{email}' already exists!")
            continue
        
        try:
            # Basic email validation
            if '@' not in email or '.' not in email.split('@')[1]:
                raise ValidationError("Invalid email format")
            break
        except ValidationError:
            print("❌ Please enter a valid email address!")
    
    # First name
    first_name = input("First name: ").strip() or "Admin"
    
    # Last name  
    last_name = input("Last name: ").strip() or "User"
    
    # Password
    while True:
        password = input("Password (min 8 characters): ").strip()
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long!")
            continue
        
        password_confirm = input("Confirm password: ").strip()
        if password != password_confirm:
            print("❌ Passwords do not match!")
            continue
        break
    
    # Phone (optional)
    phone = input("Phone number (optional): ").strip() or "+1-876-555-0000"
    
    try:
        # Create the superuser
        superuser = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            is_staff=True,
            is_superuser=True,
            is_active=True,
            email_verified=True,
            role='admin'
        )
        
        print("\n" + "=" * 50)
        print("✅ Superuser created successfully!")
        print("=" * 50)
        print(f"📧 Email: {superuser.email}")
        print(f"👤 Name: {superuser.get_full_name()}")
        print(f"📱 Phone: {superuser.phone}")
        print(f"🔑 Role: {superuser.role}")
        print(f"✅ Active: {superuser.is_active}")
        print(f"✅ Staff: {superuser.is_staff}")
        print(f"✅ Superuser: {superuser.is_superuser}")
        print("=" * 50)
        print("\n🎉 You can now access the admin interface at:")
        print("   http://localhost:8000/admin/")
        print(f"   Login with: {email}")
        print("\n💡 Don't forget to start the Django development server:")
        print("   python manage.py runserver")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating superuser: {e}")
        return False

def main():
    """Main function"""
    try:
        success = create_superuser()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Superuser creation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()