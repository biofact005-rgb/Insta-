import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import requests
import random
import datetime
import time
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import Flask
from threading import Thread


# 🔒 Ye line .env file se saare hidden secrets nikal legi
load_dotenv()

# ==========================================
# ⚙️ CONFIGURATION (SECURE & HIDDEN)
# ==========================================
# Ab yahan koi asli token nahi hai, sab os.getenv se aa raha hai
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
API_KEY = os.getenv("API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

CHANNEL_USERNAME = "@errorkid_05" 
REFER_REWARD = 20.0 
API_URL = "https://tntsmm.in/api/v2"
SERVICE_ID = 4276 
INSTA_VIEW_RATE = 0.01 

# Iske niche aapka baki ka images aur database setup wala code same rahega...


API_URL = "https://themainsmmprovider.com/api/v2"
API_KEY = "f53e6d46f93b5bbb5f473d828f698afe5c7b329f"
SERVICE_ID = 4276 
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
# ⚠️ Apna MongoDB Atlas URI yahan dalein
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")

try:
    client = MongoClient(MONGO_URI)
    db = client['vip_smm_bot']
    users_col = db['users']
    orders_col = db['orders']
    promos_col = db['promos']
    promo_usage_col = db['promo_usage']
    
    # Auto-add default NEW50 promo code (Upsert: inserts if not exists)
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
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def place_smm_order(link, quantity):
    payload = {'key': API_KEY, 'action': 'add', 'service': SERVICE_ID, 'link': link, 'quantity': quantity}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}
    try:
        response = requests.post(API_URL, data=payload, headers=headers)
        return response.json()
    except Exception:
        return {"error": "API Connection Failed"}

def check_smm_status(panel_order_id):
    payload = {'key': API_KEY, 'action': 'status', 'order': panel_order_id}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}
    try:
        response = requests.post(API_URL, data=payload, headers=headers)
        return response.json()
    except Exception:
        return {"error": "Status fetch failed"}

# ==========================================
# 📱 VIP MENUS
# ==========================================
def force_join_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📣 Channel 1", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"), InlineKeyboardButton("📣 Channel 2", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.row(InlineKeyboardButton("📣 Channel 3", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"), InlineKeyboardButton("📣 Channel 4", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.row(InlineKeyboardButton("✅ JOINED", callback_data="check_join"))
    return markup

def get_home_content(user_id, first_name):
    user_data = users_col.find_one({"_id": user_id})
    total_real_users = users_col.count_documents({})
    if not user_data: return None, None
    
    diamonds = user_data.get('diamonds', 0.0)
    invites = user_data.get('invites', 0)
    last_bonus_str = user_data.get('last_bonus', None)

    # Fake counter logic: 400 + real users
    display_users = 400 + total_real_users

    bonus_status = "🟢 Available"
    if last_bonus_str:
        last_bonus = datetime.datetime.fromisoformat(last_bonus_str)
        if (datetime.datetime.now() - last_bonus).total_seconds() < 86400:
            bonus_status = "🔴 Claimed"

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
    markup.row(InlineKeyboardButton("🔗 GET INSTA VIEWS", callback_data="insta_view"))
    markup.row(InlineKeyboardButton("🦋 REFER", callback_data="earn"), InlineKeyboardButton("🌍 PROMO CODE", callback_data="enter_promo"))
    markup.row(InlineKeyboardButton("⭐ STATS & HELP", callback_data="track_help"), InlineKeyboardButton("🆘 BUY DIAMONDS", callback_data="buy_diamond"))
    markup.row(InlineKeyboardButton("🎁 DAILY BONUS", callback_data="daily_bonus"))
    
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
# 👑 ADMIN COMMANDS
# ==========================================
@bot.message_handler(commands=['createpromo'])
def create_promo(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(message, "⚠️ <b>Format:</b> <code>/createpromo CODE DIAMONDS LIMIT</code>\nEx: <code>/createpromo VIP 50 100</code>", parse_mode='HTML')
        return
    code_name, reward, limit = args[1].upper(), float(args[2]), int(args[3])
    promos_col.update_one({"_id": code_name}, {"$set": {"reward": reward, "usage_limit": limit}}, upsert=True)
    bot.reply_to(message, f"✅ <b>Promo Created!</b>\n🎟️ Code: <code>{code_name}</code>\n💎 Reward: {reward}\n👥 Limit: {limit}", parse_mode='HTML')

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return bot.reply_to(message, "⚠️ Kripya message likhein. Ex: <code>/broadcast Hello!</code>", parse_mode='HTML')
    
    users = users_col.find({})
    bot.reply_to(message, "⏳ Broadcasting started...")
    success = 0
    for u in users:
        try:
            bot.send_message(u['_id'], f"📢 <b>ADMIN UPDATE</b>\n\n<blockquote>{text}</blockquote>", parse_mode='HTML')
            success += 1
        except: pass
    bot.reply_to(message, f"✅ Broadcast Complete! Sent to {success} users.")

@bot.message_handler(commands=['backup'])
def admin_backup(message):
    if message.from_user.id != ADMIN_ID: return
    bot.reply_to(message, "⏳ Generating MongoDB Backup...")
    
    users_data = list(users_col.find({}))
    for u in users_data:
        u['_id'] = str(u['_id']) # Convert integer ID to string for JSON
        
    with open("database_backup.json", "w") as f:
        json.dump(users_data, f, indent=4)
        
    with open("database_backup.json", "rb") as doc:
        bot.send_document(message.chat.id, doc, caption="📦 <b>Database Backup</b>\n\nAll user balances and info successfully exported.", parse_mode='HTML')
    
    os.remove("database_backup.json") # Clean up file after sending

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    user = users_col.find_one({"_id": user_id})
    if not user:
        invited_by = 0
        args = message.text.split()
        if len(args) > 1:
            try:
                referrer_id = int(args[1])
                if referrer_id != user_id:
                    invited_by = referrer_id
            except ValueError: pass
            
        users_col.insert_one({
            "_id": user_id, 
            "diamonds": 0.0, 
            "invites": 0, 
            "invited_by": invited_by, 
            "last_bonus": None
        })

    if not check_joined(user_id):
        force_join_text = "💜 <b>JOIN REQUIRED</b>\n\n<blockquote>💬 PLEASE JOIN ALL OUR OFFICIAL CHANNELS BELOW TO CONTINUE USING THE BOT.</blockquote>"
        bot.send_photo(message.chat.id, photo=IMAGES['home'], caption=force_join_text, parse_mode='HTML', reply_markup=force_join_menu())
        return

    caption, markup = get_home_content(user_id, message.from_user.first_name)
    bot.send_photo(message.chat.id, photo=IMAGES['home'], caption=caption, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id, message_id, user_id = call.message.chat.id, call.message.message_id, call.from_user.id
    first_name = call.from_user.first_name

    if call.data != "check_join" and not check_joined(user_id):
        return bot.answer_callback_query(call.id, "Please join the channels first!", show_alert=True)

    if call.data == "check_join":
        if check_joined(user_id):
            user = users_col.find_one({"_id": user_id})
            ref_id = user.get('invited_by', 0)
            
            if ref_id > 0:
                users_col.update_one({"_id": ref_id}, {"$inc": {"diamonds": REFER_REWARD, "invites": 1}})
                users_col.update_one({"_id": user_id}, {"$set": {"invited_by": 0}})
                try: bot.send_message(ref_id, f"🎉 <b>Referral Verified!</b>\nYour friend joined. You earned <b>{REFER_REWARD} Diamonds</b>!", parse_mode='HTML')
                except: pass
            
            caption, markup = get_home_content(user_id, first_name)
            bot.edit_message_caption(caption=caption, chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=markup)
            bot.answer_callback_query(call.id, "Verification Successful!")
        else:
            bot.answer_callback_query(call.id, "You haven't joined the channels yet!", show_alert=True)

    elif call.data == "back_to_main" or call.data == "cancel_order":
        try: bot.clear_step_handler_by_chat_id(chat_id)
        except: pass
        if user_id in pending_orders: del pending_orders[user_id]
        
        caption, markup = get_home_content(user_id, first_name)
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['home'], caption=caption, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=markup)
        try: bot.answer_callback_query(call.id)
        except: pass

    elif call.data == "insta_view":
        user = users_col.find_one({"_id": user_id})
        diamonds = user.get('diamonds', 0.0)
        text = f"📸 <b>Instagram Views Service</b>\n\n<blockquote>💰 <b>Rate:</b> 1000 Views = {INSTA_VIEW_RATE * 1000} Diamonds\n💎 <b>Your Balance:</b> {round(diamonds, 2)} Diamonds</blockquote>\n\n⚡ Fast Delivery & Non-Drop"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['insta'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=order_action_menu())

    elif call.data == "start_order":
        text = "🔗 <b>Link Submission</b>\n\n<blockquote>Please enter the link for your Instagram Post/Reel below:</blockquote>\n\n<i>(Click Cancel to go back)</i>"
        bot.edit_message_caption(caption=text, chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=cancel_menu())
        bot.register_next_step_handler_by_chat_id(chat_id, process_link_step, message_id)

    elif call.data == "buy_diamond":
        text = "💎 <b>Premium Diamonds Store</b>\n\n<blockquote>Enhance your account by purchasing diamonds:\n\n🔹 <b>₹10</b> = 500 Diamonds\n🔹 <b>₹20</b> = 1100 Diamonds\n🔹 <b>₹50</b> = 3000 Diamonds</blockquote>\n\n📲 <b>To purchase, please contact:</b> @errorkidk2"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['buy'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=cancel_menu())

    elif call.data == "earn":
        user = users_col.find_one({"_id": user_id})
        invites = user.get('invites', 0)
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        text = f"🔗 <b>Refer & Earn Program</b>\n\n<blockquote>Invite friends and earn <b>{REFER_REWARD} Diamonds</b> for each valid referral!</blockquote>\n\n🏆 <b>Your Referrals:</b> {invites}\n\n📤 <b>Your VIP Link:</b>\n<code>{link}</code>\n\n<i>(Tap the link to copy)</i>"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['earn'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=cancel_menu())

    elif call.data == "daily_bonus":
        now = datetime.datetime.now()
        user = users_col.find_one({"_id": user_id})
        last_bonus_str = user.get('last_bonus', None)
        
        can_claim = True
        if last_bonus_str:
            last_bonus = datetime.datetime.fromisoformat(last_bonus_str)
            if (now - last_bonus).total_seconds() < 86400:
                can_claim = False
                bot.answer_callback_query(call.id, "⏳ Reward already claimed! Come back tomorrow.", show_alert=True)
                
        if can_claim:
            bonus_dia = random.randint(2, 10)
            users_col.update_one({"_id": user_id}, {"$inc": {"diamonds": bonus_dia}, "$set": {"last_bonus": now.isoformat()}})
            bot.answer_callback_query(call.id, f"🎉 Congratulations! You claimed {bonus_dia} free Diamonds.", show_alert=True)
            caption, markup = get_home_content(user_id, first_name)
            bot.edit_message_caption(caption=caption, chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=markup)

    elif call.data == "enter_promo":
        text = "🎟️ <b>Promo Code Redemption</b>\n\n🎁 <i>Try code NEW50 for 50 Free Diamonds!</i>\n\n<blockquote>Please enter your VIP Promo Code below:</blockquote>\n\n<i>(Click Cancel to go back)</i>"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['promo'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=cancel_menu())
        bot.register_next_step_handler_by_chat_id(chat_id, process_promo_code, message_id)

    elif call.data == "track_help":
        text = "ℹ️ <b>Help & Support Center</b>\n\n<blockquote>To track an existing order, please enter your <b>Order ID</b> (e.g., ORD12345) below.</blockquote>\n\nFor further assistance, contact our admin: @errorkidk2\n\n<i>(Click Cancel to go back)</i>"
        bot.edit_message_media(media=InputMediaPhoto(IMAGES['help'], caption=text, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=cancel_menu())
        bot.register_next_step_handler_by_chat_id(chat_id, process_track_order, message_id)

    elif call.data == "confirm_order":
        if user_id in pending_orders:
            order_data = pending_orders[user_id]
            cost = order_data['cost']
            
            user = users_col.find_one({"_id": user_id})
            current_bal = user.get('diamonds', 0.0)
            
            if current_bal >= cost:
                users_col.update_one({"_id": user_id}, {"$inc": {"diamonds": -cost}})
                bot.edit_message_caption(caption="⏳ <b>Processing your order...</b>", chat_id=chat_id, message_id=message_id, parse_mode='HTML')
                
                api_res = place_smm_order(order_data['link'], order_data['qty'])
                
                if "order" in api_res:
                    bot_order_id = f"ORD{random.randint(10000, 99999)}"
                    orders_col.insert_one({"_id": bot_order_id, "panel_order_id": str(api_res["order"]), "user_id": user_id})
                    
                    success_msg = f"✅ <b>Order Confirmed!</b>\n\n<blockquote>🆔 <b>Order ID:</b> <code>{bot_order_id}</code>\n🔗 <b>Link:</b> {order_data['link']}\n🔢 <b>Quantity:</b> {order_data['qty']}</blockquote>\n\nTrack your order in the Help section."
                    bot.edit_message_caption(caption=success_msg, chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=cancel_menu())
                    
                    # 🚨 ADMIN NOTIFICATION
                    admin_alert = f"🚨 <b>NEW ORDER ALERT</b> 🚨\n\n<blockquote>👤 <b>User:</b> <code>{user_id}</code>\n🔗 <b>Link:</b> {order_data['link']}\n🔢 <b>Qty:</b> {order_data['qty']}\n💎 <b>Spent:</b> {round(cost, 2)} Diamonds</blockquote>"
                    try: bot.send_message(ADMIN_ID, admin_alert, parse_mode='HTML')
                    except: pass
                else:
                    users_col.update_one({"_id": user_id}, {"$inc": {"diamonds": cost}})
                    bot.edit_message_caption(caption=f"❌ <b>API Error!</b>\nOrder failed: {api_res.get('error', 'Unknown')}\nYour diamonds have been refunded.", chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=cancel_menu())
            else:
                bot.edit_message_caption(caption="❌ <b>Insufficient Balance!</b>", chat_id=chat_id, message_id=message_id, parse_mode='HTML', reply_markup=cancel_menu())
            del pending_orders[user_id]
        else:
            bot.answer_callback_query(call.id, "Session expired! Please order again.", show_alert=True)
            caption, markup = get_home_content(user_id, first_name)
            bot.edit_message_media(media=InputMediaPhoto(IMAGES['home'], caption=caption, parse_mode='HTML'), chat_id=chat_id, message_id=message_id, reply_markup=markup)

    try: bot.answer_callback_query(call.id)
    except: pass

# ==========================================
# 🔄 NEXT STEP HANDLERS (AUTO-DELETE)
# ==========================================
def process_link_step(message, prev_message_id):
    try: bot.delete_message(message.chat.id, message.message_id) 
    except: pass
    link = message.text
    text = "🔢 <b>Quantity Input</b>\n\n<blockquote>Please enter the desired quantity (e.g., 1000):</blockquote>\n\n<i>(Click Cancel to go back)</i>"
    bot.edit_message_caption(caption=text, chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
    bot.register_next_step_handler_by_chat_id(message.chat.id, process_quantity_step, link, prev_message_id)

def process_quantity_step(message, link, prev_message_id):
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    try:
        qty = int(message.text)
        if qty <= 0: return bot.edit_message_caption(caption="❌ Quantity must be greater than 0.", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())

        user_id = message.from_user.id
        cost = qty * INSTA_VIEW_RATE
        
        user = users_col.find_one({"_id": user_id})
        user_bal = user.get('diamonds', 0.0)
            
        if user_bal >= cost:
            rem_bal = user_bal - cost
            pending_orders[user_id] = {'link': link, 'qty': qty, 'cost': cost}
            confirm_text = f"⚠️ <b>Order Summary</b>\n\n<blockquote>🔗 <b>Link:</b> {link}\n🔢 <b>Quantity:</b> {qty}\n\n💎 <b>Cost:</b> {round(cost, 2)} Diamonds\n💰 <b>Current Balance:</b> {round(user_bal, 2)}\n💳 <b>Remaining Balance:</b> {round(rem_bal, 2)}</blockquote>\n\nPlease Confirm or Cancel:"
            bot.edit_message_caption(caption=confirm_text, chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=order_confirm_menu())
        else:
            bot.edit_message_caption(caption=f"❌ <b>Insufficient Diamonds!</b>\nYou need <b>{round(cost, 2)}</b> but have <b>{round(user_bal, 2)}</b>.", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
    except ValueError:
        bot.edit_message_caption(caption="❌ <b>Invalid Input!</b> Please enter numbers only.", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())

def process_promo_code(message, prev_message_id):
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    user_id, code = message.from_user.id, message.text.strip().upper() 
    
    promo = promos_col.find_one({"_id": code})
    if promo:
        total_used = promo_usage_col.count_documents({"code_name": code})
        already_used = promo_usage_col.find_one({"user_id": user_id, "code_name": code})
        
        if already_used:
            bot.edit_message_caption(caption="⚠️ <b>You have already claimed this promo code!</b>", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
        elif total_used >= promo['usage_limit']:
            bot.edit_message_caption(caption="❌ <b>This promo code has expired or reached its limit!</b>", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
        else:
            promo_usage_col.insert_one({"user_id": user_id, "code_name": code})
            users_col.update_one({"_id": user_id}, {"$inc": {"diamonds": promo['reward']}})
            bot.edit_message_caption(caption=f"🎉 <b>Success!</b>\nCode <code>{code}</code> Applied! You received <b>+{promo['reward']} 💎 Diamonds</b>!", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
    else:
        bot.edit_message_caption(caption="❌ <b>Invalid Promo Code!</b>", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())

def process_track_order(message, prev_message_id):
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    bot_order_id = message.text.strip()
    
    order = orders_col.find_one({"_id": bot_order_id})
    if order:
        bot.edit_message_caption(caption="⏳ <b>Fetching live status...</b>", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML')
        status_res = check_smm_status(order['panel_order_id'])
        if "error" in status_res and type(status_res) is dict:
             bot.edit_message_caption(caption=f"❌ <b>Error:</b> {status_res['error']}", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
        else:
            status = status_res.get('status', 'Pending').title()
            text = f"📊 <b>Live Status Report</b>\n\n<blockquote>🆔 <b>Order ID:</b> <code>{bot_order_id}</code>\n📌 <b>Status:</b> {status}\n🔄 <b>Remaining:</b> {status_res.get('remains', 'N/A')}</blockquote>"
            bot.edit_message_caption(caption=text, chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())
    else:
        bot.edit_message_caption(caption="❌ <b>Invalid Order ID!</b> Please check and try again.", chat_id=message.chat.id, message_id=prev_message_id, parse_mode='HTML', reply_markup=cancel_menu())

# ==========================================
# 🚀 ANTI-CRASH RUNNER
# ==========================================

# ==========================================
# 🌐 DUMMY WEB SERVER (RENDER WEB SERVICE FIX)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "VIP Bot is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Dummy server ko background me start karo
Thread(target=run_web).start()

# ==========================================
# 🚀 ANTI-CRASH RUNNER
# ==========================================
print("MongoDB VIP SMM Bot is Running on Web Service...")
while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Network issue, reconnecting in 5s... Error: {e}")
        time.sleep(5)
