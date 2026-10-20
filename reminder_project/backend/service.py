"""
Сервисный слой бизнес-логики (Service Layer).
Инкапсулирует сценарии использования приложения:
1. Просмотр списка заметок и напоминаний;
2. Просмотр информации о конкретном элементе;
3. Проверка приоритета и статуса дедлайна;
4. Просмотр активных и выполненных напоминаний;
5. Проверка доступности/напоминаний на конкретную дату (ключевой сценарий из руководства).
"""

from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from backend.entities import Note, Reminder, Priority, ValidationError
from backend.repository import (
    BaseRepository,
    JsonNoteRepository,
    JsonReminderRepository,
    EntityNotFoundError,
)


class NoteService:
    """Сервис бизнес-логики работы с заметками."""

    def __init__(self, repository: BaseRepository[Note]):
        self._repo = repository

    def list_notes(
        self,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        pinned_first: bool = True,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> List[Note]:
        """Возвращает список заметок с опциональной фильтрацией, сортировкой и срезом (offset/limit)."""
        notes = self._repo.get_all()

        if tag:
            clean_tag = tag.strip().lower()
            notes = [n for n in notes if n.has_tag(clean_tag)]

        if search:
            query = search.strip().lower()
            notes = [
                n for n in notes
                if query in n.title.lower() or query in n.content.lower()
            ]

        if pinned_first:
            # Сначала закрепленные, затем по дате обновления (новые выше)
            notes.sort(key=lambda n: (not n.is_pinned, -n.updated_at.timestamp()))
        else:
            notes.sort(key=lambda n: -n.updated_at.timestamp())

        if offset > 0:
            notes = notes[offset:]
        if limit is not None:
            notes = notes[:limit]

        return notes

    def list_notes_paginated(
        self,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Возвращает порцию заметок с метаданными пагинации (для бесконечного скролла или страниц).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        all_notes = self.list_notes(tag=tag, search=search, pinned_first=True)
        total = len(all_notes)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        offset = (page - 1) * page_size
        items = all_notes[offset : offset + page_size]
        has_more = (offset + len(items)) < total

        return {
            "items": [n.to_dict() for n in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_more": has_more,
        }

    def get_note_by_id(self, note_id: int) -> Optional[Note]:
        """Возвращает заметку по ID."""
        return self._repo.get_by_id(note_id)

    def create_note(
        self,
        title: str,
        content: str = "",
        tags: Optional[List[str]] = None,
        is_pinned: bool = False,
    ) -> Note:
        """Создает и сохраняет новую заметку."""
        note = Note(
            item_id=0,
            title=title,
            content=content,
            tags=tags or [],
            is_pinned=is_pinned,
        )
        return self._repo.add(note)

    def update_note(
        self,
        note_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_pinned: Optional[bool] = None,
    ) -> Note:
        note = self._repo.get_by_id(note_id)
        if not note:
            raise EntityNotFoundError(f"Заметка #{note_id} не найдена.")

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note._tags = [t.strip().lower() for t in tags if t and t.strip()]
        if is_pinned is not None:
            note.is_pinned = is_pinned

        return self._repo.update(note)

    def delete_note(self, note_id: int) -> bool:
        return self._repo.delete(note_id)

    def get_all_tags(self) -> List[str]:
        """Возвращает уникальный список всех использованных тегов."""
        tags_set = set()
        for note in self._repo.get_all():
            tags_set.update(note.tags)
        return sorted(list(tags_set))


class ReminderService:
    """Сервис бизнес-логики работы с напоминаниями."""

    def __init__(self, repository: BaseRepository[Reminder]):
        self._repo = repository

    def list_reminders(
        self,
        status: str = "all",  # "all", "active", "completed", "overdue", "today"
        priority: Optional[Priority] = None,
        target_date: Optional[date] = None,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> List[Reminder]:
        """Возвращает отфильтрованный список напоминаний со срезом offset/limit."""
        reminders = self._repo.get_all()
        today = date.today()

        if status == "active":
            reminders = [r for r in reminders if not r.is_completed]
        elif status == "completed":
            reminders = [r for r in reminders if r.is_completed]
        elif status == "overdue":
            reminders = [r for r in reminders if r.is_overdue(today)]
        elif status == "today":
            reminders = [r for r in reminders if r.is_due_today(today)]

        if priority:
            reminders = [r for r in reminders if r.priority == priority]

        if target_date:
            reminders = [r for r in reminders if r.due_date == target_date]

        # Сортировка: сначала незавершенные по дате дедлайна, затем завершенные
        reminders.sort(key=lambda r: (r.is_completed, r.due_date, r.due_time or time(23, 59)))

        if offset > 0:
            reminders = reminders[offset:]
        if limit is not None:
            reminders = reminders[:limit]

        return reminders

    def list_reminders_paginated(
        self,
        status: str = "all",
        priority: Optional[Priority] = None,
        target_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """Возвращает порцию напоминаний с метаданными пагинации."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        all_items = self.list_reminders(status=status, priority=priority, target_date=target_date)
        total = len(all_items)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        offset = (page - 1) * page_size
        items = all_items[offset : offset + page_size]
        has_more = (offset + len(items)) < total

        return {
            "items": [r.to_dict() for r in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_more": has_more,
        }

    def get_reminder_by_id(self, reminder_id: int) -> Optional[Reminder]:
        """Возвращает напоминание по ID."""
        return self._repo.get_by_id(reminder_id)

    def get_reminders_on_date(self, target_date: date) -> List[Reminder]:
        """
        Проверка доступности/напоминаний на конкретную дату.
        Прямой аналог сценария 'проверка доступности помещения на дату' из руководства.
        """
        reminders = [r for r in self._repo.get_all() if r.due_date == target_date]
        reminders.sort(key=lambda r: (r.is_completed, r.due_time or time(23, 59)))
        return reminders

    def get_overdue_reminders(self) -> List[Reminder]:
        """Список всех невыполненных задач с прошедшим дедлайном."""
        today = date.today()
        overdue = [r for r in self._repo.get_all() if r.is_overdue(today)]
        overdue.sort(key=lambda r: (r.due_date, r.due_time or time(23, 59)))
        return overdue

    def get_today_reminders(self) -> List[Reminder]:
        """Список напоминаний на сегодняшний день."""
        today = date.today()
        today_items = [r for r in self._repo.get_all() if r.is_due_today(today)]
        today_items.sort(key=lambda r: (r.is_completed, r.due_time or time(23, 59)))
        return today_items

    def create_reminder(
        self,
        title: str,
        due_date: date,
        due_time: Optional[time] = None,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
    ) -> Reminder:
        """Создает и сохраняет новое напоминание."""
        reminder = Reminder(
            item_id=0,
            title=title,
            due_date=due_date,
            due_time=due_time,
            description=description,
            priority=priority,
            is_completed=False,
        )
        return self._repo.add(reminder)

    def toggle_completed(self, reminder_id: int) -> Reminder:
        """Переключает статус выполнения напоминания."""
        reminder = self._repo.get_by_id(reminder_id)
        if not reminder:
            raise EntityNotFoundError(f"Напоминание #{reminder_id} не найдено.")

        if reminder.is_completed:
            reminder.mark_undone()
        else:
            reminder.mark_done()

        return self._repo.update(reminder)

    def delete_reminder(self, reminder_id: int) -> bool:
        return self._repo.delete(reminder_id)


class TaskManager:
    """
    Фасадный сервис (Facade Pattern), объединяющий работу с заметками и напоминаниями.
    Предоставляет сводную статистику и удобный интерфейс для контроллеров Django и CLI.
    """

    def __init__(
        self,
        note_repo: Optional[BaseRepository[Note]] = None,
        reminder_repo: Optional[BaseRepository[Reminder]] = None,
    ):
        self.note_repo = note_repo or JsonNoteRepository("data/notes.json")
        self.reminder_repo = reminder_repo or JsonReminderRepository("data/reminders.json")
        self.notes = NoteService(self.note_repo)
        self.reminders = ReminderService(self.reminder_repo)

    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает агрегированные метрики системы для дашборда."""
        all_notes = self.note_repo.get_all()
        all_reminders = self.reminder_repo.get_all()
        today = date.today()

        active = [r for r in all_reminders if not r.is_completed]
        completed = [r for r in all_reminders if r.is_completed]
        overdue = [r for r in all_reminders if r.is_overdue(today)]
        due_today = [r for r in all_reminders if r.is_due_today(today)]

        return {
            "total_notes": len(all_notes),
            "pinned_notes": sum(1 for n in all_notes if n.is_pinned),
            "total_tags": len(self.notes.get_all_tags()),
            "total_reminders": len(all_reminders),
            "active_reminders": len(active),
            "completed_reminders": len(completed),
            "overdue_reminders": len(overdue),
            "due_today_reminders": len(due_today),
            "today_date": today.isoformat(),
            "today_formatted": today.strftime("%d.%m.%Y"),
        }

    def export_all_data(self) -> Dict[str, Any]:
        """Полный экспорт всех данных в формате сериализуемых словарей для API."""
        return {
            "statistics": self.get_statistics(),
            "notes": [n.to_dict() for n in self.notes.list_notes()],
            "reminders": [r.to_dict() for r in self.reminders.list_reminders()],
            "tags": self.notes.get_all_tags(),
        }


# Глобальный экземпляр менеджера для использования в CLI и симуляторе
default_manager = TaskManager()
