# Generated by Django 5.1.3 on 2024-11-09 16:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0015_booking_approved_by_provider"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="action_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notification",
            name="booking",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="app.booking",
            ),
        ),
    ]