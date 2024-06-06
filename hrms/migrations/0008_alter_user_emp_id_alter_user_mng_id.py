# Generated by Django 5.0.6 on 2024-06-05 15:43

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hrms', '0007_remove_department_department_alter_user_emp_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='emp_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='mng_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
