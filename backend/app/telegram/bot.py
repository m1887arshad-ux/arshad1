"""
Telegram bot: receives messages, creates DRAFT actions only. No execution.
Runs in same container as FastAPI.
"""
import threading
from typing import Optional

from telegram.ext import Application, MessageHandler, filters

from app.core.config import settings
from app.telegram.handlers import handle_message

_bot_app: Optional[Application] = None


def _run_bot():
    global _bot_app
    _bot_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    _bot_app.run_polling(drop_pending_updates=True)


def start_bot_background():
    """Start Telegram bot in background thread. No-op if no token."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    t = threading.Thread(target=_run_bot, daemon=True)
    t.start()


def stop_bot_background():
    """Stop polling. Called on FastAPI shutdown."""
    global _bot_app
    if _bot_app and _bot_app.updater:
        try:
            _bot_app.updater.stop()
        except Exception:
            pass
