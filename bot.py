"""
Bot de Telegram — Publica video con botones directo en canales
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
    CHANNEL_IDS,
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

(ESPERANDO_VIDEO, ESPERANDO_LINK1, ESPERANDO_LINK2, ESPERANDO_CAPTION) = range(4)


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_keyboard(), parse_mode="HTML")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"<b>📌 {BOT_NAME}</b>\nElige una opción:",
        reply_markup=main_keyboard(), parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════
#  FLUJO /senal
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
        f"✅ Video recibido.\n\n"
        f"🔗 <b>Paso 2/4 — Link {BTN_OPCION1}</b>\n\n"
        f"Pega el link de Linkvertise para el botón <b>{BTN_OPCION1}</b>:\n\n/cancelar para salir.",
        parse_mode="HTML",
    )
    return ESPERANDO_LINK1


async def senal_recibir_link1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("❌ Link inválido. Debe empezar con https://\n/cancelar para salir.")
        return ESPERANDO_LINK1

    context.user_data["link1"] = link
    await update.message.reply_text(
        f"✅ Link 1 guardado.\n\n"
        f"🔗 <b>Paso 3/4 — Link {BTN_OPCION2}</b>\n\n"
        f"Pega el link de Linkvertise para el botón <b>{BTN_OPCION2}</b>:\n\n/cancelar para salir.",
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
                await context.bot.send_video(
                    chat_id=channel_id, video=file_id,
                    caption=full_caption, reply_markup=keyboard, parse_mode="HTML"
                )
            elif media_type == "photo":
                await context.bot.send_photo(
                    chat_id=channel_id, photo=file_id,
                    caption=full_caption, reply_markup=keyboard, parse_mode="HTML"
                )
            elif media_type == "animation":
                await context.bot.send_animation(
                    chat_id=channel_id, animation=file_id,
                    caption=full_caption, reply_markup=keyboard, parse_mode="HTML"
                )
            publicados += 1
            logger.info(f"✅ Publicado en canal {channel_id}")
        except Exception as e:
            logger.error(f"❌ Error publicando en {channel_id}: {e}")

    await update.message.reply_text(
        f"✅ <b>Publicado en {publicados}/{len(CHANNEL_IDS)} canales</b> con todos los botones.",
        parse_mode="HTML"
    )

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
        f"✅ <b>¡Pago confirmado!</b>\n\nBienvenido al VIP, <b>{user.first_name}</b> 🎉\n\n👉 {VIP_CHANNEL_LINK}",
        parse_mode="HTML",
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_admin = update.effective_user.id in ADMIN_IDS
    text = f"<b>📖 {BOT_NAME}</b>\n\n/start — Bienvenida\n/menu — Menú\n/ayuda — Comandos\n"
    if is_admin:
        text += "\n🔑 <b>Admin:</b>\n/senal — Publicar video en los canales\n/cancelar — Cancelar\n"
    await update.message.reply_text(text, parse_mode="HTML")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("senal", senal_inicio)],
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
