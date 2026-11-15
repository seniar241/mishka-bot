import os
import telebot
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
bot = telebot.TeleBot(API_TOKEN, skip_pending=True)

ADMIN_IDS = [1638663913]

@bot.message_handler(commands=['help_adm'])
def admin_help(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, f"❌ Ты не админ. Твой ID: {message.from_user.id}")
        return
    bot.send_message(message.chat.id, "✅ Ты админ! Команды работают.")

bot.remove_webhook()
bot.polling(non_stop=True)
