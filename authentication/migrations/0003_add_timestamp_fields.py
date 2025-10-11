# Migration to acknowledge existing timestamp columns in database
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_alter_user_managers'),
    ]

    operations = [
        # Add model fields that match existing database columns
        migrations.AddField(
            model_name='user',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='last_login_time',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='deleted_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='current_business_id',
            field=models.BigIntegerField(null=True, blank=True),
        ),
    ]