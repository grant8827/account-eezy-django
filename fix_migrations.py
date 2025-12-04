#!/usr/bin/env python3

import os
import sys
import django

# Add the Django backend directory to the path
sys.path.append('/Users/gregorygrant/Desktop/Websites/Python/React Django Webapp/account_easy/django_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_backend.settings')

django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

# Check the table structure
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'employees_employee';")
    columns = cursor.fetchall()
    print("Columns in employees_employee table:")
    for col in columns:
        print(f"  - {col[0]}")

print("\n" + "="*50)

# Check migration status
from django.core.management.commands.showmigrations import Command as ShowMigrationsCommand
from django.core.management.base import CommandError
from io import StringIO

output = StringIO()
try:
    cmd = ShowMigrationsCommand()
    cmd.stdout = output
    cmd.handle(app_label=['employees'], verbosity=2)
    print("Migration status:")
    print(output.getvalue())
except Exception as e:
    print(f"Error checking migrations: {e}")

print("\n" + "="*50)

# Try to run migrations
print("Attempting to run migrations...")
try:
    execute_from_command_line(['manage.py', 'migrate', 'employees'])
    print("Migrations completed successfully!")
except Exception as e:
    print(f"Error running migrations: {e}")