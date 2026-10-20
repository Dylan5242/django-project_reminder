from django.urls import path
from . import views

urlpatterns = [
    path('notes/', views.notes_list, name='notes_list'),                   # список
    path('notes/<int:note_id>/', views.note_detail, name='note_detail'),   # одна заметка
    path('reminders/by-date/', views.reminders_by_date, name='by_date'),  # проверка на дату
]