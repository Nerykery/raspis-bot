from __future__ import annotations

import asyncio
import json
from pathlib import Path


class UserStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._users: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._users = {
                str(user_id): dict(data)
                for user_id, data in (payload.get("users") or {}).items()
            }
        except Exception:
            self._users = {}

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"users": self._users}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    async def get_group(self, user_id: int) -> str | None:
        async with self._lock:
            return self._users.get(str(user_id), {}).get("group")

    async def set_group(self, user_id: int, group: str) -> None:
        async with self._lock:
            self._users.setdefault(str(user_id), {})["group"] = group
            self._flush()

    async def clear_group(self, user_id: int) -> None:
        async with self._lock:
            user = self._users.get(str(user_id))
            if not user:
                return
            user.pop("group", None)
            self._flush()

    async def get_notifications(self, user_id: int) -> bool:
        async with self._lock:
            return bool(self._users.get(str(user_id), {}).get("notifications"))

    async def set_notifications(self, user_id: int, enabled: bool) -> None:
        async with self._lock:
            self._users.setdefault(str(user_id), {})["notifications"] = enabled
            self._flush()

    async def get_all_users_with_notifications(self) -> list[tuple[int, str]]:
        async with self._lock:
            result: list[tuple[int, str]] = []
            for uid_str, data in self._users.items():
                if data.get("notifications") and data.get("group"):
                    result.append((int(uid_str), data["group"]))
            return result
