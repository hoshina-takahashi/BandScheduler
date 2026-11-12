# scheduler/urls.py
from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    path('', views.top, name='top'),
    path('room/create/', views.room_create, name='room_create'),
    path('room/<uuid:room_id>/', views.calendar, name='calendar'),
    path('room/<uuid:room_id>/join/', views.join, name='join'),
    path('room/<uuid:room_id>/schedule/', views.schedule_save, name='schedule_save'),
]