# Generated by Django 5.0.3 on 2024-03-27 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_user_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="name",
            field=models.CharField(default="hard", max_length=100),
            preserve_default=False,
        ),
    ]
