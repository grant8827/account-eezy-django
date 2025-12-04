import os
import sys
import django
from django.conf import settings
from django.core.management import call_command

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accounteezy.settings')
django.setup()

try:
    print("Applying migrations...")
    call_command('migrate', 'employees', verbosity=2)
    print("Migrations applied successfully!")
except Exception as e:
    print(f"Error applying migrations: {e}")
    
    # Try to manually add the column using raw SQL
    from django.db import connection
    print("Attempting to add user_id column manually...")
    
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'employees_employee' AND column_name = 'user_id'
        """)
        
        if not cursor.fetchone():
            print("Adding user_id column...")
            cursor.execute("ALTER TABLE employees_employee ADD COLUMN user_id INTEGER;")
            cursor.execute("""
                ALTER TABLE employees_employee 
                ADD CONSTRAINT employees_employee_user_id_fkey 
                FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;
            """)
            cursor.execute("CREATE INDEX employees_employee_user_id_idx ON employees_employee(user_id);")
            print("user_id column added successfully!")
        else:
            print("user_id column already exists!")