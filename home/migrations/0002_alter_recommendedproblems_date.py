# Generated by Django 4.2.1 on 2023-07-01 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recommendedproblems',
            name='date',
            field=models.IntegerField(default=0),
        ),
    ]
