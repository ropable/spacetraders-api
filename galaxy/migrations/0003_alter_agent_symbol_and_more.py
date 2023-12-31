# Generated by Django 4.2.8 on 2024-01-03 02:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0002_alter_contract_type_alter_markettradegood_activity_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="agent",
            name="symbol",
            field=models.CharField(max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name="shipyardtransaction",
            name="agent_symbol",
            field=models.CharField(default="FOOBAR", max_length=32),
            preserve_default=False,
        ),
    ]
