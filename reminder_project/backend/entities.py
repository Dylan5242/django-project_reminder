"""
Модуль доменных сущностей (Domain Entities).
Реализует концепции ООП: инкапсуляцию, наследование, полиморфизм и строгую валидацию.
"""

from abc import ABC, abstractmethod
from datetime import datetime, date, time
from enum import Enum
from typing import List, Optional, Dict, Any


class Priority(str, Enum):
    """Перечисление уровней приоритета напоминания."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def label(self) -> str:
        labels = {
            self.LOW: "Низкий",
            self.MEDIUM: "Средний",
            self.HIGH: "Высокий",
            self.CRITICAL: "Критический",
        }
        return labels.get(self, self.value)

    @classmethod
    def from_str(cls, val: str) -> "Priority":
        val_lower = val.lower().strip()
        for member in cls:
            if member.value == val_lower or member.name.lower() == val_lower:
                return member
        return cls.MEDIUM


class ValidationError(ValueError):
    """Исключение при нарушении валидации бизнес-правил сущности."""
    pass


class BaseItem(ABC):
    """
    Абстрактный базовый класс для элементов системы (Заметка / Напоминание).
    Демонстрирует инкапсуляцию общих атрибутов и полиморфные методы.
    """

    def __init__(
        self,
        item_id: int,
        title: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self._validate_title(title)
        self._id: int = item_id
        self._title: str = title.strip()
        self._created_at: datetime = created_at or datetime.now()
        self._updated_at: datetime = updated_at or datetime.now()

    @property
    def id(self) -> int:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._validate_title(value)
        self._title = value.strip()
        self._touch()

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _touch(self) -> None:
        """Обновляет дату последнего изменения."""
        self._updated_at = datetime.now()

    @staticmethod
    def _validate_title(value: str) -> None:
        if not value or not isinstance(value, str) or not value.strip():
            raise ValidationError("Заголовок не может быть пустым.")
        if len(value.strip()) > 200:
            raise ValidationError("Длина заголовка не может превышать 200 символов.")

    @abstractmethod
    def summary(self) -> str:
        """Полиморфный метод краткой сводки элемента."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация сущности в словарь для API и шаблонов."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, title='{self.title}')>"


class Note(BaseItem):
    """
    Сущность текстовой заметки.
    Наследует BaseItem, добавляет расширенное текстовое содержимое, теги и закрепление.
    """

    def __init__(
        self,
        item_id: int,
        title: str,
        content: str = "",
        tags: Optional[List[str]] = None,
        is_pinned: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        super().__init__(item_id, title, created_at, updated_at)
        self._content: str = content
        self._tags: List[str] = [t.strip().lower() for t in (tags or []) if t and t.strip()]
        self._is_pinned: bool = is_pinned

    @property
    def content(self) -> str:
        return self._content

    @content.setter
    def content(self, value: str) -> None:
        self._content = value or ""
        self._touch()

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def is_pinned(self) -> bool:
        return self._is_pinned

    @is_pinned.setter
    def is_pinned(self, value: bool) -> None:
        self._is_pinned = bool(value)
        self._touch()

    def add_tag(self, tag: str) -> None:
        clean_tag = tag.strip().lower()
        if clean_tag and clean_tag not in self._tags:
            self._tags.append(clean_tag)
            self._touch()

    def remove_tag(self, tag: str) -> None:
        clean_tag = tag.strip().lower()
        if clean_tag in self._tags:
            self._tags.remove(clean_tag)
            self._touch()

    def has_tag(self, tag: str) -> bool:
        return tag.strip().lower() in self._tags

    def preview(self, max_length: int = 120) -> str:
        """Возвращает сжатый фрагмент содержания для списков и карточек."""
        clean = " ".join(self._content.split())
        if len(clean) <= max_length:
            return clean
        return clean[:max_length].rstrip() + "..."

    def summary(self) -> str:
        pin = "[Pinned] " if self._is_pinned else ""
        tags_str = f" (#{', #'.join(self._tags)})" if self._tags else ""
        return f"{pin}{self.title}{tags_str}: {self.preview(60)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "note",
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "preview": self.preview(),
            "tags": self.tags,
            "is_pinned": self.is_pinned,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M"),
        }


class Reminder(BaseItem):
    """
    Сущность напоминания.
    Наследует BaseItem, добавляет целевую дату, время, приоритет и статус выполнения.
    """

    def __init__(
        self,
        item_id: int,
        title: str,
        due_date: date,
        due_time: Optional[time] = None,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        is_completed: bool = False,
        completed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        super().__init__(item_id, title, created_at, updated_at)
        if not isinstance(due_date, date):
            raise ValidationError("due_date должен быть экземпляром datetime.date.")
        self._due_date: date = due_date
        self._due_time: Optional[time] = due_time
        self._description: str = description or ""
        self._priority: Priority = priority if isinstance(priority, Priority) else Priority.from_str(str(priority))
        self._is_completed: bool = is_completed
        self._completed_at: Optional[datetime] = completed_at

    @property
    def due_date(self) -> date:
        return self._due_date

    @due_date.setter
    def due_date(self, value: date) -> None:
        if not isinstance(value, date):
            raise ValidationError("due_date должен быть объектом date.")
        self._due_date = value
        self._touch()

    @property
    def due_time(self) -> Optional[time]:
        return self._due_time

    @due_time.setter
    def due_time(self, value: Optional[time]) -> None:
        self._due_time = value
        self._touch()

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value or ""
        self._touch()

    @property
    def priority(self) -> Priority:
        return self._priority

    @priority.setter
    def priority(self, value: Priority) -> None:
        self._priority = value if isinstance(value, Priority) else Priority.from_str(str(value))
        self._touch()

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def mark_done(self) -> None:
        """Отмечает напоминание как выполненное."""
        if not self._is_completed:
            self._is_completed = True
            self._completed_at = datetime.now()
            self._touch()

    def mark_undone(self) -> None:
        """Снимает отметку о выполнении."""
        if self._is_completed:
            self._is_completed = False
            self._completed_at = None
            self._touch()

    def is_overdue(self, current_date: Optional[date] = None) -> bool:
        """Проверяет, просрочено ли напоминание (если еще не выполнено)."""
        if self._is_completed:
            return False
        today = current_date or date.today()
        return self._due_date < today

    def is_due_today(self, current_date: Optional[date] = None) -> bool:
        """Проверяет, наступил ли срок сегодня."""
        today = current_date or date.today()
        return self._due_date == today

    def days_remaining(self, current_date: Optional[date] = None) -> int:
        """Возвращает число дней до срока (отрицательное число означает просрочку)."""
        today = current_date or date.today()
        return (self._due_date - today).days

    def summary(self) -> str:
        status = "[DONE]" if self._is_completed else "[ACTIVE]"
        time_str = f" {self._due_time.strftime('%H:%M')}" if self._due_time else ""
        return (
            f"{status} {self.title} (Срок: {self._due_date.strftime('%d.%m.%Y')}{time_str}, "
            f"Приоритет: {self.priority.label})"
        )

    def to_dict(self) -> Dict[str, Any]:
        time_str = self._due_time.strftime("%H:%M") if self._due_time else None
        return {
            "type": "reminder",
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat(),
            "due_date_formatted": self.due_date.strftime("%d.%m.%Y"),
            "due_time": time_str,
            "priority": self.priority.value,
            "priority_label": self.priority.label,
            "is_completed": self.is_completed,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M") if self.completed_at else None,
            "is_overdue": self.is_overdue(),
            "is_due_today": self.is_due_today(),
            "days_remaining": self.days_remaining(),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M"),
        }
