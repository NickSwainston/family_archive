from django.db import models
from django.conf import settings

from django.contrib.auth.models import User
from datetime import datetime


GENDERS = (
    ('m', 'male'),
    ('f', 'female'),
    # TODO will add a non-binary option when needed
)
class MediaFile(models.Model):
    id = models.AutoField(primary_key=True)
    user_uploaded = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    date_taken = models.DateTimeField(null=True)
    media_path = models.FileField(upload_to="media/", max_length=128, null=True)

    class Meta:
        ordering = ['-id']


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    content = models.TextField()
    images = models.ManyToManyField('MediaFile', related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Post by {self.user.username}'

    class Meta:
        ordering = ['-created_at']


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rating",
        primary_key=True,
    )
    email = models.EmailField(max_length=254)


class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    media_file = models.ForeignKey(MediaFile, on_delete=models.DO_NOTHING)



class FamilyMember(models.Model):
    id = models.AutoField(primary_key=True)
    full_name  = models.CharField(max_length=128, blank=True, null=True)
    gender = models.CharField(max_length=6, choices=GENDERS, default='m')

    birth_date = models.DateField(verbose_name="Date of birth", blank=True, null=True)
    # Making this a proper location costs money to do it through google
    birth_location = models.CharField(max_length=256, verbose_name="Location of birth", blank=True, null=True)
    death_date = models.DateField(verbose_name="Date of death", blank=True, null=True)

    father = models.ForeignKey(
        'self',
        related_name="id_of_father",
        verbose_name="Father",
        help_text="ID of their father",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    mother = models.ForeignKey(
        'self',
        related_name="id_of_mother",
        verbose_name="Mother",
        help_text="ID of their mother",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    partner = models.ForeignKey(
        'self',
        related_name="id_of_partner",
        verbose_name="Partner",
        help_text="ID of their partner through marriage or who they have had children with.",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    marriage_date = models.DateField(verbose_name="Date of Marriage", help_text="Date of Marriage with their partner.", blank=True, null=True)
    marriage_location = models.CharField(max_length=256, verbose_name="Location of marriage", blank=True, null=True)

    partner2 = models.ForeignKey(
        'self',
        related_name="id_of_partner2",
        verbose_name="Partner 2",
        help_text="ID of a second partner through marriage or who they have had children with.",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    marriage_date2 = models.DateField(verbose_name="Date of Marriage 2", help_text="Date of Marriage with their second partner.", blank=True, null=True)
    marriage_location2 = models.CharField(max_length=256, verbose_name="Location of second marriage", blank=True, null=True)

    email = models.EmailField(max_length=254, blank=True, null=True)
    phone_number = models.CharField(max_length=12, blank=True, null=True)
    profile_picture = models.FileField(upload_to="media/", max_length=1024, blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} (id:{self.id})"

    class Meta:
        ordering = ['-id']