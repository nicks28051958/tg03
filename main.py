import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from googletrans import Translator  # Для перевода текста
from gtts import gTTS  # Для преобразования текста в речь
from config import WEATHER_API_KEY, TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация переводчика
translator = Translator()

# Словарь для отслеживания состояния пользователей
user_states = {}

# Функция для перевода текста с русского на английский
async def translate_text(text):
    try:
        # Перевод текста с русского на английский
        translation = translator.translate(text, src='ru', dest='en').text
        logger.info(f"Перевод выполнен: {translation}")
        return translation
    except Exception as e:
        logger.error(f"Ошибка перевода текста: {e}")
        return None

# Функция для получения данных о погоде
async def get_weather(city="Магнитогорск"):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&aqi=no"
    timeout = aiohttp.ClientTimeout(total=60)  # Увеличение таймаута до 60 секунд
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    location = data['location']
                    current = data['current']

                    name = location['name']
                    region = location['region']
                    country = location['country']
                    temp = current['temp_c']
                    feels_like = current['feelslike_c']
                    pressure = current['pressure_mb']
                    humidity = current['humidity']
                    condition = current['condition']['text']

                    return (f"Город: {name}, Регион: {region}, Страна: {country}\n"
                            f"Температура: {temp}°C\n"
                            f"Ощущаемая температура: {feels_like}°C\n"
                            f"Давление: {pressure} гПа\n"
                            f"Влажность: {humidity}%\n"
                            f"Состояние: {condition}")
                else:
                    return "Не удалось получить данные о погоде."
    except asyncio.TimeoutError:
        return "Превышен таймаут ожидания ответа от сервера."
    except aiohttp.ClientError as e:
        return f"Ошибка при запросе данных: {e}"

# Функция для создания аудиофайла OGG из текста с использованием gTTS
async def create_audio_file(text, filename, lang='en'):
    tts = gTTS(text=text, lang=lang)  # Используем английский для улучшенного произношения
    tts.save(filename)

# Функция для отправки голосового сообщения
async def send_voice_message(chat_id, voice_file_path):
    audio = FSInputFile(voice_file_path)
    await bot.send_voice(chat_id=chat_id, voice=audio)
    os.remove(voice_file_path)  # Удаляем аудиофайл после отправки

# Обработчик команды /help
async def help_command(message: Message):
    await message.answer("Этот бот умеет выполнять:\n/start\n/help\n/weather\n/translate")

# Обработчик команды /start
async def start_command(message: Message):
    await message.answer(f'Привет, {message.from_user.first_name}!')

# Обработчик команды /weather для прогноза погоды
async def weather_command(message: Message):
    logger.info(f"Получен запрос по команде /weather от пользователя {message.from_user.id}")
    weather_info = await get_weather()
    await message.answer(weather_info)

# Обработчик команды /translate
async def translate_command(message: Message):
    # Сохраняем состояние пользователя для дальнейшего отслеживания ввода текста
    user_states[message.from_user.id] = "waiting_for_translation"
    await message.answer("Введите текст, который необходимо перевести.")

# Обработчик текстовых сообщений для перевода
async def handle_text(message: Message):
    user_id = message.from_user.id

    # Проверяем состояние пользователя
    if user_id in user_states and user_states[user_id] == "waiting_for_translation":
        # Выполняем перевод текста
        translation = await translate_text(message.text)
        if translation:
            await message.answer(f"Перевод:\n{translation}")
            # Создаем аудиофайл с переводом в формате OGG с улучшенным произношением
            audio_filename = "translated_message.ogg"
            await create_audio_file(translation, audio_filename, lang='en')  # Применяем английский синтезатор
            # Отправляем голосовое сообщение
            await send_voice_message(message.chat.id, audio_filename)
        else:
            await message.answer("Не удалось выполнить перевод.")

        # Сбрасываем состояние пользователя
        user_states.pop(user_id)
    else:
        # Если нет состояния для перевода, игнорируем сообщение
        await message.answer("Отправьте команду /translate для перевода текста.")

# Главная функция для запуска бота
async def main():
    dp.message.register(help_command, Command("help"))
    dp.message.register(start_command, Command("start"))
    dp.message.register(weather_command, Command("weather"))
    dp.message.register(translate_command, Command("translate"))  # Команда для перевода
    dp.message.register(handle_text, lambda message: message.text)  # Обработчик текстовых сообщений

    logger.info("Бот запущен и готов к приему команд.")
    await dp.start_polling(bot)

# Запуск бота
if __name__ == "__main__":
    asyncio.run(main())
