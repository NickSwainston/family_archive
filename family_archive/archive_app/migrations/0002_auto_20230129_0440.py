# Generated by Django 3.2.5 on 2023-01-29 04:40

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('archive_app', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='media_file',
            new_name='MediaFile',
        ),
        migrations.RenameModel(
            old_name='user_profile',
            new_name='UserProfile',
        ),
    ]
