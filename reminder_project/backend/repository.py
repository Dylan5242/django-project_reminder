"""
Модуль абстракции хранилища (Repository Pattern).
Реализует постоянное хранение данных в формате JSON (data/notes.json и data/reminders.json),
а также базовые in-memory реализации для тестов.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import date, time, datetime, timedelta
from typing import List, Optional, Dict, Generic, TypeVar, Any
from backend.entities import Note, Reminder, Priority, BaseItem

T = TypeVar("T", bound=BaseItem)


class EntityNotFoundError(Exception):
    """Исключение, если объект с указанным идентификатором не найден."""
    pass


class BaseRepository(ABC, Generic[T]):
    """Абстрактный интерфейс репозитория (CRUD-операции)."""

    @abstractmethod
    def get_all(self) -> List[T]:
        """Возвращает список всех элементов."""
        pass

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[T]:
        """Возвращает элемент по идентификатору либо None."""
        pass

    @abstractmethod
    def add(self, item: T) -> T:
        """Сохраняет новый элемент и присваивает уникальный ID."""
        pass

    @abstractmethod
    def update(self, item: T) -> T:
        """Обновляет существующий элемент."""
        pass

    @abstractmethod
    def delete(self, item_id: int) -> bool:
        """Удаляет элемент по ID. Возвращает True при успехе."""
        pass


class JsonNoteRepository(BaseRepository[Note]):
    """
    Репозиторий заметок с постоянным хранением в JSON-файле.
    """

    def __init__(self, file_path: str = "data/notes.json", auto_seed: bool = True):
        self._file_path = file_path
        self._storage: Dict[int, Note] = {}
        self._next_id: int = 1
        self._ensure_storage(auto_seed)

    def _ensure_storage(self, auto_seed: bool) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self._file_path)), exist_ok=True)
        if os.path.exists(self._file_path) and os.path.getsize(self._file_path) > 0:
            self._load_from_file()
        elif auto_seed:
            self._seed_default_data()
            self._save_to_file()
        else:
            self._save_to_file()

    def _load_from_file(self) -> None:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            self._storage.clear()
            max_id = 0
            for raw in items:
                created_at = (
                    datetime.fromisoformat(raw["created_at"])
                    if "created_at" in raw and raw["created_at"]
                    else datetime.now()
                )
                updated_at = (
                    datetime.fromisoformat(raw["updated_at"])
                    if "updated_at" in raw and raw["updated_at"]
                    else datetime.now()
                )
                note = Note(
                    item_id=raw["id"],
                    title=raw["title"],
                    content=raw.get("content", ""),
                    tags=raw.get("tags", []),
                    is_pinned=raw.get("is_pinned", False),
                    created_at=created_at,
                    updated_at=updated_at,
                )
                self._storage[note.id] = note
                if note.id > max_id:
                    max_id = note.id
            self._next_id = max_id + 1
        except Exception as e:
            print(f"[Warning] Ошибка чтения {self._file_path}: {e}")

    def _save_to_file(self) -> None:
        data = []
        for note in self._storage.values():
            data.append({
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "tags": note.tags,
                "is_pinned": note.is_pinned,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
            })
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[Note]:
        return list(self._storage.values())

    def get_by_id(self, item_id: int) -> Optional[Note]:
        return self._storage.get(item_id)

    def add(self, item: Note) -> Note:
        new_id = self._next_id
        self._next_id += 1
        item._id = new_id
        self._storage[new_id] = item
        self._save_to_file()
        return item

    def update(self, item: Note) -> Note:
        if item.id not in self._storage:
            raise EntityNotFoundError(f"Заметка с id={item.id} не найдена.")
        item._touch()
        self._storage[item.id] = item
        self._save_to_file()
        return item

    def delete(self, item_id: int) -> bool:
        if item_id in self._storage:
            del self._storage[item_id]
            self._save_to_file()
            return True
        return False

    def _seed_default_data(self) -> None:
        sample_notes = [
            Note(
                item_id=1,
                title="Архитектура Roomly и переход к Django",
                content=(
                    "Согласно методическому пособию, сначала определяем сценарии консольного "
                    "приложения, которые получат веб-представление: просмотр списков, карточки, "
                    "выборка по дате. На первом этапе реализуем только отображение данных, "
                    "а формы добавления и редактирования добавим после изучения моделей Django."
                ),
                tags=["django", "architecture", "study"],
                is_pinned=True,
                created_at=datetime.now() - timedelta(days=2),
            ),
            Note(
                item_id=2,
                title="Паттерны ООП в Python: Entities и Repositories",
                content=(
                    "Разделение ответственности (SoC): сущности инкапсулируют бизнес-правила "
                    "и валидацию полей. Репозитории абстрагируют доступ к хранилищу (JSON-файлы, "
                    "в памяти, либо Django ORM). Сервисный слой содержит бизнес-сценарии."
                ),
                tags=["python", "oop", "patterns"],
                is_pinned=True,
                created_at=datetime.now() - timedelta(days=1),
            ),
            Note(
                item_id=3,
                title="Полезные команды Django CLI",
                content=(
                    "Создание проекта: django-admin startproject myproject .\n"
                    "Создание приложения: python manage.py startapp notes_app\n"
                    "Запуск dev-сервера: python manage.py runserver\n"
                    "Создание миграций: python manage.py makemigrations\n"
                    "Применение миграций: python manage.py migrate"
                ),
                tags=["django", "cli", "cheat-sheet"],
                is_pinned=False,
                created_at=datetime.now() - timedelta(hours=5),
            ),
            Note(
                item_id=4,
                title="Идеи для расширения системы напоминаний",
                content=(
                    "1. Добавить отправку email-уведомлений через celery/cron.\n"
                    "2. Реализовать категории заметок с цветовым кодированием.\n"
                    "3. Полнотекстовый поиск по содержимому заметок."
                ),
                tags=["ideas", "roadmap"],
                is_pinned=False,
                created_at=datetime.now() - timedelta(hours=2),
            ),
        ]
        for note in sample_notes:
            self._storage[note.id] = note
            if note.id >= self._next_id:
                self._next_id = note.id + 1


class JsonReminderRepository(BaseRepository[Reminder]):
    """
    Репозиторий напоминаний с постоянным хранением в JSON-файле.
    """

    def __init__(self, file_path: str = "data/reminders.json", auto_seed: bool = True):
        self._file_path = file_path
        self._storage: Dict[int, Reminder] = {}
        self._next_id: int = 1
        self._ensure_storage(auto_seed)

    def _ensure_storage(self, auto_seed: bool) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self._file_path)), exist_ok=True)
        if os.path.exists(self._file_path) and os.path.getsize(self._file_path) > 0:
            self._load_from_file()
        elif auto_seed:
            self._seed_default_data()
            self._save_to_file()
        else:
            self._save_to_file()

    def _load_from_file(self) -> None:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            self._storage.clear()
            max_id = 0
            for raw in items:
                due_date = date.fromisoformat(raw["due_date"])
                due_time = time.fromisoformat(raw["due_time"]) if raw.get("due_time") else None
                priority = Priority.from_str(raw.get("priority", "medium"))
                created_at = (
                    datetime.fromisoformat(raw["created_at"])
                    if "created_at" in raw and raw["created_at"]
                    else datetime.now()
                )
                updated_at = (
                    datetime.fromisoformat(raw["updated_at"])
                    if "updated_at" in raw and raw["updated_at"]
                    else datetime.now()
                )
                completed_at = (
                    datetime.fromisoformat(raw["completed_at"])
                    if raw.get("completed_at")
                    else None
                )

                reminder = Reminder(
                    item_id=raw["id"],
                    title=raw["title"],
                    due_date=due_date,
                    due_time=due_time,
                    description=raw.get("description", ""),
                    priority=priority,
                    is_completed=raw.get("is_completed", False),
                    completed_at=completed_at,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                self._storage[reminder.id] = reminder
                if reminder.id > max_id:
                    max_id = reminder.id
            self._next_id = max_id + 1
        except Exception as e:
            print(f"[Warning] Ошибка чтения {self._file_path}: {e}")

    def _save_to_file(self) -> None:
        data = []
        for r in self._storage.values():
            data.append({
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "due_date": r.due_date.isoformat(),
                "due_time": r.due_time.isoformat() if r.due_time else None,
                "priority": r.priority.value,
                "is_completed": r.is_completed,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            })
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[Reminder]:
        return list(self._storage.values())

    def get_by_id(self, item_id: int) -> Optional[Reminder]:
        return self._storage.get(item_id)

    def add(self, item: Reminder) -> Reminder:
        new_id = self._next_id
        self._next_id += 1
        item._id = new_id
        self._storage[new_id] = item
        self._save_to_file()
        return item

    def update(self, item: Reminder) -> Reminder:
        if item.id not in self._storage:
            raise EntityNotFoundError(f"Напоминание с id={item.id} не найдено.")
        item._touch()
        self._storage[item.id] = item
        self._save_to_file()
        return item

    def delete(self, item_id: int) -> bool:
        if item_id in self._storage:
            del self._storage[item_id]
            self._save_to_file()
            return True
        return False

    def _seed_default_data(self) -> None:
        today = date.today()
        sample_reminders = [
            Reminder(
                item_id=1,
                title="Сдать лабораторную работу по ООП Python",
                due_date=today - timedelta(days=1),
                due_time=time(18, 0),
                description="Подготовить демонстрацию классов сущностей, наследования и репозитория.",
                priority=Priority.CRITICAL,
                is_completed=False,
                created_at=datetime.now() - timedelta(days=4),
            ),
            Reminder(
                item_id=2,
                title="Прочитать раздел руководства по маршрутам Django (urls.py)",
                due_date=today,
                due_time=time(14, 30),
                description="Разобрать path(), include(), а также связывание URL с функциями представлений views.py.",
                priority=Priority.HIGH,
                is_completed=False,
                created_at=datetime.now() - timedelta(days=2),
            ),
            Reminder(
                item_id=3,
                title="Проверить отображение HTML-шаблона для списка заметок",
                due_date=today,
                due_time=time(20, 0),
                description="Убедиться, что теги Jinja/Django {% for item in notes %} корректно выводят карточки.",
                priority=Priority.MEDIUM,
                is_completed=False,
                created_at=datetime.now() - timedelta(days=1),
            ),
            Reminder(
                item_id=4,
                title="Написать модульные тесты для сервисного слоя",
                due_date=today + timedelta(days=1),
                due_time=time(12, 0),
                description="Протестировать фильтрацию по датам и расчет просроченных напоминаний через unittest.",
                priority=Priority.HIGH,
                is_completed=False,
                created_at=datetime.now() - timedelta(hours=10),
            ),
            Reminder(
                item_id=5,
                title="Изучить создание Django Models и механизм миграций",
                due_date=today + timedelta(days=3),
                due_time=time(10, 0),
                description="Следующий модуль курса: преобразование Python классов в django.db.models.Model.",
                priority=Priority.MEDIUM,
                is_completed=False,
                created_at=datetime.now() - timedelta(hours=8),
            ),
            Reminder(
                item_id=6,
                title="Установить виртуальное окружение venv и пакет django",
                due_date=today - timedelta(days=3),
                due_time=time(11, 0),
                description="Выполнено: создан venv, проверена версия Django 5.x.",
                priority=Priority.LOW,
                is_completed=True,
                completed_at=datetime.now() - timedelta(days=2),
                created_at=datetime.now() - timedelta(days=4),
            ),
        ]
        for reminder in sample_reminders:
            self._storage[reminder.id] = reminder
            if reminder.id >= self._next_id:
                self._next_id = reminder.id + 1


class InMemoryNoteRepository(BaseRepository[Note]):
    """Реализация репозитория заметок в оперативной памяти (для быстрых тестов без диска)."""

    def __init__(self, seed: bool = True):
        self._storage: Dict[int, Note] = {}
        self._next_id: int = 1
        if seed:
            self._seed_default_data()

    def get_all(self) -> List[Note]:
        return list(self._storage.values())

    def get_by_id(self, item_id: int) -> Optional[Note]:
        return self._storage.get(item_id)

    def add(self, item: Note) -> Note:
        new_id = self._next_id
        self._next_id += 1
        item._id = new_id
        self._storage[new_id] = item
        return item

    def update(self, item: Note) -> Note:
        if item.id not in self._storage:
            raise EntityNotFoundError(f"Заметка с id={item.id} не найдена.")
        item._touch()
        self._storage[item.id] = item
        return item

    def delete(self, item_id: int) -> bool:
        if item_id in self._storage:
            del self._storage[item_id]
            return True
        return False

    def _seed_default_data(self) -> None:
        note = Note(item_id=1, title="Тестовая заметка", content="Контент в памяти")
        self._storage[1] = note
        self._next_id = 2


class InMemoryReminderRepository(BaseRepository[Reminder]):
    """Реализация репозитория напоминаний в оперативной памяти."""

    def __init__(self, seed: bool = True):
        self._storage: Dict[int, Reminder] = {}
        self._next_id: int = 1
        if seed:
            self._seed_default_data()

    def get_all(self) -> List[Reminder]:
        return list(self._storage.values())

    def get_by_id(self, item_id: int) -> Optional[Reminder]:
        return self._storage.get(item_id)

    def add(self, item: Reminder) -> Reminder:
        new_id = self._next_id
        self._next_id += 1
        item._id = new_id
        self._storage[new_id] = item
        return item

    def update(self, item: Reminder) -> Reminder:
        if item.id not in self._storage:
            raise EntityNotFoundError(f"Напоминание с id={item.id} не найдено.")
        item._touch()
        self._storage[item.id] = item
        return item

    def delete(self, item_id: int) -> bool:
        if item_id in self._storage:
            del self._storage[item_id]
            return True
        return False

    def _seed_default_data(self) -> None:
        rem = Reminder(item_id=1, title="Тестовое напоминание", due_date=date.today())
        self._storage[1] = rem
        self._next_id = 2

