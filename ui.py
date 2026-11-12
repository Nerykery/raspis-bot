from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from group_catalog import GroupCatalog
from schedule_api import (
    MONTHS,
    TZ,
    Lesson,
    format_date_ru,
    today,
)

BTN_SCHEDULE = "📅 Расписание"
BTN_TOMORROW = "🌅 На завтра"
BTN_WEEK = "🗓 Неделя"
BTN_GROUP = "👥 Моя группа"
BTN_CHANGE = "🔄 Сменить группу"
BTN_NOTIFY = "🔔 Уведомления"

PAGE_SIZE = 12

FACULTY_SHORT = {
    "iret": "ИРЭТ",
    "pish": "ПИШ",
    "fvs": "ФВС",
    "fsu": "ФСУ",
    "fit": "ФИТ",
    "ef": "ЭФ",
    "gf": "ГФ",
    "yuf": "ЮФ",
    "fb": "ФБ",
    "fdo": "ФДО",
}

FACULTY_EMOJI = {
    "iret": "📡",
    "pish": "🏗",
    "fvs": "💻",
    "fsu": "⚙️",
    "fit": "💡",
    "ef": "📈",
    "gf": "📚",
    "yuf": "⚖️",
    "fb": "🛡",
    "fdo": "🌐",
}

WEEKDAY_SHORT = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

KIND_EMOJI = (
    ("лекц", "📖"),
    ("практ", "🧪"),
    ("семин", "💬"),
    ("лабор", "🔬"),
    ("лаб", "🔬"),
    ("экзам", "📝"),
    ("зач", "✅"),
    ("консульт", "💡"),
    ("физ", "🏃"),
)

# Мотивационные цитаты по дням недели
WEEKDAY_QUOTES = [
    "Понедельник задаёт тон всей неделе.",
    "Вторник — время войти в ритм.",
    "Среда: середина пути уже позади.",
    "Четверг — финишная прямая всё ближе.",
    "Пятница! Ещё немного — и выходные.",
    "Суббота на парах — это сила воли.",
    "Воскресенье — время собраться с мыслями.",
]

# Разделитель между карточками пар
_SEP = "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌"


def lessons_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "пара"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "пары"
    return "пар"


def kind_emoji(kind: str) -> str:
    lowered = kind.lower()
    for needle, emoji in KIND_EMOJI:
        if needle in lowered:
            return emoji
    return "📚"


def _time(value: datetime | None) -> str:
    moment = value or datetime.now(TZ)
    return moment.strftime("%H:%M")


def header_title(day: date, reference: date | None = None) -> str:
    reference = reference or today()
    delta = (day - reference).days
    if delta == 0:
        return f"Сегодня · {format_date_ru(day)}"
    if delta == 1:
        return f"Завтра · {format_date_ru(day)}"
    if delta == -1:
        return f"Вчера · {format_date_ru(day)}"
    return format_date_ru(day).capitalize()


def format_week_range(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.day}–{end.day} {MONTHS[start.month - 1]}"
    return f"{start.day} {MONTHS[start.month - 1]} – {end.day} {MONTHS[end.month - 1]}"


def _mins(hhmm: str) -> int:
    """Переводит строку HH:MM в количество минут от полуночи."""
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _duration_str(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}ч {m}мин"
    if h:
        return f"{h}ч"
    return f"{m}мин"


def _load_bar(count: int, max_count: int, width: int = 6) -> str:
    """Визуализация загруженности дня: ░░▒▒▓▓ → ▓▓▓▓▓▓."""
    if count == 0 or max_count == 0:
        return "░" * width
    filled = min(width, max(1, round(count / max_count * width)))
    return "▓" * filled + "░" * (width - filled)


def _lesson_card(lesson: Lesson) -> str:
    header = f"⏰  <b>Пара {lesson.number}  ·  {lesson.start} — {lesson.end}</b>"
    name_line = f"📚  <b>{escape(lesson.name)}</b>"

    lines: list[str] = [header, "", name_line]

    if lesson.kind:
        lines.append(f"📝  {escape(lesson.kind)}")
    if lesson.classroom:
        lines.append(f"📍  {escape(lesson.classroom)}")
    if lesson.lecturers:
        lines.append(f"👤  {escape(', '.join(lesson.lecturers))}")

    window = lesson.break_window
    if window:
        s, e, mins = window
        lines.append("")
        lines.append(f"☕  <i>Перерыв {s}–{e} · {mins} мин</i>")

    return "\n".join(lines)


def render_day_summary(lessons: list[Lesson]) -> str:
    """Краткий дайджест дня: число пар, временной охват, первая и последняя пара."""
    if not lessons:
        return ""

    first = lessons[0]
    last = lessons[-1]
    total = len(lessons)

    try:
        span = _mins(last.end) - _mins(first.start)
        time_info = f"⏱ <b>{first.start} — {last.end}</b>  ({_duration_str(span)})"
    except ValueError:
        time_info = f"⏱ <b>{first.start} — {last.end}</b>"

    lines = [f"📊 <b>{total} {lessons_word(total)}</b>  ·  {time_info}"]

    if total >= 2 and first.name != last.name:
        lines.append(
            f"▶️ <i>{escape(first.name)}</i>  →  <i>{escape(last.name)}</i>"
        )
    elif total == 1:
        lines.append(f"▶️ <i>{escape(first.name)}</i>")

    return "\n".join(lines)


def render_schedule(
    group: str,
    day: date,
    lessons: list[Lesson],
    *,
    updated_at: datetime | None = None,
) -> str:
    lines = [
        f"<b>📅 {escape(header_title(day))}</b>",
        f"👥 Группа <b>{escape(group)}</b>",
    ]

    if not lessons:
        lines.append("")
        lines.append("🎉 <b>Пар нет</b>")
        lines.append(f"<i>{WEEKDAY_QUOTES[day.weekday()]} Отдыхайте!</i>")
        return "\n".join(lines)

    summary = render_day_summary(lessons)
    if summary:
        lines.append(summary)
    lines.append("")

    for i, lesson in enumerate(lessons):
        lines.append(_lesson_card(lesson))
        if i < len(lessons) - 1:
            lines.append(f"<i>{_SEP}</i>")

    lines.append("")
    lines.append(f"<i>Обновлено в {_time(updated_at)}</i>")
    return "\n".join(lines)


def render_week(
    group: str,
    week_start: date,
    lessons_by_day: dict[date, list[Lesson]],
    *,
    updated_at: datetime | None = None,
) -> str:
    week_end = week_start + timedelta(days=6)
    lines = [
        f"<b>🗓 Неделя  ·  {escape(format_week_range(week_start, week_end))}</b>",
        f"👥 Группа <b>{escape(group)}</b>",
        "",
    ]

    counts: dict[date, int] = {}
    for i in range(7):
        d = week_start + timedelta(days=i)
        counts[d] = len(lessons_by_day.get(d, []))

    max_count = max(counts.values(), default=1) or 1
    total = sum(counts.values())
    today_date = today()

    for index in range(7):
        day = week_start + timedelta(days=index)
        count = counts[day]
        bar = _load_bar(count, max_count)
        day_str = f"{day.day} {MONTHS[day.month - 1]}"

        count_label = f"{count} {lessons_word(count)}" if count else "—"

        if day == today_date:
            line = (
                f"<b>{WEEKDAY_SHORT[index]}</b> · {day_str} · "
                f"{bar} · <b>{count_label}</b>  <i>◀ сегодня</i>"
            )
        elif count == 0:
            line = (
                f"<b>{WEEKDAY_SHORT[index]}</b> · {day_str} · "
                f"{bar} · <i>{count_label}</i>"
            )
        else:
            line = (
                f"<b>{WEEKDAY_SHORT[index]}</b> · {day_str} · "
                f"{bar} · {count_label}"
            )
        lines.append(line)

    lines.append("")
    lines.append(
        f"<b>Итого:</b> {total} {lessons_word(total)} за неделю  ·  "
        f"<i>обновлено в {_time(updated_at)}</i>"
    )
    lines.append("")
    lines.append("Выберите день 👇")
    return "\n".join(lines)


def render_welcome(
    group: str | None,
    faculty: str | None,
    reference: date | None = None,
) -> str:
    reference = reference or today()
    if not group:
        return (
            "👋 <b>Привет! Я показываю расписание ТУСУР</b>\n\n"
            "Выберите факультет и группу — дальше всё будет в один тап.\n"
            "Можно и просто отправить номер группы, например "
            "<code>746-1</code>."
        )

    quote = WEEKDAY_QUOTES[reference.weekday()]
    lines = [
        "👋 <b>Привет! Это ваше расписание</b>",
        "",
        f"<i>{quote}</i>",
        "",
        f"👥 Группа: <b>{escape(group)}</b>",
    ]
    if faculty:
        lines.append(f"🏛 {escape(faculty)}")
    lines.append(f"📅 Сегодня: {format_date_ru(reference)}")
    lines.append("")
    lines.append("Что показать? 👇")
    return "\n".join(lines)


def render_group_saved(group: str, faculty: str | None) -> str:
    lines = [
        "✅ <b>Группа сохранена</b>",
        f"👥 <b>{escape(group)}</b>",
    ]
    if faculty:
        lines.append(f"🏛 {escape(faculty)}")
    lines.append("")
    lines.append("Расписание уже можно открывать 👇")
    return "\n".join(lines)


def render_my_group(group: str | None, faculty: str | None) -> str:
    if not group:
        return "👥 <b>Группа не выбрана</b>\n\nДавайте выберем — это быстро."
    lines = ["👥 <b>Ваша группа</b>", f"<b>{escape(group)}</b>"]
    if faculty:
        lines.append(f"🏛 {escape(faculty)}")
    lines.append("")
    lines.append("Смотреть расписание 👇")
    return "\n".join(lines)


def render_faculties_prompt() -> str:
    return (
        "🏛 <b>Выберите факультет</b>\n\n"
        "Или отправьте номер группы сообщением, например <code>746-1</code>."
    )


def render_groups_prompt(faculty_name: str) -> str:
    return f"🏛 <b>{escape(faculty_name)}</b>\n\nВыберите группу:"


def render_group_not_found(group: str) -> str:
    return (
        f"🤔 <b>Группа {escape(group)} не найдена</b>\n\n"
        "Проверьте номер или выберите группу из списка."
    )


def render_api_error() -> str:
    return (
        "⚠️ <b>Сервис расписания не отвечает</b>\n\n"
        "Попробуйте ещё раз через минуту — данные подтянутся."
    )


def render_unknown() -> str:
    return (
        "🤔 <b>Не понял</b>\n\n"
        "Отправьте номер группы, например <code>746-1</code>, "
        "или выберите её в меню."
    )


def render_help() -> str:
    return (
        "ℹ️ <b>Что я умею</b>\n\n"
        f"{BTN_SCHEDULE} — пары на сегодня\n"
        f"{BTN_TOMORROW} — пары на завтра\n"
        f"{BTN_WEEK} — обзор всей недели\n"
        f"{BTN_GROUP} — текущая группа\n"
        f"{BTN_CHANGE} — выбор факультета и группы\n"
        f"{BTN_NOTIFY} — включить/выключить напоминания\n\n"
        "Ещё можно просто отправить номер группы сообщением, "
        "например <code>746-1</code>.\n\n"
        '<i>Данные: <a href="https://timetable.tusur.ru">timetable.tusur.ru</a></i>'
    )


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SCHEDULE), KeyboardButton(text=BTN_TOMORROW)],
            [KeyboardButton(text=BTN_WEEK), KeyboardButton(text=BTN_GROUP)],
            [KeyboardButton(text=BTN_CHANGE), KeyboardButton(text=BTN_NOTIFY)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Группа или действие",
    )


def menu_inline_kb(offset: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Сегодня", callback_data="sched:0")
    builder.button(text="🌅 Завтра", callback_data="sched:1")
    builder.button(text="🗓 Неделя", callback_data="week")
    builder.button(text="🔄 Обновить", callback_data=f"sched:{offset}:r")
    builder.button(text="👥 Сменить группу", callback_data="faculties")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def faculties_kb(catalog: GroupCatalog) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, _, groups in catalog.faculties:
        if not groups:
            continue
        short = FACULTY_SHORT.get(key, key.upper())
        emoji = FACULTY_EMOJI.get(key, "🏛")
        builder.button(text=f"{emoji} {short}", callback_data=f"fac:{key}:0")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu"))
    return builder.as_markup()


def groups_kb(
    catalog: GroupCatalog,
    key: str,
    page: int,
    current: str | None = None,
) -> InlineKeyboardMarkup:
    faculty = catalog.faculty(key)
    if faculty is None:
        return faculties_kb(catalog)
    _, _, groups = faculty
    pages = max(1, (len(groups) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 0), pages - 1)
    chunk = groups[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    builder = InlineKeyboardBuilder()
    for group in chunk:
        label = f"✅ {group}" if group == current else group
        builder.button(text=label, callback_data=f"pick:{group}")
    builder.adjust(2)

    if pages > 1:
        nav = InlineKeyboardBuilder()
        if page > 0:
            nav.button(text="‹", callback_data=f"fac:{key}:{page - 1}")
        nav.button(text=f"{page + 1}/{pages}", callback_data="noop")
        if page < pages - 1:
            nav.button(text="›", callback_data=f"fac:{key}:{page + 1}")
        nav.adjust(3)
        builder.attach(nav)

    builder.row(
        InlineKeyboardButton(text="🏛 К факультетам", callback_data="faculties"),
    )
    return builder.as_markup()


def week_kb(
    week_start: date,
    counts: dict[date, int],
    reference: date | None = None,
) -> InlineKeyboardMarkup:
    reference = reference or today()
    builder = InlineKeyboardBuilder()
    for index in range(7):
        day = week_start + timedelta(days=index)
        count = counts.get(day, 0)
        suffix = str(count) if count else "—"
        builder.button(
            text=f"{WEEKDAY_SHORT[index]} · {suffix}",
            callback_data=f"sched:{(day - reference).days}",
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="week:r"))
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu"))
    return builder.as_markup()


def retry_kb(offset: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Повторить", callback_data=f"sched:{offset}:r")
    builder.button(text="🏠 В меню", callback_data="menu")
    builder.adjust(2)
    return builder.as_markup()


def retry_week_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Повторить", callback_data="week:r")
    builder.button(text="🏠 В меню", callback_data="menu")
    builder.adjust(2)
    return builder.as_markup()


def not_found_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏛 Выбрать группу", callback_data="faculties")
    builder.button(text="🏠 В меню", callback_data="menu")
    builder.adjust(2)
    return builder.as_markup()


def render_notify_menu(settings: dict) -> str:
    def mark(key: str) -> str:
        return "✅" if settings.get(key) else "❌"

    has_any = any(settings.values())
    overall = "включены" if has_any else "выключены"

    return (
        f"🔔 <b>Уведомления</b> — <i>{overall}</i>\n\n"
        f"{mark('before_start')}  За 15 мин до <b>начала</b> пары\n"
        f"{mark('before_end')}  За 15 мин до <b>конца</b> пары\n"
        f"{mark('break')}  <b>Перерыв</b> в середине пары\n\n"
        "<i>Нажми на строку, чтобы включить или выключить.</i>"
    )


def notify_kb(settings: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text=("✅ Начало пары" if settings.get("before_start") else "❌ Начало пары"),
        callback_data="notify:toggle:before_start",
    )
    builder.button(
        text=("✅ Конец пары" if settings.get("before_end") else "❌ Конец пары"),
        callback_data="notify:toggle:before_end",
    )
    builder.button(
        text=("✅ Перерыв" if settings.get("break") else "❌ Перерыв"),
        callback_data="notify:toggle:break",
    )
    builder.button(text="🏠 В меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


