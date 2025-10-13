from django.core.management.base import BaseCommand
from django.db import connection
from authentication.models import User


class Command(BaseCommand):
    help = 'Setup Railway PostgreSQL database and create test user'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing Railway PostgreSQL connection...")
        
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                db_version = cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Connected to PostgreSQL: {db_version[0]}")
                )
            
            # Check existing users
            user_count = User.objects.count()
            self.stdout.write(f"👤 Found {user_count} users in database")
            
            if user_count == 0:
                self.stdout.write("➕ Creating test user for login...")
                test_user = User.objects.create_user(
                    email='admin@accounteezy.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User',
                    role='business_owner'
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Test user created: {test_user.email}")
                )
                self.stdout.write("📝 Login credentials:")
                self.stdout.write("   Email: admin@accounteezy.com")
                self.stdout.write("   Password: admin123")
            else:
                self.stdout.write("📋 Existing users:")
                for user in User.objects.all()[:5]:
                    self.stdout.write(f"  - {user.email} (role: {user.role})")
            
            # Test authentication
            from django.contrib.auth import authenticate
            test_user = authenticate(username='admin@accounteezy.com', password='admin123')
            if test_user:
                self.stdout.write(
                    self.style.SUCCESS("🔐 Authentication test: PASSED")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("⚠️  Authentication test: FAILED")
                )
            
            self.stdout.write(
                self.style.SUCCESS("🎉 Database setup complete!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error: {e}")
            )
            import traceback
            traceback.print_exc()