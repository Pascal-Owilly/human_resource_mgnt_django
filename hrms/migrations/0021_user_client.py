# Generated by Django 5.0.6 on 2024-06-24 20:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0020_client'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='hrms.client'),
        ),
    ]
