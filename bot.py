import time
import telebot
from telebot import types

import config
import database as db
from keep_alive import keep_alive

bot = telebot.TeleBot(config.BOT_TOKEN)
db.init_db()

# Adminning hozirgi holatini saqlab turish uchun
admin_state = {}   # {admin_id: {"action": "...", "file_id": "..."}}


# ================= YORDAMCHI FUNKSIYALAR =================

def is_admin(user_id):
    return user_id == config.ADMIN_ID


def check_subscription(user_id):
    """Foydalanuvchi barcha majburiy kanal/botlarni bajarganmi tekshiradi.
    Faqat kanallar tekshiriladi, botlar tekshirilmaydi."""
    channels = db.get_channels()
    not_done = []
    
    for channel_id, title, type_, invite_link in channels:
        type_ = type_ or "channel"
        if type_ == "channel":
            # Agar bu yopiq kanal bo'lib, foydalanuvchi "qo'shilish so'rovi"
            # yuborgan bo'lsa (admin hali tasdiqlamagan bo'lsa ham),
            # buni yetarli deb hisoblaymiz.
            if db.has_join_request(user_id, channel_id):
                continue
            try:
                # Kanaldan foydalanuvchi ma'lumotini olish
                member = bot.get_chat_member(channel_id, user_id)
                if member.status in ["left", "kicked"]:
                    not_done.append((channel_id, title, type_, invite_link))
            except Exception as e:
                # Agar xatolik bo'lsa (yopiq kanal yoki bot admin emas)
                # Foydalanuvchini a'zo emas deb hisoblaymiz
                not_done.append((channel_id, title, type_, invite_link))
        # type_ == "bot" - TEKSHIRILMAYDI
    
    return not_done


def subscription_keyboard(not_done):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Faqat hali obuna bo'linmagan kanallarni (not_done) va barcha botlarni
    # ko'rsatamiz. Botlar hech qachon tekshirilmagani uchun (faqat zayavka
    # tashlash kifoya), ular har doim ro'yxatda qoladi, lekin kanallar
    # obuna bo'lingandan so'ng ro'yxatdan chiqib ketadi.
    bots = [item for item in db.get_channels() if (item[2] or "channel") == "bot"]
    all_items = list(not_done) + bots
    
    # Raqamlash uchun indeks
    idx = 1
    for channel_id, title, type_, invite_link in all_items:
        type_ = type_ or "channel"
        
        # Havola yaratish
        if type_ == "channel":
            # Agar invite_link bo'lsa, undan foydalanamiz
            if invite_link and invite_link.startswith('https://t.me/'):
                url = invite_link
            else:
                # Aks holda username orqali
                username = str(channel_id).lstrip('@')
                url = f"https://t.me/{username}"
            
            button_text = f"{idx}-Kanal"
        else:  # bot
            username = str(channel_id).lstrip('@')
            url = f"https://t.me/{username}"
            button_text = f"{idx}-Bot"
        
        markup.add(types.InlineKeyboardButton(button_text, url=url))
        idx += 1
    
    markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return markup


def admin_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📊 Statistika", callback_data="adm_stats"),
        types.InlineKeyboardButton("📢 Majburiy obuna", callback_data="adm_channels"),
        types.InlineKeyboardButton("🎬 Kinolar", callback_data="adm_videos"),
    )
    return markup


# ================= FOYDALANUVCHI QISMI =================

@bot.message_handler(commands=['start'])
def start_handler(message):
    db.add_user(message.from_user.id)
    
    # Foydalanuvchi ismini olish
    user = message.from_user
    first_name = user.first_name or "Foydalanuvchi"
    
    not_done = check_subscription(message.from_user.id)
    if not_done:
        bot.send_message(
            message.chat.id,
            f"👋 Salom {first_name} botimizga xush kelibsiz.\n\n"
            "Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling, "
            "so'ng \"✅ Tekshirish\" tugmasini bosing:",
            reply_markup=subscription_keyboard(not_done),
        )
        return
    
    bot.send_message(
        message.chat.id,
        f"👋 Salom {first_name} botimizga xush kelibsiz.\n\n"
        "✍🏻 Kino kodini yuboring.\n"
        "Masalan: 130",
    )


@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    not_done = check_subscription(call.from_user.id)
    if not_done:
        bot.answer_callback_query(call.id, "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
    
    user = call.from_user
    first_name = user.first_name or "Foydalanuvchi"
    
    bot.edit_message_text(
        f"✅ Tasdiqlandi!\n\n"
        f"👋 Salom {first_name} botimizga xush kelibsiz.\n\n"
        f"✍🏻 Kino kodini yuboring.\n"
        f"Masalan: 130",
        call.message.chat.id,
        call.message.message_id,
    )


@bot.chat_join_request_handler()
def handle_chat_join_request(chat_join_request):
    """Foydalanuvchi yopiq kanalga 'qo'shilish so'rovi' yuborganda ishga tushadi.
    Admin so'rovni hali tasdiqlamagan bo'lsa ham, so'rov yuborilganining o'zi
    bazaga yoziladi va bu kanal uchun 'obuna bo'ldi' deb hisoblanadi."""
    user_id = chat_join_request.from_user.id
    chat = chat_join_request.chat
    # Kanal bazada @username yoki raqamli ID sifatida saqlangan bo'lishi
    # mumkin - ikkalasi ham mos tushishi uchun ikkalasini ham yozamiz.
    db.add_join_request(user_id, chat.id)
    if chat.username:
        db.add_join_request(user_id, f"@{chat.username}")


# ================= ADMIN PANEL =================

@bot.message_handler(commands=['admin'])
def admin_handler(message):
    if not is_admin(message.from_user.id):
        return
    admin_state.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "🔧 Admin panel", reply_markup=admin_main_menu())


@bot.callback_query_handler(func=lambda call: call.data == "adm_back")
def adm_back(call):
    if not is_admin(call.from_user.id):
        return
    admin_state.pop(call.from_user.id, None)
    bot.edit_message_text("🔧 Admin panel", call.message.chat.id, call.message.message_id, reply_markup=admin_main_menu())


@bot.callback_query_handler(func=lambda call: call.data == "adm_stats")
def adm_stats(call):
    if not is_admin(call.from_user.id):
        return
    users = db.get_users_count()
    videos = db.get_videos_count()
    requests_count = db.get_requests_count()
    text = (
        "📊 Statistika\n\n"
        f"👤 Foydalanuvchilar soni: {users}\n"
        f"🎬 Kinolar soni: {videos}\n"
        f"📥 Kod so'rovlari soni: {requests_count}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="adm_back"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "adm_channels")
def adm_channels(call):
    if not is_admin(call.from_user.id):
        return
    channels = db.get_channels()
    text = "📢 Majburiy obuna ro'yxati:\n\n"
    if channels:
        for idx, (cid, title, type_, invite_link) in enumerate(channels, 1):
            icon = "📢" if (type_ or "channel") == "channel" else "🤖"
            display_title = title or cid
            if invite_link:
                display_title += f" (🔗 havola bilan)"
            text += f"{idx}. {icon} {display_title}\n"
    else:
        text += "Hozircha hech narsa qo'shilmagan."
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ Kanal qo'shish", callback_data="adm_addchannel_channel"),
        types.InlineKeyboardButton("➕ Bot qo'shish", callback_data="adm_addchannel_bot"),
        types.InlineKeyboardButton("➖ O'chirish", callback_data="adm_delchannel"),
        types.InlineKeyboardButton("⬅️ Orqaga", callback_data="adm_back"),
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ("adm_addchannel_channel", "adm_addchannel_bot"))
def adm_addchannel(call):
    if not is_admin(call.from_user.id):
        return
    type_ = "channel" if call.data == "adm_addchannel_channel" else "bot"
    admin_state[call.from_user.id] = {"action": "waiting_channel_add", "type": type_}
    bot.answer_callback_query(call.id)
    if type_ == "channel":
        bot.send_message(
            call.message.chat.id,
            "📢 Kanalni qo'shish uchun biror usulni tanlang:\n\n"
            "📌 Ochiq kanal: @kanal_username yoki https://t.me/kanal_username\n"
            "📌 Yopiq kanal: kanaldan istalgan bitta POSTNI shu botga FORWARD qiling\n"
            "   (t.me/+... yoki t.me/joinchat/... havolasidan ID aniqlab bo'lmaydi)\n\n"
            "⚠️ Diqqat: bot o'sha kanalda ADMIN bo'lishi shart!",
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "🤖 Bot username'ini yuboring (masalan: @boshqabot).\n\n"
            "ℹ️ Bot faqat ro'yxatda ko'rinadi, a'zolik tekshirilmaydi.",
        )


@bot.callback_query_handler(func=lambda call: call.data == "adm_delchannel")
def adm_delchannel(call):
    if not is_admin(call.from_user.id):
        return
    channels = db.get_channels()
    if not channels:
        bot.answer_callback_query(call.id, "Ro'yxat bo'sh", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, (cid, title, type_, invite_link) in enumerate(channels, 1):
        icon = "📢" if (type_ or "channel") == "channel" else "🤖"
        display_title = title or cid
        if len(display_title) > 25:
            display_title = display_title[:22] + "..."
        markup.add(types.InlineKeyboardButton(
            f"❌ {idx}. {icon} {display_title}", 
            callback_data=f"delch_{cid}"
        ))
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="adm_channels"))
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "O'chirmoqchi bo'lgan punktni tanlang:", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("delch_"))
def delch_callback(call):
    if not is_admin(call.from_user.id):
        return
    channel_id = call.data.replace("delch_", "", 1)
    db.remove_channel(channel_id)
    bot.answer_callback_query(call.id, "✅ O'chirildi")
    adm_channels(call)


# ---------- Kinolar menyusi ----------

@bot.callback_query_handler(func=lambda call: call.data == "adm_videos")
def adm_videos(call):
    if not is_admin(call.from_user.id):
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ Kino qo'shish", callback_data="adm_addvideo"),
        types.InlineKeyboardButton("🗑 Kino o'chirish", callback_data="adm_delvideo"),
        types.InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="adm_listvideos"),
        types.InlineKeyboardButton("⬅️ Orqaga", callback_data="adm_back"),
    )
    bot.edit_message_text("🎬 Kinolar bo'limi", call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "adm_addvideo")
def adm_addvideo(call):
    if not is_admin(call.from_user.id):
        return
    admin_state[call.from_user.id] = {"action": "waiting_video"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🎬 Kino faylini yuboring (video sifatida).")


@bot.callback_query_handler(func=lambda call: call.data == "adm_listvideos")
def adm_listvideos(call):
    if not is_admin(call.from_user.id):
        return
    codes = db.get_all_video_codes()
    if codes:
        text = "📋 Kinolar ro'yxati:\n\n" + "\n".join(f"• {c}" for c in codes[:100])
        if len(codes) > 100:
            text += f"\n\n... va yana {len(codes) - 100} ta"
    else:
        text = "Hozircha kino qo'shilmagan."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="adm_videos"))
    bot.answer_callback_query(call.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "adm_delvideo")
def adm_delvideo(call):
    if not is_admin(call.from_user.id):
        return
    admin_state[call.from_user.id] = {"action": "waiting_delete_code"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🗑 O'chirmoqchi bo'lgan kinoning kodini yuboring (masalan: 130-677):")


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id)
    and admin_state.get(m.from_user.id, {}).get("action") == "waiting_delete_code"
)
def process_delete_video(message):
    code = message.text.strip()
    admin_state.pop(message.from_user.id, None)
    if db.delete_video(code):
        bot.send_message(message.chat.id, f"✅ '{code}' kodidagi kino o'chirildi.", reply_markup=admin_main_menu())
    else:
        bot.send_message(message.chat.id, f"❌ '{code}' kodi topilmadi.", reply_markup=admin_main_menu())


# ================= ADMIN INPUT (matn / video) =================

@bot.message_handler(
    content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'],
    func=lambda m: is_admin(m.from_user.id)
    and admin_state.get(m.from_user.id, {}).get("action") == "waiting_channel_add"
)
def process_add_channel(message):
    type_ = admin_state[message.from_user.id].get("type", "channel")

    invite_link = None
    channel_id = None
    title = None

    # 1) Eng ishonchli usul: admin kanaldan post FORWARD qilgan bo'lsa,
    #    bot haqiqiy chat.id ni to'g'ridan-to'g'ri oladi (yopiq kanallar uchun ham ishlaydi)
    if message.forward_from_chat and message.forward_from_chat.type in ("channel", "supergroup"):
        chat = message.forward_from_chat
        channel_id = str(chat.id)
        title = chat.title or channel_id
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
    else:
        user_input = (message.text or "").strip()
        if not user_input:
            bot.send_message(
                message.chat.id,
                "⚠️ Iltimos, @username yuboring yoki kanaldan bitta postni FORWARD qiling.",
            )
            return

        if user_input.startswith('https://t.me/') or user_input.startswith('t.me/'):
            link = user_input if user_input.startswith('https://') else 'https://' + user_input
            path = link.split('t.me/', 1)[1].split('?')[0].strip('/')
            if path.startswith('+') or path.lower().startswith('joinchat/'):
                # Yopiq kanal havolasi - undan ID ni aniqlab bo'lmaydi
                bot.send_message(
                    message.chat.id,
                    "⚠️ Bu yopiq kanal havolasi, undan kanal ID'sini avtomatik aniqlab bo'lmaydi.\n\n"
                    "Iltimos, o'sha kanaldan istalgan bitta postni ushbu botga FORWARD qiling "
                    "(bot o'sha kanalda ADMIN bo'lishi kerak).",
                )
                return
            # Ochiq kanal linki (t.me/username) - shundan username ajratib olinadi
            channel_id = '@' + path
            invite_link = link
        elif user_input.startswith('@'):
            channel_id = user_input
        elif user_input.startswith('-100'):
            channel_id = user_input
        else:
            channel_id = '@' + user_input

    # Kanal nomini olishga urinamiz (agar hali aniqlanmagan bo'lsa)
    if not title:
        title = channel_id
        try:
            chat = bot.get_chat(channel_id)
            title = chat.title or channel_id
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"⚠️ Kanal topilmadi yoki bot admin emas.\n\n"
                f"Xatolik: {str(e)}\n\n"
                f"Kanal ID: {channel_id}\n"
                f"Kanal shunday saqlanadi, lekin a'zolikni tekshirish ishlamasligi mumkin.",
            )

    # Botlar har doim ochiq username'ga ega, shuning uchun havolani
    # o'zimiz yasab olamiz va admindan alohida so'ramaymiz
    if type_ == "bot" and not invite_link and channel_id and channel_id.startswith('@'):
        invite_link = f"https://t.me/{channel_id.lstrip('@')}"

    # Agar kanal username'i (va demak invite_link) bo'lmasa - tugma uchun
    # havola kerak bo'ladi, shuni admindan alohida so'raymiz
    if not invite_link:
        admin_state[message.from_user.id] = {
            "action": "waiting_channel_invite_link",
            "type": type_,
            "channel_id": channel_id,
            "title": title,
        }
        bot.send_message(
            message.chat.id,
            "🔗 Bu kanalda ochiq username yo'q, shuning uchun foydalanuvchilar bosadigan "
            "tugma uchun taklif havolasi (Invite link) kerak.\n\n"
            "Kanal sozlamalaridan \"Invite link\" ni nusxalab shu yerga yuboring:",
        )
        return

    db.add_channel(channel_id, title, type_, invite_link)
    admin_state.pop(message.from_user.id, None)
    label = "Kanal" if type_ == "channel" else "Bot"

    bot.send_message(
        message.chat.id,
        f"✅ {label} qo'shildi!\n"
        f"Nomi: {title}\n"
        f"Havola: {invite_link}",
        reply_markup=admin_main_menu(),
    )


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id)
    and admin_state.get(m.from_user.id, {}).get("action") == "waiting_channel_invite_link"
)
def process_channel_invite_link(message):
    state = admin_state[message.from_user.id]
    invite_link = message.text.strip()
    if not (invite_link.startswith('https://t.me/') or invite_link.startswith('t.me/')):
        bot.send_message(message.chat.id, "⚠️ Iltimos, to'g'ri havola yuboring (https://t.me/... bilan boshlanishi kerak).")
        return
    if not invite_link.startswith('https://'):
        invite_link = 'https://' + invite_link

    db.add_channel(state["channel_id"], state["title"], state["type"], invite_link)
    admin_state.pop(message.from_user.id, None)
    label = "Kanal" if state["type"] == "channel" else "Bot"
    bot.send_message(
        message.chat.id,
        f"✅ {label} qo'shildi!\n"
        f"Nomi: {state['title']}\n"
        f"Havola: {invite_link}",
        reply_markup=admin_main_menu(),
    )


@bot.message_handler(
    content_types=['video', 'document'],
    func=lambda m: is_admin(m.from_user.id)
    and admin_state.get(m.from_user.id, {}).get("action") == "waiting_video",
)
def process_add_video(message):
    file_id = message.video.file_id if message.video else message.document.file_id
    admin_state[message.from_user.id] = {"action": "waiting_video_code", "file_id": file_id}
    bot.send_message(message.chat.id, "🔢 Endi shu kino uchun kod kiriting (masalan: 130-677):")


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id)
    and admin_state.get(m.from_user.id, {}).get("action") == "waiting_video_code"
)
def process_video_code(message):
    code = message.text.strip()
    admin_state[message.from_user.id]["code"] = code
    admin_state[message.from_user.id]["action"] = "waiting_video_caption"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➡️ O'tkazib yuborish", callback_data="skip_caption"))
    bot.send_message(
        message.chat.id,
        "✏️ Endi kino tagiga chiqadigan matnni (caption) yuboring.\n"
        "Masalan: nomi, yili, tavsifi va h.k.\n\n"
        "Agar matn kerak bo'lmasa, pastdagi tugmani bosing.",
        reply_markup=markup,
    )


def save_video_with_caption(user_id, chat_id, caption):
    state = admin_state.get(user_id, {})
    code = state.get("code")
    file_id = state.get("file_id")
    already_existed = db.code_exists(code)
    db.add_video(code, file_id, caption)
    if already_existed:
        text = f"♻️ '{code}' kodi allaqachon mavjud edi, kino yangilandi."
    else:
        text = f"✅ Kino '{code}' kodi bilan saqlandi!"
    admin_state.pop(user_id, None)
    bot.send_message(chat_id, text, reply_markup=admin_main_menu())


@bot.callback_query_handler(func=lambda call: call.data == "skip_caption")
def skip_caption_callback(call):
    if not is_admin(call.from_user.id):
        return
    if admin_state.get(call.from_user.id, {}).get("action") != "waiting_video_caption":
        return
    bot.answer_callback_query(call.id)
    save_video_with_caption(call.from_user.id, call.message.chat.id, "")


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id)
    and admin_state.get(m.from_user.id, {}).get("action") == "waiting_video_caption"
)
def process_video_caption(message):
    caption = message.text.strip()
    save_video_with_caption(message.from_user.id, message.chat.id, caption)


# ================= FOYDALANUVCHI: KOD SO'ROVI =================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def code_request_handler(message):
    # /start va /admin buyruqlarini qayta ishlamaslik uchun
    if message.text.startswith('/'):
        return
    
    db.add_user(message.from_user.id)
    
    not_done = check_subscription(message.from_user.id)
    if not_done:
        user = message.from_user
        first_name = user.first_name or "Foydalanuvchi"
        
        bot.send_message(
            message.chat.id,
            f"👋 Salom {first_name} botimizga xush kelibsiz.\n\n"
            "Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling, "
            "so'ng \"✅ Tekshirish\" tugmasini bosing:",
            reply_markup=subscription_keyboard(not_done),
        )
        return

    code = message.text.strip()
    result = db.get_video(code)
    if result:
        file_id, caption = result
        db.log_request(message.from_user.id, code)
        try:
            bot.send_video(message.chat.id, file_id, caption=caption or None, protect_content=True)
        except Exception:
            bot.send_document(message.chat.id, file_id, caption=caption or None, protect_content=True)
    else:
        bot.send_message(message.chat.id, "❌ Bunday kod topilmadi. Kodni tekshirib qaytadan yuboring.")


# ================= ISHGA TUSHIRISH =================

if __name__ == "__main__":
    keep_alive()
    print("Bot ishga tushdi...")
    
    # Botni to'g'ri ishga tushirish
    # allowed_updates ro'yxatiga "chat_join_request" ni ham qo'shamiz,
    # aks holda bot yopiq kanallarga yuborilgan qo'shilish so'rovlarini
    # ko'ra olmaydi.
    allowed = ["message", "edited_message", "callback_query", "chat_join_request"]
    try:
        bot.infinity_polling(skip_pending=True, timeout=60, allowed_updates=allowed)
    except Exception as e:
        print(f"Xatolik: {e}")
        time.sleep(5)
        bot.infinity_polling(skip_pending=True, timeout=60, allowed_updates=allowed)