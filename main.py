
from environs import Env
import openai
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardRemove
from aiogram.types import Message

env = Env()
env.read_env('.env')
# Здесь вставьте токен, полученный от BotFather
TOKEN = env("TG_BOT_API")

# Здесь вставьте свой ключ API OpenAI
openai.api_key = env("KEY_OPENAI")

# Создаем объект бота
bot = Bot(token=TOKEN)

# Создаем объект для обработки событий бота
dispatcher = Dispatcher(bot, storage=MemoryStorage())

# Создаем состояние, в котором бот ждет сообщения от пользователя
class UserInput(StatesGroup):
    waiting_for_message = State()

# Создаем функцию, которая будет генерировать ответ на сообщение пользователя
async def generate_response(message: Message):
    # Получаем ID чата и последний ответ пользователя
    chat_id = message.chat.id
    last_message = message.text

    # Используем состояние для сохранения контекста диалога
    async with bot.get_db() as db:
        last_response = await db.get(chat_id)
        
    # Если уже был предыдущий ответ на сообщение пользователя, используем его как начальную точку
    if last_response:
        prompt = f"{last_message}{last_response}"
    else:
        prompt = last_message

    # Генерируем ответ с помощью модели Chat GPT
    response = openai.Completion.create(
        engine='text-davinci-003',
        prompt=prompt,
        max_tokens=2000,
        temperature=0.5,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.6,
        stop=["Stop:"]
    )

    # Обрабатываем ответ для улучшения его читаемости
    formatted_response = format_response(response.choices[0].text)

    # Сохраняем ответ в базу данных для использования в следующем диалоге
    async with bot.get_db() as db:
        await db.set(chat_id, formatted_response)

    # Отправляем сгенерированный ответ пользователю
    await message.answer(md.text(formatted_response))

# Создаем обработчик команды /start
@dispatcher.message_handler(commands=['start'])
async def start(message:Message):
    await message.answer(md.text("Привет! Я чат-бот, который использует модель Chat GPT для генерации ответов на твои сообщения."))

    # Ожидаем сообщение от пользователя
    await UserInput.waiting_for_message.set()

# Создаем обработчик текстовых сообщений
@dispatcher.message_handler(state=UserInput.waiting_for_message, content_types=types.ContentTypes.TEXT)
async def process_message(message: Message, state: FSMContext):

    await bot.send_chat_action(message.chat.id, "typing")

    # Генерируем ответ на сообщение пользователя
    await generate_response(message)

    # Ожидаем следующее сообщение от пользователя
    await UserInput.waiting_for_message.set()

@dispatcher.message_handler(commands=['stop'])
async def stop(message: Message):
    # Сбрасываем состояние диалога
    await UserInput.waiting_for_message.set()
    async with bot.get_db() as db:
    await db.delete(message.chat.id)
    await message.answer("Диалог завершен. Если хочешь начать заново, отправь мне сообщение.")

@dispatcher.message_handler(content_types=types.ContentTypes.ANY)
async def unknown(message: Message):
    await message.answer("Извините, я не понимаю вас. Пожалуйста, используйте команду /start, чтобы начать диалог.")

# Функция для форматирования ответа Chat GPT
def format_response(response):
    # Удаляем переносы строк из ответа
    response = response.replace("\n", "")

    # Заменяем последовательности пробелов на один пробел
    response = " ".join(response.split())



    # Возвращаем отформатированный ответ
    return response

# Запускаем бота
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dispatcher)
