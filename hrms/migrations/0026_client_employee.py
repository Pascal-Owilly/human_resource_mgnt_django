# Generated by Django 5.0.6 on 2024-06-27 12:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0025_remove_user_client_client_account_manager'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
