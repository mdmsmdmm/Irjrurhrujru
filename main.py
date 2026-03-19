import logging
import asyncio
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

# Настройки
BOT_TOKEN = "8781605873:AAEspoRLer5CV_axfPAVg3qyHnB2fBYpDuw"
CHANNEL_ID = "@rextu_love"  # Telegram канал для подписки
YOUTUBE_CHANNEL = "@rextuxu"  # YouTube канал для подписки
YOUTUBE_URL = "https://youtube.com/@rextuxu"
CHAT_ID = -1003722226864  # ID группы с топиками (обновлен!)
MODERATOR_IDS = [7688341117]  # ID администратора

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM
class ApplicationStates(StatesGroup):
    waiting_for_youtube_screenshot = State()
    waiting_for_video1_screenshot = State()
    waiting_for_video2_screenshot = State()
    waiting_for_comment = State()

# Вспомогательные функции
async def check_subscription(user_id: int) -> bool:
    """Проверка подписки на Telegram канал"""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

async def create_application_topic(user_id: int, username: str) -> Optional[int]:
    """Создание топика для заявки пользователя"""
    try:
        # Получаем имя пользователя
        user_info = await bot.get_chat(user_id)
        display_name = user_info.full_name or f"ID {user_id}"
        
        topic_name = f"📝 Заявка от {display_name}"
        result = await bot.create_forum_topic(
            chat_id=CHAT_ID,
            name=topic_name
        )
        return result.message_thread_id
    except Exception as e:
        logger.error(f"Ошибка создания топика: {e}")
        return None

# Клавиатуры
def get_start_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📝 Подать заявку на тестирование", callback_data="apply")],
        [
            InlineKeyboardButton(text="📢 Telegram канал", url="https://t.me/rextu_love"),
            InlineKeyboardButton(text="📺 YouTube канал", url=YOUTUBE_URL)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Да, всё верно", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm_no")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_moderation_keyboard(user_id: int):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Принять заявку", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Обработчики команд
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "👋 **Добро пожаловать в бота для тестирования мода Minecraft от @rextu_love!**\n\n"
        "Чтобы получить доступ к тестированию, выполните простые условия:\n\n"
        "1️⃣ **Подпишитесь на Telegram-канал** @rextu_love\n"
        "2️⃣ **Подпишитесь на YouTube-канал** @rextuxu (пришлите скриншот)\n"
        "3️⃣ **Поставьте лайк на последние 2 видео** (2 скриншота)\n\n"
        "После проверки модератор выдаст вам доступ к тестовой версии мода!\n\n"
        "👇 **Нажмите кнопку ниже, чтобы начать**"
    )
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_start_keyboard(),
        disable_web_page_preview=True
    )

@dp.callback_query(F.data == "apply")
async def process_apply(callback: CallbackQuery, state: FSMContext):
    # Проверяем подписку на Telegram канал
    await callback.message.edit_text(
        "🔄 **Проверяем подписку на Telegram-канал** @rextu_love...",
        parse_mode="Markdown"
    )
    
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text(
            "✅ **Подписка на Telegram-канал подтверждена!**\n\n"
            f"📺 **Теперь отправьте скриншот**, подтверждающий подписку на YouTube-канал [{YOUTUBE_CHANNEL}]({YOUTUBE_URL}).\n\n"
            "*Скриншот должен показывать, что вы подписаны на канал*",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        await state.set_state(ApplicationStates.waiting_for_youtube_screenshot)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на Telegram", url="https://t.me/rextu_love")],
            [InlineKeyboardButton(text="🔄 Я подписался, проверить", callback_data="apply")]
        ])
        await callback.message.edit_text(
            "❌ **Вы не подписаны на Telegram-канал** @rextu_love!\n\n"
            "Пожалуйста, подпишитесь и нажмите кнопку проверки.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

@dp.message(ApplicationStates.waiting_for_youtube_screenshot, F.photo)
async def process_youtube_screenshot(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    await state.update_data(youtube_screenshot=file.file_id)
    
    await message.answer(
        "✅ **Скриншот подписки на YouTube получен!**\n\n"
        "❤️ **Теперь отправьте скриншот** с лайком на **самое последнее видео** на канале @rextuxu.\n\n"
        "*Убедитесь, что на скриншоте видна кнопка лайка*",
        parse_mode="Markdown"
    )
    await state.set_state(ApplicationStates.waiting_for_video1_screenshot)

@dp.message(ApplicationStates.waiting_for_video1_screenshot, F.photo)
async def process_video1_screenshot(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    await state.update_data(video1_screenshot=file.file_id)
    
    await message.answer(
        "✅ **Первый лайк подтверждён!**\n\n"
        "❤️ **Теперь отправьте скриншот** с лайком на **второе (предпоследнее) видео** на канале @rextuxu.\n\n"
        "*Это важно для проверки активности*",
        parse_mode="Markdown"
    )
    await state.set_state(ApplicationStates.waiting_for_video2_screenshot)

@dp.message(ApplicationStates.waiting_for_video2_screenshot, F.photo)
async def process_video2_screenshot(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    await state.update_data(video2_screenshot=file.file_id)
    
    # Спрашиваем комментарий (опционально)
    await message.answer(
        "✅ **Все скриншоты получены!**\n\n"
        "💬 **Напишите краткий комментарий** (необязательно):\n"
        "- Почему хотите тестировать мод?\n"
        "- Сколько играете в Minecraft?\n"
        "- Какие моды уже использовали?\n\n"
        "Или отправьте \"-\" чтобы пропустить",
        parse_mode="Markdown"
    )
    await state.set_state(ApplicationStates.waiting_for_comment)

@dp.message(ApplicationStates.waiting_for_comment)
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text != "-" else "Без комментария"
    await state.update_data(comment=comment)
    
    # Собираем все данные
    data = await state.get_data()
    user = message.from_user
    
    # Создаём предварительный просмотр
    preview = (
        f"📋 **Проверьте данные заявки:**\n\n"
        f"👤 **Имя:** {user.full_name}\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"📱 **Username:** @{user.username if user.username else 'нет'}\n"
        f"💬 **Комментарий:** {data.get('comment', 'Без комментария')}\n\n"
        f"**Подтверждения:**\n"
        f"✅ Подписка на Telegram-канал @rextu_love\n"
        f"✅ Подписка на YouTube @rextuxu (скриншот)\n"
        f"✅ Лайк на последнее видео (скриншот)\n"
        f"✅ Лайк на предпоследнее видео (скриншот)\n\n"
        f"**Всё верно?**"
    )
    
    # Отправляем первый скриншот с превью
    await message.answer_photo(
        photo=data['youtube_screenshot'],
        caption=preview,
        parse_mode="Markdown",
        reply_markup=get_confirm_keyboard()
    )

@dp.callback_query(F.data.startswith("confirm_"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "confirm_yes":
        data = await state.get_data()
        user = callback.from_user
        
        # Сообщение о создании заявки
        await callback.message.edit_caption(
            caption="⏳ **Создаём вашу заявку...**",
            parse_mode="Markdown"
        )
        
        # Создаём топик для заявки
        topic_id = await create_application_topic(user.id, user.username or f"user_{user.id}")
        
        if topic_id:
            # Отправляем заявку в топик
            application_text = (
                f"📨 **Новая заявка на тестирование мода Minecraft**\n\n"
                f"👤 **Пользователь:** {user.full_name}\n"
                f"🆔 **ID:** `{user.id}`\n"
                f"📱 **Username:** @{user.username if user.username else 'Нет'}\n"
                f"💬 **Комментарий:** {data.get('comment', 'Без комментария')}\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"**Прикреплённые скриншоты:**"
            )
            
            await bot.send_message(
                chat_id=CHAT_ID,
                message_thread_id=topic_id,
                text=application_text,
                parse_mode="Markdown",
                reply_markup=get_moderation_keyboard(user.id)
            )
            
            # Отправляем скриншоты в топик
            screenshots = [
                ("📺 Подписка YouTube @rextuxu", data['youtube_screenshot']),
                ("❤️ Лайк на последнее видео", data['video1_screenshot']),
                ("❤️ Лайк на предпоследнее видео", data['video2_screenshot'])
            ]
            
            for caption, photo_id in screenshots:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    message_thread_id=topic_id,
                    photo=photo_id,
                    caption=caption
                )
            
            # Отправляем уведомление модератору в ЛС
            try:
                for mod_id in MODERATOR_IDS:
                    await bot.send_message(
                        chat_id=mod_id,
                        text=f"🔔 **Новая заявка** от {user.full_name}\n"
                             f"Перейдите в [группу с топиками](https://t.me/+XD6YfK8txVtjZDEy) для проверки",
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
            except:
                pass
            
            await callback.message.edit_caption(
                caption="✅ **Заявка успешно отправлена!**\n\n"
                        "Модератор проверит её в ближайшее время.\n"
                        "Вы получите уведомление о результате проверки.\n\n"
                        "Спасибо за интерес к нашему моду! 🎮",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_caption(
                caption="❌ **Произошла ошибка при создании заявки.**\n\n"
                        "Пожалуйста, попробуйте позже или свяжитесь с администратором: @rextu_love",
                parse_mode="Markdown"
            )
        
        await state.clear()
    else:
        await callback.message.edit_caption(
            caption="❌ **Заявка отменена.**\n\n"
                    "Если хотите подать заявку заново, нажмите /start",
            parse_mode="Markdown"
        )
        await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_application(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    
    try:
        # Уведомляем пользователя со ссылкой на Telegram канал вместо мода
        await bot.send_message(
            chat_id=user_id,
            text="✅ **Поздравляем!**\n\n"
                 "Ваша заявка на тестирование мода **ОДОБРЕНА**!\n\n"
                 "🎮 **Актуальная информация о моде:**\n"
                 "Подпишитесь на наш Telegram канал @rextu_love\n\n"
                 "📢 **В канале вы найдёте:**\n"
                 "• Ссылку на скачивание мода\n"
                 "• Инструкцию по установке\n"
                 "• Новости и обновления\n"
                 "• Поддержку игроков\n\n"
                 "👉 **Переходите:** https://t.me/rextu_love\n\n"
                 "Спасибо за поддержку! ❤️",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        # Обновляем сообщение в топике
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ **ЗАЯВКА ОДОБРЕНА** модератором",
            parse_mode="Markdown",
            reply_markup=None
        )
        
        await callback.answer("✅ Заявка одобрена, пользователь уведомлён!")
        
    except Exception as e:
        logger.error(f"Ошибка при одобрении заявки: {e}")
        await callback.answer("❌ Ошибка при отправке уведомления", show_alert=True)

@dp.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    
    try:
        # Уведомляем пользователя
        await bot.send_message(
            chat_id=user_id,
            text="❌ **К сожалению, ваша заявка отклонена**\n\n"
                 "**Возможные причины:**\n"
                 "• Скриншоты не показывают подписку на YouTube\n"
                 "• Лайки не видны на скриншотах\n"
                 "• Не те видео (нужны последние 2 видео)\n"
                 "• Скриншоты низкого качества\n\n"
                 "📝 **Вы можете подать заявку заново**, выполнив все условия правильно.\n\n"
                 "По вопросам: @rextu_love",
            parse_mode="Markdown"
        )
        
        # Обновляем сообщение в топике
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ **ЗАЯВКА ОТКЛОНЕНА** модератором",
            parse_mode="Markdown",
            reply_markup=None
        )
        
        await callback.answer("❌ Заявка отклонена, пользователь уведомлён!")
        
    except Exception as e:
        logger.error(f"Ошибка при отклонении заявки: {e}")
        await callback.answer("❌ Ошибка при отправке уведомления", show_alert=True)

@dp.message(Command("status"))
async def check_status(message: types.Message):
    await message.answer(
        "🔍 **Проверка статуса заявки**\n\n"
        "Если вы подавали заявку, модератор скоро её проверит.\n"
        "Вы получите уведомление о результате.\n\n"
        "По вопросам: @rextu_love",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_other_messages(message: types.Message):
    if message.photo:
        await message.answer(
            "📸 **Скриншот получен, но нужно начать заявку сначала.**\n"
            "Нажмите /start для подачи новой заявки",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❓ Используйте /start для начала работы с ботом",
            parse_mode="Markdown"
        )

async def main():
    logger.info("🚀 Бот для тестирования мода Minecraft запущен!")
    logger.info(f"Telegram канал: {CHANNEL_ID}")
    logger.info(f"YouTube канал: {YOUTUBE_CHANNEL}")
    logger.info(f"Группа с топиками: {CHAT_ID}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())