from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    """
    ❌ ОБРАБОТЧИК КОМАНДЫ /CANCEL
    Отменяет текущее состояние (например, создание напоминания)
    и убирает клавиатуру
    """
    await message.answer(
        "Текущее действие отменено. Используйте /start для просмотра доступных команд.",
        reply_markup=types.ReplyKeyboardRemove()  # 🗑️ Убираем специальную клавиатуру
    )