from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import re

from database import Database

router = Router()
db = Database()

class ReminderStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_time = State()
    waiting_for_delete = State()

@router.message(Command("new"))
async def cmd_new_reminder(message: types.Message, state: FSMContext):
    """Начало создания нового напоминания"""
    await message.answer(
        "📝 Введите текст напоминания:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(ReminderStates.waiting_for_text)

@router.message(ReminderStates.waiting_for_text)
async def process_reminder_text(message: types.Message, state: FSMContext):
    """Обработка текста напоминания"""
    if len(message.text) > 500:
        await message.answer("❌ Текст напоминания слишком длинный. Максимум 500 символов.")
        return

    await state.update_data(text=message.text)
    
    # Создаем клавиатуру с быстрыми вариантами времени
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Через 1 час"), types.KeyboardButton(text="Через 2 часа")],
            [types.KeyboardButton(text="Через 6 часов"), types.KeyboardButton(text="Завтра в это же время")],
            [types.KeyboardButton(text="Указать вручную")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "⏰ Когда напомнить?\n\n"
        "Выберите один из вариантов или укажите время вручную в формате:\n"
        "• <b>ДД.ММ.ГГГГ ЧЧ:ММ</b> (например, 25.12.2024 15:30)\n"
        "• <b>ЧЧ:ММ</b> (на сегодня, например, 18:00)",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(ReminderStates.waiting_for_time)

@router.message(ReminderStates.waiting_for_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    """Обработка времени напоминания"""
    user_data = await state.get_data()
    reminder_text = user_data['text']
    
    try:
        reminder_time = await parse_time_input(message.text)
        
        # Проверяем, что время в будущем
        if reminder_time <= datetime.now():
            await message.answer(
                "❌ Время напоминания должно быть в будущем! Попробуйте снова:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
        
        # Сохраняем напоминание в базу данных
        reminder_id = await db.add_reminder(
            user_id=message.from_user.id,
            text=reminder_text,
            reminder_time=reminder_time.strftime('%Y-%m-%d %H:%M')
        )
        
        await message.answer(
            f"✅ Напоминание создано!\n\n"
            f"📝 Текст: {reminder_text}\n"
            f"⏰ Время: {reminder_time.strftime('%d.%m.%Y в %H:%M')}\n"
            f"🆔 ID: {reminder_id}",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except ValueError as e:
        await message.answer(
            f"❌ Неверный формат времени: {str(e)}\n\n"
            "Пожалуйста, укажите время в одном из форматов:\n"
            "• <b>ДД.ММ.ГГГГ ЧЧ:ММ</b> (например, 25.12.2024 15:30)\n"
            "• <b>ЧЧ:ММ</b> (на сегодня, например, 18:00)",
            parse_mode="HTML"
        )

@router.message(Command("list"))
async def cmd_list_reminders(message: types.Message):
    """Показать список напоминаний пользователя"""
    reminders = await db.get_user_reminders(message.from_user.id)
    
    if not reminders:
        await message.answer("📭 У вас нет активных напоминаний.")
        return
    
    reminders_text = "📋 Ваши напоминания:\n\n"
    for reminder in reminders:
        reminder_id, user_id, text, reminder_time, created_at, is_completed = reminder
        reminder_dt = datetime.strptime(reminder_time, '%Y-%m-%d %H:%M')
        reminders_text += (
            f"🆔 <b>ID: {reminder_id}</b>\n"
            f"📝 {text}\n"
            f"⏰ {reminder_dt.strftime('%d.%m.%Y в %H:%M')}\n"
            f"────────────────────\n"
        )
    
    reminders_text += "\nДля удаления напоминания используйте /delete <ID>"
    await message.answer(reminders_text, parse_mode="HTML")

@router.message(Command("delete"))
async def cmd_delete_reminder(message: types.Message, state: FSMContext):
    """Удаление напоминания"""
    args = message.text.split()
    
    if len(args) == 2 and args[1].isdigit():
        # Если передан ID напрямую
        reminder_id = int(args[1])
        reminder = await db.get_reminder_by_id(reminder_id, message.from_user.id)
        
        if reminder:
            await db.delete_reminder(reminder_id, message.from_user.id)
            await message.answer(f"✅ Напоминание с ID {reminder_id} удалено.")
        else:
            await message.answer("❌ Напоминание с таким ID не найдено или вам не принадлежит.")
    else:
        # Показываем список для выбора
        reminders = await db.get_user_reminders(message.from_user.id)
        
        if not reminders:
            await message.answer("📭 У вас нет активных напоминаний для удаления.")
            return
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=str(reminder[0]))] for reminder in reminders] +
            [[types.KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
        
        await message.answer(
            "Выберите ID напоминания для удаления:",
            reply_markup=keyboard
        )
        await state.set_state(ReminderStates.waiting_for_delete)

@router.message(ReminderStates.waiting_for_delete, F.text == "Отмена")
async def cancel_delete(message: types.Message, state: FSMContext):
    """Отмена удаления"""
    await message.answer("❌ Удаление отменено.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

@router.message(ReminderStates.waiting_for_delete)
async def process_delete_reminder(message: types.Message, state: FSMContext):
    """Обработка выбора напоминания для удаления"""
    if message.text.isdigit():
        reminder_id = int(message.text)
        reminder = await db.get_reminder_by_id(reminder_id, message.from_user.id)
        
        if reminder:
            await db.delete_reminder(reminder_id, message.from_user.id)
            await message.answer(
                f"✅ Напоминание с ID {reminder_id} удалено.",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.answer("❌ Напоминание с таким ID не найдено. Попробуйте снова:")
    else:
        await message.answer("❌ Пожалуйста, введите числовой ID напоминания:")

async def parse_time_input(time_str: str) -> datetime:
    """Парсинг введенного времени"""
    now = datetime.now()
    
    # Быстрые варианты
    if time_str == "Через 1 час":
        return now + timedelta(hours=1)
    elif time_str == "Через 2 часа":
        return now + timedelta(hours=2)
    elif time_str == "Через 6 часов":
        return now + timedelta(hours=6)
    elif time_str == "Завтра в это же время":
        return now + timedelta(days=1)
    elif time_str == "Указать вручную":
        raise ValueError("Укажите время вручную")
    
    # Формат ЧЧ:ММ (на сегодня)
    time_match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if time_match:
        hours, minutes = int(time_match.group(1)), int(time_match.group(2))
        reminder_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        if reminder_time <= now:
            reminder_time += timedelta(days=1)
        return reminder_time
    
    # Формат ДД.ММ.ГГГГ ЧЧ:ММ
    datetime_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})$', time_str)
    if datetime_match:
        day, month, year, hours, minutes = map(int, datetime_match.groups())
        return datetime(year, month, day, hours, minutes)
    
    raise ValueError("Неверный формат времени")