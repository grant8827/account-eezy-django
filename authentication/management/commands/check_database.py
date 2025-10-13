from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
from django.db import connection
from authentication.models import User


class Command(BaseCommand):
    help = 'Check database status and run migrations if needed'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking database status...")
        
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS("✅ Database connection: OK"))
            
            # Check if migrations are needed
            try:
                user_count = User.objects.count()
                self.stdout.write(f"👤 Current users in database: {user_count}")
                
                # Check if the auth_user table exists and has the right structure
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'auth_user'
                    """)
                    columns = [row[0] for row in cursor.fetchall()]
                    
                expected_columns = ['id', 'email', 'first_name', 'last_name', 'role', 'phone', 'trn']
                missing_columns = [col for col in expected_columns if col not in columns]
                
                if missing_columns:
                    self.stdout.write(f"⚠️  Missing columns: {missing_columns}")
                    self.stdout.write("Running migrations...")
                    execute_from_command_line(['manage.py', 'migrate'])
                else:
                    self.stdout.write(self.style.SUCCESS("✅ Database schema: OK"))
                
            except Exception as e:
                self.stdout.write(f"⚠️  Database schema issue: {e}")
                self.stdout.write("Running migrations...")
                execute_from_command_line(['manage.py', 'migrate'])
            
            # Create a test user if none exist
            if User.objects.count() == 0:
                self.stdout.write("➕ Creating test user...")
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
            
            self.stdout.write(self.style.SUCCESS("\n🎉 Database setup complete!"))
            self.stdout.write("📊 Summary:")
            self.stdout.write(f"  Total users: {User.objects.count()}")
            self.stdout.write("  Registration endpoint: /api/auth/register/")
            self.stdout.write("  Login endpoint: /api/auth/login/")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Database setup failed: {e}")
            )
            self.stdout.write("💡 Troubleshooting tips:")
            self.stdout.write("1. Check database connection settings in .env")
            self.stdout.write("2. Ensure Railway PostgreSQL is accessible")
            self.stdout.write("3. Run: python manage.py migrate --run-syncdb")