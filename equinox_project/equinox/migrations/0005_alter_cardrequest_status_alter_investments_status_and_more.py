# Generated by Django 5.0.6 on 2024-06-09 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equinox', '0004_alter_investments_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardrequest',
            name='status',
            field=models.CharField(choices=[('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=100),
        ),
        migrations.AlterField(
            model_name='investments',
            name='status',
            field=models.CharField(choices=[('rejected', 'Rejected'), ('In progress', 'In progress')], default='awaiting slot entry', max_length=100),
        ),
        migrations.AlterField(
            model_name='withdrawalrequest',
            name='RequestID',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
