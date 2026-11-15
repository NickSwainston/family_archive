from django import forms
from django.forms import ClearableFileInput
from django.contrib.auth.models import User

from multiupload.fields import MultiFileField

from .models import MediaFile, FamilyMember, Event


class MediaFileForm(forms.ModelForm):
    class Meta:
        model = MediaFile
        fields = ['date_taken']
        widgets = {
            'date_taken': forms.DateInput(attrs={
                'type': 'text',
                'placeholder': 'Pick a date…',
                'class': 'datepicker',
                'autocomplete': 'off',
            })
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'place', 'start_date', 'end_date', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'end_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {'end_date': 'End date (optional)'}
        help_texts = {'end_date': 'Leave blank for a single-day event.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Native date inputs need ISO format, regardless of the site-wide DATE_INPUT_FORMATS
        for name in ('start_date', 'end_date'):
            self.fields[name].input_formats = ['%Y-%m-%d']
