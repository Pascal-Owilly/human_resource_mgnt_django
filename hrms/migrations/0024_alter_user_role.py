# Generated by Django 5.0.6 on 2024-06-27 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0023_user_is_archived'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('superuser', 'Superuser'), ('employee', 'Employee'), ('account_manager', 'AccountManager'), ('client', 'Client'), ('can_clockin_anywhere', 'Can clock in from anywhere'), ('Within the organization', 'Cannot clock in from anywhere'), ('no_role', 'No role')], default='no_role', max_length=255),
        ),
    ]
