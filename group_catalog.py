from __future__ import annotations

import asyncio
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import aiohttp

BASE_URL = "https://timetable.tusur.ru"

FACULTIES: list[tuple[str, str]] = [
    ("iret", "Институт радиоэлектронной техники"),
    (
        "pish",
        "Передовая инженерная школа «Электронное приборостроение и системы связи»",
    ),
    ("fvs", "Факультет вычислительных систем"),
    ("fsu", "Факультет систем управления"),
    ("fit", "Факультет инновационных технологий"),
    ("ef", "Экономический факультет"),
    ("gf", "Гуманитарный факультет"),
    ("yuf", "Юридический факультет"),
    ("fb", "Факультет безопасности"),
    ("fdo", "Факультет дистанционного обучения"),
]

_ANCHOR = re.compile(
    r'href="/faculties/([a-z]+)/groups/([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
)
_GROUP_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,19}$")


def normalize_group(value: str) -> str:
    text = value.strip().lower().replace("топ", "top")
    text = re.sub(r"\s+", "", text)
    return text


def is_group_like(value: str) -> bool:
    return bool(_GROUP_RE.match(normalize_group(value)))


def group_sort_key(group: str) -> tuple[int, str]:
    match = re.match(r"(\d+)", group)
    return (int(match.group(1)) if match else 10**9, group)


class GroupCatalog:
    def __init__(self, cache_path: Path) -> None:
        self._cache_path = cache_path
        self.faculties: list[tuple[str, str, list[str]]] = []
        self._index: dict[str, str] = {}

    @property
    def all_groups(self) -> dict[str, str]:
        return self._index

    def faculty(self, key: str) -> tuple[str, str, list[str]] | None:
        for item in self.faculties:
            if item[0] == key:
                return item
        return None

    def has(self, group: str) -> bool:
        return normalize_group(group) in self._index

    def faculty_name_for(self, group: str) -> str | None:
        key = self._index.get(normalize_group(group))
        if key is None:
            return None
        faculty = self.faculty(key)
        return faculty[1] if faculty else None

    async def load(self, session: aiohttp.ClientSession) -> None:
        cached = self._read_cache()
        fetched = await self._fetch_all(session)
        if fetched:
            self._apply(fetched)
            self._write_cache(fetched)
        elif cached:
            self._apply(cached)
        else:
            self._apply([(key, name, []) for key, name in FACULTIES])

    async def _fetch_faculty(
        self, session: aiohttp.ClientSession, key: str
    ) -> list[str]:
        async with session.get(f"{BASE_URL}/faculties/{key}") as response:
            response.raise_for_status()
            text = (await response.read()).decode("utf-8", "replace")
        groups: list[str] = []
        for faculty_key, raw_group, _ in _ANCHOR.findall(text):
            if faculty_key != key:
                continue
            group = normalize_group(unquote(html.unescape(raw_group)))
            if group and group not in groups:
                groups.append(group)
        return groups

    async def _fetch_all(
        self, session: aiohttp.ClientSession
    ) -> list[tuple[str, str, list[str]]] | None:
        async def one(key: str, name: str):
            try:
                return key, name, await self._fetch_faculty(session, key)
            except Exception:  # noqa: BLE001
                return key, name, []

        results = await asyncio.gather(*(one(key, name) for key, name in FACULTIES))
        if not any(groups for _, _, groups in results):
            return None
        return list(results)

    def _apply(self, faculties: list[tuple[str, str, list[str]]]) -> None:
        self.faculties = []
        self._index = {}
        for key, name, groups in faculties:
            sorted_groups = sorted(dict.fromkeys(groups), key=group_sort_key)
            self.faculties.append((key, name, sorted_groups))
            for group in sorted_groups:
                self._index[group] = key

    def _read_cache(self) -> list[tuple[str, str, list[str]]] | None:
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            faculties = [
                (item["key"], item["name"], list(item.get("groups") or []))
                for item in payload["faculties"]
            ]
            return faculties or None
        except Exception:  # noqa: BLE001
            return None

    def _write_cache(self, faculties: list[tuple[str, str, list[str]]]) -> None:
        payload = {
            "fetched_at": int(time.time()),
            "faculties": [
                {"key": key, "name": name, "groups": groups}
                for key, name, groups in faculties
            ],
        }
        tmp = self._cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self._cache_path)


def validate_format(value: str) -> str | None:
    group = normalize_group(value)
    return group if _GROUP_RE.match(group) else None
