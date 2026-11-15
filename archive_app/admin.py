from django.contrib import admin

from . import models


class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'father', 'mother', 'gender', 'partner', 'birth_date', 'death_date')
    search_fields = ('full_name',)
    autocomplete_fields = ('partner', 'partner2', 'mother', 'father')


admin.site.register(models.MediaFile)
admin.site.register(models.FamilyMember, FamilyMemberAdmin)


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'start_date', 'end_date', 'created_by')
    search_fields = ('title', 'place')
    filter_horizontal = ('images',)
    raw_id_fields = ('cover',)
