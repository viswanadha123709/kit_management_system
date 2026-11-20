from django.contrib import admin
from .models import user, kit, instrument, schedule

@admin.register(user)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_name', 'user_age', 'user_number', 'user_adhar')
    search_fields = ('user_name', 'user_number', 'user_adhar')

@admin.register(instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'instrument_name', 'brand', 'working', 'specifiations')
    list_filter = ('working', 'brand')
    search_fields = ('instrument_name', 'brand', 'specifiations')

@admin.register(kit)
class KitAdmin(admin.ModelAdmin):
    list_display = ('id', 'cost', 'items')
    search_fields = ('id',)

@admin.register(schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'kit_id', 'user_id', 'start', 'end')
    list_filter = ('start', 'end')
    search_fields = ('kit_id', 'user_id')
