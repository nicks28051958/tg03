import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from config import WEATHER_API_KEY, TOKEN
import sqlite3
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging

logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение состояний
class Form(StatesGroup):
    name = State()
    age = State()
    city = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('user_data.db')
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        city TEXT NOT NULL
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
    await state.update_data(age=message.text)
    await message.answer("В каком городе ты живешь?")
    await state.set_state(Form.city)

# Обработка города и получение погоды
@dp.message(Form.city)
async def city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)

    # Получение данных от пользователя
    user_data = await state.get_data()

    # Вставка данных в базу данных
    conn = sqlite3.connect('user_data.db')
    cur = conn.cursor()
    cur.execute('''
    INSERT INTO users (name, age, city) VALUES (?, ?, ?)''',
                (user_data['name'], user_data['age'], user_data['city']))
    conn.commit()
    conn.close()

    # Получение данных о погоде
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={user_data['city']}&aqi=no") as response:
            if response.status == 200:
                weather_data = await response.json()
                current = weather_data['current']
                temperature = current['temp_c']
                humidity = current['humidity']
                description = current['condition']['text']

                # Формирование отчета о погоде
                weather_report = (f"Город - {user_data['city']}\n"
                                  f"Температура - {temperature}°C\n"
                                  f"Влажность воздуха - {humidity}%\n"
                                  f"Описание погоды - {description}")
                await message.answer(weather_report)
            else:
                await message.answer("Не удалось получить данные о погоде")

    # Очистка состояния
    await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



