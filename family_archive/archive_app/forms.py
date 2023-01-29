from django import forms
from django.forms import ClearableFileInput
from .models import MediaFile


class MediaFileForm(forms.ModelForm):
    class Meta:
        model = MediaFile
        fields = ['media_path']
        widgets = {
            'media_path': ClearableFileInput(attrs={'multiple': True}),
        }