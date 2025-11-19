import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, CHECK_REMINDERS_INTERVAL
from database import Database
from handlers import start_router, reminders_router, menu_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReminderBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.db = Database()
        
        # Регистрация роутеров
        self.dp.include_router(start_router)
        self.dp.include_router(reminders_router)
        self.dp.include_router(menu_router)
    
    async def check_reminders(self):
        """Проверка и отправка напоминаний"""
        while True:
            try:
                reminders = await self.db.get_all_pending_reminders()
                now = datetime.now()
                
                for reminder in reminders:
                    reminder_id, user_id, text, reminder_time, created_at, is_completed = reminder
                    reminder_dt = datetime.strptime(reminder_time, '%Y-%m-%d %H:%M')
                    
                    # Если время напоминания наступило
                    if reminder_dt <= now:
                        try:
                            await self.bot.send_message(
                                user_id,
                                f"🔔 Напоминание!\n\n{text}",
                                parse_mode="HTML"
                            )
                            await self.db.mark_reminder_completed(reminder_id)
                            logger.info(f"Отправлено напоминание {reminder_id} пользователю {user_id}")
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания {reminder_id}: {e}")
                            # Если пользователь заблокировал бота, помечаем напоминание как выполненное
                            if "bot was blocked" in str(e).lower():
                                await self.db.mark_reminder_completed(reminder_id)
                
                await asyncio.sleep(CHECK_REMINDERS_INTERVAL)
                
            except Exception as e:
                logger.error(f"Ошибка в check_reminders: {e}")
                await asyncio.sleep(CHECK_REMINDERS_INTERVAL)
    
    async def start(self):
        """Запуск бота"""
        # Создание таблиц
        await self.db.create_tables()
        logger.info("База данных инициализирована")
        
        # Запуск проверки напоминаний в фоне
        asyncio.create_task(self.check_reminders())
        
        # Запуск бота
        logger.info("Бот запущен")
        await self.dp.start_polling(self.bot)

async def main():
    bot = ReminderBot()
    await bot.start()

if __name__ == "__main__":
    # Импортируем здесь, чтобы избежать циклического импорта
    from datetime import datetime
    asyncio.run(main())