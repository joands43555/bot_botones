"""
Bot de Telegram — Video + 4 Botones por publicación
Flujo admin: /señal → video → link1 → link2 → caption → publica
"""

import logging
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
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Estados del flujo de publicación
(
    ESPERANDO_VIDEO,
    ESPERANDO_LINK1,
    ESPERANDO_LINK2,
    ESPERANDO_CAPTION,
) = range(4)


# ── Teclado por publicación (links dinámicos) ──────────────
def build_keyboard(link1: str, link2: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"👉 {BTN_OPCION1}", url=link1),
            InlineKeyboardButton(f"👉 {BTN_OPCION2}", url=link2),
        ],
        [
            InlineKeyboardButton("💎 VIP via PayPal",    url=PAYPAL_URL),
            InlineKeyboardButton("⭐ VIP via Estrellas",  callback_data="buy_stars"),
        ],
        [
            InlineKeyboardButton("📋 TUTORIAL",           url=TUTORIAL_URL),
        ],
    ])


# ── Teclado fijo para /start y /menu ──────────────────────
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 VIP via PayPal",    url=PAYPAL_URL),
            InlineKeyboardButton("⭐ VIP via Estrellas",  callback_data="buy_stars"),
        ],
        [
            InlineKeyboardButton("📋 TUTORIAL",           url=TUTORIAL_URL),
        ],
    ])


# ── /start ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_keyboard(), parse_mode="HTML")


# ── /menu ──────────────────────────────────────────────────
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"<b>📌 {BOT_NAME}</b>\nElige una opción:",
        reply_markup=main_keyboard(), parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════
#  FLUJO DE PUBLICACIÓN  /señal
# ══════════════════════════════════════════════════════════

async def senal_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Sin permiso.")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        "🎬 <b>Paso 1/4 — Video</b>\n\n"
        "Envía el <b>video</b> que quieres publicar.\n\n"
        "/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_VIDEO


async def senal_recibir_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message

    # Acepta video, foto o GIF (animation)
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
        await msg.reply_text("❌ Envía un video, foto o GIF. /cancelar para salir.")
        return ESPERANDO_VIDEO

    await msg.reply_text(
        f"✅ Video recibido.\n\n"
        f"🔗 <b>Paso 2/4 — Link OPCIÓN 1 ({BTN_OPCION1})</b>\n\n"
        f"Pega el link de Linkvertise para el botón <b>{BTN_OPCION1}</b>:\n\n"
        f"/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_LINK1


async def senal_recibir_link1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("❌ Link inválido (debe empezar con https://). Intenta de nuevo.\n/cancelar para salir.")
        return ESPERANDO_LINK1

    context.user_data["link1"] = link
    await update.message.reply_text(
        f"✅ Link 1 guardado.\n\n"
        f"🔗 <b>Paso 3/4 — Link OPCIÓN 2 ({BTN_OPCION2})</b>\n\n"
        f"Pega el link de Linkvertise para el botón <b>{BTN_OPCION2}</b>:\n\n"
        f"/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_LINK2


async def senal_recibir_link2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("❌ Link inválido. Intenta de nuevo.\n/cancelar para salir.")
        return ESPERANDO_LINK2

    context.user_data["link2"] = link
    await update.message.reply_text(
        "✏️ <b>Paso 4/4 — Descripción</b>\n\n"
        "Escribe el texto que irá debajo del video:\n\n"
        "<i>Ejemplo:\n"
        "🔥 Lucia Rossi\n"
        "#LuciaRossi</i>\n\n"
        "/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_CAPTION


async def senal_publicar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    caption  = update.message.text.strip()
    link1    = context.user_data["link1"]
    link2    = context.user_data["link2"]
    media_type = context.user_data["media_type"]
    file_id  = context.user_data["file_id"]

    full_caption = f"{caption}\n\n{SIGNAL_FOOTER}"
    keyboard = build_keyboard(link1, link2)

    if media_type == "video":
        await update.message.reply_video(
            video=file_id, caption=full_caption,
            reply_markup=keyboard, parse_mode="HTML",
        )
    elif media_type == "photo":
        await update.message.reply_photo(
            photo=file_id, caption=full_caption,
            reply_markup=keyboard, parse_mode="HTML",
        )
    elif media_type == "animation":
        await update.message.reply_animation(
            animation=file_id, caption=full_caption,
            reply_markup=keyboard, parse_mode="HTML",
        )

    logger.info(f"✅ Publicado por {update.effective_user.username}")
    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Publicación cancelada.")
    return ConversationHandler.END


# ── Pago con Stars ─────────────────────────────────────────
async def buy_stars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=f"⭐ Acceso VIP — {BOT_NAME}",
        description="Acceso ilimitado al canal VIP. Pago seguro con Telegram Stars. ✅",
        payload="vip_stars_payment",
        currency="XTR",
        prices=[LabeledPrice("VIP Access", STARS_PRICE)],
        provider_token="",
    )

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"✅ <b>¡Pago confirmado!</b>\n\n"
        f"Bienvenido al VIP, <b>{user.first_name}</b> 🎉\n\n"
        f"👉 {VIP_CHANNEL_LINK}",
        parse_mode="HTML",
    )


# ── /ayuda ─────────────────────────────────────────────────
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id in ADMIN_IDS
    text = (
        f"<b>📖 {BOT_NAME}</b>\n\n"
        "/start — Bienvenida\n/menu — Menú\n/ayuda — Comandos\n"
    )
    if is_admin:
        text += "\n🔑 <b>Admin:</b>\n/señal — Publicar video con botones\n/cancelar — Cancelar\n"
    await update.message.reply_text(text, parse_mode="HTML")


# ── Main ───────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("senal", senal_inicio),
            CommandHandler("señal", senal_inicio),
        ],
        states={
            ESPERANDO_VIDEO:   [MessageHandler(filters.VIDEO | filters.PHOTO | filters.ANIMATION, senal_recibir_video)],
            ESPERANDO_LINK1:   [MessageHandler(filters.TEXT & ~filters.COMMAND, senal_recibir_link1)],
            ESPERANDO_LINK2:   [MessageHandler(filters.TEXT & ~filters.COMMAND, senal_recibir_link2)],
            ESPERANDO_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, senal_publicar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu",  menu))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CallbackQueryHandler(buy_stars_callback, pattern="^buy_stars$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    logger.info(f"🤖 {BOT_NAME} iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
