from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    # メインタブ
    path('', views.my_calendar, name='my_calendar'),
    path('recurring/', views.recurring, name='recurring'),
    path('group/create/', views.group_create, name='group_create'),
    path('groups/', views.group_list, name='group_list'),
    path('settings/', views.user_settings, name='user_settings'),
    # グループカレンダー
    path('room/<uuid:room_id>/', views.group_calendar, name='group_calendar'),
    path('room/<uuid:room_id>/join/', views.join, name='join'),
    # API
    path('api/personal-schedule/', views.personal_schedule_api, name='personal_schedule_api'),
    path('api/personal-recurring/', views.personal_recurring_api, name='personal_recurring_api'),
    path('api/room/<uuid:room_id>/schedule/', views.schedule_save, name='schedule_save'),
    path('room/<uuid:room_id>/delete/', views.group_delete, name='group_delete'),
]
