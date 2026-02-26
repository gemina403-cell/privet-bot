import os, io, logging, urllib.request
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8536905259:AAFcIuz_3JYknR-cHdzMDXEuEsi6sDrEZFA")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== ШРИФТЫ =====
FONTS = {
    "oswald":   ("💪 Oswald (как STKILL)",   "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf"),
    "bebas":    ("🔥 Bebas Neue (жирный)",    "https://github.com/google/fonts/raw/main/ofl/bebasneuepro/BebasNeuePro-SemiExpBook.ttf"),
    "bangers":  ("💥 Bangers (комиксы)",      "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf"),
    "russo":    ("🇷🇺 Russo One (русский стиль)", "https://github.com/google/fonts/raw/main/ofl/russoone/RussoOne-Regular.ttf"),
    "ultra":    ("⚡ Ultra (мощный)",          "https://github.com/google/fonts/raw/main/ofl/ultra/Ultra-Regular.ttf"),
    "teko":     ("🎮 Teko (игровой)",          "https://github.com/google/fonts/raw/main/ofl/teko/Teko%5Bwght%5D.ttf"),
    "boogaloo": ("😎 Boogaloo (крутой)",       "https://github.com/google/fonts/raw/main/ofl/boogaloo/Boogaloo-Regular.ttf"),
    "satisfy":  ("✨ Satisfy (красивый)",       "https://github.com/google/fonts/raw/main/ofl/satisfy/Satisfy-Regular.ttf"),
}

font_cache = {}

def ensure_font(font_key):
    if font_key in font_cache:
        return font_cache[font_key]
    path = f"/app/font_{font_key}.ttf"
    if not os.path.exists(path):
        try:
            url = FONTS[font_key][1]
            logger.info(f"Скачиваю шрифт {font_key}...")
            urllib.request.urlretrieve(url, path)
            ImageFont.truetype(path, 50)  # проверка
            logger.info(f"Шрифт {font_key} скачан!")
        except Exception as e:
            logger.warning(f"Не удалось скачать {font_key}: {e}")
            path = None
    font_cache[font_key] = path
    return path

def get_font(font_key, size):
    path = ensure_font(font_key)
    fallbacks = [
        path,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in fallbacks:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

# Скачиваем первый шрифт сразу при старте
ensure_font("oswald")

# ===== ЦВЕТА =====
COLORS = {
    "teal":     ("💎 Бирюзовый",  (0,   210, 190)),
    "white":    ("⬜ Белый",      (255, 255, 255)),
    "red":      ("🔴 Красный",    (220, 50,  50)),
    "blue":     ("🔵 Синий",      (30,  100, 220)),
    "green":    ("🟢 Зелёный",    (50,  200, 80)),
    "yellow":   ("🟡 Жёлтый",     (255, 220, 0)),
    "orange":   ("🟠 Оранжевый",  (255, 140, 0)),
    "purple":   ("🟣 Фиолетовый", (140, 50,  200)),
    "pink":     ("🌸 Розовый",    (255, 100, 180)),
    "cyan":     ("🩵 Голубой",    (0,   180, 255)),
    "lavender": ("💜 Лавандовый", (170, 130, 255)),
    "maroon":   ("🟥 Бордовый",   (180, 20,  50)),
    "gold":     ("🥇 Золотой",    (255, 200, 0)),
    "gray":     ("⚪ Серый",      (180, 180, 180)),
}

# ===== СТИЛИ =====
STYLES = {
    "1": "Стандартный",
    "2": "Без фона",
    "3": "С тенью",
    "4": "С обводкой",
    "5": "Неон",
    "6": "Маленький",
    "7": "Большой",
    "8": "По центру",
    "9": "Сверху",
    "10": "Снизу слева",
    "11": "Снизу справа",
}

user_sessions = {}

def get_session(uid):
    if uid not in user_sessions:
        user_sessions[uid] = {
            "photo": None, "color": "teal", "style": "1",
            "font": "oswald", "text_type": "logo", "custom_text": "PRIVET",
        }
    return user_sessions[uid]

def draw_outlined(draw, pos, text, font, fill, outline=(0,0,0), width=3):
    x, y = pos
    for dx in range(-width, width+1):
        for dy in range(-width, width+1):
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=(*outline, 200), anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")

def draw_neon(draw, pos, text, font, color):
    x, y = pos
    r, g, b = color
    for w in [8, 5, 3]:
        alpha = 80
        draw.text((x, y), text, font=font, fill=(r, g, b, alpha), anchor="mm",
                  stroke_width=w, stroke_fill=(r, g, b, alpha))
    draw.text((x, y), text, font=font, fill=(r, g, b, 255), anchor="mm")

def generate_avatar(photo_bytes, session):
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
    img = img.resize((600, 600), Image.LANCZOS)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    color_rgb = COLORS[session["color"]][1]
    style = session["style"]
    font_key = session["font"]
    W, H = 600, 600

    size_main = 95
    size_top = 38
    if style == "6": size_main, size_top = 58, 24
    elif style == "7": size_main, size_top = 120, 48

    font_main = get_font(font_key, size_main)
    font_top = get_font(font_key, size_top)

    top_text = "KOD" if session["text_type"] == "logo" else ""
    main_text = "PRIVET" if session["text_type"] == "logo" else session["custom_text"].upper()

    positions = {"8": (W//2, H//2), "9": (W//2, 110), "10": (155, H-115), "11": (W-155, H-115)}
    cx, cy = positions.get(style, (W//2, H-115))

    # Фон
    if style not in ("2", "5"):
        bw = max(len(main_text) * (size_main // 2) + 50, 220)
        bh = (size_main + size_top + 24) if top_text else (size_main + 22)
        draw.rounded_rectangle([cx-bw//2, cy-bh//2, cx+bw//2, cy+bh//2],
                               radius=16, fill=(0, 0, 0, 170))

    fill = (*color_rgb, 255)
    oy = cy + (size_top // 2 + 2 if top_text else 0)

    # Верхний текст
    if top_text:
        draw_outlined(draw, (cx, cy - size_top), top_text, font_top, (255,255,255,255), width=2)

    # Основной текст по стилю
    if style == "3":
        draw.text((cx+5, oy+5), main_text, font=font_main, fill=(0,0,0,150), anchor="mm")
        draw_outlined(draw, (cx, oy), main_text, font_main, fill, width=2)
    elif style == "4":
        draw_outlined(draw, (cx, oy), main_text, font_main, fill, width=4)
    elif style == "5":
        draw_neon(draw, (cx, oy), main_text, font_main, color_rgb)
    else:
        draw_outlined(draw, (cx, oy), main_text, font_main, fill, width=2)

    result = Image.alpha_composite(img, overlay).convert("RGB")
    out = io.BytesIO()
    result.save(out, format="JPEG", quality=93)
    out.seek(0)
    return out.read()

# ===== КЛАВИАТУРЫ =====
def main_menu(session):
    text = (f"🎨 Цвет: {COLORS[session['color']][0]}\n"
            f"✍️ Шрифт: {FONTS[session['font']][0]}\n"
            f"🖼 Стиль: {STYLES[session['style']]}\n"
            f"📝 Текст: {'КОД PRIVET' if session['text_type']=='logo' else session['custom_text']}")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Цвет", callback_data="menu_color"),
         InlineKeyboardButton("✍️ Шрифт", callback_data="menu_font")],
        [InlineKeyboardButton("🖼 Стиль", callback_data="menu_style"),
         InlineKeyboardButton("✏️ Свой текст", callback_data="menu_custom")],
        [InlineKeyboardButton("🔁 КОД PRIVET", callback_data="menu_logo")],
        [InlineKeyboardButton("✅ Создать аватарку!", callback_data="generate")],
    ])
    return text, kb

def color_keyboard():
    rows = []
    row = []
    for k, (label, _) in COLORS.items():
        row.append(InlineKeyboardButton(label, callback_data=f"color_{k}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(rows)

def font_keyboard():
    rows = []
    for k, (label, _) in FONTS.items():
        rows.append([InlineKeyboardButton(label, callback_data=f"font_{k}")])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(rows)

def style_keyboard():
    rows = []
    row = []
    for k, label in STYLES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"style_{k}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(rows)

# ===== ХЭНДЛЕРЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Создаю аватарки с логотипом *PRIVET*.\n\n"
        "📸 Отправь своё фото и начнём!\n\n"
        "Можно выбрать:\n• 8 разных шрифтов\n• 14 цветов\n• 11 стилей",
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = get_session(uid)
    photo = update.message.photo[-1]
    file = await photo.get_file()
    session["photo"] = bytes(await file.download_as_bytearray())
    text, kb = main_menu(session)
    await update.message.reply_text("✅ Фото загружено!\n\n" + text, reply_markup=kb)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    session = get_session(uid)
    data = query.data

    if data == "menu_color":
        await query.edit_message_text("🎨 Выбери цвет:", reply_markup=color_keyboard())
    elif data == "menu_font":
        await query.edit_message_text("✍️ Выбери шрифт:\n(первый раз может качаться ~5 сек)", reply_markup=font_keyboard())
    elif data == "menu_style":
        await query.edit_message_text("🖼 Выбери стиль:", reply_markup=style_keyboard())
    elif data == "menu_custom":
        session["text_type"] = "custom"
        context.user_data["waiting_text"] = True
        await query.edit_message_text("✏️ Напиши текст следующим сообщением (макс. 15 символов):")
    elif data == "menu_logo":
        session["text_type"] = "logo"
        text, kb = main_menu(session)
        await query.edit_message_text(text, reply_markup=kb)
    elif data.startswith("color_"):
        session["color"] = data[6:]
        text, kb = main_menu(session)
        await query.edit_message_text(text, reply_markup=kb)
    elif data.startswith("font_"):
        session["font"] = data[5:]
        # Качаем шрифт в фоне
        ensure_font(session["font"])
        text, kb = main_menu(session)
        await query.edit_message_text(text, reply_markup=kb)
    elif data.startswith("style_"):
        session["style"] = data[6:]
        text, kb = main_menu(session)
        await query.edit_message_text(text, reply_markup=kb)
    elif data == "back":
        text, kb = main_menu(session)
        await query.edit_message_text(text, reply_markup=kb)
    elif data == "generate":
        if not session["photo"]:
            await query.edit_message_text("❌ Сначала отправь фото!")
            return
        await query.edit_message_text("⏳ Создаю аватарку...")
        try:
            result = generate_avatar(session["photo"], session)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=InputFile(io.BytesIO(result), filename="privet.jpg"),
                caption="🎉 Готово! Отправь новое фото чтобы сделать ещё."
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await context.bot.send_message(query.message.chat_id, "❌ Ошибка. Попробуй ещё раз.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = get_session(uid)
    if context.user_data.get("waiting_text"):
        context.user_data["waiting_text"] = False
        session["custom_text"] = update.message.text.strip()[:15]
        text, kb = main_menu(session)
        await update.message.reply_text(f"✅ Текст: «{session['custom_text']}»\n\n" + text, reply_markup=kb)
    else:
        await update.message.reply_text("📸 Отправь фото!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот PRIVET запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

