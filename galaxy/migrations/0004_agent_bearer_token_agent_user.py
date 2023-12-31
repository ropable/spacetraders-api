# Generated by Django 4.2.8 on 2024-01-05 23:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("galaxy", "0003_alter_agent_symbol_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="bearer_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="agent",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
