from django.db import models
from django.conf import settings

from datetime import datetime


class MediaFile(models.Model):
    id = models.AutoField(primary_key=True)
    media_path = models.FileField(upload_to="media/", max_length=1024, null=True)

    class Meta:
        ordering = ['-id']


class UserProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rating",
        primary_key=True,
    )
    email = models.EmailField(max_length=254)
