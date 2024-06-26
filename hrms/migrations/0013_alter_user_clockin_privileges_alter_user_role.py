# Generated by Django 5.0.6 on 2024-06-12 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0012_user_clockin_privileges_alter_attendance_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='clockin_privileges',
            field=models.CharField(choices=[('Cannot clock-in from anywhere', 'No privileges'), ('can_clockin_anywhere', 'Can clock in from anywhere')], default='Cannot clock-in from anywhere', max_length=255),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('superuser', 'Superuser'), ('employee', 'Employee'), ('manager', 'Manager'), ('client', 'Client'), ('can_clockin_anywhere', 'Can clock in from anywhere'), ('Cannot clock-in from anywhere', 'Cannot clock in from anywhere'), ('no_role', 'No role')], default='no_role', max_length=255),
        ),
    ]
