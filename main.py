import os
import logging
import asyncio
import io
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from dotenv import load_dotenv
from aiohttp import web

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
CUSTOM_EMOJI_CREATE    = "6084717714847306634"   # 📌 (для кнопки "Создать сделку")

BANNER_URL = "https://i.ibb.co/KcVyKTVc/IMG-1682.jpg"

# ---------- Команда /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Текст без цифровых эмодзи — только премиум-эмодзи и HTML-теги
    text = (
        f"<b>{EMOJI_TROPHY} Добро пожаловать в Lolz Deals</b>\n\n"
        f"<b>{EMOJI_ROBOT} Ваш надёжный P2P-гарант:</b>\n"
        f"— <b>Автоматические сделки</b> с NFT и валютами\n"
        f"— {EMOJI_SHIELD} <b>Полная защита</b> обеих сторон\n"
        f"— {EMOJI_MONEY} <b>Реферальная программа</b> — <i>50% от комиссии</i>\n"
        f"— {EMOJI_PACKAGE} <b>Передача товаров</b> через менеджера: @LZSupp\n\n"
        f"{EMOJI_MEGAPHONE} <b>Канал:</b> @LiveLolz\n\n"
        f"<blockquote><b>Мои реквизиты:</b> {EMOJI_LIGHTNING} <b>Создать сделку</b></blockquote>"
    )

    # ---------- Симметричная клавиатура без кнопки "Сайт" ----------
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
        # Отдельный ряд для кнопки "Создать сделку" (на всю ширину)
        [
            InlineKeyboardButton(
                text="Создать сделку",
                icon_custom_emoji_id=CUSTOM_EMOJI_CREATE,
                callback_data="create"
            )
        ],
        # Отдельный расширенный ряд для "Техподдержка" (на всю ширину)
        [
            InlineKeyboardButton(
                text="Техподдержка",
                icon_custom_emoji_id=CUSTOM_EMOJI_SUPPORT,
                callback_data="support"
            )
        ]
    ])

    # Отправка баннера
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BANNER_URL) as resp:
                if resp.status == 200:
                    photo_data = await resp.read()
                    photo = InputFile(io.BytesIO(photo_data), filename="banner.jpg")
                    await message.answer_photo(
                        photo=photo,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при отправке фото: {e}")
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


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

@dp.callback_query(lambda c: c.data == "create")
async def cb_create(callback: types.CallbackQuery):
    await callback.answer("✍️ Создание новой сделки (заглушка)", show_alert=True)

@dp.callback_query(lambda c: c.data == "support")
async def cb_support(callback: types.CallbackQuery):
    await callback.answer("🛠 Связь с поддержкой: @LZSupportBot", show_alert=True)


# ---------- HTTP-сервер для Render (чтобы не падал) ----------
async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
