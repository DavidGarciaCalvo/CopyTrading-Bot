from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import Config
from runtime.state_manager import RuntimeStateManager
from runtime.command_manager import RuntimeCommandManager


runtime_state = RuntimeStateManager()
runtime_commands = RuntimeCommandManager()


def usuario_autorizado(update: Update) -> bool:
    if update.effective_chat is None:
        return False

    return update.effective_chat.id == Config.TELEGRAM_ALLOWED_CHAT_ID


async def respuesta_no_autorizado(update: Update):
    if update.message:
        await update.message.reply_text("❌ No autorizado.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update):
        await respuesta_no_autorizado(update)
        return

    mensaje = (
        "🤖 Bot de control remoto activo.\n\n"
        "Comandos disponibles:\n"
        "/status - ver estado del bot principal\n"
        "/stopbot - parar el bot principal\n"
        "/closeall - cerrar todas las posiciones\n"
        "/help - mostrar esta ayuda"
    )
    await update.message.reply_text(mensaje)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update):
        await respuesta_no_autorizado(update)
        return

    mensaje = (
        "📋 Comandos disponibles:\n\n"
        "/status - ver estado actual\n"
        "/stopbot - parar el bot principal\n"
        "/closeall - cerrar todas las posiciones"
    )
    await update.message.reply_text(mensaje)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update):
        await respuesta_no_autorizado(update)
        return

    state = runtime_state.read_current_state()

    if not state:
        await update.message.reply_text(
            "⚪ No hay estado runtime disponible todavía.\n"
            "Probablemente el bot principal no se ha ejecutado aún."
        )
        return

    running = state.get("running", False)
    status_text = "🟢 RUNNING" if running else "🔴 STOPPED"

    mensaje = (
        f"Estado: {status_text}\n"
        f"PID: {state.get('pid')}\n"
        f"Started at: {state.get('started_at')}\n"
        f"Last heartbeat: {state.get('last_heartbeat')}\n"
        f"Last cycle OK: {state.get('last_cycle_ok')}\n"
        f"Open positions: {state.get('open_positions')}\n"
        f"Balance actual: {state.get('balance_actual')} USDT\n"
        f"Last error: {state.get('last_error')}\n"
        f"Shutdown reason: {state.get('shutdown_reason')}"
    )

    await update.message.reply_text(mensaje)


async def stopbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update):
        await respuesta_no_autorizado(update)
        return

    state = runtime_state.read_current_state()
    if state and not state.get("running", False):
        await update.message.reply_text("⚪ El bot principal ya está parado.")
        return

    command = runtime_commands.add_command("stop")
    await update.message.reply_text(
        f"🛑 Comando STOP enviado correctamente.\n"
        f"ID comando: {command['id']}"
    )


async def closeall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_autorizado(update):
        await respuesta_no_autorizado(update)
        return

    state = runtime_state.read_current_state()
    if state and not state.get("running", False):
        await update.message.reply_text(
            "⚠️ El bot principal está parado.\n"
            "No puede procesar el comando closeall ahora mismo."
        )
        return

    command = runtime_commands.add_command("closeall")
    await update.message.reply_text(
        f"🧨 Comando CLOSEALL enviado correctamente.\n"
        f"ID comando: {command['id']}"
    )


def main():
    app = Application.builder().token(Config.TELEGRAM_CONTROL_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stopbot", stopbot))
    app.add_handler(CommandHandler("closeall", closeall))

    print("🤖 Telegram control bot corriendo...")
    app.run_polling()


if __name__ == "__main__":
    main()