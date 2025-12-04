# Generated manually to fix field naming

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('businesses', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            'ALTER TABLE business RENAME COLUMN name TO business_name;',
            'ALTER TABLE business RENAME COLUMN business_name TO name;',
        ),
    ]