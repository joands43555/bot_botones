"""
Bot de Telegram — Publica video con botones directo en canales
"""

import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, PreCheckoutQueryHandler,
    ContextTypes, filters,
)
from config import (
    BOT_TOKEN, ADMIN_IDS, TUTORIAL_URL, PAYPAL_URL,
    VIP_CHANNEL_LINK, STARS_PRICE, WELCOME_TEXT,
    SIGNAL_FOOTER, BOT_NAME, BTN_OPCION1, BTN_OPCION2,
    CHANNEL_IDS, BOT_USERNAME,
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Estados /senal
(ESPERANDO_VIDEO, ESPERANDO_LINK1, ESPERANDO_LINK2, ESPERANDO_CAPTION) = range(4)

# Estados /anuncio
(AN_VIDEO, AN_CAPTION) = range(4, 6)


# ── Teclado completo (para /senal) ─────────────────────────
def build_keyboard(link1: str, link2: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"👉 {BTN_OPCION1}", url=link1),
            InlineKeyboardButton(f"👉 {BTN_OPCION2}", url=link2),
        ],
        [
            InlineKeyboardButton("💎 VIP via PayPal",    url=PAYPAL_URL),
            InlineKeyboardButton("⭐ VIP via Estrellas",  url=f"https://t.me/{BOT_USERNAME}?start=vip_stars"),
        ],
        [
            InlineKeyboardButton("📋 TUTORIAL", url=TUTORIAL_URL),
        ],
    ])


# ── Teclado solo VIP (para /anuncio) ──────────────────────
def vip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 VIP via PayPal",    url=PAYPAL_URL),
            InlineKeyboardButton("⭐ VIP via Estrellas",  url=f"https://t.me/{BOT_USERNAME}?start=vip_stars"),
        ],
    ])


# ── Teclado /start y /menu ─────────────────────────────────
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 VIP via PayPal",    url=PAYPAL_URL),
            InlineKeyboardButton("⭐ VIP via Estrellas",  url=f"https://t.me/{BOT_USERNAME}?start=vip_stars"),
        ],
        [
            InlineKeyboardButton("📋 TUTORIAL", url=TUTORIAL_URL),
        ],
    ])


async def send_stars_invoice(chat_id, context):
    await context.bot.send_invoice(
        chat_id=chat_id,
        title=f"⭐ Acceso VIP — {BOT_NAME}",
        description="Acceso ilimitado al canal VIP. Pago seguro con Telegram Stars. ✅",
        payload="vip_stars_payment",
        currency="XTR",
        prices=[LabeledPrice("VIP Access", STARS_PRICE)],
        provider_token="",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0] == "vip_stars":
        await send_stars_invoice(update.effective_user.id, context)
        return
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_keyboard(), parse_mode="HTML")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"<b>📌 {BOT_NAME}</b>\nElige una opción:",
        reply_markup=main_keyboard(), parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════
#  FLUJO /senal — Video completo con 4 botones
# ══════════════════════════════════════════════════════════

async def senal_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Sin permiso.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "🎬 <b>Paso 1/4 — Video</b>\n\nEnvía el video que quieres publicar.\n\n/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_VIDEO


async def senal_recibir_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.video:
        context.user_data["media_type"] = "video"
        context.user_data["file_id"] = msg.video.file_id
    elif msg.photo:
        context.user_data["media_type"] = "photo"
        context.user_data["file_id"] = msg.photo[-1].file_id
    elif msg.animation:
        context.user_data["media_type"] = "animation"
        context.user_data["file_id"] = msg.animation.file_id
    else:
        await msg.reply_text("❌ Envía un video, foto o GIF.\n/cancelar para salir.")
        return ESPERANDO_VIDEO

    await msg.reply_text(
        f"✅ Video recibido.\n\n🔗 <b>Paso 2/4 — Link {BTN_OPCION1}</b>\n\n"
        f"Pega el link de Linkvertise para <b>{BTN_OPCION1}</b>:\n\n/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_LINK1


async def senal_recibir_link1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("❌ Link inválido.\n/cancelar para salir.")
        return ESPERANDO_LINK1
    context.user_data["link1"] = link
    await update.message.reply_text(
        f"✅ Link 1 guardado.\n\n🔗 <b>Paso 3/4 — Link {BTN_OPCION2}</b>\n\n"
        f"Pega el link de Linkvertise para <b>{BTN_OPCION2}</b>:\n\n/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_LINK2


async def senal_recibir_link2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("❌ Link inválido.\n/cancelar para salir.")
        return ESPERANDO_LINK2
    context.user_data["link2"] = link
    await update.message.reply_text(
        "✏️ <b>Paso 4/4 — Descripción</b>\n\nEscribe el texto que irá debajo del video:\n\n"
        "<i>Ejemplo:\n🔥 Lucia Rossi\n#LuciaRossi</i>\n\n/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_CAPTION


async def senal_publicar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    caption    = update.message.text.strip()
    link1      = context.user_data["link1"]
    link2      = context.user_data["link2"]
    media_type = context.user_data["media_type"]
    file_id    = context.user_data["file_id"]
    full_caption = f"{caption}\n\n{SIGNAL_FOOTER}"
    keyboard     = build_keyboard(link1, link2)

    publicados = 0
    for channel_id in CHANNEL_IDS:
        try:
            if media_type == "video":
                await context.bot.send_video(chat_id=channel_id, video=file_id, caption=full_caption, reply_markup=keyboard, parse_mode="HTML")
            elif media_type == "photo":
                await context.bot.send_photo(chat_id=channel_id, photo=file_id, caption=full_caption, reply_markup=keyboard, parse_mode="HTML")
            elif media_type == "animation":
                await context.bot.send_animation(chat_id=channel_id, animation=file_id, caption=full_caption, reply_markup=keyboard, parse_mode="HTML")
            publicados += 1
        except Exception as e:
            logger.error(f"❌ Error en canal {channel_id}: {e}")

    await update.message.reply_text(f"✅ <b>Publicado en {publicados}/{len(CHANNEL_IDS)} canales.</b>", parse_mode="HTML")
    context.user_data.clear()
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════
#  FLUJO /anuncio — Preview con solo botones VIP
# ══════════════════════════════════════════════════════════

async def anuncio_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Sin permiso.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "📢 <b>Paso 1/2 — Video o imagen</b>\n\n"
        "Envía el video o foto del anuncio.\n\n"
        "/cancelar para salir.",
        parse_mode="HTML",
    )
    return AN_VIDEO


async def anuncio_recibir_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.video:
        context.user_data["media_type"] = "video"
        context.user_data["file_id"] = msg.video.file_id
    elif msg.photo:
        context.user_data["media_type"] = "photo"
        context.user_data["file_id"] = msg.photo[-1].file_id
    elif msg.animation:
        context.user_data["media_type"] = "animation"
        context.user_data["file_id"] = msg.animation.file_id
    else:
        await msg.reply_text("❌ Envía un video, foto o GIF.\n/cancelar para salir.")
        return AN_VIDEO

    await msg.reply_text(
        "✅ Recibido.\n\n"
        "✏️ <b>Paso 2/2 — Descripción</b>\n\n"
        "Escribe el texto del anuncio:\n\n"
        "<i>Ejemplo:\n🔒 Video completo disponible solo en el canal VIP\n#LuciaRossi</i>\n\n"
        "/cancelar para salir.",
        parse_mode="HTML",
    )
    return AN_CAPTION


async def anuncio_publicar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    caption    = update.message.text.strip()
    media_type = context.user_data["media_type"]
    file_id    = context.user_data["file_id"]
    keyboard   = vip_keyboard()
    full_caption = f"{caption}\n\n🔒 <b>Contenido completo disponible en el canal VIP</b>"

    publicados = 0
    for channel_id in CHANNEL_IDS:
        try:
            if media_type == "video":
                await context.bot.send_video(chat_id=channel_id, video=file_id, caption=full_caption, reply_markup=keyboard, parse_mode="HTML")
            elif media_type == "photo":
                await context.bot.send_photo(chat_id=channel_id, photo=file_id, caption=full_caption, reply_markup=keyboard, parse_mode="HTML")
            elif media_type == "animation":
                await context.bot.send_animation(chat_id=channel_id, animation=file_id, caption=full_caption, reply_markup=keyboard, parse_mode="HTML")
            publicados += 1
        except Exception as e:
            logger.error(f"❌ Error en canal {channel_id}: {e}")

    await update.message.reply_text(f"✅ <b>Anuncio publicado en {publicados}/{len(CHANNEL_IDS)} canales.</b>", parse_mode="HTML")
    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelado.")
    return ConversationHandler.END


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"✅ <b>¡Pago confirmado!</b>\n\nBienvenido al VIP, <b>{user.first_name}</b> 🎉\n\n👉 {VIP_CHANNEL_LINK}",
        parse_mode="HTML",
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id in ADMIN_IDS
    text = f"<b>📖 {BOT_NAME}</b>\n\n/start — Bienvenida\n/menu — Menú\n/ayuda — Comandos\n"
    if is_admin:
        text += (
            "\n🔑 <b>Admin:</b>\n"
            "/senal — Publicar video con 4 botones (Linkvertise + VIP)\n"
            "/anuncio — Publicar preview con solo botones VIP\n"
            "/cancelar — Cancelar lo que estés haciendo\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_senal = ConversationHandler(
        entry_points=[CommandHandler("senal", senal_inicio)],
        states={
            ESPERANDO_VIDEO:   [MessageHandler(filters.VIDEO | filters.PHOTO | filters.ANIMATION, senal_recibir_video)],
            ESPERANDO_LINK1:   [MessageHandler(filters.TEXT & ~filters.COMMAND, senal_recibir_link1)],
            ESPERANDO_LINK2:   [MessageHandler(filters.TEXT & ~filters.COMMAND, senal_recibir_link2)],
            ESPERANDO_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, senal_publicar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    conv_anuncio = ConversationHandler(
        entry_points=[CommandHandler("anuncio", anuncio_inicio)],
        states={
            AN_VIDEO:   [MessageHandler(filters.VIDEO | filters.PHOTO | filters.ANIMATION, anuncio_recibir_video)],
            AN_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, anuncio_publicar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_senal)
    app.add_handler(conv_anuncio)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu",  menu))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    threading.Thread(target=run_health_server, daemon=True).start()
    logger.info(f"🤖 {BOT_NAME} iniciado.")
    import asyncio
    asyncio.run(app.run_polling(allowed_updates=Update.ALL_TYPES))


if __name__ == "__main__":
    main()
