from django import forms
from django.forms import ClearableFileInput
from django.contrib.auth.models import User

from multiupload.fields import MultiFileField

from .models import MediaFile, FamilyMember


class MediaFileForm(forms.ModelForm):
    class Meta:
        model = MediaFile
        fields = ['date_taken']
        widgets = {'date_taken': forms.DateInput(attrs={'type': 'date'})}
