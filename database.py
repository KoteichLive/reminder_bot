import aiosqlite
import asyncio
from config import DB_NAME
from datetime import datetime

class Database:
    """
    🗃️ КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ SQLite
    Все методы асинхронные для эффективной работы с ботом
    """
    
    def __init__(self, db_name: str = DB_NAME):
        # Инициализация с именем базы данных из config.py
        self.db_name = db_name

    async def create_tables(self):
        """📋 СОЗДАНИЕ ТАБЛИЦ В БАЗЕ ДАННЫХ при первом запуске"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,      -- Уникальный ID
                    user_id INTEGER NOT NULL,                  -- ID пользователя Telegram
                    text TEXT NOT NULL,                        -- Текст напоминания
                    reminder_time TEXT NOT NULL,               -- Время напоминания
                    created_at TEXT NOT NULL,                  -- Дата создания
                    is_completed BOOLEAN DEFAULT FALSE         -- Статус выполнения
                )
            ''')
            await db.commit()  # Сохраняем изменения в БД

    async def add_reminder(self, user_id: int, text: str, reminder_time: str) -> int:
        """
        ➕ ДОБАВЛЕНИЕ НОВОГО НАПОМИНАНИЯ в базу данных
        
        Аргументы:
        - user_id: ID пользователя (из message.from_user.id)
        - text: текст напоминания
        - reminder_time: время срабатывания
        
        Возвращает:
        - ID созданного напоминания (для отображения пользователю)
        """
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Текущее время
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'INSERT INTO reminders (user_id, text, reminder_time, created_at) VALUES (?, ?, ?, ?)',
                (user_id, text, reminder_time, created_at)  # Параметры для защиты от SQL-инъекций
            )
            await db.commit()
            return cursor.lastrowid  # Возвращаем ID новой записи

    async def get_user_reminders(self, user_id: int) -> list:
        """
        👀 ПОЛУЧЕНИЕ ВСЕХ НАПОМИНАНИЙ ПОЛЬЗОВАТЕЛЯ
        
        Аргументы:
        - user_id: ID пользователя
        
        Возвращает:
        - Список напоминаний только этого пользователя, отсортированных по времени
        - Только невыполненные напоминания (is_completed = FALSE)
        """
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT * FROM reminders WHERE user_id = ? AND is_completed = FALSE ORDER BY reminder_time',
                (user_id,)
            )
            return await cursor.fetchall()  # Возвращаем все найденные записи

    async def get_all_pending_reminders(self) -> list:
        """
        🔔 ПОЛУЧЕНИЕ ВСЕХ ОЖИДАЮЩИХ НАПОМИНАНИЙ (для отправки уведомлений)
        
        Возвращает:
        - Список ВСЕХ невыполненных напоминаний всех пользователей
        - Используется для проверки, какие напоминания пора отправить
        """
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT * FROM reminders WHERE is_completed = FALSE ORDER BY reminder_time'
            )
            return await cursor.fetchall()

    async def mark_reminder_completed(self, reminder_id: int):
        """
        ✅ ОТМЕТКА НАПОМИНАНИЯ КАК ВЫПОЛНЕННОГО после отправки
        
        Аргументы:
        - reminder_id: ID напоминания которое было отправлено
        """
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE reminders SET is_completed = TRUE WHERE id = ?',
                (reminder_id,)
            )
            await db.commit()

    async def delete_reminder(self, reminder_id: int, user_id: int):
        """
        🗑️ УДАЛЕНИЕ НАПОМИНАНИЯ (только если оно принадлежит пользователю)
        
        Аргументы:
        - reminder_id: ID напоминания для удаления
        - user_id: ID пользователя (проверка владельца)
        """
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'DELETE FROM reminders WHERE id = ? AND user_id = ?',
                (reminder_id, user_id)
            )
            await db.commit()

    async def get_reminder_by_id(self, reminder_id: int, user_id: int):
        """
        🔎 ПОЛУЧЕНИЕ НАПОМИНАНИЯ ПО ID (с проверкой владельца)
        
        Аргументы:
        - reminder_id: ID напоминания
        - user_id: ID пользователя для проверки
        
        Возвращает:
        - Напоминание или None если не найдено или не принадлежит пользователю
        """
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'SELECT * FROM reminders WHERE id = ? AND user_id = ?',
                (reminder_id, user_id)
            )
            return await cursor.fetchone()