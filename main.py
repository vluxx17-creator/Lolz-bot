import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from dotenv import load_dotenv
import aiohttp
import io

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ---------- Премиум-эмодзи для текста (HTML) ----------
EMOJI_TROPHY    = '<tg-emoji emoji-id="5893255507380014983">🏆</tg-emoji>'
EMOJI_LIGHTNING = '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>'
EMOJI_ROBOT     = '<tg-emoji emoji-id="5794164805065514131">🤖</tg-emoji>'
EMOJI_SHIELD    = '<tg-emoji emoji-id="5794085322400733645">🛡</tg-emoji>'
EMOJI_MONEY     = '<tg-emoji emoji-id="5794280000383358988">💰</tg-emoji>'
EMOJI_PACKAGE   = '<tg-emoji emoji-id="5794241397217304511">📦</tg-emoji>'
EMOJI_MEGAPHONE = '<tg-emoji emoji-id="5893290369629556374">📢</tg-emoji>'

# ---------- ID премиум-эмодзи для кнопок ----------
CUSTOM_EMOJI_BALANCE   = "6041730074376410123"   # 📥
CUSTOM_EMOJI_DEALS     = "5417924076503062111"   # 💰
CUSTOM_EMOJI_REFERRALS = "5357080225463149588"   # 🤝
CUSTOM_EMOJI_LANG      = "5197269100878907942"   # ✍️
CUSTOM_EMOJI_SUPPORT   = "5447410659077661506"   # 🌐
CUSTOM_EMOJI_SITE      = "5258503720928288433"   # ℹ️
CUSTOM_EMOJI_MESSAGE   = "6084717714847306634"   # 📌
CUSTOM_EMOJI_CREATE    = "6084717714847306634"   # 📌 (для кнопки "Создать сделку")

# ---------- URL баннера ----------
BANNER_URL = "https://i.ibb.co/KcVyKTVc/IMG-1682.jpg"

# ---------- Команда /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Формируем текст с HTML-разметкой (жирный, курсив, цитата)
    text = (
        f"<b>{EMOJI_TROPHY} Добро пожаловать в Lolz Deals</b>\n\n"
        f"<b>{EMOJI_ROBOT} Ваш надёжный P2P-гарант:</b>\n"
        f"1️⃣ <b>Автоматические сделки</b> с NFT и валютами\n"
        f"2️⃣ {EMOJI_SHIELD} <b>Полная защита</b> обеих сторон\n"
        f"3️⃣ {EMOJI_MONEY} <b>Реферальная программа</b> — <i>50% от комиссии</i>\n"
        f"4️⃣ {EMOJI_PACKAGE} <b>Передача товаров</b> через менеджера: @LZSupp\n\n"
        f"{EMOJI_MEGAPHONE} <b>Канал:</b> @LiveLolz\n\n"
        f"<blockquote><b>Мои реквизиты:</b> {EMOJI_LIGHTNING} <b>Создать сделку</b></blockquote>"
    )

    # ---------- Симметричная инлайн-клавиатура (2 кнопки в ряду) ----------
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Баланс",
                icon_custom_emoji_id=CUSTOM_EMOJI_BALANCE,
                callback_data="balance"
            ),
            InlineKeyboardButton(
                text="Мои сделки",
                icon_custom_emoji_id=CUSTOM_EMOJI_DEALS,
                callback_data="deals"
            )
        ],
        [
            InlineKeyboardButton(
                text="Рефералы",
                icon_custom_emoji_id=CUSTOM_EMOJI_REFERRALS,
                callback_data="referrals"
            ),
            InlineKeyboardButton(
                text="Язык / Lang",
                icon_custom_emoji_id=CUSTOM_EMOJI_LANG,
                callback_data="lang"
            )
        ],
        [
            InlineKeyboardButton(
                text="Техподдержка",
                icon_custom_emoji_id=CUSTOM_EMOJI_SUPPORT,
                callback_data="support"
            ),
            InlineKeyboardButton(
                text="Сайт",
                icon_custom_emoji_id=CUSTOM_EMOJI_SITE,
                url="https://lolz.live"
            )
        ]
    ])

    # ---------- Отправка фото с подписью и клавиатурой ----------
    try:
        # Скачиваем баннер из интернета
        async with aiohttp.ClientSession() as session:
            async with session.get(BANNER_URL) as resp:
                if resp.status == 200:
                    photo_data = await resp.read()
                    photo_file = io.BytesIO(photo_data)
                    photo_file.name = "banner.jpg"
                    
                    await message.answer_photo(
                        photo=FSInputFile(photo_file),
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    # Если баннер не загрузился — отправляем только текст
                    await message.answer(
                        text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
    except Exception:
        # В случае любой ошибки с фото — отправляем только текст
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


# ---------- Обработчики нажатий ----------
@dp.callback_query(lambda c: c.data == "balance")
async def cb_balance(callback: types.CallbackQuery):
    await callback.answer("💰 Ваш баланс: 0.00 ₽", show_alert=True)

@dp.callback_query(lambda c: c.data == "deals")
async def cb_deals(callback: types.CallbackQuery):
    await callback.answer("📋 Список ваших сделок пуст", show_alert=True)

@dp.callback_query(lambda c: c.data == "referrals")
async def cb_referrals(callback: types.CallbackQuery):
    await callback.answer("👥 Приглашено рефералов: 0", show_alert=True)

@dp.callback_query(lambda c: c.data == "lang")
async def cb_lang(callback: types.CallbackQuery):
    await callback.answer("🌐 Выберите язык: /lang_ru или /lang_en", show_alert=True)

@dp.callback_query(lambda c: c.data == "support")
async def cb_support(callback: types.CallbackQuery):
    await callback.answer("🛠 Связь с поддержкой: @LZSupportBot", show_alert=True)


# ---------- Запуск ----------
if __name__ == "__main__":
    dp.run_polling(bot)
