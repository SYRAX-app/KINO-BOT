# 🎬 Telegram Video-Kod Bot (Admin panel bilan)

## Bot nima qiladi?
- `/start` bosilganda majburiy kanallarga obunani tekshiradi
- Admin panel orqali:
  1. Majburiy **kanal** va **bot**larni qo'shish/o'chirish
  2. Statistikani ko'rish (foydalanuvchilar, videolar, so'rovlar soni)
  3. Videoni kod bilan joylash (masalan `130-677`) va kod bo'yicha **o'chirish**
- Oddiy foydalanuvchi kod yuborsa — mos video yuboriladi

### ⚠️ Majburiy "bot" haqida muhim eslatma
Telegram Bot API orqali **boshqa botga foydalanuvchi /start bosganini tekshirib bo'lmaydi**
(bu faqat kanal/guruh a'zoligi uchun ishlaydi). Shu sabab bot punktlari uchun foydalanuvchi
botni ochib, qaytib kelib **"☑️ Tasdiqlayman"** tugmasini bosishi kerak — bu haqiqiy texnik
tekshiruv emas, ishonchga asoslangan tasdiqlash. Kanal punktlari esa **real tekshiriladi**
(bot o'sha kanalda admin bo'lishi sharti bilan).

---

## 1-QADAM: Bot yaratish (BotFather)
1. Telegramda **@BotFather** ni oching
2. `/newbot` yuboring, nom va username bering
3. Sizga **BOT_TOKEN** beriladi (masalan `123456:AAExxxx...`) — saqlab qo'ying

## 2-QADAM: Admin ID ni bilib olish
1. Telegramda **@userinfobot** ga o'ting
2. `/start` bosing — u sizga **ID** raqamingizni beradi (masalan `987654321`) — bu **ADMIN_ID**

## 3-QADAM: GitHubga yuklash
1. GitHub'da yangi repository yarating (masalan `video-kod-bot`)
2. Shu papkadagi barcha fayllarni (`bot.py`, `database.py`, `keep_alive.py`, `config.py`,
   `requirements.txt`, `Procfile`) shu repoga yuklang
   - Android telefonda: GitHub ilovasi orqali yoki brauzerdan "Add file → Upload files"
     qilib zipdan chiqarilgan fayllarni tashlang

## 4-QADAM: Renderda deploy qilish
1. https://render.com ga kiring, GitHub akkountingiz bilan bog'lang
2. **New → Web Service** tugmasini bosing
3. Yangi yuklagan repositoryingizni tanlang
4. Sozlamalar:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Free
5. **Environment Variables** bo'limiga qo'shing:
   - `BOT_TOKEN` = BotFatherdan olgan tokeningiz
   - `ADMIN_ID` = sizning Telegram ID raqamingiz
6. **Create Web Service** ni bosing — Render avtomatik build qilib botni ishga tushiradi
7. Loglarda `Bot ishga tushdi...` yozuvini ko'rsangiz — bot ishlayapti ✅

## 5-QADAM: UptimeRobot bilan botni "uxlab qolishdan" saqlash
Renderning bepul tarifi 15 daqiqa harakatsiz tursa "uxlab qoladi". Buni oldini olish uchun:
1. Render loyihangiz sahifasida yuqorida turgan **URL**ni nusxa oling
   (masalan `https://video-kod-bot.onrender.com`)
2. https://uptimerobot.com ga kirib ro'yxatdan o'ting
3. **+ New Monitor** tugmasini bosing:
   - Monitor Type: **HTTP(s)**
   - URL: Renderdagi manzilingiz
   - Monitoring Interval: **5 daqiqa**
4. Saqlang — endi UptimeRobot har 5 daqiqada botingizni "uyg'otib" turadi

## 6-QADAM: Botdan foydalanish
1. Telegramda botingizni oching, `/start` bosing
2. Admin sifatida `/admin` buyrug'ini yuboring — admin panel ochiladi
3. **📢 Majburiy obuna → Kanal qo'shish** (yoki **Bot qo'shish**) orqali username yuboring
   - Kanal uchun: bot o'sha kanalda **admin** bo'lishi shart
   - Bot uchun: real tekshiruv yo'q, faqat foydalanuvchi tasdiqlaydi (yuqoridagi eslatmaga qarang)
   - **➖ O'chirish** orqali istalgan punktni ro'yxatdan olib tashlash mumkin
4. **🎬 Kinolar** bo'limida:
   - **➕ Kino qo'shish** — video yuborib, kod kiriting (masalan `130-677`), so'ng kino tagiga
     chiqadigan matnni (caption) yuboring — kerak bo'lmasa "O'tkazib yuborish" tugmasini bosing
   - **🗑 Kino o'chirish** — o'chirmoqchi bo'lgan kodni yozing
   - **📋 Kinolar ro'yxati** — barcha joylangan kodlarni ko'rish
5. Endi istalgan foydalanuvchi shu kodni yuborsa, o'sha kino (matni bilan) chiqadi.
   Kino **forward qilib bo'lmaydigan** va **saqlab (download) bo'lmaydigan** holatda yuboriladi
   (Telegram'ning "content protection" xususiyati orqali).

---

## ⚠️ Muhim eslatma (ma'lumotlar bazasi haqida)
Bu bot ma'lumotlarni (foydalanuvchilar, kanallar, video kodlar) oddiy `sqlite` faylida saqlaydi.
Render'ning bepul tarifida bu fayl **har safar qayta deploy qilinganda** (masalan kodni
yangilaganingizda) **tozalanishi mumkin**, lekin oddiy qayta ishga tushish/uyg'onishda saqlanib
qoladi. Agar ma'lumotlar doimiy saqlanishi zarur bo'lsa, keyinchalik Render'ning **Persistent Disk**
(pullik) xizmatidan yoki tashqi bazadan (masalan PostgreSQL) foydalanish tavsiya etiladi.

## Fayllar tuzilishi
```
telegram-video-bot/
├── bot.py           # asosiy bot logikasi
├── database.py       # sqlite bilan ishlash
├── keep_alive.py      # Render/UptimeRobot uchun mini server
├── config.py         # tokenlar (.env orqali)
├── requirements.txt   # kutubxonalar
├── Procfile           # Render start buyrug'i
└── README.md
```
