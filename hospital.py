import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging

from config import TOKEN  # Используйте ваш TOKEN

logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение состояний
class Form(StatesGroup):
    name = State()
    age = State()
    polis_number = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('hospital_data.db')
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS pacients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        polis_number TEXT NOT NULL CHECK(LENGTH(polis_number) = 16)
    )''')
    conn.commit()
    conn.close()

init_db()

# Обработка команды /start
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await message.answer("Привет! Как тебя зовут?")
    await state.set_state(Form.name)

# Обработка имени
@dp.message(Form.name)
async def name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(Form.age)

# Обработка возраста
@dp.message(Form.age)
async def age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите возраст числом.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Введите номер полиса по маске: 74541XXXXXXXXXXXX (всего 16 цифр)")
    await state.set_state(Form.polis_number)

# Обработка номера полиса
@dp.message(Form.polis_number)
async def polis_number(message: Message, state: FSMContext):
    polis = message.text
    if len(polis) != 16 or not polis.startswith('74541') or not polis.isdigit():
        await message.answer("Номер полиса должен содержать 16 цифр и начинаться с 74541.")
        return

    await state.update_data(polis_number=polis)

    # Получение данных от пользователя
    user_data = await state.get_data()

    # Вставка данных в базу данных
    conn = sqlite3.connect('hospital_data.db')
    cur = conn.cursor()
    cur.execute('''
    INSERT INTO pacients (name, age, polis_number) VALUES (?, ?, ?)''',
                (user_data['name'], user_data['age'], user_data['polis_number']))
    conn.commit()
    conn.close()

    await message.answer("Ваши данные сохранены. Спасибо!")
    await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
