import telebot
import sqlite3
import os
from flask import Flask
from threading import Thread

# 🌐 Render / UptimeRobot 24/7 Web Server
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running 24/7!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

BOT_TOKEN='8615606026:AAGFeTfHay72Cs1Te6MbehEmjQW45jNQBjE'
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_ID = 8609938129  
CHANNEL_ID = -1003794082614  

def get_db_connection():
    return sqlite3.connect("database.db", check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, status TEXT DEFAULT "unpaid", pending_movie INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER, title TEXT, category TEXT DEFAULT "others")')
    conn.commit()
    conn.close()

init_db()

def get_main_keyboard(user_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎬 የፊልሞች ዝርዝር", "🌐 የፊልም ምድቦች")
    markup.add("💰 የዋጋ ዝርዝር", "🏦 የባንክ አካውንቶች")
    markup.add("💬 አስተዳዳሪውን ለማናገር")
    # 👑 ለአስተዳዳሪው ብቻ የሚታይ ልዩ በተን
    if user_id == ADMIN_ID:
        markup.add("⚙️ አድሚን ፓነል (Admin Panel)")
    return markup

def generate_invite_link():
    try:
        invite = bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        return invite.invite_link
    except Exception as e:
        print(f"Invite link generation error: {e}")
        return None

@bot.message_handler(commands=['start'])
def start_welcome(message):
    user_id = message.from_user.id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.execute("INSERT INTO users (user_id, status) VALUES (?, 'unpaid')", (user_id,))
        conn.commit()
    conn.close()

    welcome_text = (
        "👋 **እንኳን ወደ የትርጉም እና አማርኛ ፊልሞች ቦት በሰላም መጡ!**\n\n"
        "✨ **የአባልነት ፓኬጆቻችን፦**\n"
        "🎬 **ነጠላ ፊልም፦** 5 ብር (አንድ ፊልም ብቻ)\n"
        "☀️ **የዕለታዊ Unlimited፦** 30 ብር (ለ 1 ቀን)\n"
        "📅 **የሳምንታዊ Unlimited፦** 70 ብር (ለ 7 ቀን)\n"
        "🗓️ **የወርሃዊ VIP Unlimited፦** 100 ብር (ለ 30 ቀን)\n\n"
        "👇 ለመጀመር ከታች ያሉትን በተኖች ይጠቀሙ!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

# 📸 የደረሰኝ ፎቶ ሲላክ (አሁን የ 5 ብሩን በተን ሁልጊዜ ለአድሚን ያመጣል)
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    photo_id = message.photo[-1].file_id
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pending_movie FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    pending_movie = res[0] if res and res[0] else 0
    conn.close()

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    # የ 5 ብር ነጠላ ፊልም በተን
    btn_single = telebot.types.InlineKeyboardButton("🎬 5 ብር (ነጠላ ፊልም)", callback_data=f"app_single_{user_id}_{pending_movie}")
    btn_day = telebot.types.InlineKeyboardButton("☀️ 30 ብር (ዕለታዊ)", callback_data=f"app_unlim_{user_id}")
    btn_week = telebot.types.InlineKeyboardButton("📅 70 ብር (ሳምንታዊ)", callback_data=f"app_unlim_{user_id}")
    btn_month = telebot.types.InlineKeyboardButton("🗓️ 100 ብር (ወርሃዊ)", callback_data=f"app_unlim_{user_id}")
    btn_reject = telebot.types.InlineKeyboardButton("❌ ከልክል (Reject)", callback_data=f"reject_{user_id}")
    
    markup.add(btn_single)
    markup.add(btn_day, btn_week, btn_month)
    markup.add(btn_reject)
    
    bot.send_photo(
        ADMIN_ID, 
        photo_id, 
        caption=f"📩 አዲስ የክፍያ ደረሰኝ ከ 👤 {user_name} (ID: `{user_id}`) ደርሷል።\n\nእባክህ የከፈለውን የፓኬጅ አይነት መርጠህ አጽድቅ፦",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.reply_to(message, "⏳ የደረሰኝ ፎቶዎ ለአስተዳዳሪው ተልኳል። ክፍያዎ ተረጋግጦ እስኪከፈትልዎት ድረስ እባክዎ በትዕግስት ይቆዩ!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("app_") or call.data.startswith("reject_"))
def callback_listener(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "ይህንን ለማድረግ ፈቃድ የለዎትም!", show_alert=True)
        return

    data = call.data.split("_")
    action = data[1]
    target_user_id = int(data[2])

    if action == "unlim":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'paid' WHERE user_id = ?", (target_user_id,))
        conn.commit()
        conn.close()
        
        invite_link = generate_invite_link()
        
        bot.edit_message_caption(
            chat_id=ADMIN_ID,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n🟢 **VIP ተፈቅዷል! የቻናል ሊንክ ተልኮለታል።**",
            reply_markup=None
        )
        
        msg = "🎉 **መልካም ዜና! የ Unlimited VIP ክፍያዎ ተረጋግጧል።**\n\n"
        if invite_link:
            msg += f"🔗 **የ VIP ቻናላችንን ለመቀላቀል ይህንን ሊንክ ይጫኑ፦**\n{invite_link}\n\n*(ማሳሰቢያ፦ ይህ ሊንክ የሚሰራው ለአንድ ሰው ብቻ ነው!)*"
        else:
            msg += "አሁን ቦቱን እና ቻናሉን መጠቀም ይችላሉ!"

        bot.send_message(target_user_id, msg, reply_markup=get_main_keyboard(target_user_id), parse_mode="Markdown")
        
    elif action == "single":
        movie_msg_id = int(data[3])
        
        bot.edit_message_caption(
            chat_id=ADMIN_ID,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n🟢 **የ5 ብር ነጠላ ፊልም ተፈቅዷል!**",
            reply_markup=None
        )
        
        if movie_msg_id > 0:
            bot.send_message(target_user_id, "🎉 **የ5 ብር ክፍያዎ ተረጋግጧል! የፈለጉት ፊልም እነሆ፦**")
            try:
                bot.copy_message(chat_id=target_user_id, from_chat_id=CHANNEL_ID, message_id=movie_msg_id)
            except Exception:
                bot.send_message(target_user_id, "⚠️ ፊልሙን መላክ አልተቻለም። ቦቱ ቻናሉ ላይ አድሚን መሆኑን ያረጋገጡ።")
        else:
            bot.send_message(target_user_id, "🎉 **የ5 ብር ክፍያዎ ተረጋግጧል!** አሁን ከፊልም ዝርዝር ውስጥ የመረጡትን ፊልም ማውረድ ይችላሉ።")

    elif action == "reject":
        bot.edit_message_caption(
            chat_id=ADMIN_ID,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n🔴 **ተከልክሏል! ክፍያው ውድቅ ተደርጓል።**",
            reply_markup=None
        )
        bot.send_message(target_user_id, "❌ የላኩት ክፍያ ተቀባይነት አላገኘም። እባክዎ ትክክለኛውን የክፍያ ደረሰኝ ፎቶ መላክዎን ያረጋግጡ።")

# ⚙️ የአስተዳዳሪ ብቻ ፓነል እና አባላትን ማስወገጃ Command
@bot.message_handler(func=lambda message: message.text == "⚙️ አድሚን ፓነል (Admin Panel)" or message.text.startswith('/revoke'))
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text.startswith('/revoke'):
        try:
            target_id = int(message.text.split()[1])
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET status = 'unpaid' WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            
            try:
                bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=target_id)
                bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=target_id)
                chan_msg = "\n✅ ተጠቃሚው ከVIP ቻናሉም ተባሯል!"
            except Exception as ex:
                chan_msg = f"\n⚠️ ከቻናል ለማስወጣት አልተቻለም፦ {ex}"

            bot.reply_to(message, f"⛔ ID `{target_id}` ያለው ተጠቃሚ ከ VIP ተሰርዟል!{chan_msg}", parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, "⚠️ እባክህ በዚህ መልክ ጻፍ፦ `/revoke 12345678` (ማስወገድ የምትፈልገውን ሰው ID አስገባ)")
    else:
        admin_info = (
            "👑 **የአስተዳዳሪ መቆጣጠሪያ ፓነል**\n\n"
            "📌 **አባል ከ VIP ቻናል ለማስወገድ፦**\n"
            "በቦቱ ላይ `/revoke USER_ID` ብለህ ጻፍ።\n"
            "ምሳሌ፦ `/revoke 8609938129`\n\n"
            "*(ይህ ሲደረግ አባሉ ከVIP ቻናሉም ይባረራል፡ ቦቱም ላይ ወደ አልከፈለ ተጠቃሚ ይይረጋል)*"
        )
        bot.send_message(ADMIN_ID, admin_info, parse_mode="Markdown")

# 🎬 ቻናሉ ላይ ፊልም ሲጫን ለአድሚኑ የምድብ መምረጫ መላኪያ
@bot.channel_post_handler(content_types=['video', 'document', 'audio', 'text'])
def handle_channel_post(message):
    if message.chat.id == CHANNEL_ID:
        title = None
        if message.caption:
            title = message.caption
        elif message.text:
            title = message.text
        elif message.video and message.video.file_name:
            title = os.path.splitext(message.video.file_name)[0]
        elif message.document and message.document.file_name:
            title = os.path.splitext(message.document.file_name)[0]
        
        if not title or title.strip() == "":
            title = f"የፊልም ቪዲዮ #{message.message_id}"

        clean_title = title.strip()
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        btn1 = telebot.types.InlineKeyboardButton("🇮🇳 የህንድ", callback_data=f"set_hind_{message.message_id}")
        btn2 = telebot.types.InlineKeyboardButton("🇪🇹 የአማርኛ ነጠላ", callback_data=f"set_amharicsingle_{message.message_id}")
        btn3 = telebot.types.InlineKeyboardButton("📺 የአማርኛ ተከታታይ", callback_data=f"set_amharicseries_{message.message_id}")
        btn4 = telebot.types.InlineKeyboardButton("🇹🇷 የቱርክ", callback_data=f"set_turkish_{message.message_id}")
        btn5 = telebot.types.InlineKeyboardButton("🇨🇳 የቻይና", callback_data=f"set_chinese_{message.message_id}")
        btn6 = telebot.types.InlineKeyboardButton("🌍 የሌሎች ሀገር ተከታታይ", callback_data=f"set_otherseries_{message.message_id}")
        btn7 = telebot.types.InlineKeyboardButton("💥 አክሽን", callback_data=f"set_action_{message.message_id}")
        btn8 = telebot.types.InlineKeyboardButton("📁 ሌላ", callback_data=f"set_others_{message.message_id}")
        
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
        
        bot.send_message(
            ADMIN_ID, 
            f"🎬 **አዲስ ፊልም ተገኝቷል፦**\n👉 `{clean_title}`\n\nእባክህ የዚህን ፊልም ምድብ ምረጥ፦", 
            reply_markup=markup,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def save_movie_by_category(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    parts = call.data.split("_")
    category = parts[1]
    message_id = int(parts[2])
    
    orig_text = call.message.text
    try:
        full_title = orig_text.split("👉")[1].split("\n")[0].strip().replace("`", "")
    except Exception:
        full_title = f"Movie {message_id}"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO movies (message_id, title, category) VALUES (?, ?, ?)", (message_id, full_title, category))
    conn.commit()
    conn.close()
    
    cat_names = {
        "hind": "🇮🇳 የህንድ", "amharicsingle": "🇪🇹 የአማርኛ ነጠላ", "amharicseries": "📺 የአማርኛ ተከታታይ", 
        "turkish": "🇹🇷 የቱርክ", "chinese": "🇨🇳 የቻይና", "otherseries": "🌍 የሌሎች ሀገር ተከታታይ",
        "action": "💥 አክሽን", "others": "📁 ሌላ"
    }
    friendly_name = cat_names.get(category, "ሌላ")
    
    bot.edit_message_text(
        chat_id=ADMIN_ID,
        message_id=call.message.message_id,
        text=f"✅ **በስኬት ተመዝግቧል!**\n🎥 ፊልም፦ `{full_title}`\n📂 ምድብ፦ **{friendly_name}**",
        reply_markup=None,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text in ["🎬 የፊልሞች ዝርዝር", "🌐 የፊልም ምድቦች", "💰 የዋጋ ዝርዝር", "🏦 የባንክ አካውንቶች", "💬 አስተዳዳሪውን ለማናገር"])
def handle_menu_buttons(message):
    user_id = message.from_user.id
    if message.text == "🎬 የፊልሞች ዝርዝር":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, title FROM movies ORDER BY id DESC")
        movies = cursor.fetchall()
        conn.close()
        
        if movies:
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            for movie in movies:
                markup.add(telebot.types.InlineKeyboardButton(f"🎥 {movie[1]}", callback_data=f"askpay_{movie[0]}"))
            bot.send_message(message.chat.id, "🎬 **የፊልሞች ዝርዝር እነሆ!** ማየት የሚፈልጉትን ፊልም ይጫኑ፦", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "😔 በአሁኑ ሰዓት በዳታቤዛችን ውስጥ ምንም ፊልም የለም።")

    elif message.text == "🌐 የፊልም ምድቦች":
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        btn1 = telebot.types.InlineKeyboardButton("🇮🇳 የህንድ ፊልሞች", callback_data="cat_hind")
        btn2 = telebot.types.InlineKeyboardButton("🇪🇹 የአማርኛ ነጠላ", callback_data="cat_amharicsingle")
        btn3 = telebot.types.InlineKeyboardButton("📺 የአማርኛ ተከታታይ", callback_data="cat_amharicseries")
        btn4 = telebot.types.InlineKeyboardButton("🇹🇷 የቱርክ ፊልሞች", callback_data="cat_turkish")
        btn5 = telebot.types.InlineKeyboardButton("🇨🇳 የቻይና ፊልሞች", callback_data="cat_chinese")
        btn6 = telebot.types.InlineKeyboardButton("🌍 የሌሎች ሀገር ተከታታይ", callback_data="cat_otherseries")
        btn7 = telebot.types.InlineKeyboardButton("💥 አክሽን ፊልሞች", callback_data="cat_action")
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
        bot.send_message(message.chat.id, "🍿 የትኛውን ምድብ መመልከት ይፈልጋሉ? ከታች ይምረጡ፦", reply_markup=markup)

    elif message.text == "💰 የዋጋ ዝርዝር":
        price_text = (
            "💰 **የአባልነት የዋጋ ዝርዝር**\n\n"
            "🎬 **የነጠላ ፊልም (Single Movie)፦** 5 ብር\n"
            "☀️ **የዕለታዊ Unlimited (1 ቀን)፦** 30 ብር\n"
            "📅 **የሳምንታዊ Unlimited (7 ቀን)፦** 70 ብር\n"
            "🗓️ **የወርሃዊ VIP (30 ቀን)፦** 100 ብር\n\n"
            "🔥 *የሚፈልጉትን ፓኬጅ መርጠው በባንክ አካውንታችን ክፍያ ፈጽመው ደረሰኝ ይላኩ!*"
        )
        bot.send_message(message.chat.id, price_text, parse_mode="Markdown")

    elif message.text == "🏦 የባንክ አካውንቶች":
        bank_text = (
            "🏦 **የክፍያ መቀበያ የባንክ አካውንቶች ዝርዝር**\n"
            "👤 **የአካውንት ባለቤት ስም፦** ሰንደቁ አስማማው\n\n"
            "📱 **በቴሌብር (Telebirr)፦**\n👉 `0998703233`\n\n"
            "🏦 **የኢትዮጵያ ንግድ ባንክ (CBE)፦**\n👉 `1000745390448`\n\n"
            "🏦 **አቢሲኒያ ባንክ (BOA)፦**\n👉 `92707617`\n\n"
            "🏦 **አማራ ባንክ (Amhara Bank)፦**\n👉 `9900039885356`\n\n"
            "⚠️ *ክፍያውን ከፈጸሙ በኋላ ደረሰኙን ፎቶ አንስተው እዚህ ቦት ላይ መላክዎን አይርሱ!*"
        )
        bot.send_message(message.chat.id, bank_text, parse_mode="Markdown")

    elif message.text == "💬 አስተዳዳሪውን ለማናገር":
        contact_text = (
            "🙋‍♂️ **እርዳታ ወይም ጥያቄ አልዎት?**\n\n"
            "የክፍያ ችግር፣ አስተያየት ወይም ተጨማሪ መረጃ ከፈለጉ አስተዳዳሪውን ቀጥታ ማናገር ይችላሉ፦\n\n"
            "👉 **የቴሌግራም አድራሻ፦** @Power_werked"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        btn_contact = telebot.types.InlineKeyboardButton("💬 ቀጥታ አድሚኑን አውራ (Chat)", url="https://t.me/Power_werked")
        markup.add(btn_contact)
        bot.send_message(message.chat.id, contact_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def handle_category_selection(call):
    cat_type = call.data.split("_")[1]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT message_id, title FROM movies WHERE category = ? ORDER BY id DESC", (cat_type,))
    movies = cursor.fetchall()
    conn.close()
    
    cat_names = {
        "hind": "🇮🇳 የህንድ", "amharicsingle": "🇪🇹 የአማርኛ ነጠላ", "amharicseries": "📺 የአማርኛ ተከታታይ", 
        "turkish": "🇹🇷 የቱርክ", "chinese": "🇨🇳 የቻይና", "otherseries": "🌍 የሌሎች ሀገር ተከታታይ", "action": "💥 አክሽን"
    }
    friendly_name = cat_names.get(cat_type, "ሌሎች")
    
    if movies:
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for movie in movies:
            markup.add(telebot.types.InlineKeyboardButton(f"🎥 {movie[1]}", callback_data=f"askpay_{movie[0]}"))
        bot.send_message(call.message.chat.id, f"🌐 **የ {friendly_name} ዝርዝር፦**\nለመውረድ የሚፈልጉትን ፊልም ይጫኑ፦", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, f"😔 በአሁኑ ሰዓት በ {friendly_name} ምድብ ውስጥ የተመዘገበ ፊልም የለም።")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("askpay_"))
def handle_movie_request(call):
    user_id = call.from_user.id
    message_id = int(call.data.split("_")[1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    if res and res[0] == 'paid':
        conn.close()
        bot.answer_callback_query(call.id, "🔄 ፊልሙን እየላክሁ ነው...")
        try:
            bot.copy_message(chat_id=user_id, from_chat_id=CHANNEL_ID, message_id=message_id)
        except Exception:
            bot.send_message(user_id, "⚠️ ፊልሙን መላክ አልተቻለም።")
    else:
        cursor.execute("UPDATE users SET pending_movie = ? WHERE user_id = ?", (message_id, user_id))
        conn.commit()
        conn.close()
        
        pay_info = (
            "🔒 **ይህንን ፊልም ለማውረድ ክፍያ መክፈል አለብዎት!**\n\n"
            "✨ **የክፍያ አማራጮች፦**\n"
            "1️⃣ **ለዚህ ፊልም ብቻ (5 ብር)**\n"
            "2️⃣ **የ 1 ቀን Unlimited (30 ብር)**\n"
            "3️⃣ **የ 7 ቀን Unlimited (70 ብር)**\n"
            "4️⃣ **የ 30 ቀን VIP (100 ብር)**\n\n"
            "📌 **የመክፈያ ቁጥሮች (ባለቤት፦ ሰንደቁ አስማማው)፦**\n"
            "- 📱 **ቴሌብር፦** `0998703233`\n"
            "- 🏦 **CBE ባንክ፦** `1000745390448`\n\n"
            "📸 ክፍያውን እንደፈጸሙ የደረሰኙን ፎቶ (Screenshot) እዚህ ቦት ላይ ይላኩ!"
        )
        bot.send_message(user_id, pay_info, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True)
def handle_movie_search(message):
    query = message.text.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT message_id, title FROM movies WHERE title LIKE ?", (f"%{query}%",))
    search_results = cursor.fetchall()
    conn.close()
    
    if search_results:
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for movie in search_results:
            markup.add(telebot.types.InlineKeyboardButton(f"🎥 {movie[1]}", callback_data=f"askpay_{movie[0]}"))
        bot.reply_to(message, f"🔍 **ከተደረገው ፍለጋ ጋር የሚዛመዱ {len(search_results)} ፊልሞች ተገኝተዋል፦**", reply_markup=markup)
    else:
        bot.reply_to(message, "😔 ይቅርታ፣ የፈለጉት ፊልም በዳታቤዛችን ውስጥ አልተገኘም።")

print("የተሻሻለው አዲሱ ፊልም ቦት በተሳካ ሁኔታ ዝግጁ ሆኗል...")
bot.infinity_polling()
