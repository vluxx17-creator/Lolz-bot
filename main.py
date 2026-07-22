import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

BANNER_URL = os.getenv("BANNER_URL", "https://i.ibb.co/KcVyKTVc/IMG-1682.jpg")

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ---------- Хранилище языков пользователей ----------
user_lang = {}  # user_id: 'ru' или 'en'

# ---------- Премиум-эмодзи ----------
EMOJI_TROPHY    = '<tg-emoji emoji-id="5893255507380014983">🏆</tg-emoji>'
EMOJI_ROBOT     = '<tg-emoji emoji-id="5794164805065514131">🤖</tg-emoji>'
EMOJI_SHIELD    = '<tg-emoji emoji-id="5794085322400733645">🛡</tg-emoji>'
EMOJI_MONEY     = '<tg-emoji emoji-id="5794280000383358988">💰</tg-emoji>'
EMOJI_PACKAGE   = '<tg-emoji emoji-id="5794241397217304511">📦</tg-emoji>'
EMOJI_MEGAPHONE = '<tg-emoji emoji-id="5893290369629556374">📢</tg-emoji>'
EMOJI_FLAG_RU   = '🇷🇺'   # обычный эмодзи
EMOJI_FLAG_US   = '🇺🇸'   # обычный эмодзи
EMOJI_GLOSSARY  = '<tg-emoji emoji-id="5893255507380014983">📖</tg-emoji>'  # для красоты

# ---------- ID премиум-эмодзи для кнопок ----------
CUSTOM_EMOJI_BALANCE   = "6041730074376410123"
CUSTOM_EMOJI_DEALS     = "5417924076503062111"
CUSTOM_EMOJI_REFERRALS = "5357080225463149588"
CUSTOM_EMOJI_LANG      = "5197269100878907942"
CUSTOM_EMOJI_REQUISITES = "6084717714847306634"
CUSTOM_EMOJI_CREATE    = "6084717714847306634"
CUSTOM_EMOJI_SUPPORT   = "5447410659077661506"
CUSTOM_EMOJI_COPY      = "6084717714847306634"   # для кнопки "Скопировать"
CUSTOM_EMOJI_BACK      = "5197269100878907942"   # для кнопки "Назад"

# ---------- Тексты для разных языков ----------
TEXTS = {
    'ru': {
        'welcome': (
            f"<b>{EMOJI_TROPHY} Добро пожаловать в Lolz Deals</b>\n\n"
            f"<blockquote><b>{EMOJI_ROBOT} Ваш надёжный P2P-гарант:</b>\n"
            f"— <b>Автоматические сделки</b> с NFT и валютами\n"
            f"— {EMOJI_SHIELD} <b>Полная защита</b> обеих сторон\n"
            f"— {EMOJI_MONEY} <b>Реферальная программа</b> — <i>50% от комиссии</i>\n"
            f"— {EMOJI_PACKAGE} <b>Передача товаров</b> через менеджера: @LZSupp</blockquote>\n\n"
            f"{EMOJI_MEGAPHONE} <b>Канал:</b> @LiveLolz"
        ),
        'lang_prompt': (
            f"<b>{EMOJI_GLOSSARY} Выберите язык:</b>\n"
            f"<i>изменено 22:58</i>"
        ),
        'lang_ru': "Русский",
        'lang_en': "English",
        'referral_title': (
            f"<b>{EMOJI_MONEY} Реферальная программа</b>"
        ),
        'referral_body': (
            f"<blockquote><b>Ваша ссылка:</b>\n"
            f"<code>{REF_LINK_TEMPLATE}</code>\n"
            f"<b>Рефералов:</b> 0\n"
            f"<b>Заработано:</b> 0.0 TON</blockquote>\n\n"
            f"<b>Бонус:</b> 50% от комиссии с каждой сделки реферала!\n"
            f"<i>изменено 22:58</i>"
        ),
        'copy_btn': "Скопировать реф. ссылку",
        'back_btn': "Назад в меню",
        'main_buttons': {
            'balance': "Баланс",
            'deals': "Мои сделки",
            'referrals': "Рефералы",
            'lang': "Язык / Lang",
            'requisites': "Мои реквизиты",
            'create': "Создать сделку",
            'support': "Техподдержка"
        }
    },
    'en': {
        'welcome': (
            f"<b>{EMOJI_TROPHY} Welcome to Lolz Deals</b>\n\n"
            f"<blockquote><b>{EMOJI_ROBOT} Your trusted P2P guarantor:</b>\n"
            f"— <b>Automated deals</b> with NFTs and currencies\n"
            f"— {EMOJI_SHIELD} <b>Full protection</b> for both parties\n"
            f"— {EMOJI_MONEY} <b>Referral program</b> — <i>50% of fee</i>\n"
            f"— {EMOJI_PACKAGE} <b>Goods transfer</b> via manager: @LZSupp</blockquote>\n\n"
            f"{EMOJI_MEGAPHONE} <b>Channel:</b> @LiveLolz"
        ),
        'lang_prompt': (
            f"<b>{EMOJI_GLOSSARY} Select language:</b>\n"
            f"<i>changed 22:58</i>"
        ),
        'lang_ru': "Russian",
        'lang_en': "English",
        'referral_title': (
            f"<b>{EMOJI_MONEY} Referral program</b>"
        ),
        'referral_body': (
            f"<blockquote><b>Your referral link:</b>\n"
            f"<code>{REF_LINK_TEMPLATE}</code>\n"
            f"<b>Referrals:</b> 0\n"
            f"<b>Earned:</b> 0.0 TON</blockquote>\n\n"
            f"<b>Bonus:</b> 50% of commission from each referral deal!\n"
            f"<i>changed 22:58</i>"
        ),
        'copy_btn': "Copy referral link",
        'back_btn': "Back to menu",
        'main_buttons': {
            'balance': "Balance",
            'deals': "My deals",
            'referrals': "Referrals",
            'lang': "Language / Lang",
            'requisites': "My requisites",
            'create': "Create deal",
            'support': "Support"
        }
    }
}

# Шаблон ссылки (замените @lolzgaranterbot на актуальное имя бота)
REF_LINK_TEMPLATE = "https://t.me/lolzgaranterbot?start=ref{user_id}"

# ---------- Вспомогательные функции ----------
def get_text(user_id: int, key: str, **kwargs) -> str:
    lang = user_lang.get(user_id, 'ru')
    text = TEXTS[lang].get(key, TEXTS['ru'][key])
    if key == 'referral_body':
        # подставляем ссылку с user_id
        ref_link = REF_LINK_TEMPLATE.format(user_id=user_id)
        # заменяем плейсхолдер в тексте (если есть)
        # но у нас в шаблоне REF_LINK_TEMPLATE, поэтому подставим напрямую
        # но text содержит плейсхолдер {REF_LINK_TEMPLATE}? Лучше динамически
        # переделаем: используем format с переданным ref_link
        return text.replace('{REF_LINK_TEMPLATE}', ref_link)
    return text

def get_button_text(user_id: int, btn_key: str) -> str:
    lang = user_lang.get(user_id, 'ru')
    return TEXTS[lang]['main_buttons'].get(btn_key, TEXTS['ru']['main_buttons'][btn_key])

# ---------- Главное меню ----------
async def show_main_menu(message: types.Message, user_id: int, edit: bool = False):
    text = get_text(user_id, 'welcome')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_button_text(user_id, 'balance'), icon_custom_emoji_id=CUSTOM_EMOJI_BALANCE, callback_data="balance"),
            InlineKeyboardButton(text=get_button_text(user_id, 'deals'), icon_custom_emoji_id=CUSTOM_EMOJI_DEALS, callback_data="deals")
        ],
        [
            InlineKeyboardButton(text=get_button_text(user_id, 'referrals'), icon_custom_emoji_id=CUSTOM_EMOJI_REFERRALS, callback_data="referrals"),
            InlineKeyboardButton(text=get_button_text(user_id, 'lang'), icon_custom_emoji_id=CUSTOM_EMOJI_LANG, callback_data="lang")
        ],
        [
            InlineKeyboardButton(text=get_button_text(user_id, 'requisites'), icon_custom_emoji_id=CUSTOM_EMOJI_REQUISITES, callback_data="requisites"),
            InlineKeyboardButton(text=get_button_text(user_id, 'create'), icon_custom_emoji_id=CUSTOM_EMOJI_CREATE, callback_data="create")
        ],
        [
            InlineKeyboardButton(text=get_button_text(user_id, 'support'), icon_custom_emoji_id=CUSTOM_EMOJI_SUPPORT, callback_data="support")
        ]
    ])

    if edit:
        await message.edit_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
    else:
        # Отправляем с баннером
        try:
            await message.answer_photo(photo=BANNER_URL, caption=text, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка отправки баннера: {e}")
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

# ---------- Команда /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_lang:
        user_lang[user_id] = 'ru'  # по умолчанию русский
    await show_main_menu(message, user_id)

# ---------- Обработчик выбора языка ----------
@dp.callback_query(lambda c: c.data == "lang")
async def cb_lang(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'lang_prompt')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{EMOJI_FLAG_RU} {get_text(user_id, 'lang_ru')}", callback_data="lang_ru"),
            InlineKeyboardButton(text=f"{EMOJI_FLAG_US} {get_text(user_id, 'lang_en')}", callback_data="lang_en")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")
        ]
    ])
    # Редактируем текущее сообщение (если это возможно) или отправляем новое
    try:
        await callback.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=keyboard)
    except:
        # если не удалось отредактировать (например, это не фото), отправляем новое
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def cb_lang_set(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[1]  # 'ru' или 'en'
    user_lang[user_id] = lang_code
    # Возвращаем главное меню с новым языком
    # Редактируем текущее сообщение или отправляем новое
    await show_main_menu(callback.message, user_id, edit=False)  # отправляем новое, так как фото может быть другое
    await callback.answer()

# ---------- Реферальная страница ----------
@dp.callback_query(lambda c: c.data == "referrals")
async def cb_referrals(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    title = get_text(user_id, 'referral_title')
    body = get_text(user_id, 'referral_body', user_id=user_id)  # передаём user_id для ссылки
    text = f"{title}\n\n{body}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(user_id, 'copy_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_COPY, callback_data="copy_ref")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")
        ]
    ])
    # Отправляем новым сообщением (без баннера)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "copy_ref")
async def cb_copy_ref(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    ref_link = REF_LINK_TEMPLATE.format(user_id=user_id)
    # Показываем ссылку в alert для копирования
    await callback.answer(f"Ссылка скопирована:\n{ref_link}", show_alert=True)
    # Также можно отправить сообщение с текстом, но пока просто алерт

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # Отправляем главное меню новым сообщением (с баннером)
    await show_main_menu(callback.message, user_id, edit=False)
    await callback.answer()

# ---------- Остальные обработчики ----------
@dp.callback_query(lambda c: c.data == "balance")
async def cb_balance(callback: types.CallbackQuery):
    lang = user_lang.get(callback.from_user.id, 'ru')
    msg = "💰 Баланс: 0.00 ₽" if lang == 'ru' else "💰 Balance: 0.00 ₽"
    await callback.answer(msg, show_alert=True)

@dp.callback_query(lambda c: c.data == "deals")
async def cb_deals(callback: types.CallbackQuery):
    lang = user_lang.get(callback.from_user.id, 'ru')
    msg = "📋 Сделок нет" if lang == 'ru' else "📋 No deals"
    await callback.answer(msg, show_alert=True)

@dp.callback_query(lambda c: c.data == "requisites")
async def cb_requisites(callback: types.CallbackQuery):
    lang = user_lang.get(callback.from_user.id, 'ru')
    msg = "💳 Реквизиты: карта ****, BTC..." if lang == 'ru' else "💳 Requisites: card ****, BTC..."
    await callback.answer(msg, show_alert=True)

@dp.callback_query(lambda c: c.data == "create")
async def cb_create(callback: types.CallbackQuery):
    lang = user_lang.get(callback.from_user.id, 'ru')
    msg = "✍️ Создание сделки (заглушка)" if lang == 'ru' else "✍️ Create deal (stub)"
    await callback.answer(msg, show_alert=True)

@dp.callback_query(lambda c: c.data == "support")
async def cb_support(callback: types.CallbackQuery):
    lang = user_lang.get(callback.from_user.id, 'ru')
    msg = "🛠 Поддержка: @LZSupportBot" if lang == 'ru' else "🛠 Support: @LZSupportBot"
    await callback.answer(msg, show_alert=True)

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
