# Generated by Django 5.1.2 on 2024-11-05 00:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_service_created_at_service_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='provider',
            field=models.BooleanField(default=False),
        ),
    ]
