# Generated by Django 5.0.6 on 2024-06-12 10:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0013_alter_user_clockin_privileges_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='clockin_privileges',
            field=models.CharField(choices=[('no_clockin_privileges', 'No privileges'), ('can_clockin_anywhere', 'Can clock in from anywhere')], default='no_clockin_privileges', max_length=255),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('superuser', 'Superuser'), ('employee', 'Employee'), ('manager', 'Manager'), ('client', 'Client'), ('can_clockin_anywhere', 'Can clock in from anywhere'), ('no_clockin_privileges', 'Cannot clock in from anywhere'), ('no_role', 'No role')], default='no_role', max_length=255),
        ),
    ]
