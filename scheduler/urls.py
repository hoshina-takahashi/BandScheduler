from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    path('', views.index, name='index'),
    path('group/<slug:slug>/', views.calendar, name='calendar'),
    path('group/<slug:slug>/input/', views.input_schedule, name='input'),  # ← 追加
]