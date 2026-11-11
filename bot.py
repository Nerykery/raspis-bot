from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, CallbackQuery, Message

import config
import ui
from group_catalog import GroupCatalog, is_group_like, normalize_group
from schedule_api import TimetableAPI, today
from storage import UserStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("raspis-bot")

router = Router()


async def _respond(
    target: Message,
    text: str,
    keyboard,
    *,
    edit: bool,
) -> None:
    if not edit:
        await target.answer(text, reply_markup=keyboard)
        return
    try:
        await target.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def send_schedule(
    message: Message,
    group: str,
    day: date,
    api: TimetableAPI,
    *,
    force: bool = False,
    edit: bool = False,
) -> None:
    offset = (day - today()).days
    try:
        lessons = await api.get_lessons(group, day, force=force)
    except (TimeoutError, aiohttp.ClientError):
        log.warning("Не удалось получить расписание для %s", group)
        await _respond(
            message,
            ui.render_api_error(),
            ui.retry_kb(offset),
            edit=edit,
        )
        return

    if lessons is None:
        await _respond(
            message,
            ui.render_group_not_found(group),
            ui.not_found_kb(),
            edit=edit,
        )
        return

    await _respond(
        message,
        ui.render_schedule(group, day, lessons),
        ui.menu_inline_kb(offset),
        edit=edit,
    )


async def send_week(
    message: Message,
    group: str,
    day: date,
    api: TimetableAPI,
    *,
    force: bool = False,
    edit: bool = False,
) -> None:
    week_start = day - timedelta(days=day.weekday())
    try:
        week = await api.get_week_lessons(group, day, force=force)
    except (TimeoutError, aiohttp.ClientError):
        log.warning("Не удалось получить неделю для %s", group)
        await _respond(
            message,
            ui.render_api_error(),
            ui.retry_week_kb(),
            edit=edit,
        )
        return

    if week is None:
        await _respond(
            message,
            ui.render_group_not_found(group),
            ui.not_found_kb(),
            edit=edit,
        )
        return

    counts = {lesson_day: len(items) for lesson_day, items in week.items()}
    await _respond(
        message,
        ui.render_week(group, week_start, week),
        ui.week_kb(week_start, counts),
        edit=edit,
    )


async def show_faculties(target: Message, catalog: GroupCatalog) -> None:
    await target.answer(
        ui.render_faculties_prompt(),
        reply_markup=ui.faculties_kb(catalog),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, store, catalog: GroupCatalog) -> None:
    group = await store.get_group(message.from_user.id)
    faculty = catalog.faculty_name_for(group) if group else None
    await message.answer(
        ui.render_welcome(group, faculty),
        reply_markup=ui.main_menu_kb(),
    )
    if group:
        await message.answer("Быстрый доступ 👇", reply_markup=ui.menu_inline_kb())
        return
    await show_faculties(message, catalog)


@router.message(Command("schedule"))
@router.message(F.text == ui.BTN_SCHEDULE)
async def cmd_schedule(
    message: Message, store, catalog: GroupCatalog, api: TimetableAPI
) -> None:
    group = await store.get_group(message.from_user.id)
    if not group:
        await show_faculties(message, catalog)
        return
    await send_schedule(message, group, today(), api)


@router.message(Command("tomorrow"))
@router.message(F.text == ui.BTN_TOMORROW)
async def cmd_tomorrow(
    message: Message, store, catalog: GroupCatalog, api: TimetableAPI
) -> None:
    group = await store.get_group(message.from_user.id)
    if not group:
        await show_faculties(message, catalog)
        return
    await send_schedule(message, group, today() + timedelta(days=1), api)


@router.message(Command("week"))
@router.message(F.text == ui.BTN_WEEK)
async def cmd_week(
    message: Message, store, catalog: GroupCatalog, api: TimetableAPI
) -> None:
    group = await store.get_group(message.from_user.id)
    if not group:
        await show_faculties(message, catalog)
        return
    await send_week(message, group, today(), api)


@router.message(Command("group"))
@router.message(F.text == ui.BTN_GROUP)
async def cmd_group(message: Message, store, catalog: GroupCatalog) -> None:
    group = await store.get_group(message.from_user.id)
    if not group:
        await show_faculties(message, catalog)
        return
    faculty = catalog.faculty_name_for(group)
    await message.answer(
        ui.render_my_group(group, faculty),
        reply_markup=ui.menu_inline_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(ui.render_help(), reply_markup=ui.main_menu_kb())


@router.message(F.text == ui.BTN_CHANGE)
async def cmd_change_group(message: Message, catalog: GroupCatalog) -> None:
    await show_faculties(message, catalog)


@router.message(Command("change"))
async def cmd_change(message: Message, catalog: GroupCatalog) -> None:
    await show_faculties(message, catalog)


@router.callback_query(F.data == "faculties")
async def cb_faculties(callback: CallbackQuery, catalog: GroupCatalog) -> None:
    if callback.message:
        try:
            await callback.message.edit_text(
                ui.render_faculties_prompt(),
                reply_markup=ui.faculties_kb(catalog),
            )
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("fac:"))
async def cb_faculty(callback: CallbackQuery, store, catalog: GroupCatalog) -> None:
    _, key, page = callback.data.split(":")
    faculty = catalog.faculty(key)
    if faculty is None or callback.message is None:
        await callback.answer("Факультет не найден", show_alert=False)
        return
    _, name, _ = faculty
    current = await store.get_group(callback.from_user.id)
    try:
        await callback.message.edit_text(
            ui.render_groups_prompt(name),
            reply_markup=ui.groups_kb(catalog, key, int(page), current),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"))
async def cb_pick(callback: CallbackQuery, store, catalog: GroupCatalog) -> None:
    group = normalize_group(callback.data.split(":", 1)[1])
    if not catalog.has(group):
        await callback.answer("Группа не найдена", show_alert=True)
        return

    await store.set_group(callback.from_user.id, group)
    faculty = catalog.faculty_name_for(group)
    if callback.message:
        try:
            await callback.message.edit_text(
                ui.render_group_saved(group, faculty),
                reply_markup=ui.menu_inline_kb(),
            )
        except TelegramBadRequest:
            pass
        await callback.message.answer(
            "Главное меню 👇",
            reply_markup=ui.main_menu_kb(),
        )
    await callback.answer("Готово")


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, store, catalog: GroupCatalog) -> None:
    group = await store.get_group(callback.from_user.id)
    faculty = catalog.faculty_name_for(group) if group else None
    if callback.message:
        try:
            await callback.message.edit_text(
                ui.render_my_group(group, faculty),
                reply_markup=ui.menu_inline_kb(),
            )
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("sched:"))
async def cb_schedule(callback: CallbackQuery, store, api: TimetableAPI) -> None:
    parts = callback.data.split(":")
    offset = int(parts[1])
    force = len(parts) > 2 and parts[-1] == "r"
    group = await store.get_group(callback.from_user.id)
    if not group:
        await callback.answer("Сначала выберите группу", show_alert=True)
        return
    day = today() + timedelta(days=offset)
    if callback.message:
        await send_schedule(
            callback.message,
            group,
            day,
            api,
            force=force,
            edit=True,
        )
    await callback.answer("Обновлено" if force else None)


@router.callback_query(F.data.startswith("week"))
async def cb_week(callback: CallbackQuery, store, api: TimetableAPI) -> None:
    force = callback.data.endswith(":r")
    group = await store.get_group(callback.from_user.id)
    if not group:
        await callback.answer("Сначала выберите группу", show_alert=True)
        return
    if callback.message:
        await send_week(
            callback.message,
            group,
            today(),
            api,
            force=force,
            edit=True,
        )
    await callback.answer("Обновлено" if force else None)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.message(F.text.is_not(None))
async def any_group_text(
    message: Message, store, catalog: GroupCatalog, api: TimetableAPI
) -> None:
    text = (message.text or "").strip()
    if text.startswith("/"):
        await message.answer(ui.render_help(), reply_markup=ui.main_menu_kb())
        return
    if not is_group_like(text):
        await message.answer(ui.render_unknown(), reply_markup=ui.main_menu_kb())
        return

    group = normalize_group(text)
    if not catalog.has(group):
        try:
            exists = await api.group_exists(group)
        except (TimeoutError, aiohttp.ClientError):
            await message.answer(ui.render_api_error(), reply_markup=ui.retry_kb(0))
            return
        if not exists:
            await message.answer(
                ui.render_group_not_found(group),
                reply_markup=ui.not_found_kb(),
            )
            return

    await store.set_group(message.from_user.id, group)
    faculty = catalog.faculty_name_for(group)
    await message.answer(
        ui.render_group_saved(group, faculty),
        reply_markup=ui.main_menu_kb(),
    )
    await message.answer("Меню 👇", reply_markup=ui.menu_inline_kb())


async def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан")

    bot = Bot(
        config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    store = UserStore(config.USERS_FILE)
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        catalog = GroupCatalog(config.GROUPS_CACHE)
        await catalog.load(session)
        api = TimetableAPI(session)

        dispatcher["store"] = store
        dispatcher["catalog"] = catalog
        dispatcher["api"] = api
        dispatcher.include_router(router)

        await bot.set_my_commands(
            [
                BotCommand(command="start", description="👋 Начать"),
                BotCommand(command="schedule", description="📅 Расписание на сегодня"),
                BotCommand(command="tomorrow", description="🌅 На завтра"),
                BotCommand(command="week", description="🗓 Неделя"),
                BotCommand(command="group", description="👥 Моя группа"),
                BotCommand(command="change", description="🔄 Сменить группу"),
                BotCommand(command="help", description="ℹ️ Помощь"),
            ]
        )
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("Бот запущен, групп в каталоге: %s", len(catalog.all_groups))
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
