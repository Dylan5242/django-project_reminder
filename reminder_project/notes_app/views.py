from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from backend.service import default_manager
from datetime import date, datetime

# 1. Страница списка заметок
def notes_list(request):
    notes = default_manager.notes.list_notes()
    return render(request, 'notes_app/notes_list.html', {'notes': notes})

# 2. Страница детального просмотра заметки
def note_detail(request, note_id):
    note = default_manager.notes.get_note_by_id(note_id)
    return render(request, 'notes_app/note_detail.html', {'note': note})

# 3. Страница проверки напоминаний на дату (главный сценарий из методички!)
def reminders_by_date(request):
    raw_date = request.GET.get('date') # дата из формы календаря
    target_date = datetime.strptime(raw_date, '%Y-%m-%d').date() if raw_date else date.today()
    
    # Получаем дела на эту дату из сервиса
    reminders = default_manager.reminders.get_reminders_on_date(target_date)
    
    return render(request, 'notes_app/reminders_by_date.html', {
        'target_date': target_date,
        'reminders': reminders,
        'is_free': len(reminders) == 0,
    })

