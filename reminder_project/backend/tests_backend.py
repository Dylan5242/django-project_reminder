"""
Модульные тесты для проверки корректности ООП-бекенда (unittest).
Проверяют инкапсуляцию, валидацию, расчет сроков, репозитории и сервисы.
"""

import unittest
from datetime import date, time, datetime, timedelta
from backend.entities import Note, Reminder, Priority, ValidationError
from backend.repository import InMemoryNoteRepository, InMemoryReminderRepository, EntityNotFoundError
from backend.service import NoteService, ReminderService, TaskManager


class TestEntities(unittest.TestCase):
    """Тестирование доменных сущностей и правил валидации."""

    def test_note_creation_and_encapsulation(self):
        note = Note(item_id=1, title="Тестовая заметка", content="Текст заметки", tags=["python", "test"])
        self.assertEqual(note.id, 1)
        self.assertEqual(note.title, "Тестовая заметка")
        self.assertEqual(note.content, "Текст заметки")
        self.assertTrue(note.has_tag("python"))
        self.assertTrue(note.has_tag("test"))
        self.assertFalse(note.has_tag("django"))

    def test_note_empty_title_validation(self):
        with self.assertRaises(ValidationError):
            Note(item_id=1, title="   ", content="Пустой заголовок")

    def test_note_tag_operations(self):
        note = Note(item_id=2, title="Заметка с тегами")
        note.add_tag("DJANGO")
        self.assertIn("django", note.tags)
        note.remove_tag("django")
        self.assertNotIn("django", note.tags)

    def test_reminder_due_calculations(self):
        today = date.today()
        # Просроченное напоминание
        past_reminder = Reminder(
            item_id=10,
            title="Прошедший дедлайн",
            due_date=today - timedelta(days=2),
            priority=Priority.CRITICAL,
        )
        self.assertTrue(past_reminder.is_overdue(today))
        self.assertFalse(past_reminder.is_due_today(today))
        self.assertLess(past_reminder.days_remaining(today), 0)

        # Выполнение снимает статус просрочки
        past_reminder.mark_done()
        self.assertTrue(past_reminder.is_completed)
        self.assertFalse(past_reminder.is_overdue(today))

        # Напоминание на сегодня
        today_reminder = Reminder(
            item_id=11,
            title="Дедлайн сегодня",
            due_date=today,
            priority=Priority.HIGH,
        )
        self.assertTrue(today_reminder.is_due_today(today))
        self.assertFalse(today_reminder.is_overdue(today))
        self.assertEqual(today_reminder.days_remaining(today), 0)


class TestRepositories(unittest.TestCase):
    """Тестирование слоя репозиториев (In-Memory)."""

    def setUp(self):
        self.note_repo = InMemoryNoteRepository(seed=False)
        self.reminder_repo = InMemoryReminderRepository(seed=False)

    def test_note_repository_crud(self):
        new_note = Note(item_id=0, title="Новая заметка", content="Контент")
        saved = self.note_repo.add(new_note)
        self.assertEqual(saved.id, 1)

        fetched = self.note_repo.get_by_id(1)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Новая заметка")

        saved.title = "Обновленный заголовок"
        self.note_repo.update(saved)
        self.assertEqual(self.note_repo.get_by_id(1).title, "Обновленный заголовок")

        deleted = self.note_repo.delete(1)
        self.assertTrue(deleted)
        self.assertIsNone(self.note_repo.get_by_id(1))

    def test_update_non_existing_raises_error(self):
        fake_note = Note(item_id=999, title="Не существует")
        with self.assertRaises(EntityNotFoundError):
            self.note_repo.update(fake_note)


class TestServices(unittest.TestCase):
    """Тестирование бизнес-сценариев сервисного слоя."""

    def setUp(self):
        self.note_repo = InMemoryNoteRepository(seed=False)
        self.reminder_repo = InMemoryReminderRepository(seed=False)
        self.note_service = NoteService(self.note_repo)
        self.reminder_service = ReminderService(self.reminder_repo)

        # Добавим тестовые данные
        self.n1 = self.note_service.create_note("Заметка А", "Контент А", tags=["work"], is_pinned=False)
        self.n2 = self.note_service.create_note("Заметка Б", "Контент Б", tags=["study"], is_pinned=True)

        today = date.today()
        self.r1 = self.reminder_service.create_reminder("Задача сегодня", due_date=today, priority=Priority.HIGH)
        self.r2 = self.reminder_service.create_reminder("Задача завтра", due_date=today + timedelta(days=1), priority=Priority.LOW)
        self.r3 = self.reminder_service.create_reminder("Просроченная задача", due_date=today - timedelta(days=1), priority=Priority.CRITICAL)

    def test_list_notes_pinned_first(self):
        notes = self.note_service.list_notes(pinned_first=True)
        self.assertEqual(len(notes), 2)
        # Закрепленная заметка должна быть первой
        self.assertTrue(notes[0].is_pinned)
        self.assertEqual(notes[0].id, self.n2.id)

    def test_filter_reminders_on_date(self):
        """Проверка ключевого сценария: получение напоминаний на конкретную дату."""
        today = date.today()
        today_reminders = self.reminder_service.get_reminders_on_date(today)
        self.assertEqual(len(today_reminders), 1)
        self.assertEqual(today_reminders[0].title, "Задача сегодня")

        tomorrow = today + timedelta(days=1)
        tomorrow_reminders = self.reminder_service.get_reminders_on_date(tomorrow)
        self.assertEqual(len(tomorrow_reminders), 1)
        self.assertEqual(tomorrow_reminders[0].title, "Задача завтра")

    def test_overdue_reminders(self):
        overdue = self.reminder_service.get_overdue_reminders()
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0].title, "Просроченная задача")

    def test_toggle_completed(self):
        self.assertFalse(self.r1.is_completed)
        updated = self.reminder_service.toggle_completed(self.r1.id)
        self.assertTrue(updated.is_completed)
        reverted = self.reminder_service.toggle_completed(self.r1.id)
        self.assertFalse(reverted.is_completed)

    def test_notes_pagination(self):
        # Добавим еще заметок для проверки пагинации
        for i in range(5):
            self.note_service.create_note(f"Заметка {i+3}", f"Контент {i+3}")

        # Всего 7 заметок
        page1 = self.note_service.list_notes_paginated(page=1, page_size=3)
        self.assertEqual(len(page1["items"]), 3)
        self.assertEqual(page1["total"], 7)
        self.assertEqual(page1["total_pages"], 3)
        self.assertTrue(page1["has_more"])

        page3 = self.note_service.list_notes_paginated(page=3, page_size=3)
        self.assertEqual(len(page3["items"]), 1)
        self.assertFalse(page3["has_more"])

    def test_reminders_pagination(self):
        res = self.reminder_service.list_reminders_paginated(page=1, page_size=2)
        self.assertEqual(len(res["items"]), 2)
        self.assertEqual(res["total"], 3)
        self.assertTrue(res["has_more"])


class TestJsonRepositories(unittest.TestCase):
    """Тестирование сохранения и загрузки из постоянного JSON-хранилища."""

    def setUp(self):
        self.test_notes_file = "data/test_notes.json"
        self.test_reminders_file = "data/test_reminders.json"

    def tearDown(self):
        import os
        for f in (self.test_notes_file, self.test_reminders_file):
            if os.path.exists(f):
                os.remove(f)

    def test_json_note_repository_persistence(self):
        from backend.repository import JsonNoteRepository
        repo = JsonNoteRepository(file_path=self.test_notes_file, auto_seed=False)
        note = Note(item_id=0, title="Persistent Note", content="JSON Content", tags=["json"])
        saved = repo.add(note)
        self.assertEqual(saved.id, 1)

        # Создаем новый экземпляр репозитория, читающий тот же файл с диска
        repo2 = JsonNoteRepository(file_path=self.test_notes_file, auto_seed=False)
        loaded = repo2.get_by_id(1)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Persistent Note")
        self.assertEqual(loaded.content, "JSON Content")
        self.assertIn("json", loaded.tags)

    def test_json_reminder_repository_persistence(self):
        from backend.repository import JsonReminderRepository
        repo = JsonReminderRepository(file_path=self.test_reminders_file, auto_seed=False)
        today = date.today()
        rem = Reminder(item_id=0, title="Persistent Reminder", due_date=today, priority=Priority.HIGH)
        saved = repo.add(rem)
        self.assertEqual(saved.id, 1)

        repo2 = JsonReminderRepository(file_path=self.test_reminders_file, auto_seed=False)
        loaded = repo2.get_by_id(1)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Persistent Reminder")
        self.assertEqual(loaded.priority, Priority.HIGH)
        self.assertEqual(loaded.due_date, today)


if __name__ == "__main__":
    unittest.main()
