from django import forms
from django.forms import ClearableFileInput
from django.contrib.auth.models import User

from multiupload.fields import MultiFileField

from .models import MediaFile, FamilyMember


class MediaFileForm(forms.ModelForm):

    media_path = MultiFileField(min_num=1, max_num=3, max_file_size=1024*1024*5)

    def save(self, commit=True):
        instance = super(MediaFile, self).save(commit)

        # Grab user id
        user_id = self.cleaned_data['user']
        user = User.objects.get(id=user_id)

        # Save each file
        for each in self.cleaned_data['files']:
            MediaFile.objects.create(file=each, message=instance)

        return instance
    class Meta:
        model = MediaFile
        fields = ['media_path']
