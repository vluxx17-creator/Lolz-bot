import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

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

# ---------- ID премиум-эмодзи для кнопок (из задания) ----------
CUSTOM_EMOJI_BALANCE   = "6041730074376410123"   # 📥
CUSTOM_EMOJI_DEALS     = "5417924076503062111"   # 💰
CUSTOM_EMOJI_REFERRALS = "5357080225463149588"   # 🤝
CUSTOM_EMOJI_LANG      = "5197269100878907942"   # ✍️
CUSTOM_EMOJI_SUPPORT   = "5447410659077661506"   # 🌐
CUSTOM_EMOJI_SITE      = "5258503720928288433"   # ℹ️
CUSTOM_EMOJI_MESSAGE   = "6084717714847306634"   # 📌

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        f"<b>{EMOJI_TROPHY} Lolz Deals</b>\n"
        f"121 605 пользователей\n\n"
        f"<b>Закреплённое сообщение</b>\n"
        f"✅ Добро пожаловать в команду поддерж...\n\n"
        f"<b>{EMOJI_LIGHTNING} Добро пожаловать в Lolz Deals</b>\n\n"
        f"{EMOJI_ROBOT} <b>Ваш надёжный P2P-гарант:</b>\n"
        f"1️⃣ Автоматические сделки с NFT и валютами\n"
        f"2️⃣ {EMOJI_SHIELD} Полная защита обеих сторон\n"
        f"3️⃣ {EMOJI_MONEY} Реферальная программа — 50% от комиссии\n"
        f"4️⃣ {EMOJI_PACKAGE} Передача товаров через менеджера: @LZSurp\n\n"
        f"{EMOJI_MEGAPHONE} <b>Канал:</b> @LiveLolz\n"
        f"00:50\n\n"
        f"<b>Мои реквизиты:</b>"
    )

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
            ),
            InlineKeyboardButton(
                text="Сообщение",
                icon_custom_emoji_id=CUSTOM_EMOJI_MESSAGE,
                callback_data="message"
            )
        ]
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


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

@dp.callback_query(lambda c: c.data == "message")
async def cb_message(callback: types.CallbackQuery):
    await callback.answer("✍️ Отправьте ваше сообщение в этот чат", show_alert=True)


if __name__ == "__main__":
    dp.run_polling(bot)
