# RemindMe & Notes — Python OOP Core (Standalone)

Чистое объектно-ориентированное ядро приложения заметок и напоминаний на Python с хранением данных в JSON-файлах и консольным интерфейсом (CLI).
Данный архив подготовлен без Django-интерфейса, чтобы вы могли реализовать его самостоятельно!

---

## 📁 Структура проекта

```text
├── backend/
│   ├── __init__.py           # Пакет backend
│   ├── entities.py           # Доменные сущности (BaseItem, Note, Reminder, Priority)
│   ├── repository.py         # Хранилище (JsonNoteRepository, JsonReminderRepository)
│   ├── service.py            # Сервисный слой бизнес-логики (NoteService, ReminderService, TaskManager)
│   └── tests_backend.py      # Модульные тесты (unittest)
├── data/
│   ├── notes.json            # Постоянное хранилище заметок (JSON)
│   └── reminders.json        # Постоянное хранилище напоминаний (JSON)
├── cli.py                    # Консольное приложение (CLI) с интерактивным меню и флагами
└── README.md                 # Документация и руководство
```

---

## 🚀 Запуск и использование

### 1. Запуск консольного приложения (CLI)
Интерактивный режим с текстовым меню:
```bash
python3 cli.py
```

Быстрые команды (флаги CLI):
```bash
python3 cli.py --stats                    # Сводная статистика системы
python3 cli.py --list-notes               # Вывод списка всех заметок
python3 cli.py --list-reminders           # Вывод списка всех напоминаний
python3 cli.py --check-date 2026-10-18    # Проверка напоминаний на конкретную дату
python3 cli.py --json-dump                # Полный экспорт данных в JSON
```

### 2. Запуск модульных тестов
```bash
python3 -m unittest backend/tests_backend.py -v
```

---

## 🎯 Как подключить это ядро к вашему Django-проекту

1. **Создайте проект и приложение Django:**
   ```bash
   pip install django
   django-admin startproject mynotes_project .
   python manage.py startapp notes_app
   ```

2. **Скопируйте папку `backend/` и `data/` в корень Django-проекта.**

3. **В файле `notes_app/views.py` импортируйте менеджер:**
   ```python
   from django.shortcuts import render
   from backend.service import default_manager
   from datetime import date, datetime

   # 1. Список заметок
   def notes_list(request):
       tag = request.GET.get('tag')
       search = request.GET.get('q')
       notes = default_manager.notes.list_notes(tag=tag, search=search)
       return render(request, 'notes_app/notes_list.html', {'notes': notes})

   # 2. Карточка заметки
   def note_detail(request, note_id):
       note = default_manager.notes.get_note_by_id(note_id)
       return render(request, 'notes_app/note_detail.html', {'note': note})

   # 3. Список напоминаний
   def reminders_list(request):
       status = request.GET.get('status', 'all')
       reminders = default_manager.reminders.list_reminders(status=status)
       return render(request, 'notes_app/reminders_list.html', {'reminders': reminders})

   # 4. Проверка на дату (сценарий из методички!)
   def reminders_by_date(request):
       raw_date = request.GET.get('date')
       target_date = datetime.strptime(raw_date, '%Y-%m-%d').date() if raw_date else date.today()
       reminders = default_manager.reminders.get_reminders_on_date(target_date)
       return render(request, 'notes_app/reminders_by_date.html', {
           'target_date': target_date,
           'reminders': reminders,
           'is_free': len(reminders) == 0,
       })
   ```

4. **Создайте `notes_app/urls.py` и свяжите с `mynotes_project/urls.py`.**
5. **Создайте HTML-шаблоны в `notes_app/templates/notes_app/`.**
