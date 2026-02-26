"""
PRIVET Avatar Editor Bot
Телеграм-бот для создания аватарок с логотипом PRIVET
Установка: pip install python-telegram-bot pillow
"""

import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ====== НАСТРОЙКИ ======
BOT_TOKEN = "8536905259:AAFcIuz_3JYknR-cHdzMDXEuEsi6sDrEZFA"  # Получить у @BotFather

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== ЦВЕТА ======
COLORS = {
    "white":     ("⬜ Белый",     (255, 255, 255)),
    "black":     ("⬛ Чёрный",    (0,   0,   0)),
    "red":       ("🔴 Красный",   (220, 50,  50)),
    "blue":      ("🔵 Синий",     (30,  100, 220)),
    "green":     ("🟢 Зелёный",   (50,  200, 80)),
    "yellow":    ("🟡 Жёлтый",    (255, 220, 0)),
    "orange":    ("🟠 Оранжевый", (255, 140, 0)),
    "purple":    ("🟣 Фиолетовый",(140, 50,  200)),
    "pink":      ("🌸 Розовый",   (255, 100, 180)),
    "cyan":      ("🩵 Голубой",   (0,   180, 255)),
    "teal":      ("💎 Бирюзовый", (0,   200, 180)),
    "lavender":  ("💜 Лавандовый",(170, 130, 255)),
    "maroon":    ("🟥 Бордовый",  (150, 20,  50)),
    "gray":      ("⚪ Серый",     (160, 160, 160)),
}

# ====== СТИЛИ НАЛОЖЕНИЯ ======
# Каждый стиль — это настройки отрисовки логотипа
STYLES = {
    "1": "Стандартный",
    "2": "Жирный",
    "3": "Тонкий",
    "4": "С тенью",
    "5": "С обводкой",
    "6": "Курсив",
    "7": "Заглавные буквы",
    "8": "Маленький размер",
    "9": "Большой размер",
    "10": "По центру",
    "11": "Угловой",
}

# Хранилище сессий пользователей
user_sessions = {}

def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "photo": None,
            "color": "teal",
            "style": "1",
            "text_type": "logo",  # logo / custom
            "custom_text": "PRIVET",
        }
    return user_sessions[user_id]


# ====== ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ ======
def generate_avatar(photo_bytes: bytes, session: dict) -> bytes:
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
    img = img.resize((600, 600), Image.LANCZOS)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    color_rgb = COLORS[session["color"]][1]
    style = session["style"]
    text = session["custom_text"] if session["text_type"] == "custom" else None

    # Формируем текст
    line1 = "КОД" if text is None else ""
    line2 = "PRIVET" if text is None else text.upper()

    # Настройки стиля
    font_size_main = 90
    font_size_top = 38

    if style == "8":
        font_size_main = 55
        font_size_top = 25
    elif style == "9":
        font_size_main = 110
        font_size_top = 46
    
    import urllib.request, os
    font_path = "/app/font.ttf"
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(
                "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf",
                font_path
            )
        except:
            font_path = None

    try:
        if font_path and os.path.exists(font_path):
            font_main = ImageFont.truetype(font_path, font_size_main)
            font_top = ImageFont.truetype(font_path, font_size_top)
        else:
            raise Exception("no font")
    except:
        try:
            font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_main)
            font_top = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size_top)
        except:
            font_main = ImageFont.load_default().font_variant(size=font_size_main)
            font_top = ImageFont.load_default().font_variant(size=font_size_top)

    W, H = img.size

    # Позиция
    if style == "11":
        cx, cy = W - 160, H - 120
    else:
        cx, cy = W // 2, H - 130

    # Фоновый прямоугольник (полупрозрачный)
    if style not in ("3", "6"):
        bg_w, bg_h = 300, 130 if line1 else 100
        draw.rounded_rectangle(
            [cx - bg_w//2, cy - bg_h//2, cx + bg_w//2, cy + bg_h//2],
            radius=16,
            fill=(0, 0, 0, 160)
        )

    # Тень
    if style == "4":
        draw.text((cx + 3, cy + 3 + (0 if not line1 else 18)),
                  line2, font=font_main, fill=(0, 0, 0, 180), anchor="mm")

    # Текст "КОД" (маленький, белый)
    if line1:
        draw.text((cx, cy - 38), line1, font=font_top,
                  fill=(255, 255, 255, 255), anchor="mm")

    # Основной текст PRIVET с обводкой
    if style == "5":
        for dx in [-2, 2]:
            for dy in [-2, 2]:
                draw.text((cx + dx, cy + (20 if line1 else 0) + dy),
                          line2, font=font_main, fill=(0, 0, 0, 200), anchor="mm")

    draw.text(
        (cx, cy + (20 if line1 else 0)),
        line2,
        font=font_main,
        fill=(*color_rgb, 255),
        anchor="mm"
    )

    # Наложение
    result = Image.alpha_composite(img, overlay).convert("RGB")
    out = io.BytesIO()
    result.save(out, format="JPEG", quality=92)
    out.seek(0)
    return out.read()


# ====== КЛАВИАТУРЫ ======
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Выбрать цвет", callback_data="menu_color"),
         InlineKeyboardButton("🖼 Выбрать стиль", callback_data="menu_style")],
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
        row.append(InlineKeyboardButton(f"#{key} {label}", callback_data=f"style_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(buttons)


# ====== ХЭНДЛЕРЫ ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для создания аватарок с логотипом *PRIVET*.\n\n"
        "📸 Просто отправь мне своё фото, и мы начнём!",
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)

    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = await file.download_as_bytearray()
    session["photo"] = bytes(photo_bytes)

    color_label = COLORS[session["color"]][0]
    style_label = STYLES[session["style"]]
    text_info = "КОД PRIVET" if session["text_type"] == "logo" else f"«{session['custom_text']}»"

    await update.message.reply_text(
        f"✅ Фото загружено!\n\n"
        f"🎨 Цвет: {color_label}\n"
        f"🖼 Стиль: #{session['style']} {style_label}\n"
        f"📝 Текст: {text_info}\n\n"
        f"Настрой параметры или сразу создавай аватарку 👇",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = get_session(user_id)
    data = query.data

    if data == "menu_color":
        await query.edit_message_text("🎨 Выбери цвет наложения:", reply_markup=color_keyboard())

    elif data == "menu_style":
        await query.edit_message_text("🖼 Выбери стиль оформления:", reply_markup=style_keyboard())

    elif data == "menu_custom":
        session["text_type"] = "custom"
        await query.edit_message_text(
            "✏️ Отправь мне текст, который хочешь нанести на аватарку.\n"
            "Напиши его в следующем сообщении:"
        )
        context.user_data["waiting_custom_text"] = True

    elif data == "menu_logo":
        session["text_type"] = "logo"
        session["custom_text"] = "PRIVET"
        await query.edit_message_text(
            "✅ Режим «КОД PRIVET» выбран!",
            reply_markup=main_menu_keyboard()
        )

    elif data.startswith("color_"):
        key = data.replace("color_", "")
        session["color"] = key
        label = COLORS[key][0]
        await query.edit_message_text(
            f"✅ Цвет выбран: {label}",
            reply_markup=main_menu_keyboard()
        )

    elif data.startswith("style_"):
        key = data.replace("style_", "")
        session["style"] = key
        await query.edit_message_text(
            f"✅ Стиль выбран: #{key} {STYLES[key]}",
            reply_markup=main_menu_keyboard()
        )

    elif data == "back":
        color_label = COLORS[session["color"]][0]
        style_label = STYLES[session["style"]]
        text_info = "КОД PRIVET" if session["text_type"] == "logo" else f"«{session['custom_text']}»"
        await query.edit_message_text(
            f"🎨 Цвет: {color_label}\n"
            f"🖼 Стиль: #{session['style']} {style_label}\n"
            f"📝 Текст: {text_info}\n\n"
            f"Выбери что изменить или создавай аватарку 👇",
            reply_markup=main_menu_keyboard()
        )

    elif data == "generate":
        if not session["photo"]:
            await query.edit_message_text(
                "❌ Сначала отправь фото!\nНапиши /start и загрузи фото."
            )
            return

        await query.edit_message_text("⏳ Создаю аватарку, подожди...")

        try:
            result_bytes = generate_avatar(session["photo"], session)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=InputFile(io.BytesIO(result_bytes), filename="privet_avatar.jpg"),
                caption="🎉 Аватарка готова! Сохрани и поставь себе на профиль.\n\n"
                        "Хочешь изменить? Просто отправь новое фото или нажми кнопки выше."
            )
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ошибка при создании. Попробуй ещё раз."
            )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)

    if context.user_data.get("waiting_custom_text"):
        context.user_data["waiting_custom_text"] = False
        text = update.message.text.strip()[:20]  # Ограничение 20 символов
        session["custom_text"] = text
        session["text_type"] = "custom"
        await update.message.reply_text(
            f"✅ Текст установлен: «{text}»",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "📸 Отправь мне фото для создания аватарки!\n"
            "Или напишите /start"
        )


# ====== ЗАПУСК ======
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
