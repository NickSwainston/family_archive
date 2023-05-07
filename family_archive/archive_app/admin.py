from django.contrib import admin

from . import models
from django.db import models as django_models


class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'partner', 'partner2')
    search_fields = ('full_name',)
    autocomplete_fields = ('partner', 'partner2', 'mother', 'father')


admin.site.register(models.MediaFile)
admin.site.register(models.FamilyMember, FamilyMemberAdmin)
