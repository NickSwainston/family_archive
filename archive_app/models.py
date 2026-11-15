from django.db import models
from django.conf import settings

from django.contrib.auth.models import User
from datetime import datetime

from django.core.exceptions import ValidationError


GENDERS = (
    ('m', 'male'),
    ('f', 'female'),
    # TODO will add a non-binary option when needed
)

class UploadedBy(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    date = models.DateTimeField(auto_now_add=True)


class MediaFile(models.Model):
    uploaded_by = models.ForeignKey(UploadedBy, on_delete=models.DO_NOTHING)
    date_taken = models.DateTimeField(null=True)
    media_path = models.FileField(upload_to="media/", max_length=128, null=True)

    class Meta:
        ordering = ['-id']

    @property
    def is_video(self):
        name = (self.media_path.name or "").lower()
        return name.endswith(('.mp4', '.mov', '.webm', '.avi', '.mkv', '.m4v', '.3gp'))


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


class Event(models.Model):
    """A shared family event (holiday, wedding, reunion...) shown on the timeline."""
    title = models.CharField(max_length=200)
    place = models.CharField(max_length=256, blank=True)
    start_date = models.DateField()
    # Leave blank for a single-day event
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    images = models.ManyToManyField(MediaFile, related_name='events', blank=True)
    # Optional cover photo; falls back to the first image
    cover = models.ForeignKey(MediaFile, related_name='+', on_delete=models.SET_NULL, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return f"{self.title} ({self.start_date})"

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be before the start date.'})

    @property
    def is_multi_day(self):
        return bool(self.end_date and self.end_date != self.start_date)

    def date_range_display(self):
        """Compact range, e.g. '3 Jan 2024', '3 – 9 Jan 2024', '28 Dec 2023 – 2 Jan 2024'."""
        start, end = self.start_date, self.end_date
        fmt = lambda d: f"{d.day} {d:%b %Y}"
        if not self.is_multi_day:
            return fmt(start)
        if start.year != end.year:
            return f"{fmt(start)} – {fmt(end)}"
        if start.month != end.month:
            return f"{start.day} {start:%b} – {fmt(end)}"
        return f"{start.day} – {fmt(end)}"

    def cover_image(self):
        """Cover photo, else the first non-video image attached to the event."""
        if self.cover_id:
            return self.cover
        for media in self.images.all():
            if not media.is_video:
                return media
        return None
