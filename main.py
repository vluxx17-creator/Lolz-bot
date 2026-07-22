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

# ---------- Премиум-эмодзи для текста ----------
EMOJI_TROPHY    = '<tg-emoji emoji-id="5893255507380014983">🏆</tg-emoji>'
EMOJI_ROBOT     = '<tg-emoji emoji-id="5794164805065514131">🤖</tg-emoji>'
EMOJI_SHIELD    = '<tg-emoji emoji-id="5794085322400733645">🛡</tg-emoji>'
EMOJI_MONEY     = '<tg-emoji emoji-id="5794280000383358988">💰</tg-emoji>'
EMOJI_PACKAGE   = '<tg-emoji emoji-id="5794241397217304511">📦</tg-emoji>'
EMOJI_MEGAPHONE = '<tg-emoji emoji-id="5893290369629556374">📢</tg-emoji>'

# ---------- ID премиум-эмодзи для кнопок ----------
CUSTOM_EMOJI_BALANCE   = "6041730074376410123"
CUSTOM_EMOJI_DEALS     = "5417924076503062111"
CUSTOM_EMOJI_REFERRALS = "5357080225463149588"
CUSTOM_EMOJI_LANG      = "5197269100878907942"
CUSTOM_EMOJI_REQUISITES = "6084717714847306634"
CUSTOM_EMOJI_CREATE    = "6084717714847306634"
CUSTOM_EMOJI_SUPPORT   = "5447410659077661506"

BANNER_URL = "https://i.ibb.co/KcVyKTVc/IMG-1682.jpg"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        f"<b>{EMOJI_TROPHY} Добро пожаловать в Lolz Deals</b>\n\n"
        f"<blockquote><b>{EMOJI_ROBOT} Ваш надёжный P2P-гарант:</b>\n"
        f"— <b>Автоматические сделки</b> с NFT и валютами\n"
        f"— {EMOJI_SHIELD} <b>Полная защита</b> обеих сторон\n"
        f"— {EMOJI_MONEY} <b>Реферальная программа</b> — <i>50% от комиссии</i>\n"
        f"— {EMOJI_PACKAGE} <b>Передача товаров</b> через менеджера: @LZSupp</blockquote>\n\n"
        f"{EMOJI_MEGAPHONE} <b>Канал:</b> @LiveLolz"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Баланс", icon_custom_emoji_id=CUSTOM_EMOJI_BALANCE, callback_data="balance"),
            InlineKeyboardButton(text="Мои сделки", icon_custom_emoji_id=CUSTOM_EMOJI_DEALS, callback_data="deals")
        ],
        [
            InlineKeyboardButton(text="Рефералы", icon_custom_emoji_id=CUSTOM_EMOJI_REFERRALS, callback_data="referrals"),
            InlineKeyboardButton(text="Язык / Lang", icon_custom_emoji_id=CUSTOM_EMOJI_LANG, callback_data="lang")
        ],
        [
            InlineKeyboardButton(text="Мои реквизиты", icon_custom_emoji_id=CUSTOM_EMOJI_REQUISITES, callback_data="requisites"),
            InlineKeyboardButton(text="Создать сделку", icon_custom_emoji_id=CUSTOM_EMOJI_CREATE, callback_data="create")
        ],
        [
            InlineKeyboardButton(text="Техподдержка", icon_custom_emoji_id=CUSTOM_EMOJI_SUPPORT, callback_data="support")
        ]
    ])

    # ---------- Отправка баннера с правильными заголовками ----------
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(BANNER_URL, timeout=10) as resp:
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
                    logging.error(f"Баннер не загружен: статус {resp.status}")
                    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка при скачивании баннера: {e}")
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "balance")
async def cb_balance(callback: types.CallbackQuery):
    await callback.answer("💰 Баланс: 0.00 ₽", show_alert=True)

@dp.callback_query(lambda c: c.data == "deals")
async def cb_deals(callback: types.CallbackQuery):
    await callback.answer("📋 Сделок нет", show_alert=True)

@dp.callback_query(lambda c: c.data == "referrals")
async def cb_referrals(callback: types.CallbackQuery):
    await callback.answer("👥 Рефералов: 0", show_alert=True)

@dp.callback_query(lambda c: c.data == "lang")
async def cb_lang(callback: types.CallbackQuery):
    await callback.answer("🌐 Язык: RU / EN", show_alert=True)

@dp.callback_query(lambda c: c.data == "requisites")
async def cb_requisites(callback: types.CallbackQuery):
    await callback.answer("💳 Реквизиты: карта ****, BTC...", show_alert=True)

@dp.callback_query(lambda c: c.data == "create")
async def cb_create(callback: types.CallbackQuery):
    await callback.answer("✍️ Создание сделки (заглушка)", show_alert=True)

@dp.callback_query(lambda c: c.data == "support")
async def cb_support(callback: types.CallbackQuery):
    await callback.answer("🛠 Поддержка: @LZSupportBot", show_alert=True)


# ---------- HTTP-сервер для Render ----------
async def health_check(request):
    return web.Response(text="OK")

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
