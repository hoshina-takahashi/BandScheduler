# scheduler/admin.py
from django.contrib import admin
from .models import Room, Member, Schedule


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'room', 'created_at']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['member', 'date', 'start_time', 'end_time', 'label']
    list_filter = ['date', 'member__room']
    
    
from .models import Room, Member, Schedule, RecurringSchedule

@admin.register(RecurringSchedule)
class RecurringScheduleAdmin(admin.ModelAdmin):
    list_display = ['member', 'weekday', 'start_time', 'end_time', 'label']