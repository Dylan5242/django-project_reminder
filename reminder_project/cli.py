#!/usr/bin/env python3
"""
Консольное приложение (CLI) для заметок и напоминаний.
Реализует основные сценарии работы с системой в терминале:
1. Просмотр списка заметок
2. Просмотр информации о конкретной заметке
3. Просмотр списка напоминаний
4. Просмотр информации о конкретном напоминании
5. Проверка напоминаний на конкретную дату (сценарий проверки доступности на дату)
6. Просмотр просроченных напоминаний и приоритетов
7. Запуск unit-тестов
"""

import sys
import json
import argparse
import unittest
from datetime import date, datetime
from typing import Optional

from backend.entities import Priority, ValidationError
from backend.service import default_manager, TaskManager
from backend.repository import EntityNotFoundError


def print_banner():
    print("=" * 65)
    print("      RemindMe & Notes CLI — Python OOP Backend Console      ")
    print("=" * 65)


def display_menu():
    print("\n[ Основное меню ]")
    print("  1. Просмотреть список заметок")
    print("  2. Подробная информация о заметке (по ID)")
    print("  3. Просмотреть список всех напоминаний")
    print("  4. Подробная информация о напоминании (по ID)")
    print("  5. Проверить напоминания на дату (сценарий доступности на дату)")
    print("  6. Список просроченных и срочных напоминаний")
    print("  7. Сводная статистика системы")
    print("  8. Добавить новую заметку")
    print("  9. Добавить новое напоминание")
    print(" 10. Переключить статус выполнения напоминания")
    print(" 11. Запустить автоматические unit-тесты")
    print("  0. Выход")


def handle_list_notes(manager: TaskManager):
    print("\n--- Список заметок ---")
    tag_filter = input("Фильтр по тегу (Enter для пропуска): ").strip() or None
    search_query = input("Поиск по тексту (Enter для пропуска): ").strip() or None

    notes = manager.notes.list_notes(tag=tag_filter, search=search_query)
    if not notes:
        print("Заметки не найдены.")
        return

    print(f"\nНайдено заметок: {len(notes)}")
    print("-" * 65)
    for note in notes:
        pin = "[Pin] " if note.is_pinned else "      "
        tags = f" (#{', #'.join(note.tags)})" if note.tags else ""
        print(f"{pin}#{note.id:<2} | {note.title}{tags}")
        print(f"       {note.preview(80)}")
        print(f"       Обновлено: {note.updated_at.strftime('%Y-%m-%d %H:%M')}")
        print("-" * 65)


def handle_view_note(manager: TaskManager):
    print("\n--- Просмотр заметки ---")
    raw_id = input("Введите ID заметки: ").strip()
    if not raw_id.isdigit():
        print("Ошибка: ID должен быть числом.")
        return

    note = manager.notes.get_note_by_id(int(raw_id))
    if not note:
        print(f"Заметка с ID #{raw_id} не найдена.")
        return

    print("\n" + "=" * 50)
    print(f"Заметка #{note.id}: {note.title}")
    if note.is_pinned:
        print("[!] Закрепленная заметка")
    print(f"Теги: {', '.join(note.tags) if note.tags else 'нет'}")
    print(f"Создано: {note.created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"Обновлено: {note.updated_at.strftime('%Y-%m-%d %H:%M')}")
    print("-" * 50)
    print("Содержимое:")
    print(note.content if note.content else "(нет текста)")
    print("=" * 50)


def handle_list_reminders(manager: TaskManager):
    print("\n--- Список напоминаний ---")
    print("Фильтры статуса: [1] Все, [2] Только активные, [3] Выполненные, [4] На сегодня")
    choice = input("Выберите вариант (Enter для всех): ").strip()
    status_map = {"1": "all", "2": "active", "3": "completed", "4": "today"}
    status = status_map.get(choice, "all")

    reminders = manager.reminders.list_reminders(status=status)
    if not reminders:
        print("Напоминания не найдены.")
        return

    print(f"\nНайдено напоминаний: {len(reminders)}")
    print("-" * 75)
    for r in reminders:
        status_box = "[V]" if r.is_completed else "[ ]"
        overdue_badge = " [ПРОСРОЧЕНО]" if r.is_overdue() else ""
        time_str = f" {r.due_time.strftime('%H:%M')}" if r.due_time else ""
        print(f"{status_box} #{r.id:<2} | {r.title}{overdue_badge}")
        print(f"      Срок: {r.due_date.strftime('%d.%m.%Y')}{time_str} | Приоритет: {r.priority.label}")
        if r.description:
            print(f"      Описание: {r.description}")
        print("-" * 75)


def handle_view_reminder(manager: TaskManager):
    print("\n--- Просмотр напоминания ---")
    raw_id = input("Введите ID напоминания: ").strip()
    if not raw_id.isdigit():
        print("Ошибка: ID должен быть числом.")
        return

    r = manager.reminders.get_reminder_by_id(int(raw_id))
    if not r:
        print(f"Напоминание с ID #{raw_id} не найдено.")
        return

    print("\n" + "=" * 55)
    print(f"Напоминание #{r.id}: {r.title}")
    status = "Выполнено" if r.is_completed else ("Просрочено" if r.is_overdue() else "Активно")
    print(f"Статус:      {status}")
    print(f"Приоритет:   {r.priority.label} ({r.priority.value})")
    time_str = f" в {r.due_time.strftime('%H:%M')}" if r.due_time else ""
    print(f"Дедлайн:     {r.due_date.strftime('%d.%m.%Y')}{time_str}")
    days = r.days_remaining()
    if not r.is_completed:
        if days < 0:
            print(f"Просрочка:   {-days} дн. назад")
        elif days == 0:
            print("Срок:        СЕГОДНЯ")
        else:
            print(f"Осталось:    {days} дн.")
    print(f"Описание:    {r.description or '(нет описания)'}")
    print(f"Создано:     {r.created_at.strftime('%Y-%m-%d %H:%M')}")
    if r.completed_at:
        print(f"Завершено:   {r.completed_at.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)


def handle_check_reminders_on_date(manager: TaskManager):
    """
    Аналог сценария из методички: 'проверка доступности помещения на дату'.
    Показывает, какие задачи/напоминания запланированы на выбранный день.
    """
    print("\n--- Проверка напоминаний на выбранную дату ---")
    today_str = date.today().isoformat()
    raw_date = input(f"Введите дату в формате ГГГГ-ММ-ДД (Enter для сегодня: {today_str}): ").strip()
    target_date_str = raw_date if raw_date else today_str

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        print("Ошибка: неверный формат даты. Используйте ГГГГ-ММ-ДД (например, 2026-10-18).")
        return

    reminders = manager.reminders.get_reminders_on_date(target_date)
    print(f"\nНапоминания на дату: {target_date.strftime('%d.%m.%Y')} ({len(reminders)} шт.):")
    if not reminders:
        print("На эту дату запланированных напоминаний нет (день свободен).")
        return

    print("-" * 65)
    for r in reminders:
        status = "[Выполнено]" if r.is_completed else "[Активно]"
        time_str = r.due_time.strftime("%H:%M") if r.due_time else "весь день"
        print(f"{status} #{r.id} ({time_str}): {r.title} [Приоритет: {r.priority.label}]")
    print("-" * 65)


def handle_overdue_and_urgent(manager: TaskManager):
    print("\n--- Просроченные и срочные напоминания ---")
    overdue = manager.reminders.get_overdue_reminders()
    today_items = manager.reminders.get_today_reminders()

    print(f"\n[!] Просроченные задачи ({len(overdue)}):")
    if overdue:
        for r in overdue:
            days = -r.days_remaining()
            print(f" - #{r.id} {r.title} (просрочено на {days} дн., дедлайн был {r.due_date.strftime('%d.%m.%Y')})")
    else:
        print(" Отлично! Просроченных задач нет.")

    print(f"\n[*] Срочно на сегодня ({len(today_items)}):")
    if today_items:
        for r in today_items:
            status = " [Выполнено]" if r.is_completed else ""
            print(f" - #{r.id} {r.title}{status} [Приоритет: {r.priority.label}]")
    else:
        print(" На сегодня задач не запланировано.")


def handle_statistics(manager: TaskManager):
    print("\n--- Сводная статистика системы ---")
    stats = manager.get_statistics()
    print(f"Сегодняшняя дата:          {stats['today_formatted']}")
    print(f"Всего заметок:             {stats['total_notes']} (закрепленных: {stats['pinned_notes']})")
    print(f"Используемых тегов:        {stats['total_tags']}")
    print(f"Всего напоминаний:         {stats['total_reminders']}")
    print(f"  - Активных:              {stats['active_reminders']}")
    print(f"  - Завершенных:           {stats['completed_reminders']}")
    print(f"  - На сегодня:            {stats['due_today_reminders']}")
    print(f"  - Просроченных:          {stats['overdue_reminders']}")


def handle_add_note(manager: TaskManager):
    print("\n--- Добавление новой заметки ---")
    try:
        title = input("Заголовок заметки: ").strip()
        content = input("Текст заметки: ").strip()
        tags_raw = input("Теги через запятую (например: python, study): ").strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        is_pin = input("Закрепить заметку? (y/N): ").strip().lower() == "y"

        new_note = manager.notes.create_note(title=title, content=content, tags=tags, is_pinned=is_pin)
        print(f"\n[Успех] Заметка #{new_note.id} '{new_note.title}' успешно сохранена!")
    except ValidationError as e:
        print(f"\n[Ошибка валидации] {e}")


def handle_add_reminder(manager: TaskManager):
    print("\n--- Добавление нового напоминания ---")
    try:
        title = input("Заголовок напоминания: ").strip()
        date_raw = input("Дата дедлайна (ГГГГ-ММ-ДД, например 2026-10-25): ").strip()
        due_date = datetime.strptime(date_raw, "%Y-%m-%d").date()

        time_raw = input("Время (ЧЧ:ММ, например 15:30, Enter если не требуется): ").strip()
        due_time = datetime.strptime(time_raw, "%H:%M").time() if time_raw else None

        desc = input("Дополнительное описание (Enter для пропуска): ").strip()
        print("Приоритеты: 1. low, 2. medium, 3. high, 4. critical")
        prio_choice = input("Выберите приоритет (1-4, по умолчанию 2): ").strip()
        prio_map = {"1": Priority.LOW, "2": Priority.MEDIUM, "3": Priority.HIGH, "4": Priority.CRITICAL}
        priority = prio_map.get(prio_choice, Priority.MEDIUM)

        new_rem = manager.reminders.create_reminder(
            title=title,
            due_date=due_date,
            due_time=due_time,
            description=desc,
            priority=priority,
        )
        print(f"\n[Успех] Напоминание #{new_rem.id} '{new_rem.title}' добавлено на {new_rem.due_date.strftime('%d.%m.%Y')}!")
    except (ValueError, ValidationError) as e:
        print(f"\n[Ошибка] Некорректный ввод: {e}")


def handle_toggle_reminder(manager: TaskManager):
    print("\n--- Переключение статуса выполнения ---")
    raw_id = input("Введите ID напоминания: ").strip()
    if not raw_id.isdigit():
        print("Ошибка: ID должен быть числом.")
        return

    try:
        rem = manager.reminders.toggle_completed(int(raw_id))
        status_text = "ВЫПОЛНЕНО" if rem.is_completed else "ВОЗВРАЩЕНО В АКТИВНЫЕ"
        print(f"[Успех] Напоминание #{rem.id} теперь: {status_text}")
    except EntityNotFoundError as e:
        print(f"[Ошибка] {e}")


def handle_run_tests():
    print("\n--- Запуск модульных тестов unittest ---")
    loader = unittest.TestLoader()
    suite = loader.discover("backend", pattern="tests_backend.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n[OK] Все модульные тесты успешно пройдены!")
    else:
        print(f"\n[FAIL] Ошибок: {len(result.errors)}, сбоев: {len(result.failures)}")


def run_interactive():
    print_banner()
    manager = default_manager

    while True:
        display_menu()
        choice = input("\nВыберите действие (0-11): ").strip()
        if choice == "1":
            handle_list_notes(manager)
        elif choice == "2":
            handle_view_note(manager)
        elif choice == "3":
            handle_list_reminders(manager)
        elif choice == "4":
            handle_view_reminder(manager)
        elif choice == "5":
            handle_check_reminders_on_date(manager)
        elif choice == "6":
            handle_overdue_and_urgent(manager)
        elif choice == "7":
            handle_statistics(manager)
        elif choice == "8":
            handle_add_note(manager)
        elif choice == "9":
            handle_add_reminder(manager)
        elif choice == "10":
            handle_toggle_reminder(manager)
        elif choice == "11":
            handle_run_tests()
        elif choice == "0":
            print("\nВыход из программы. До свидания!")
            break
        else:
            print("Неверный выбор. Пожалуйста, введите цифру от 0 до 11.")


def parse_cli_args():
    parser = argparse.ArgumentParser(description="RemindMe & Notes Python OOP Backend CLI")
    parser.add_argument("--json-dump", action="store_true", help="Экспорт всех данных в формате JSON")
    parser.add_argument("--notes-json", action="store_true", help="Порция заметок в JSON с учетом --page и --limit")
    parser.add_argument("--reminders-json", action="store_true", help="Порция напоминаний в JSON с учетом --page и --limit")
    parser.add_argument("--page", type=int, default=1, help="Номер страницы (по умолчанию 1)")
    parser.add_argument("--limit", type=int, default=10, help="Размер страницы/порции (по умолчанию 10)")
    parser.add_argument("--tag", type=str, default=None, help="Фильтр заметок по тегу")
    parser.add_argument("--status", type=str, default="all", help="Фильтр напоминаний (all, active, today, overdue, completed)")
    parser.add_argument("--list-notes", action="store_true", help="Вывод списка всех заметок")
    parser.add_argument("--list-reminders", action="store_true", help="Вывод списка всех напоминаний")
    parser.add_argument("--check-date", type=str, help="Проверка напоминаний на дату (ГГГГ-ММ-ДД)")
    parser.add_argument("--stats", action="store_true", help="Сводная статистика")
    parser.add_argument("--run-tests", action="store_true", help="Запуск модульных тестов")
    return parser.parse_args()


def main():
    args = parse_cli_args()
    manager = default_manager

    if args.json_dump:
        print(json.dumps(manager.export_all_data(), ensure_ascii=False, indent=2))
        return

    if args.notes_json:
        data = manager.notes.list_notes_paginated(tag=args.tag, page=args.page, page_size=args.limit)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if args.reminders_json:
        data = manager.reminders.list_reminders_paginated(status=args.status, page=args.page, page_size=args.limit)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if args.list_notes:
        notes = manager.notes.list_notes(tag=args.tag, limit=args.limit)
        for n in notes:
            print(f"#{n.id} {n.title} [Tags: {', '.join(n.tags)}]")
        return

    if args.list_reminders:
        reminders = manager.reminders.list_reminders(status=args.status, limit=args.limit)
        for r in reminders:
            status = "DONE" if r.is_completed else "ACTIVE"
            print(f"#{r.id} [{status}] {r.title} (due {r.due_date})")
        return

    if args.check_date:
        try:
            d = datetime.strptime(args.check_date, "%Y-%m-%d").date()
            items = manager.reminders.get_reminders_on_date(d)
            print(f"На дату {args.check_date} найдено {len(items)} напоминаний:")
            for item in items:
                print(f"  #{item.id} {item.title} (приоритет: {item.priority.label})")
        except ValueError:
            print(f"Неверный формат даты: {args.check_date}")
            sys.exit(1)
        return

    if args.stats:
        print(json.dumps(manager.get_statistics(), ensure_ascii=False, indent=2))
        return

    if args.run_tests:
        handle_run_tests()
        return

    # Если параметров нет, запускаем интерактивный режим
    run_interactive()


if __name__ == "__main__":
    main()
