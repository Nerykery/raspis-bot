from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from schedule_api import TimetableAPI
from storage import UserStore

log = logging.getLogger("raspis-bot.notifier")

BREAK_MINUTES = 5  # длительность перерыва
NOTIFY_BEFORE = 15  # минут до начала пары


def _hm(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


class NotificationScheduler:
    def __init__(self, bot: Bot, store: UserStore, api: TimetableAPI) -> None:
        self._bot = bot
        self._store = store
        self._api = api
        # sent: (user_id, date_iso, event_key) -> bool
        self._sent: set[tuple[int, str, str]] = set()

    async def run(self) -> None:
        """Фоновая задача — проверяет каждую минуту."""
        while True:
            try:
                await self._tick()
            except Exception:
                log.exception("Ошибка в планировщике уведомлений")
            await asyncio.sleep(60)

    async def _tick(self) -> None:
        now = datetime.now(ZoneInfo("Asia/Tomsk"))
        now_m = now.hour * 60 + now.minute
        date_str = now.date().isoformat()

        users = await self._store.get_all_users_with_notifications()
        log.info(
            "Notifier tick %s — пользователей с уведомлениями: %d",
            now.strftime("%H:%M"),
            len(users),
        )

        for user_id, group in users:
            settings = await self._store.get_notify_settings(user_id)
            try:
                lessons = await self._api.get_lessons(group, now.date())
            except Exception:
                log.exception("Не удалось получить расписание для %s", group)
                continue
            if not lessons:
                continue

            for lesson in lessons:
                start_m = _hm(lesson.start)
                end_m = _hm(lesson.end)
                break_m = start_m + 45

                # За 15 мин до начала
                if settings.get("before_start"):
                    key = f"start_{lesson.number}"
                    if self._in_window(start_m - NOTIFY_BEFORE, now_m) and (
                        user_id,
                        date_str,
                        key,
                    ) not in self._sent:
                        self._sent.add((user_id, date_str, key))
                        await self._send_before_start(user_id, lesson)

                # За 15 мин до конца
                if settings.get("before_end"):
                    key = f"end_{lesson.number}"
                    if self._in_window(end_m - NOTIFY_BEFORE, now_m) and (
                        user_id,
                        date_str,
                        key,
                    ) not in self._sent:
                        self._sent.add((user_id, date_str, key))
                        await self._send_before_end(user_id, lesson)

                # Перерыв в середине пары
                if settings.get("break") and end_m - break_m >= BREAK_MINUTES:
                    key = f"break_{lesson.number}"
                    if self._in_window(break_m, now_m) and (
                        user_id,
                        date_str,
                        key,
                    ) not in self._sent:
                        self._sent.add((user_id, date_str, key))
                        from schedule_api import _to_hhmm

                        break_end = _to_hhmm(break_m + BREAK_MINUTES)
                        await self._send_break(user_id, lesson, break_end)

    @staticmethod
    def _in_window(target: int, now: int) -> bool:
        """True если target попадает в текущую или предыдущую минуту.

        Двухминутное окно страхует от дрейфа asyncio.sleep(60).
        """
        return target in (now, now - 1)

    async def _send_before_start(self, user_id: int, lesson) -> None:
        text = (
            f"⏰  <b>Через {NOTIFY_BEFORE} минут</b> начнётся пара\n\n"
            f"📚  <b>{escape(lesson.name)}</b>\n"
        )
        if lesson.kind:
            text += f"📝  {escape(lesson.kind)}\n"
        if lesson.classroom:
            text += f"📍  {escape(lesson.classroom)}\n"
        text += f"\n🕐  {lesson.start} — {lesson.end}"
        await self._safe_send(user_id, text)

    async def _send_before_end(self, user_id: int, lesson) -> None:
        text = (
            f"⏰  <b>Через {NOTIFY_BEFORE} минут</b> пара закончится\n\n"
            f"📚  <b>{escape(lesson.name)}</b>\n"
            f"🕐  {lesson.start} — {lesson.end}"
        )
        await self._safe_send(user_id, text)

    async def _send_break(self, user_id: int, lesson, break_end: str) -> None:
        text = (
            f"☕  <b>Перерыв!</b> {BREAK_MINUTES} минут\n\n"
            f"<i>Пара продолжится в {break_end}</i>\n\n"
            f"📚  <b>{escape(lesson.name)}</b>"
        )
        await self._safe_send(user_id, text)

    async def _safe_send(self, user_id: int, text: str) -> None:
        try:
            await self._bot.send_message(user_id, text)
        except TelegramForbiddenError:
            log.info("Пользователь %s заблокировал бота", user_id)
        except TelegramBadRequest as e:
            log.warning("Ошибка отправки пользователю %s: %s", user_id, e)
        except Exception:
            log.exception("Не удалось отправить уведомление пользователю %s", user_id)
