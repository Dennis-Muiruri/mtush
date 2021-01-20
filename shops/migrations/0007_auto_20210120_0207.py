# Generated by Django 2.2.16 on 2021-01-20 02:07

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0006_auto_20210120_0130'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderitem',
            name='timestamp',
        ),
        migrations.AddField(
            model_name='billingaddress',
            name='county',
            field=models.CharField(default=django.utils.timezone.now, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='billingaddress',
            name='zip',
            field=models.CharField(default=django.utils.timezone.now, max_length=100),
            preserve_default=False,
        ),
    ]
