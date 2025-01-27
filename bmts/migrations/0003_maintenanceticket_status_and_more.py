# Generated by Django 5.1.2 on 2024-11-18 22:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bmts', '0002_maintenanceticket'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenanceticket',
            name='status',
            field=models.CharField(choices=[('Open', 'Open'), ('Resolved', 'Resolved')], default='Open', max_length=20),
        ),
        migrations.AddField(
            model_name='maintenanceticket',
            name='ticket_number',
            field=models.CharField(blank=True, max_length=10, unique=True),
        ),
    ]
