# Generated by Django 4.2.1 on 2023-07-02 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_rename_recommendedproblems_recommendedproblem'),
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('problem_id', models.CharField(max_length=20)),
                ('submission_time', models.IntegerField(default=0)),
            ],
        ),
    ]
