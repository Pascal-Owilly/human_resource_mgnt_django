# Generated by Django 5.0.6 on 2024-06-05 13:30

import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0004_employee_user_alter_attendance_status_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='address',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='bank',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='email',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='emergency',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='emp_id',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='gender',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='joined',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='language',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='mobile',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='nuban',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='salary',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='thumb',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='user',
        ),
        migrations.AddField(
            model_name='employee',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='user',
            name='address',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='bank',
            field=models.CharField(default='Equity', max_length=25),
        ),
        migrations.AddField(
            model_name='user',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='hrms.department'),
        ),
        migrations.AddField(
            model_name='user',
            name='emergency',
            field=models.CharField(blank=True, max_length=11, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='emp_id',
            field=models.CharField(default='emp735', max_length=70),
        ),
        migrations.AddField(
            model_name='user',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'MALE'), ('female', 'FEMALE')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='joined',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='user',
            name='language',
            field=models.CharField(choices=[('english', 'ENGLISH'), ('french', 'FRENCH'), ('yoruba', 'YORUBA'), ('hausa', 'HAUSA')], default='english', max_length=10),
        ),
        migrations.AddField(
            model_name='user',
            name='mng_id',
            field=models.CharField(default='mng480', max_length=70),
        ),
        migrations.AddField(
            model_name='user',
            name='mobile',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None),
        ),
        migrations.AddField(
            model_name='user',
            name='nuban',
            field=models.CharField(default='0123456789', max_length=10),
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('superuser', 'Superuser'), ('employee', 'Employee'), ('manager', 'Manager'), ('client', 'Client'), ('no_role', 'No Role')], default='no_role', max_length=255),
        ),
        migrations.AddField(
            model_name='user',
            name='salary',
            field=models.CharField(default='00,000.00', max_length=16),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='first_name',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_name',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=30, unique=True),
        ),
    ]