from __future__ import annotations

import html
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp

API_BASE = "https://api.tusur.ru"
TZ = ZoneInfo("Asia/Tomsk")
CACHE_TTL = 600

WEEKDAYS = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]
MONTHS = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def today() -> date:
    return datetime.now(TZ).date()


def format_date_ru(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"


def _to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _to_hhmm(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


def short_lecturer(person: dict) -> str:
    last = (person.get("lastName") or "").strip()
    first = (person.get("firstName") or "").strip()
    middle = (person.get("middleName") or "").strip()
    initials = "".join(f"{part[0]}." for part in (first, middle) if part)
    return f"{last} {initials}".strip()


@dataclass(slots=True)
class Lesson:
    number: int
    name: str
    kind: str
    start: str
    end: str
    classroom: str
    lecturers: list[str] = field(default_factory=list)

    @property
    def break_window(self) -> tuple[str, str, int] | None:
        start = _to_minutes(self.start)
        end = _to_minutes(self.end)
        break_start = start + 45
        break_end = end - 45
        if break_end - break_start < 1:
            return None
        return _to_hhmm(break_start), _to_hhmm(break_end), break_end - break_start


def _parse_lesson(raw: dict) -> Lesson | None:
    start = raw.get("startTime") or ""
    end = raw.get("endTime") or ""
    if not start or not end:
        return None
    try:
        number = int(raw.get("number") or 0)
    except (TypeError, ValueError):
        number = 0
    return Lesson(
        number=number,
        name=html.unescape(raw.get("name") or "Без названия"),
        kind=html.unescape(raw.get("kind") or ""),
        start=start,
        end=end,
        classroom=html.unescape(raw.get("classroom") or ""),
        lecturers=[short_lecturer(p) for p in raw.get("lecturers") or []],
    )


def _parse_week(payload: dict, week_start: date) -> dict[date, list[Lesson]]:
    days = {week_start + timedelta(days=i): [] for i in range(7)}
    for entry in payload.get("data") or []:
        try:
            day = date.fromisoformat(entry.get("date") or "")
        except ValueError:
            continue
        if day not in days:
            continue
        for raw in entry.get("lessons") or []:
            lesson = _parse_lesson(raw)
            if lesson is not None:
                days[day].append(lesson)
    for lessons in days.values():
        lessons.sort(key=lambda lesson: (lesson.start, lesson.number))
    return days


class TimetableAPI:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._cache: dict[tuple[str, date], tuple[float, dict[date, list[Lesson]]]] = {}

    async def _fetch_week(
        self, group: str, week_start: date
    ) -> dict[date, list[Lesson]] | None:
        url = f"{API_BASE}/api/v1/timetable/lessons/{quote(group, safe='')}"
        params = {
            "dateFrom": week_start.isoformat(),
            "dateTo": (week_start + timedelta(days=6)).isoformat(),
        }
        async with self._session.get(url, params=params) as response:
            if response.status == 404:
                return None
            response.raise_for_status()
            payload = await response.json()
        return _parse_week(payload, week_start)

    async def get_week_lessons(
        self, group: str, day: date, *, force: bool = False
    ) -> dict[date, list[Lesson]] | None:
        week_start = day - timedelta(days=day.weekday())
        key = (group, week_start)
        cached = self._cache.get(key)
        if not force and cached and time.monotonic() - cached[0] < CACHE_TTL:
            return cached[1]

        week = await self._fetch_week(group, week_start)
        if week is None:
            return None
        self._cache[key] = (time.monotonic(), week)
        return week

    async def get_lessons(
        self, group: str, day: date, *, force: bool = False
    ) -> list[Lesson] | None:
        week = await self.get_week_lessons(group, day, force=force)
        if week is None:
            return None
        return week.get(day, [])

    async def group_exists(self, group: str) -> bool:
        lessons = await self.get_lessons(group, today())
        return lessons is not None


async def validate_group(group: str) -> bool:
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=15)
    ) as session:
        return await TimetableAPI(session).group_exists(group)
