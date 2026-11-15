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

# ТВОЙ ID
ADMIN_IDS = [1638663913] 
REQUIRED_CHANNELS = ['@aaxf566'] 
BOT_USERNAME = 'refkafchat_bot'
MAX_WINNERS = 1

def is_admin(message):
    return message.from_user.id in ADMIN_IDS

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
            if current_time - last_task_time < 86400 or task_completed == 1:
                return

            execute_query("UPDATE users SET task_completed = 1 WHERE telegram_id = ?", (user_id,))
            bot.send_message(message.chat.id, f"✅ @{message.from_user.username}, задание выполнено! Перейди в бота и нажми «Задание дня», чтобы забрать награду.")

@bot.callback_query_handler(func=lambda call: call.data == "daily_bonus")
def daily_bonus(call):
    user_id = call.from_user.id
    data = execute_query("SELECT last_bonus_time FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
    
    if not data:
        bot.answer_callback_query(call.id, text="❌ Напиши /start", show_alert=True)
        return
        
    last_time = data[0]
    current_time = int(time.time())
    
    if current_time - last_time >= 86400:
        rand_val = random.random()
        if rand_val < 0.70:
            bonus_points = 1
        elif rand_val < 0.90:
            bonus_points = 2
        elif rand_val < 0.99:
            bonus_points = 3
        else:
            bonus_points = 5

        execute_query("UPDATE users SET invites_count = invites_count + ?, last_bonus_time = ? WHERE telegram_id = ?", (bonus_points, current_time, user_id))
        
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        execute_query("INSERT INTO points_history (user_id, amount, reason, action_time) VALUES (?, ?, ?, ?)", (user_id, bonus_points, "Ежедневный бонус", now_str))
        
        if bonus_points == 1:
            msg = "🎁 Бонус получен! Тебе начислено 1 очко."
        elif bonus_points == 2:
            msg = "🎁 Ого! Бонус получен! Тебе начислено 2 очка."
        elif bonus_points == 3:
            msg = "🔥 Крупный улов! Бонус получен! Тебе начислено 3 очка!"
        else:
            msg = "💥 ДЖЕКПОТ! Тебе выпало 5 очков! 🎉"
            
        bot.answer_callback_query(call.id, text=msg, show_alert=True)
    else:
        remaining_seconds = 86400 - (current_time - last_time)
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        bot.answer_callback_query(call.id, text=f"⏳ Ты уже забирал бонус. Следующий через {hours} ч. {minutes} мин.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "show_link")
def show_link(call):
    user_id = call.from_user.id
    data = execute_query("SELECT referral_code FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
    if not data:
        bot.answer_callback_query(call.id, text="❌ Ошибка. Напиши /start", show_alert=True)
        return
        
    invite_link = f"https://t.me/{BOT_USERNAME}?start={data[0]}"
    text = (
        f"🔗 <b>Твоя реферальная ссылка:</b>\n\n"
        f"<code>{invite_link}</code>\n\n"
        f"Нажми на ссылку, чтобы скопировать её, и отправляй друзьям!"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=text, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data == "my_referrals")
def show_my_referrals(call):
    user_id = call.from_user.id
    history = execute_query("SELECT invited_id, invited_username, join_time FROM referral_history WHERE inviter_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    
    if not history:
        text = "👥 <b>Твои рефералы</b>\n\nПока никого нет. Кидай свою ссылку друзьям, и они появятся здесь!"
    else:
        text = f"👥 <b>Твои рефералы (всего {len(history)}):</b>\n\n"
        for i, record in enumerate(history[:20], 1):
            inv_id, inv_username, join_time = record
            name = f"@{inv_username}" if inv_username != "Нет юзернейма" else f"ID:{inv_id}"
            date_only = join_time.split()[0] 
            text += f"{i}. {name} ({date_only})\n"
        if len(history) > 20:
            text += f"\n...и еще {len(history) - 20} чел."

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_profile")
def show_profile(call):
    user_id = call.from_user.id
    data = execute_query("SELECT invites_count, last_bonus_time FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
    if not data:
        bot.answer_callback_query(call.id, text="❌ Ты не найден в базе. Напиши /start", show_alert=True)
        return
        
    invites, last_bonus = data
    
    rank_data = execute_query("SELECT COUNT(*) FROM users WHERE invites_count > ?", (invites,)).fetchone()
    rank = rank_data[0] + 1 if invites > 0 else "—"
    
    current_time = int(time.time())
    if current_time - last_bonus >= 86400:
        bonus_status = "Доступен! 🎁"
    else:
        remaining = 86400 - (current_time - last_bonus)
        bonus_status = f"Через {remaining // 3600} ч. {(remaining % 3600) // 60} мин."

    profile_text = (
        f"👤 <b>Твой профиль</b>\n\n"
        f"🐻 <b>Очки:</b> {invites}\n"
        f"🏆 <b>Место в топе:</b> {rank}\n"
        f"🎁 <b>Ежедневный бонус:</b> {bonus_status}\n\n"
        f"Чтобы получить ссылку, нажми кнопку «Моя ссылка»."
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=profile_text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_top")
def show_top(call):
    user_id = call.from_user.id
    users = execute_query("SELECT telegram_id, invites_count FROM users WHERE invites_count > 0 ORDER BY invites_count DESC LIMIT 10").fetchall()
    
    if not users:
        text = "🏆 <b>Топ пока пуст.</b>\nПригласи первого друга, чтобы возглавить список!"
    else:
        text = "🏆 <b>Топ-10 охотников за мишками:</b>\n\n"
        for i, (uid, invites) in enumerate(users, 1):
            try:
                chat = bot.get_chat(uid)
                username = f"@{chat.username}" if chat.username else f"ID:{uid}"
            except:
                username = f"ID:{uid}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {username} — {invites} очк.\n"
            
        user_pts_data = execute_query("SELECT invites_count FROM users WHERE telegram_id = ?", (user_id,)).fetchone()
        if user_pts_data:
            user_pts = user_pts_data[0]
            if len(users) >= 3:
                third_place_pts = users[2][1]
                if user_pts < third_place_pts and uid != user_id:
                    diff = third_place_pts - user_pts
                    text += f"\n🔥 <b>До 3-го места тебе осталось всего {diff} очк.!</b>"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=get_active_user_text(), parse_mode='HTML', reply_markup=get_main_menu())

# ================= АДМИН-КОМАНДЫ =================

@bot.message_handler(commands=['add_points'])
def add_points(message):
    if not is_admin(message): return
    try:
        args = message.text.split()
        target_id = int(args[1])
        points_to_add = int(args[2])
    except:
        bot.send_message(message.chat.id, "Пример: /add_points 123456789 5")
        return
    user = execute_query("SELECT telegram_id FROM users WHERE telegram_id = ?", (target_id,)).fetchone()
    if not user:
        bot.send_message(message.chat.id, f"❌ Пользователь {target_id} не найден.")
        return
    execute_query("UPDATE users SET invites_count = invites_count + ? WHERE telegram_id = ?", (points_to_add, target_id))
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    execute_query("INSERT INTO points_history (user_id, amount, reason, action_time) VALUES (?, ?, ?, ?)", (target_id, points_to_add, "Ручное начисление админом", now_str))
    bot.send_message(message.chat.id, f"✅ Пользователю {target_id} начислено {points_to_add} очк.")

@bot.message_handler(commands=['remove_points'])
def remove_points(message):
    if not is_admin(message): return
    try:
        args = message.text.split()
        target_id = int(args[1])
        points_to_remove = int(args[2])
    except:
        bot.send_message(message.chat.id, "Пример: /remove_points 123456789 5")
        return
    user = execute_query("SELECT invites_count FROM users WHERE telegram_id = ?", (target_id,)).fetchone()
    if not user:
        bot.send_message(message.chat.id, f"❌ Пользователь {target_id} не найден.")
        return
    current_points = user[0]
    if current_points < points_to_remove:
        bot.send_message(message.chat.id, f"⚠️ У пользователя только {current_points} очков. Нельзя списать {points_to_remove}.")
        return
    execute_query("UPDATE users SET invites_count = invites_count - ? WHERE telegram_id = ?", (points_to_remove, target_id))
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    execute_query("INSERT INTO points_history (user_id, amount, reason, action_time) VALUES (?, ?, ?, ?)", (target_id, -points_to_remove, "Ручное списание админом", now_str))
    bot.send_message(message.chat.id, f"✅ У пользователя {target_id} списано {points_to_remove} очк.")

@bot.message_handler(commands=['user_info'])
def user_info(message):
    if not is_admin(message): return
    try:
        target_id = int(message.text.split()[1])
    except:
        bot.send_message(message.chat.id, "Пример: /user_info 123456789")
        return
    data = execute_query("SELECT invites_count, inviter, last_bonus_time FROM users WHERE telegram_id = ?", (target_id,)).fetchone()
    if not data:
        bot.send_message(message.chat.id, f"❌ Пользователь {target_id} не найден.")
        return
    points, inviter_id, last_bonus = data
    inviter_name = f"ID:{inviter_id}" if inviter_id else "Пришел сам"
    if inviter_id:
        try:
            inviter_name = f"@{bot.get_chat(inviter_id).username}" if bot.get_chat(inviter_id).username else inviter_name
        except:
            pass
    current_time = int(time.time())
    if current_time - last_bonus >= 86400:
        bonus_status = "Может забрать 🎁"
    else:
        remaining = 86400 - (current_time - last_bonus)
        bonus_status = f"Через {remaining // 3600} ч. {(remaining % 3600) // 60} мин."
    text = (
        f"🕵️‍♂️ <b>Инфо о пользователе</b>\n\n"
        f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
        f"🐻 <b>Очки:</b> {points}\n"
        f"🤝 <b>Кто пригласил:</b> {inviter_name}\n"
        f"🎁 <b>Ежедн. бонус:</b> {bonus_status}"
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['check_user'])
def check_user_history(message):
    if not is_admin(message): return
    try:
        target_id = int(message.text.split()[1])
    except:
        bot.send_message(message.chat.id, "Пример: /check_user 123456789")
        return
    user = execute_query("SELECT invites_count FROM users WHERE telegram_id = ?", (target_id,)).fetchone()
    if not user:
        bot.send_message(message.chat.id, f"❌ Пользователь {target_id} не найден в базе.")
        return
    total_invites = user[0]
    history = execute_query("SELECT amount, reason, action_time FROM points_history WHERE user_id = ? ORDER BY id DESC", (target_id,)).fetchall()
    if not history:
        bot.send_message(message.chat.id, f"👤 Пользователь ID:{target_id}\nОчков: {total_invites}\n\n📭 История операций пуста.")
        return
    text = f"👤 <b>История операций ID:{target_id}</b>\n"
    text += f"Текущий баланс: {total_invites}\n\n"
    for i, record in enumerate(history[:40], 1):
        amount, reason, action_time = record
        sign = "+" if amount > 0 else ""
        text += f"{i}. {sign}{amount} | {reason} | {action_time}\n"
    if len(history) > 40:
        text += f"\n...и еще {len(history) - 40} операций."
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['set_winners'])
def set_winners(message):
    if not is_admin(message): return
    try:
        new_winners_count = int(message.text.split()[1])
        global MAX_WINNERS
        MAX_WINNERS = new_winners_count
        bot.send_message(message.chat.id, f"Количество победителей изменено на {MAX_WINNERS}.")
    except:
        bot.send_message(message.chat.id, "Пример: /set_winners 3")

@bot.message_handler(commands=['delete_user'])
def delete_user(message):
    if not is_admin(message): return
    try:
        telegram_id = int(message.text.split()[1])
    except:
        bot.send_message(message.chat.id, 'Пример: /delete_user 123456789')
        return
    user = execute_query("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    if not user:
        bot.send_message(message.chat.id, f'Пользователь {telegram_id} не найден.')
    else:
        inviter_of_user = user[2]
        try:
            execute_query("UPDATE users SET invites_count = invites_count - 1 WHERE telegram_id = ?", (inviter_of_user,))
            execute_query("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
            execute_query("DELETE FROM referral_history WHERE invited_id = ?", (telegram_id,))
            execute_query("DELETE FROM points_history WHERE user_id = ?", (telegram_id,))
            execute_query("UPDATE users SET particip = 0 WHERE invites_count < 1")
            bot.send_message(message.chat.id, f'Пользователь {telegram_id} удален.')
        except:
            pass

@bot.message_handler(commands=['draw'])
def draw_raffle(message):
    if not is_admin(message): return
    all_partic = execute_query("SELECT telegram_id, invites_count FROM users WHERE invites_count >= 1").fetchall()
    if not all_partic:
        bot.send_message(message.chat.id, 'Нет участников с очками.')
        return
    total_invites = sum([pair[1] for pair in all_partic])
    users = [pair[0] for pair in all_partic]
    probs = [pair[1] / total_invites for pair in all_partic]
    max_winners = min(len(users), MAX_WINNERS)
    winners = np.random.choice(users, size=max_winners, replace=False, p=probs)
    winners_message = '🎉 Победители:\n'
    for winner in winners:
        try:
            chat = bot.get_chat(winner)
            username = f'@{chat.username}' if chat.username else f'ID: {winner}'
            winners_message += f'- {username}\n'
        except:
            winners_message += f'- ID: {winner}\n'
    bot.send_message(message.chat.id, winners_message)

@bot.message_handler(commands=['reset_users'])
def reset_users(message):
    if not is_admin(message): return
    execute_query("DELETE FROM users")
    execute_query("DELETE FROM referral_history")
    execute_query("DELETE FROM points_history")
    bot.send_message(message.chat.id, 'Все данные удалены.')

@bot.message_handler(commands=['participants'])
def show_participants(message):
    if not is_admin(message): return
    users = execute_query("SELECT telegram_id, invites_count, inviter FROM users ORDER BY invites_count DESC").fetchall()
    if not users:
        bot.send_message(message.chat.id, 'Пока нет участников.')
        return
    participants_message = "🏆 Топ по очкам:\n\n"
    for user in users:
        telegram_id, invites_count, inviter = user
        if invites_count > 0:
            try:
                username = bot.get_chat(telegram_id).username
                name = f"@{username}" if username else f"ID:{telegram_id}"
            except:
                name = f"ID:{telegram_id}"
            participants_message += f"{name} — {invites_count} очк.\n"
    bot.send_message(message.chat.id, participants_message)

@bot.message_handler(commands=['help_adm'])
def admin_help(message):
    if not is_admin(message): 
        bot.send_message(message.chat.id, f"❌ У тебя нет прав. Твой ID: {message.from_user.id}")
        return
    help_message = """
    Админ-команды:
    /add_points [ID] [кол-во] - Начислить очки.
    /remove_points [ID] [кол-во] - Списать очки.
    /user_info [ID] - Инфо о юзере.
    /check_user [ID] - История операций (рефки + ручные).
    /set_winners [число] - Кол-во победителей.
    /draw - Провести розыгрыш.
    /participants - Показать общий топ.
    /delete_user [ID] - Удалить юзера.
    /reset_users - Очистить базу.
    """
    bot.send_message(message.chat.id, help_message)

bot.remove_webhook()
bot.polling(non_stop=True)
