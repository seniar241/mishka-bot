from dotenv import load_dotenv
import os
import sqlite3
import telebot
import numpy as np
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import random
from datetime import datetime

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
bot = telebot.TeleBot(API_TOKEN, skip_pending=True)

ADMIN_USERNAMES = ['seniartys'] 
REQUIRED_CHANNELS = ['@aaxf566'] 
BOT_USERNAME = 'refkafchat_bot'
MAX_WINNERS = 1

def is_admin(message):
    username = message.from_user.username
    if not username:
        return False
    return username.lower() in [admin.lower() for admin in ADMIN_USERNAMES]

def execute_query(query, parameters=()):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, parameters)
        conn.commit()
        return cursor

def init_db():
    execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            referral_code TEXT,
            inviter INTEGER,
            invites_count INTEGER DEFAULT 0,
            particip INTEGER DEFAULT 0,
            last_bonus_time INTEGER DEFAULT 0,
            last_task_time INTEGER DEFAULT 0,
            task_completed INTEGER DEFAULT 0
        )
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS referral_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER,
            invited_id INTEGER,
            invited_username TEXT,
            join_time TEXT
        )
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS points_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            reason TEXT,
            action_time TEXT
        )
    """)

init_db()

def check_subscriptions(user_id):
    for channel in REQUIRED_CHANNELS:
        if not is_subscribed(user_id, channel):
            return False, channel
    return True, None

def is_subscribed(user_id, channel_id):
    try:
        status = bot.get_chat_member(channel_id, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    btn_top = InlineKeyboardButton("🏆 Топ", callback_data="show_top")
    btn_profile = InlineKeyboardButton("👤 Мой профиль", callback_data="show_profile")
    btn_link = InlineKeyboardButton("🔗 Моя ссылка", callback_data="show_link")
    btn_bonus = InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily_bonus")
    btn_refs = InlineKeyboardButton("👥 Мои рефералы", callback_data="my_referrals")
    btn_task = InlineKeyboardButton("📜 Задание дня", callback_data="daily_task")
    
    markup.add(btn_top, btn_profile)
    markup.add(btn_link, btn_bonus)
    markup.add(btn_refs, btn_task)
    return markup

def get_welcome_text():
    return (
        f'<b>🐻 Добро пожаловать в Битву за Мишек!</b>\n\n'
        f'Хочешь забрать приз? Всё просто: собирай друзей и зарабатывай очки!\n\n'
        f'<b>Как это работает:</b>\n'
        f'1️⃣ Приглашай друзей по своей личной ссылке.\n'
        f'2️⃣ Получай <b>1 очко</b> за каждого, кто зайдёт.\n'
        f'3️⃣ Заходи каждый день и забирай <b>ежедневный бонус</b> (до 5 очков!).\n'
        f'4️⃣ Выполняй <b>задание дня</b> в нашем чате.\n'
        f'5️⃣ Кто наберёт больше всех очков — тот и уносит мишку! 🏆\n\n'
        f'⚠️ <b>Внимание!</b> Чтобы начать, тебе нужно подписаться на группу:\n'
        f'🔗 <a href="https://t.me/aaxf566">@aaxf566</a>\n\n'
        f'✨ После подписки жми кнопку ниже.'
    )

def get_active_user_text():
    return (
        f'<b>🐻 Ты в игре, охотник!</b>\n\n'
        f'Твоя задача — приглашать друзей и собирать очки. Чем больше очков, тем выше ты в топе и тем больше шансов забрать мишку.\n\n'
        f'Жми на кнопки ниже, чтобы посмотреть свои очки или скопировать ссылку.'
    )

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_data = execute_query("SELECT particip FROM users WHERE telegram_id = ?", (user_id,)).fetchone()

    if user_data:
        if user_data[0] == 1: 
            bot.send_message(message.chat.id, get_active_user_text(), parse_mode='HTML', reply_markup=get_main_menu())
        else: 
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="🎉 Участвовать", callback_data="participate"))
            bot.send_message(message.chat.id, get_welcome_text(), parse_mode='HTML', reply_markup=markup)
    else:
        args = message.text.split()
        referral_link = f'{user_id}'
        inviter_id = None

        if len(args) > 1:
            ref_code = args[1]
            inviter = execute_query("SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code,)).fetchone()
            if inviter:
                inviter_id = inviter[0]
                execute_query("UPDATE users SET invites_count = invites_count + 1 WHERE telegram_id = ?", (inviter_id,))
                now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                invited_username = message.from_user.username or "Нет юзернейма"
                
                execute_query("INSERT INTO referral_history (inviter_id, invited_id, invited_username, join_time) VALUES (?, ?, ?, ?)", (inviter_id, user_id, invited_username, now_str))
                reason_text = f"Реферал @{invited_username} (ID: {user_id})"
                execute_query("INSERT INTO points_history (user_id, amount, reason, action_time) VALUES (?, ?, ?, ?)", (inviter_id, 1, reason_text, now_str))
                
                try:
                    bot.send_message(inviter_id, f"🎉 Тебе засчитано очко! Кто-то зашел по твоей ссылке.")
                except:
                    pass

        execute_query("INSERT INTO users (telegram_id, referral_code, inviter, invites_count, last_bonus_time, last_task_time) VALUES (?, ?, ?, ?, ?, ?)", (user_id, referral_link, inviter_id, 0, 0, 0))

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="🎉 Участвовать", callback_data="participate"))
        bot.send_message(message.chat.id, get_welcome_text(), parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "participate")
def participate(call):
    user_id = call.from_user.id
    user = execute_query("SELECT particip FROM users WHERE telegram_id = ?", (user_id,)).fetchone()

    if user is None:
        bot.answer_callback_query(call.id, text='❌ Напиши /start, чтобы начать.', show_alert=True)
        return

    subscribed, _ = check_subscriptions(user_id)
    if not subscribed:
        bot.answer_callback_query(call.id, text='⚠️ Ты не подписан на группу! Подпишись и попробуй снова.', show_alert=True)
        return

    if user[0] == 0:
        execute_query("UPDATE users SET particip = 1 WHERE telegram_id = ?", (user_id,))
        
        invite_link = f'https://t.me/{BOT_USERNAME}?start={user_id}'
        text = (
            f'🎉 <b>Ты в игре!</b>\n\n'
            f'❗️ Вот твоя уникальная ссылка:\n<a href="{invite_link}">{invite_link}</a>\n\n'
            f'Кидай её друзьям. За каждого, кто зайдет и пройдет регистрацию, ты получишь <b>1 очко</b>.\n'
            f'Не забывай забирать ежедневный бонус! 🎁'
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=text, parse_mode='HTML', reply_markup=get_main_menu(), disable_web_page_preview=True)
        bot.answer_callback_query(call.id, text='🎉 Ты в игре!', show_alert=True)
    else:
        bot.answer_callback_query(call.id, text='Ты уже участвуешь!', show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "daily_task")
def daily_task(call):
    user_id = call.from_user.id
    data = execute_query("SELECT last_task_time, task_completed FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
    
    if not data:
        bot.answer_callback_query(call.id, text="❌ Напиши /start", show_alert=True)
        return
        
    last_time, task_completed = data
    current_time = int(time.time())
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    if task_completed == 1:
        execute_query("UPDATE users SET invites_count = invites_count + 1, task_completed = 0, last_task_time = ? WHERE telegram_id = ?", (current_time, user_id))
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        execute_query("INSERT INTO points_history (user_id, amount, reason, action_time) VALUES (?, ?, ?, ?)", (user_id, 1, "Выполнение задания дня", now_str))
        
        text = (
            f"🎉 <b>Награда получена!</b>\n\n"
            f"Ты выполнил задание и получил <b>1 очко</b>.\n"
            f"Возвращайся завтра за новым заданием!"
        )
        bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())
        return

    if current_time - last_time < 86400:
        remaining_seconds = 86400 - (current_time - last_time)
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        
        text = (
            f"✅ <b>Задание выполнено!</b>\n\n"
            f"Ты уже получил очко за сегодня.\n"
            f"Новое задание будет через <b>{hours} ч. {minutes} мин.</b>"
        )
        bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())
        return
        
    words = ["МИШКА", "ТОП", "ПРИЗ", "ОХОТА", "ПОБЕДА", "БИТВА"]
    task_word = random.choice(words)
        
    text = (
        f"📜 <b>Твоё задание на сегодня:</b>\n\n"
        f"Перейди в наш чат: <a href='https://t.me/aaxf566'>@aaxf566</a>\n"
        f"И напиши там слово: <code>{task_word}</code>\n\n"
        f"После этого возвращайся сюда и жми кнопку, чтобы забрать награду!"
    )
    bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())

# ОБРАБОТЧИК ЧАТА (без удаления и без спама)
@bot.message_handler(func=lambda message: True)
def check_task_word(message):
    if message.chat.type in ['group', 'supergroup']:
        user_id = message.from_user.id
        if not message.text:
            return
            
        text = message.text.upper().strip()
        
        user_data = execute_query("SELECT last_task_time, task_completed FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
        if not user_data:
            return 
            
        last_task_time, task_completed = user_data
        current_time = int(time.time())
            
        words = ["МИШКА", "ТОП", "ПРИЗ", "ОХОТА", "ПОБЕДА", "БИТВА"]
        
        if text in words:
            # Если он уже выполнил сегодня - просто игнорируем
            if current_time - last_task_time < 86400 or task_completed == 1:
                return

            # Если еще не выполнил - отмечаем и пишем ОДИН раз
            execute_query("UPDATE users SET task_completed = 1 WHERE telegram_id = ?", (user_id,))
            bot.send_message(message.chat.id, f"✅ @{message.from_user.username}, задание выполнено! Перейди в бота и нажми «Задание дня», чтобы забрать награду.")
