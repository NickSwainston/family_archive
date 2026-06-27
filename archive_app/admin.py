from django.contrib import admin

from . import models


class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'father', 'mother', 'gender', 'partner', 'birth_date', 'death_date')
    search_fields = ('full_name',)
    autocomplete_fields = ('partner', 'partner2', 'mother', 'father')


admin.site.register(models.MediaFile)
admin.site.register(models.FamilyMember, FamilyMemberAdmin)
