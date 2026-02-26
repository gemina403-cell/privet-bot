"""
PRIVET Avatar Editor Bot
"""

import os
import io
import logging
import urllib.request
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8536905259:AAFcIuz_3JYknR-cHdzMDXEuEsi6sDrEZFA")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Скачиваем шрифт при старте
FONT_PATH = "/app/font.ttf"
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"

def download_font():
    if not os.path.exists(FONT_PATH):
        try:
            logger.info("Скачиваю шрифт...")
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
            logger.info("Шрифт скачан!")
        except Exception as e:
            logger.error(f"Не удалось скачать шрифт: {e}")

download_font()

COLORS = {
    "white":    ("⬜ Белый",      (255, 255, 255)),
    "black":    ("⬛ Чёрный",     (0,   0,   0)),
    "red":      ("🔴 Красный",    (220, 50,  50)),
    "blue":     ("🔵 Синий",      (30,  100, 220)),
    "green":    ("🟢 Зелёный",    (50,  200, 80)),
    "yellow":   ("🟡 Жёлтый",     (255, 220, 0)),
    "orange":   ("🟠 Оранжевый",  (255, 140, 0)),
    "purple":   ("🟣 Фиолетовый", (140, 50,  200)),
    "pink":     ("🌸 Розовый",    (255, 100, 180)),
    "cyan":     ("🩵 Голубой",    (0,   180, 255)),
    "teal":     ("💎 Бирюзовый",  (0,   200, 180)),
    "lavender": ("💜 Лавандовый", (170, 130, 255)),
    "maroon":   ("🟥 Бордовый",   (150, 20,  50)),
    "gray":     ("⚪ Серый",      (160, 160, 160)),
}

STYLES = {
    "1": "Стандартный",
    "2": "Жирный",
    "3": "Без фона",
    "4": "С тенью",
    "5": "С обводкой",
    "6": "Маленький",
    "7": "Большой",
    "8": "По центру",
    "9": "Снизу слева",
    "10": "Снизу справа",
    "11": "Сверху",
}

user_sessions = {}

def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "photo": None,
            "color": "teal",
            "style": "1",
            "text_type": "logo",
            "custom_text": "PRIVET",
        }
    return user_sessions[user_id]

def get_font(size):
    paths = [
        FONT_PATH,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

def generate_avatar(photo_bytes: bytes, session: dict) -> bytes:
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
    img = img.resize((600, 600), Image.LANCZOS)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    color_rgb = COLORS[session["color"]][1]
    style = session["style"]
    W, H = img.size

    # Размеры шрифта
    size_main = 90
    size_top = 36
    if style == "6":
        size_main = 55
        size_top = 22
    elif style == "7":
        size_main = 115
        size_top = 46

    font_main = get_font(size_main)
    font_top = get_font(size_top)

    # Текст
    top_text = "КОД" if session["text_type"] == "logo" else ""
    main_text = "PRIVET" if session["text_type"] == "logo" else session["custom_text"].upper()

    # Позиция
    if style == "9":
        cx, cy = 160, H - 120
    elif style == "10":
        cx, cy = W - 160, H - 120
    elif style == "11":
        cx, cy = W // 2, 120
    else:
        cx, cy = W // 2, H - 120

    # Фон
    if style != "3":
        bw, bh = 320, 140 if top_text else 110
        draw.rounded_rectangle(
            [cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2],
            radius=18, fill=(0, 0, 0, 170)
        )

    # Тень
    if style == "4":
        offset_y = cy + (22 if top_text else 0)
        draw.text((cx+3, offset_y+3), main_text, font=font_main,
                  fill=(0, 0, 0, 180), anchor="mm")

    # Верхний текст КОД
    if top_text:
        draw.text((cx, cy - 38), top_text, font=font_top,
                  fill=(255, 255, 255, 255), anchor="mm")

    # Обводка
    if style == "5":
        for dx in [-3, 3]:
            for dy in [-3, 3]:
                draw.text((cx+dx, cy + (22 if top_text else 0) + dy),
                          main_text, font=font_main,
                          fill=(0, 0, 0, 200), anchor="mm")

    # Основной текст
    draw.text(
        (cx, cy + (22 if top_text else 0)),
        main_text,
        font=font_main,
        fill=(*color_rgb, 255),
        anchor="mm"
    )

    result = Image.alpha_composite(img, overlay).convert("RGB")
    out = io.BytesIO()
    result.save(out, format="JPEG", quality=92)
    out.seek(0)
    return out.read()

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Цвет", callback_data="menu_color"),
         InlineKeyboardButton("🖼 Стиль", callback_data="menu_style")],
        [InlineKeyboardButton("✏️ Свой текст", callback_data="menu_custom"),
         InlineKeyboardButton("🔁 КОД PRIVET", callback_data="menu_logo")],
        [InlineKeyboardButton("✅ Создать аватарку!", callback_data="generate")],
    ])

def color_keyboard():
    buttons = []
    row = []
    for key, (label, _) in COLORS.items():
        row.append(InlineKeyboardButton(label, callback_data=f"color_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)

def style_keyboard():
    buttons = []
    row = []
    for key, label in STYLES.items():
        row.append(InlineKeyboardButton(f"{label}", callback_data=f"style_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для создания аватарок с логотипом *PRIVET*.\n\n"
        "📸 Отправь своё фото и начнём!",
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)
    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()
    session["photo"] = bytes(photo_bytes)

    await update.message.reply_text(
        "✅ Фото загружено! Настрой параметры или сразу создавай 👇",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = get_session(user_id)
    data = query.data

    if data == "menu_color":
        await query.edit_message_text("🎨 Выбери цвет:", reply_markup=color_keyboard())

    elif data == "menu_style":
        await query.edit_message_text("🖼 Выбери стиль:", reply_markup=style_keyboard())

    elif data == "menu_custom":
        session["text_type"] = "custom"
        context.user_data["waiting_custom_text"] = True
        await query.edit_message_text("✏️ Напиши текст для аватарки (следующим сообщением):")

    elif data == "menu_logo":
        session["text_type"] = "logo"
        await query.edit_message_text("✅ Режим «КОД PRIVET» выбран!", reply_markup=main_menu_keyboard())

    elif data.startswith("color_"):
        session["color"] = data.replace("color_", "")
        await query.edit_message_text(
            f"✅ Цвет: {COLORS[session['color']][0]}",
            reply_markup=main_menu_keyboard()
        )

    elif data.startswith("style_"):
        session["style"] = data.replace("style_", "")
        await query.edit_message_text(
            f"✅ Стиль: {STYLES[session['style']]}",
            reply_markup=main_menu_keyboard()
        )

    elif data == "back":
        await query.edit_message_text(
            "Выбери параметры или создавай аватарку 👇",
            reply_markup=main_menu_keyboard()
        )

    elif data == "generate":
        if not session["photo"]:
            await query.edit_message_text("❌ Сначала отправь фото!")
            return
        await query.edit_message_text("⏳ Создаю аватарку...")
        try:
            result_bytes = generate_avatar(session["photo"], session)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=InputFile(io.BytesIO(result_bytes), filename="privet_avatar.jpg"),
                caption="🎉 Аватарка готова!\n\nОтправь новое фото чтобы сделать ещё."
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ошибка. Попробуй ещё раз."
            )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)
    if context.user_data.get("waiting_custom_text"):
        context.user_data["waiting_custom_text"] = False
        text = update.message.text.strip()[:20]
        session["custom_text"] = text
        session["text_type"] = "custom"
        await update.message.reply_text(
            f"✅ Текст: «{text}»",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text("📸 Отправь фото для создания аватарки!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот PRIVET Avatar запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
