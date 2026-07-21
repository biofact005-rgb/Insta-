import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import requests
import random
import datetime
import time
import os
import json
import uuid  # Naya module - Unique link generate karne ke liye
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ==========================================
# ⚙️ CONFIGURATION (SECURE & HIDDEN)
# ==========================================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8718760365")) 
API_KEY = os.getenv("API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# 🔗 NAYA: Shortener Config (Apni .env file me add kar lena)
SHORTENER_API = os.getenv("SHORTENER_API", "YOUR_SHORTENER_API_KEY_HERE") 
SHORTENER_URL = os.getenv("SHORTENER_URL", "https://gplinks.in/api") # Ya Shareus/Shrinkme ka URL

MAINTENANCE_MODE = False
CHANNEL_USERNAME_1 = "@errorkid_05" 
CHANNEL_USERNAME_2 = "@ER_INSTAUPDATE" 
PROOF_CHANNEL = "@live_proff" 

REFER_REWARD = 20.0 
LINK_REWARD = 10.0 # 🔴 NAYA: Short link open karne par kitne diamonds milenge

API_URL = "https://tntsmm.in/api/v2"
SERVICE_ID = 12567
INSTA_VIEW_RATE = 0.01 

IMAGES = {
    "home": "https://graph.org/file/95b88e6251f19b911c08f-c36ee2ffe4f047e079.jpg",
    "insta": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80",
    "buy": "https://images.unsplash.com/photo-1580508174046-170816f65662?w=800&q=80",
    "earn": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80",
    "promo": "https://images.unsplash.com/photo-1607083206869-4c7672e72a8a?w=800&q=80",
    "help": "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=800&q=80"
}

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 💾 MONGODB SETUP
# ==========================================
try:
    client = MongoClient(MONGO_URI)
    db = client['vip_smm_bot']
    users_col = db['users']
    orders_col = db['orders']
    promos_col = db['promos']
    promo_usage_col = db['promo_usage']
    tasks_col = db['tasks'] # 🔴 NAYA: Short links track karne ke liye
    
    promos_col.update_one(
        {"_id": "NEW50"}, 
        {"$setOnInsert": {"reward": 50.0, "usage_limit": 10000}}, 
        upsert=True
    )
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")

pending_orders = {}

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def check_joined(user_id):
    try:
        status1 = bot.get_chat_member(CHANNEL_USERNAME_1, user_id).status
        status2 = bot.get_chat_member(CHANNEL_USERNAME_2, user_id).status
        valid_statuses = ['member', 'administrator', 'creator']
        return status1 in valid_statuses and status2 in valid_statuses
    except Exception:
        return False

def force_join_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📣 Join Channel 1", url=f"https://t.me/{CHANNEL_USERNAME_1[1:]}"), 
               InlineKeyboardButton("📣 Join Channel 2", url=f"https://t.me/{CHANNEL_USERNAME_2[1:]}"))
    markup.row(InlineKeyboardButton("✅ JOINED", callback_data="check_join"))
    return markup

def place_smm_order(link, quantity):
    payload = {'key': API_KEY, 'action': 'add', 'service': SERVICE_ID, 'link': link, 'quantity': quantity}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.post(API_URL, data=payload, headers=headers)
        return response.json()
    except Exception:
        return {"error": "API Connection Failed"}

def check_smm_status(panel_order_id):
    payload = {'key': API_KEY, 'action': 'status', 'order': panel_order_id}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.post(API_URL, data=payload, headers=headers)
        return response.json()
    except Exception:
        return {"error": "Status fetch failed"}

# 🔴 NAYA: URL Shortener Function
def create_short_link(long_url):
    try:
        api_req = f"{SHORTENER_URL}?api={SHORTENER_API}&url={long_url}"
        res = requests.get(api_req).json()
        if res.get("status") == "success":
            return res.get("shortenedUrl")
    except Exception as e:
        print(f"Shortener API Error: {e}")
    return None

# ==========================================
# 📱 VIP MENUS
# ==========================================
def get_home_content(user_id, first_name):
    user_data = users_col.find_one({"_id": user_id})
    total_real_users = users_col.count_documents({})
    if not user_data: return None, None
    
    diamonds = user_data.get('diamonds', 0.0)
    invites = user_data.get('invites', 0)
    display_users = 400 + total_real_users

    caption = (
        "⭐ <b>WELCOME TO VIP PANEL</b> ⭐\n\n"
        "<blockquote>👤 <b>Name:</b> {0}\n"
        "🆔 <b>User ID:</b> <code>{1}</code>\n"
        "💎 <b>Balance:</b> {2}\n"
        "👥 <b>Refers:</b> {3}\n"
        "📈 <b>Total Users:</b> {4}</blockquote>\n\n"
        "<blockquote>💬 SELECT AN OPTION BELOW TO CONTINUE.</blockquote>"
    ).format(first_name, user_id, round(diamonds, 2), invites, display_users)

    markup = InlineKeyboardMarkup()
    # 🔴 NAYA BUTTON: Earn Free Diamonds (Ads) ko top par laga diya!
    markup.row(InlineKeyboardButton("🔗 EARN FREE DIAMONDS (WATCH ADS)", callback_data="earn_shortlink"))
    markup.row(InlineKeyboardButton("📈 GET INSTA VIEWS", callback_data="insta_view"))
    markup.row(InlineKeyboardButton("👥 REFER", callback_data="earn"), InlineKeyboardButton("🎟️ PROMO", callback_data="enter_promo"))
    markup.row(InlineKeyboardButton("⭐ STATS & HELP", callback_data="track_help"), InlineKeyboardButton("🎁 DAILY BONUS", callback_data="daily_bonus"))
    
    return caption, markup

def cancel_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("❌ Cancel / Back", callback_data="back_to_main"))
    return markup

def order_action_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛒 Order Now", callback_data="start_order"), InlineKeyboardButton("❌ Cancel", callback_data="back_to_main"))
    return markup

def order_confirm_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✅ Confirm", callback_data="confirm_order"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_order"))
    return markup

# ==========================================
# 🤖 BOT HANDLERS (START & REWARD VERIFICATION)
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if MAINTENANCE_MODE and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "🚧 <b>BOT IS UNDER MAINTENANCE</b> 🚧", parse_mode='HTML')
        return

    user_id = message.from_user.id
    args = message.text.split()
    
    # 🔴 NAYA: Short Link Task Verification Logic
    if len(args) > 1 and args[1].startswith("task_"):
        task_id = args[1]
        task = tasks_col.find_one({"_id": task_id, "user_id": user_id})
        
        if task:
            users_col.update_one({"_id": user_id}, {"$inc": {"diamonds": LINK_REWARD}})
            tasks_col.delete_one({"_id": task_id}) # Ek baar use hone ke baad delete
            bot.send_message(user_id, f"🎉 <b>TASK COMPLETED SUCCESSFULLY!</b>\n\nYou earned <b>{LINK_REWARD} Diamonds</b>. Ab aap in diamonds se Reel views kharid sakte hain!", parse_mode='HTML')
        else:
            bot.send_message(user_id, "❌ <b>Task Expired ya Invalid hai!</b>\nKripya naya link generate karein.", parse_mode='HTML')

    user = users_col.find_one({"_id": user_id})
    if not user:
        invited_by = 0
        if len(args) > 1 and not args[1].startswith("task_"):
            try:
                referrer_id = int(args[1])
                if referrer_id != user_id: invited_by = referrer_id
            except ValueError: pass
            
        users_col.insert_one({"_id": user_id, "diamonds": 0.0, "invites": 0, "invited_by": invited_by, "last_bonus": None})

    if not check_joined(user_id):
        bot.send_photo(message.chat.id, photo=IMAGES['home'], caption="💜 <b>JOIN REQUIRED</b>\nPlease join to continue.", parse_mode='HTML', reply_markup=force_join_menu())
        return

    caption, markup = get_home_content(user_id, message.from_user.first_name)
    bot.send_photo(message.chat.id, photo=IMAGES['home'], caption=caption, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if MAINTENANCE_MODE and call.from_user.id != ADMIN_ID:
        return bot.answer_callback_query(call.id, "🚧 Bot is under maintenance!", show_alert=True)
    
    chat_id, message_id, user_id = call.message.chat.id, call.message.message_id, call.fromuser_id = call.from_user.id
    first_name = call.from_user.first_name

    if call.data != "check_join" and not check_joined(user_id):
        return bot.answer_callback_query(call.id, "Please join the channels first!", show_alert=True)

    if call.data == "back_to_main" or call.data == "cancel_order":
        try: bot.clear_step_handler_by_chat_id(chat_id)
        except: pass
        if user_id in pending_orders: del pending_orders[user_id]
        
        caption, markup = get_home_content(user_id, first_name)
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['home'], caption=caption, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=markup)

    # 🔴 NAYA: Generate Shortlink Task 
    elif call.data == "earn_shortlink":
        bot.answer_callback_query(call.id, "Generating your link... Please wait ⏳")
        bot.edit_message_caption(caption="⏳ <i>Generating your exclusive task link...</i>", chat_id=chat_id, message_id=message_id, parse_mode='HTML')
        
        # 1. Unique task id banao
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        
        # 2. Apne bot ka deep link banao jahan user wapas aayega
        bot_info = bot.get_me()
        long_url = f"https://t.me/{bot_info.username}?start={task_id}"
        
        # 3. GPlinks/Shareus se chota karo
        short_url = create_short_link(long_url)
        
        if short_url:
            # 4. Database me save karo
            tasks_col.insert_one({"_id": task_id, "user_id": user_id, "created_at": datetime.datetime.now()})
            
            text = f"🔗 <b>EARN FREE {LINK_REWARD} DIAMONDS!</b>\n\n<blockquote><b>Step 1:</b> Click the button below.\n<b>Step 2:</b> Complete the Captcha & bypass Ads.\n<b>Step 3:</b> Come back to this bot automatically and get your Diamonds instantly!</blockquote>\n\n⚠️ <i>You can use these diamonds to get Free Insta Views!</i>"
            
            task_markup = InlineKeyboardMarkup()
            task_markup.row(InlineKeyboardButton("🔓 OPEN LINK TO EARN", url=short_url))
            task_markup.row(InlineKeyboardButton("❌ Go Back", callback_data="back_to_main"))
            
            bot.edit_message_media(media=InputMediaPhoto(IMAGES['earn'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=task_markup)
        else:
            bot.edit_message_caption(caption="❌ <b>API Error!</b>\nLink server is currently down. Please try again later.", chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=cancel_menu())

    # BAAKI SAB PURANA CODE WAISE HI HAI... (Insta View, Order, Bonus, etc.)
    elif call.data == "insta_view":
        user = users_col.find_one({"_id": user_id})
        diamonds = user.get('diamonds', 0.0)
        text = f"📸 <b>Instagram Views Service</b>\n\n<blockquote>💰 <b>Rate:</b> 1000 Views = {INSTA_VIEW_RATE * 1000} Diamonds\n💎 <b>Your Balance:</b> {round(diamonds, 2)} Diamonds</blockquote>\n\n⚡ Fast Delivery & Non-Drop\n\n<blockquote>🩵 <b>MINIMUM ORDER 100 VIEW ONLY</b></blockquote>"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['insta'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=order_action_menu())

    elif call.data == "start_order":
        text = "🔗 <b>Link Submission</b>\n\n<blockquote>Please enter the link for your Instagram Post/Reel below:</blockquote>"
        bot.edit_message_caption(caption=text, chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=cancel_menu())
        bot.register_next_step_handler_by_chat_id(chat_id, process_link_step, message_id)

    # Note: Maine code clean rakhne ke liye 'earn' aur 'daily_bonus' wale purane functions skip kiye hain is text me, 
    # Par aap unhe upar wale bot.py se as it is rakhna. Wo perfectly fine the.

    try: bot.answer_callback_query(call.id)
    except: pass

# --- (Yahan Niche Apna Purana process_link_step, process_quantity_step aur Flask Webhook wala code add rakhna) ---
